import React, { useCallback, useEffect, useRef, useState } from 'react';
import TestRenderer, { act } from 'react-test-renderer';
import { MemoryRouter } from 'react-router-dom';
import { test, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import axios from 'axios';
import api, { onAuthSessionExpired } from '../src/api';
import CaseVisitOverview from '../src/components/CaseVisitOverview';
import CaseLabRangeReview from '../src/components/CaseLabRangeReview';
import CaseLabComparison from '../src/components/CaseLabComparison';
import { readOverview } from '../src/visitOverview';
import { readRangeReview } from '../src/labRangeReview';
import { itemSelection, previewComparison, readComparison } from '../src/labComparison';
import overviewFixture from '../../tests/fixtures/clinical_case_overview_cw_b10_cases.json';
import rangeFixture from '../../tests/fixtures/clinical_lab_range_review_cw_b11_cases.json';
import comparisonFixture from '../../tests/fixtures/clinical_lab_comparison_cw_b12_cases.json';

const owner = 'synthetic-owner', summaryUrl = '/api/diagnostic-data/cases/1/summary';
const variants = [
  { name: 'overview', Panel: CaseVisitOverview, suffix: '/visit-overview', refresh: '刷新就诊资料总览', fixture: overviewFixture.overview, read: readOverview },
  { name: 'range', Panel: CaseLabRangeReview, suffix: '/lab-range-review', refresh: '刷新检验区间核对', fixture: rangeFixture.review, read: readRangeReview },
  { name: 'comparison', Panel: CaseLabComparison, suffix: '/lab-comparison', refresh: '刷新检验前后对照', fixture: comparisonFixture.review, read: readComparison },
];
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };
const tick = () => new Promise(resolve => setTimeout(resolve, 0));
const response = (config, data) => ({ config, status: 200, data });
let renderer, token, adapter, requests, listeners, docListeners, unsubscribe, selected;
const output = () => JSON.stringify(renderer.toJSON());
const button = label => renderer.root.findAllByType('button').find(node => node.children.join('') === label);
const emit = async (events, name, event = {}) => { for (const callback of [...(events[name] || [])]) await callback(event); };
const comparisonRequest = () => {
  const saved = comparisonFixture.review;
  return { snapshot: saved.snapshot, a: itemSelection(saved.reports[0], saved.reports[0].items[3]),
    b: itemSelection(saved.reports[1], saved.reports[1].items[3]), doctor_confirmed: true };
};
const comparisonResult = request => ({ ...request, schema: comparisonFixture.review.schema, rules: comparisonFixture.review.rules,
  case_id: 1, read_at: comparisonFixture.review.read_at, read_only: true, writes_database: false, includes_unsaved_drafts: false,
  can_calculate: true, reasons: [], reference_changed: true,
  delta: { value: comparisonFixture.expected_deltas[3], state: 'increase', unit: 'mmol/L' } });

function Harness({ Panel }) {
  const live = useRef(true), [expired, setExpired] = useState(false);
  const isSessionCurrent = useCallback(() => live.current, []);
  useEffect(() => onAuthSessionExpired(() => { live.current = false; setExpired(true); }), []);
  return <MemoryRouter><Panel caseId={1} requestToken={owner} sessionExpired={expired}
    isSessionCurrent={isSessionCurrent} onSelect={() => { selected++; }} /></MemoryRouter>;
}
beforeEach(() => {
  token = owner; requests = []; listeners = {}; docListeners = {}; selected = 0;
  global.localStorage = { getItem: () => token, removeItem: () => { token = null; } };
  global.alert = () => {};
  global.window = { addEventListener: (key, fn) => (listeners[key] ??= new Set()).add(fn), removeEventListener: (key, fn) => listeners[key]?.delete(fn) };
  global.document = { hidden: false, addEventListener: (key, fn) => (docListeners[key] ??= new Set()).add(fn), removeEventListener: (key, fn) => docListeners[key]?.delete(fn) };
  adapter = async config => {
    if (config.url === summaryUrl) throw Object.assign(Error('expired'), { config, response: { status: 401, data: {} } });
    if (config.url.endsWith('/lab-comparison/preview')) return response(config, comparisonResult(JSON.parse(config.data)));
    const variant = variants.find(value => config.url.endsWith(value.suffix));
    if (variant) return response(config, structuredClone(variant.fixture));
    throw Error('Unexpected request: ' + config.url);
  };
  api.defaults.adapter = config => { requests.push(config); return adapter(config); };
});
afterEach(() => { if (renderer) act(() => renderer.unmount()); renderer = null; unsubscribe?.(); unsubscribe = null; });
async function mount(Panel) { await act(async () => { renderer = TestRenderer.create(<Harness Panel={Panel} />); }); }
async function expire() { await act(async () => { await assert.rejects(api.get(summaryUrl)); }); assert.equal(token, null); }

