import React, { useCallback, useEffect, useRef, useState } from 'react';
import TestRenderer, { act } from 'react-test-renderer';
import { test, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { createHash, webcrypto } from 'node:crypto';
import axios from 'axios';
import api, { onAuthSessionExpired } from '../src/api';
import CaseLabResults from '../src/components/CaseLabResults';
import CaseImagingRecords from '../src/components/CaseImagingRecords';
import CaseAttachments from '../src/components/CaseAttachments';
import { manualLabClient } from '../src/manualLabResults';
import { manualImagingClient } from '../src/manualImagingRecords';
import { attachmentClient } from '../src/caseAttachments';

const owner = 'synthetic-owner';
const attachmentId = 'a'.repeat(64), version = 'b'.repeat(64);
const bytes = new Uint8Array([1, 2, 3]).buffer;
const source = { id: attachmentId, name: 'synthetic.pdf', mime: 'application/pdf', size: 3,
  sha256: createHash('sha256').update(new Uint8Array(bytes)).digest('hex'), state: 'active',
  metadata: { title: '合成原件', kind: 'lab', taken_at: '', reported_at: '', source: '', note: '' } };
const raw = '  原文 café 🐾\n<report> & {{literal}}  ';
const summaryUrl = '/api/diagnostic-data/cases/1/summary';
let renderer, token, adapter, requests, changed, downloads, unsubscribe;
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };
const response = (config, data) => ({ config, status: 200, data });
const tick = () => new Promise(resolve => setTimeout(resolve, 0));
const text = () => JSON.stringify(renderer.toJSON());
const button = label => renderer.root.findAllByType('button').find(n => n.children.join('') === label);
const field = label => renderer.root.findByProps({ 'aria-label': label });
const click = async label => { assert(button(label) && !button(label).props.disabled, label); await act(async () => { await button(label).props.onClick(); }); };
const change = (label, value) => act(() => field(label).props.onChange({ target: { value } }));
const check = label => act(() => field(label).props.onChange({ target: { checked: true } }));
const codes = () => renderer.root.findAllByType('code').map(n => n.children.join(''));
const originals = () => renderer.root.findAllByType('pre').map(n => n.children.join('')).join('\n');

// The same contract as CaseDetail: the listener retires its live lease before
// React renders the expired state, while preserving the mounted panel instance.
function ExpiryHarness({ Panel }) {
  const lease = useRef(true);
  const [expired, setExpired] = useState(false);
  const isSessionCurrent = useCallback(() => lease.current, []);
  useEffect(() => onAuthSessionExpired(() => { lease.current = false; setExpired(true); }), []);
  return <Panel caseId={1} requestToken={owner} sessionExpired={expired}
    isSessionCurrent={isSessionCurrent} onChanged={() => { changed++; }} />;
}

beforeEach(() => {
  token = owner; requests = []; changed = 0; downloads = 0;
  Object.defineProperty(globalThis, 'crypto', { configurable: true, value: webcrypto });
  global.localStorage = { getItem: () => token, removeItem: () => { token = null; }, setItem() { throw Error('Drafts must remain in memory'); } };
  global.sessionStorage = { setItem() { throw Error('Drafts must remain in memory'); } };
  global.window = { confirm: () => true, addEventListener() {}, removeEventListener() {} };
  global.document = { addEventListener() {}, removeEventListener() {}, createElement() { return { click() { downloads++; } }; } };
  global.alert = () => {};
  adapter = async config => {
    const current = { case_id: 1, patient_name: '合成病例', species: 'dog', case_token: version };
    if (config.url === summaryUrl) throw Object.assign(Error('expired'), { config, response: { status: 401, data: { detail: 'expired' } } });
    if (/\/(manual-lab|manual-imaging)$/.test(config.url)) return response(config, { ...current, sources: [source], reports: [] });
    if (config.url.endsWith('/attachments')) return response(config, { ...current, items: [source], legacy_count: 0 });
    if (config.url.includes('/content?')) return response(config, bytes);
    if (config.url.endsWith('/preview')) {
      const body = JSON.parse(config.data);
      return response(config, { ...current, case: current, identity: {}, source, operation: body.operation,
        data: body.data, reason: body.reason, preview_token: version, proposed: { ...source, metadata: body.metadata } });
    }
    if (config.url.includes('/uploads/')) return response(config, { state: 'pending', attachment: source });
    if (config.url.endsWith('/confirm') || config.url.includes('/requests/')) return response(config, { state: 'committed', attachment: source });
    throw Error('Unexpected request ' + config.url);
  };
  api.defaults.adapter = config => { requests.push(config); return adapter(config); };
});
afterEach(() => { if (renderer) act(() => renderer.unmount()); renderer = null; unsubscribe?.(); unsubscribe = null; });