for (const variant of variants) {
  test(`${variant.name}: parallel summary expiry removes derived data and rejects late reads after same-token restoration`, async () => {
    await mount(variant.Panel);
    assert(output().includes(variant.fixture.identity.patient_name), 'the initial read must really be displayed');
    const refresh = button(variant.refresh).props.onClick, gate = deferred(), normal = adapter;
    adapter = config => config.url.endsWith(variant.suffix) ? gate.promise.then(() => normal(config)) : normal(config);
    let pending;
    await act(async () => { pending = refresh(); await tick(); });
    await expire(); token = owner;
    const count = requests.length;
    await act(async () => {
      await refresh(); await emit(listeners, 'focus'); await emit(listeners, 'storage', { key: 'token' });
      await emit(docListeners, 'visibilitychange'); gate.resolve(); await pending;
    });
    assert.equal(requests.length, count, 'retired refresh/focus/visibility/storage must not read again');
    assert(!output().includes(variant.fixture.identity.patient_name));
    assert.doesNotMatch(output(), /正在读取|正在核对保存版本/);
    assert.equal(button(variant.refresh).props.disabled, true);
    assert.equal(selected, 0);
  });
}

for (const variant of [...variants, { name: 'comparison preview', suffix: '/lab-comparison/preview',
  read: (_caseId, tokenValue, signal, current) => previewComparison(comparisonFixture.review, comparisonRequest(), tokenValue, signal, current) }]) {
  test(`${variant.name}: an Axios-queued request cannot dispatch after expiry even if the identical credential is restored`, async () => {
    let live = true;
    unsubscribe = onAuthSessionExpired(() => { live = false; });
    const gate = deferred();
    const interceptor = api.interceptors.request.use(async config => {
      if (config.url.endsWith(variant.suffix)) await gate.promise;
      return config;
    });
    try {
      const pending = variant.read(1, owner, undefined, () => live);
      const rejected = assert.rejects(pending, error => axios.isCancel(error));
      await tick(); await assert.rejects(api.get(summaryUrl)); token = owner;
      gate.resolve(); await rejected;
      assert.equal(requests.filter(config => config.url.endsWith(variant.suffix)).length, 0);
    } finally { gate.resolve(); api.interceptors.request.eject(interceptor); }
  });
}

test('comparison: late preview cannot restore a calculable result or select a document after parallel expiry', async () => {
  await mount(CaseLabComparison);
  for (const [label, value] of [['对照报告 A', '1'], ['对照报告 B', '2'], ['对照项目 A', '4'], ['对照项目 B', '4']]) {
    act(() => renderer.root.findByProps({ 'aria-label': label }).props.onChange({ target: { value } }));
  }
  act(() => renderer.root.findByProps({ 'aria-label': '确认方法与采样条件可比' }).props.onChange({ target: { checked: true } }));
  const run = button('核对条件并预览数值差').props.onClick, gate = deferred(), normal = adapter;
  adapter = config => config.url.endsWith('/lab-comparison/preview') ? gate.promise.then(() => normal(config)) : normal(config);
  let pending;
  await act(async () => { pending = run(); await tick(); });
  await expire(); token = owner;
  const count = requests.length;
  await act(async () => { await run(); gate.resolve(); await pending; });
  assert.equal(requests.length, count);
  assert.doesNotMatch(output(), /差值 B−A|纳入本次文书核对|正在核对保存版本/);
  assert.equal(selected, 0);
});

test('comparison: a completed preview and its captured select handler remain retired after expiry', async () => {
  await mount(CaseLabComparison);
  for (const [label, value] of [['对照报告 A', '1'], ['对照报告 B', '2'], ['对照项目 A', '4'], ['对照项目 B', '4']]) {
    act(() => renderer.root.findByProps({ 'aria-label': label }).props.onChange({ target: { value } }));
  }
  act(() => renderer.root.findByProps({ 'aria-label': '确认方法与采样条件可比' }).props.onChange({ target: { checked: true } }));
  await act(async () => { await button('核对条件并预览数值差').props.onClick(); });
  assert.match(output(), /差值 B−A/);
  const choose = button('纳入本次文书核对').props.onClick;
  await expire(); token = owner;
  const count = requests.length;
  await act(async () => { choose(); await emit(listeners, 'focus'); });
  assert.equal(requests.length, count);
  assert.doesNotMatch(output(), /差值 B−A|纳入本次文书核对|正在核对保存版本/);
  assert.equal(selected, 0);
});