const variants = [
  { name: 'laboratory confirm', Panel: CaseLabResults, write: '/confirm', submit: '确认保存检验记录', clear: '放弃本页检验草稿', read: '核对检验保存结果', review: '整份检验核对',
    async prepare() {
      await click('录入检验报告'); change('检验原件', attachmentId); change('报告标题', raw);
      change('项目 1 项目名称', '合成项目'); change('项目 1 结果原文', '0.0100'); change('项目 1 页码或原件位置', '第1页');
      check('已核对项目 1'); await click('核对整份检验记录'); check('已核对整份检验记录');
      return () => field('报告标题').props.onChange({ target: { value: 'SHOULD NOT REPLACE' } });
    } },
  { name: 'imaging confirm', Panel: CaseImagingRecords, write: '/confirm', submit: '确认保存影像记录', clear: '放弃本页影像草稿', read: '核对影像保存结果', review: '整份影像核对',
    async prepare() {
      await click('录入影像报告'); change('影像原件', attachmentId); change('报告标题', '合成报告'); change('检查部位', '胸部');
      change('检查时间（含时区）', '2026-10-07T09:30:00+08:00'); change('所见原文', raw); change('页码或原件位置', '第1页');
      check('已核对所见原文'); check('已核对结论原文'); await click('核对整份影像记录'); check('已核对整份影像记录');
      return () => field('所见原文').props.onChange({ target: { value: 'SHOULD NOT REPLACE' } });
    } },
  { name: 'attachment confirm', Panel: CaseAttachments, write: '/confirm', submit: '确认资料操作', clear: '取消本次操作', read: '核对操作结果', review: '资料关联核对',
    async prepare() {
      await click('更正资料信息'); const note = renderer.root.findByType('textarea');
      act(() => note.props.onChange({ target: { value: raw } })); await click('核对资料关联');
      act(() => renderer.root.findAllByType('input').find(n => n.props.type === 'checkbox').props.onChange({ target: { checked: true } }));
      return () => renderer.root.findByType('textarea').props.onChange({ target: { value: 'SHOULD NOT REPLACE' } });
    } },
  { name: 'attachment upload', Panel: CaseAttachments, write: '/uploads/', submit: '上传待核对原件', read: '核对操作结果',
    async prepare() {
      const select = renderer.root.findAllByType('input').find(n => n.props.type === 'file').props.onChange;
      act(() => select({ target: { files: [{ name: '合成原文 café.png', size: 3 }] } }));
      return () => select({ target: { files: [{ name: 'SHOULD NOT REPLACE.png', size: 3 }] } });
    } },
];
const isWrite = (config, variant) => config.method === 'post' && config.url.includes(variant.write);
async function expire() { await act(async () => { await assert.rejects(api.get(summaryUrl)); }); assert.equal(token, null); }
function retained(variant, id) {
  assert(codes().includes(id), 'the original request locator remains selectable');
  assert(originals().includes(variant.name.includes('upload') ? '合成原文 café.png' : raw), 'copyable originals retain exact spaces, newline, and literals');
  assert.doesNotMatch(text(), /正在处理…|SHOULD NOT REPLACE/);
  if (variant.review) assert.equal(renderer.root.findAllByProps({ 'aria-label': variant.review }).length, 0);
  assert.equal(button(variant.read).props.disabled, true);
  assert.equal(changed, 0); assert.equal(downloads, 0);
}

for (const variant of variants) {
  test(`${variant.name}: a parallel summary 401 retains the in-flight locator and original, and retires late callbacks`, async () => {
    await act(async () => { renderer = TestRenderer.create(<ExpiryHarness Panel={variant.Panel} />); });
    const mutate = await variant.prepare(), discard = variant.clear ? button(variant.clear).props.onClick : null;
    const submit = button(variant.submit).props.onClick, gate = deferred(), normal = adapter;
    adapter = config => isWrite(config, variant) ? gate.promise.then(() => normal(config)) : normal(config);
    let pending;
    await act(async () => { pending = submit(); await tick(); });
    assert.match(text(), /正在处理…/);
    const write = requests.find(config => isWrite(config, variant)); assert(write);
    const id = variant.write === '/uploads/' ? write.url.split('/').at(-1) : JSON.parse(write.data).request_id;
    assert(codes().includes(id), 'request locator exists before a write response');
    await expire(); retained(variant, id);
    const count = requests.length;
    token = owner; // Restoring the identical credential cannot revive the retired page.
    await act(async () => { mutate(); discard?.(); await submit(); await button(variant.read).props.onClick(); gate.resolve(); await pending; });
    retained(variant, id);
    assert.equal(requests.length, count, 'no readback or repeat write occurs after expiry');
    assert.equal(requests.filter(config => isWrite(config, variant)).length, 1);
    assert.doesNotMatch(text(), /记录已保存|资料操作已保存|操作结果已回读|原件已暂存/);
  });

  test(`${variant.name}: an already unknown result survives a later summary 401 without clearing or resubmitting`, async () => {
    await act(async () => { renderer = TestRenderer.create(<ExpiryHarness Panel={variant.Panel} />); });
    const mutate = await variant.prepare(), normal = adapter;
    adapter = config => isWrite(config, variant) || config.url.includes('/requests/') || config.url.includes('/uploads/') ? Promise.reject(Error('offline')) : normal(config);
    await click(variant.submit);
    const id = codes()[0]; assert(id); assert.match(text(), /结果未知/);
    await expire(); retained(variant, id);
    const count = requests.length; token = owner;
    await act(async () => { mutate(); await button(variant.read).props.onClick(); });
    retained(variant, id); assert.equal(requests.length, count);
    assert.equal(requests.filter(config => isWrite(config, variant)).length, 1);
  });
}

for (const [name, Panel, prepare, download] of [
  ['laboratory', CaseLabResults, async () => { await click('录入检验报告'); change('检验原件', attachmentId); }, '打开核对原件'],
  ['imaging', CaseImagingRecords, async () => { await click('录入影像报告'); change('影像原件', attachmentId); }, '打开核对原件'],
  ['attachment', CaseAttachments, async () => {}, '下载原件'],
]) {
  test(`${name}: a late original-file response after summary 401 cannot create a download`, async () => {
    await act(async () => { renderer = TestRenderer.create(<ExpiryHarness Panel={Panel} />); }); await prepare();
    const gate = deferred(), normal = adapter;
    adapter = config => config.url.includes('/content?') ? gate.promise.then(() => normal(config)) : normal(config);
    let pending; await act(async () => { pending = button(download).props.onClick(); await tick(); });
    await expire(); assert.doesNotMatch(text(), /正在处理…/); token = owner;
    await act(async () => { gate.resolve(); await pending; });
    assert.equal(downloads, 0); assert.equal(changed, 0);
  });
}

for (const [name, client] of [['laboratory', manualLabClient], ['imaging', manualImagingClient], ['attachment', attachmentClient]]) {
  test(`${name} helper cancels a queued write when a parallel 401 retires its lease, even after same-token restoration`, async () => {
    let live = true;
    unsubscribe = onAuthSessionExpired(() => { live = false; });
    const gate = deferred();
    const interceptor = api.interceptors.request.use(async config => {
      if (config.url.endsWith('/confirm')) await gate.promise;
      return config;
    });
    try {
      const pending = client(1, owner, undefined, () => live)('post', '/confirm', { request_id: 'queued-synthetic' });
      const rejected = assert.rejects(pending, error => axios.isCancel(error));
      await tick(); await assert.rejects(api.get(summaryUrl)); token = owner;
      gate.resolve(); await rejected;
      assert.equal(requests.filter(config => config.url.endsWith('/confirm')).length, 0);
    } finally { gate.resolve(); api.interceptors.request.eject(interceptor); }
  });
}
