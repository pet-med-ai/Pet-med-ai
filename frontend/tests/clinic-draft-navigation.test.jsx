import React from 'react';
import TestRenderer, { act } from 'react-test-renderer';
import { test, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import ClinicReadPilot from '../src/pages/ClinicReadPilot';
import { requestHash } from '../src/pages/TreatmentWorkspace';

// Both production components are mounted. Only HTTP, browser storage and the
// native confirmation dialog are simulated.
const scopes = ['A', 'B'].map(id => ({
  org_id: 'org', org_name: '合成机构', clinic_id: id, clinic_name: '合成院区 ' + id,
  permissions: ['clinical.read', 'patient.demographics.read'],
}));
const localText = '尚未保存的原文 café 🐾\n{{literal}}';
const response = (body, status = 200) => ({ ok: status < 400, status, json: async () => body });
const record = id => ({ id, patient_name: '合成病例 ' + id, species: 'dog' });
const planId = id => '00000000-0000-4000-8000-' + String(id).padStart(12, '0');
function aggregate(id, version = 1, assessment = '服务端草稿 ' + id) {
  return { actor_id: 7, plan: { id: planId(id) }, draft_etag: '"draft:' + version + '"',
    draft: { draft_version: version, content: { schema: 'treatment-content-v1', diagnoses: [], assessment,
      linked_orders: [], provenance: { ai_generation_ids: [], voice_transcript_revision_ids: [] },
      treatment: { goals: [], management_text: '', monitoring_text: '', followup_text: '' } } },
    revisions: [], reviews: [], signatures: [], events: [], allowed_actions: { edit: true }, policy: {} };
}
async function draftReceipt(options, id, state) {
  const operation = 'draft.save';
  const request_hash = await requestHash({
    actor_id: 7, scope: { org_id: 'org', clinic_id: 'A', case_id: id }, operation,
    target: 'draft', precondition: options.headers['If-Match'] ?? options.headers['If-None-Match'], body: JSON.parse(options.body),
  });
  const receipt = { state, operation, request_hash, idempotency_key: options.headers['Idempotency-Key'] };
  if (state === 'committed') {
    return { ...receipt, plan_id: planId(id), audit_id: '10000000-0000-4000-8000-000000000001',
      draft_version: 2, draft_etag: '"draft:2"', etag: '"plan:2"' };
  }
  return receipt;
}
const pendingSave = async (options, id) => response(await draftReceipt(options, id, 'pending'), 202);
let renderer, calls, prompts, allowLeave, onDetail, onTreatment, onSave, stored, savedAggregate;
let oldFetch, oldWindow, oldStorage;
const byLabel = name => renderer.root.findByProps({ 'aria-label': name });
const button = name => renderer.root.findAllByType('button').find(node => node.children.join('') === name);
const output = () => JSON.stringify(renderer.toJSON());
const editor = () => byLabel('治疗评估').props.value;
const writeCalls = () => calls.filter(c => c.method !== 'GET' && c.url.includes('/organizations/'));
const commandCalls = () => calls.filter(c => c.url.includes('/commands/'));
const detailHeading = () => byLabel('病例详情').findAllByType('h2')[0].children.join('');
const listCalls = () => calls.filter(c => c.url.includes('/cases?'));
const click = name => act(async () => { await button(name).props.onClick(); });
const select = (label, value) => act(async () => { await byLabel(label).props.onChange({target: {value}}); });
const edit = (label, value) => act(() => { byLabel(label).props.onChange({target: {value}}); });
function rowClick(id) {
  const row = renderer.root.findAllByType('tr').find(r => r.findAllByType('td')[0]?.children.join('') === '#' + id);
  return row.findByType('button').props.onClick();
}
function typeNumber(id) {
  act(() => { renderer.root.findByProps({inputMode:'numeric'}).props.onChange({target:{value:String(id)}}); });
}
function submitNumber() {
  return byLabel('按病例号查阅').props.onSubmit({preventDefault() {}});
}
async function lookup(id) {
  typeNumber(id);
  await act(async () => { await submitNumber(); });
}
async function openChart(expectedAssessment = '服务端草稿 101') {
  await act(async () => { renderer = TestRenderer.create(<ClinicReadPilot />); });
  act(() => {
    renderer.root.findByProps({type:'email'}).props.onChange({target:{value:'doctor@example.invalid'}});
    renderer.root.findByProps({type:'password'}).props.onChange({target:{value:'synthetic'}});
  });
  await act(async () => {
    await renderer.root.findByType('form').props.onSubmit({preventDefault() {}});
  });
  await select('机构／院区', 'org/A');
  await act(async () => { await rowClick(101); });
  // A missing build flag would unmount this component and fail every case.
  assert.equal(editor(), expectedAssessment);
}
beforeEach(() => {
  oldFetch = global.fetch; oldWindow = global.window; oldStorage = global.sessionStorage;
  calls = []; prompts = []; allowLeave = false; stored = new Map(); savedAggregate = null;
  global.window = { confirm: text => { prompts.push(text); return allowLeave; } };
  global.sessionStorage = {getItem:k=>stored.get(k) ?? null, setItem:(k,v)=>stored.set(k,v), removeItem:k=>stored.delete(k)};
  onDetail = id => response(record(id));
  onTreatment = id => response((id === 101 && savedAggregate) || aggregate(id));
  onSave = async (options, id) => {
    const body = JSON.parse(options.body);
    savedAggregate = aggregate(id, 2, body.content.assessment);
    return response(await draftReceipt(options, id, 'committed'), 201);
  };
  global.fetch = async (url, options) => {
    calls.push({url, method:options.method});
    const {pathname, searchParams} = new URL(url, 'http://clinic.invalid');
    if (pathname.endsWith('/auth/login')) return response({access_token:'synthetic-session'});
    if (pathname.endsWith('/auth/logout')) return response(null, 204);
    if (pathname.endsWith('/scopes')) return response({items:scopes});
    if (pathname.endsWith('/cases')) return response(searchParams.get('after') === '0'
      ? {items:[record(101), record(102)], next_after:102} : {items:[record(103)], next_after:null});
    const id = Number(pathname.match(/\/cases\/(\d+)/)?.[1]);
    if (pathname.endsWith('/treatment/draft') && options.method === 'PATCH') return onSave(options, id);
    const command = pathname.match(/\/commands\/([0-9a-f]{64})$/);
    if (command && options.method === 'GET') {
      return response({state:'not_observed', operation:searchParams.get('operation'), idempotency_key:command[1]}, 202);
    }
    if (pathname.endsWith('/treatment')) return onTreatment(id);
    if (pathname.endsWith('/cases/' + id)) return onDetail(id);
    throw new Error('Unexpected synthetic route ' + pathname);
  };
});
afterEach(() => {
  if (renderer) act(() => renderer.unmount());
  renderer = null; global.fetch = oldFetch; global.window = oldWindow; global.sessionStorage = oldStorage;
  for (const text of prompts) assert.ok(!text.includes(localText), 'dialog should not contain clinical text');
});

test('row navigation and case-number navigation preserve the local draft on cancel; explicit leave changes case without saving', async () => {
  await openChart();
  edit('治疗评估', localText);
  await act(async () => { await rowClick(102); });
  assert.equal(prompts.length, 1); assert.equal(detailHeading(), '病例 #101 · 合成病例 101');
  assert.equal(editor(), localText);
  await lookup(207);
  assert.equal(prompts.length, 2); assert.equal(editor(), localText);
  allowLeave = true;
  await lookup(207);
  assert.equal(prompts.length, 3); assert.equal(editor(), '服务端草稿 207');
  assert.doesNotMatch(output(), /尚未保存的原文/);
  assert.deepEqual(writeCalls(), []); assert.equal(stored.size, 0);
});

test('lookup checks the latest dirty state after authorization succeeds, even if clean when submitted', async () => {
  await openChart();
  let release, request;
  onDetail = () => new Promise(resolve => { release = resolve; });
  typeNumber(207);
  act(() => { request = submitNumber(); });
  assert.equal(prompts.length, 0); assert.equal(editor(), '服务端草稿 101');
  edit('治疗诊断', '诊断一\n\n');
  await act(async () => { release(response(record(207))); await request; });
  assert.equal(prompts.length, 1); assert.equal(byLabel('治疗诊断').props.value, '诊断一\n\n');
  assert.equal(detailHeading(), '病例 #101 · 合成病例 101');
  assert.deepEqual(writeCalls(), []); assert.equal(stored.size, 0);
});

test('same case number, same row and denied lookup of another case never discard local text or prompt', async () => {
  await openChart(); edit('治疗评估', localText);
  await lookup('00101');
  await act(async () => { await rowClick(101); });
  assert.equal(editor(), localText);
  for (const status of [403, 404, 503]) {
    onDetail = () => response({}, status);
    await lookup(207);
    assert.equal(editor(), localText); assert.equal(detailHeading(), '病例 #101 · 合成病例 101');
  }
  assert.equal(prompts.length, 0); assert.deepEqual(writeCalls(), []);
});

for (const [name, action, verify] of [
  ['scope', () => select('机构／院区', 'org/B'), () => assert.equal(byLabel('机构／院区').props.value, 'org/B')],
  ['projection', () => select('资料范围', 'demographics'), () => assert.equal(byLabel('资料范围').props.value, 'demographics')],
  ['next page', () => click('下一页'), () => assert.match(listCalls().at(-1).url, /after=102$/)],
  ['case list refresh', () => click('重新读取病例'), () => assert.match(listCalls().at(-1).url, /after=0$/)],
]) {
  test(name + ' changes only after affirmative consent for a dirty open draft', async () => {
    await openChart(); edit('治疗评估', localText);
    const before = calls.length;
    await action();
    assert.equal(prompts.length, 1); assert.equal(calls.length, before);
    assert.equal(byLabel('机构／院区').props.value, 'org/A');
    assert.equal(byLabel('资料范围').props.value, 'clinical');
    assert.equal(editor(), localText);
    allowLeave = true; await action();
    assert.equal(prompts.length, 2); verify();
    assert.equal(renderer.root.findAllByProps({'aria-label':'治疗签署'}).length, 0);
    assert.doesNotMatch(output(), /尚未保存的原文/); assert.deepEqual(writeCalls(), []);
  });
}

for (const status of [401, 403, 404]) {
  test('current-case ' + status + ' clears sensitive information without a leave prompt', async () => {
    await openChart(); edit('治疗评估', localText); onDetail = () => response({}, status);
    await act(async () => { await rowClick(101); });
    assert.equal(prompts.length, 0); assert.doesNotMatch(output(), /尚未保存的原文/);
    assert.equal(renderer.root.findAllByProps({'aria-label':'病例详情'}).length, 0);
    if (status === 401) assert.ok(button('登录'));
    assert.deepEqual(writeCalls(), []);
  });
}

test('logout clears dirty text immediately and an earlier successful lookup cannot prompt or repopulate the chart', async () => {
  await openChart(); edit('治疗评估', localText);
  let release, request;
  onDetail = () => new Promise(resolve => { release = resolve; });
  typeNumber(207);
  act(() => { request = submitNumber(); });
  await click('退出登录');
  assert.ok(button('登录')); assert.doesNotMatch(output(), /尚未保存的原文/);
  await act(async () => { release(response(record(207))); await request; });
  assert.equal(prompts.length, 0); assert.ok(button('登录')); assert.doesNotMatch(output(), /合成病例 207/);
  assert.deepEqual(writeCalls(), []); assert.equal(stored.size, 0);
});

test('confirmed draft save and readback clears the guard for the next case', async () => {
  await openChart(); edit('治疗评估', localText); await click('保存治疗草稿');
  assert.equal(editor(), localText); assert.equal(stored.size, 0);
  await act(async () => { await rowClick(102); });
  assert.equal(editor(), '服务端草稿 102'); assert.equal(prompts.length, 0);
  assert.deepEqual(writeCalls().map(c => c.method), ['PATCH']);
});

test('a pending first draft is neither cancelled nor resubmitted when leaving and reopening the case', async () => {
  onTreatment = id => response(id === 101 ? {...aggregate(id), plan:null, draft:null, draft_etag:null} : aggregate(id));
  await openChart('');
  onSave = pendingSave;
  await click('保存治疗草稿');
  assert.ok(button('查询原请求')); assert.equal(stored.size, 1);
  const original = [...stored.entries()];
  await act(async () => { await rowClick(102); });
  assert.equal(prompts.length, 0); assert.equal(button('查询原请求'), undefined);
  await act(async () => { await rowClick(101); });
  assert.equal(prompts.length, 0); assert.ok(button('查询原请求'));
  assert.deepEqual([...stored.entries()], original); assert.deepEqual(commandCalls(), []);
  assert.deepEqual(writeCalls().map(c => c.method), ['PATCH']);
});

test('dirty text with an unresolved save keeps its original receipt across cancel and an explicit case switch', async () => {
  await openChart(); edit('治疗评估', localText);
  onSave = pendingSave;
  await click('保存治疗草稿');
  const entries = [...stored.entries()];
  assert.equal(entries.length, 1);
  const [partition, value] = entries[0];
  assert.equal(partition, 'pmai:treatment:7:org:A:101');
  const receipt = JSON.parse(value);
  assert.deepEqual(Object.keys(receipt).sort(), ['key', 'operation', 'request_hash']);
  assert.equal(receipt.operation, 'draft.save');
  await lookup(207);
  assert.equal(prompts.length, 1); assert.equal(editor(), localText); assert.ok(button('查询原请求'));
  allowLeave = true; await lookup(207);
  assert.equal(prompts.length, 2); assert.equal(button('查询原请求'), undefined);
  await lookup(101);
  assert.ok(button('查询原请求')); assert.doesNotMatch(output(), /尚未保存的原文/);
  assert.deepEqual([...stored.entries()], entries); assert.deepEqual(commandCalls(), []);
  assert.deepEqual(writeCalls().map(c => c.method), ['PATCH']);
});

test('denied row for another case retains the dirty chart and performs no write', async () => {
  await openChart(); edit('治疗评估', localText);
  onDetail = () => response({}, 404);
  await act(async () => { await rowClick(102); });
  assert.equal(editor(), localText); assert.equal(detailHeading(), '病例 #101 · 合成病例 101');
  assert.match(output(), /病例不存在或当前账号无权查看/);
  assert.equal(prompts.length, 0); assert.deepEqual(writeCalls(), []);
});

test('a mismatched commit leaves the original request recoverable only in its case after navigation', async () => {
  await openChart();
  edit('治疗评估', localText);
  let original;
  onSave = async (options, id) => {
    const reply = await draftReceipt(options, id, 'committed');
    original = {key:reply.idempotency_key, operation:reply.operation, request_hash:reply.request_hash};
    const otherKey = (original.key.startsWith('0') ? '1' : '0') + original.key.slice(1);
    return response({...reply, idempotency_key:otherKey}, 201);
  };
  await click('保存治疗草稿');
  const partition = 'pmai:treatment:7:org:A:101';
  assert.ok(stored.has(partition), 'a commit for a different request must not clear the original recovery key');
  assert.deepEqual(JSON.parse(stored.get(partition)), original);
  assert.equal(stored.size, 1); assert.equal(editor(), localText);
  assert.equal(renderer.root.findByType('fieldset').props.disabled, true);
  assert.doesNotMatch(output(), /已从服务端核对保存结果/);
  allowLeave = true;
  await lookup(207);
  assert.equal(prompts.length, 1); assert.equal(button('查询原请求'), undefined);
  assert.ok(!output().includes(original.key)); assert.doesNotMatch(output(), /尚未保存的原文/);
  await lookup(101);
  assert.equal(commandCalls().length, 0);
  await click('查询原请求');
  assert.deepEqual(commandCalls(), [{
    method:'GET', url:'/api/v2/organizations/org/clinics/A/cases/101/commands/' + original.key + '?operation=draft.save',
  }]);
  assert.deepEqual(JSON.parse(stored.get(partition)), original);
  assert.equal(stored.size, 1); assert.equal(renderer.root.findByType('fieldset').props.disabled, true);
  assert.deepEqual(writeCalls().map(c => c.method), ['PATCH']);
});

test('same-row reread verifies case and current treatment rights while preserving edits made against an older draft', async () => {
  await openChart(); edit('治疗评估', localText);
  onTreatment = id => response({...aggregate(id, 2, '另一版草稿'), allowed_actions: {edit:false}});
  const before = calls.length;
  await act(async () => { await rowClick(101); });
  assert.deepEqual(calls.slice(before).map(c => c.url), [
    '/api/v2/organizations/org/clinics/A/cases/101?projection=clinical',
    '/api/v2/organizations/org/clinics/A/cases/101/treatment',
  ]);
  assert.equal(prompts.length, 0); assert.equal(editor(), localText);
  assert.equal(renderer.root.findByType('fieldset').props.disabled, true);
  assert.equal(button('保存治疗草稿').props.disabled, true);
  assert.ok(byLabel('草稿版本冲突'));
  assert.deepEqual(writeCalls(), []);
});

for (const status of [403, 404]) {
  test('same chart authorized but treatment GET ' + status + ' clears all treatment data without affecting authorized case detail', async () => {
    onTreatment = id => {
      const result = aggregate(id);
      result.profile = {display_name:'先前服务端医生'};
      result.plan.head_revision_id = 'frozen';
      result.revisions = [{id:'frozen', revision_no:1, draft_version:1, origin:'clinical', content_sha256:'a'.repeat(64),
        source_manifest: {case: {patient_name:'仅限旧冻结快照的内容'}}, content:result.draft.content}];
      return response(result);
    };
    await openChart();
    assert.match(output(), /先前服务端医生/); assert.match(output(), /仅限旧冻结快照的内容/);
    edit('治疗评估', localText);
    onTreatment = () => response({}, status);
    const before = calls.length;
    await act(async () => { await rowClick(101); });
    assert.equal(calls.slice(before).filter(c => c.url.endsWith('/101/treatment')).length, 1);
    assert.equal(prompts.length, 0); assert.equal(detailHeading(), '病例 #101 · 合成病例 101');
    assert.doesNotMatch(output(), /先前服务端医生|仅限旧冻结快照的内容/);
    assert.doesNotMatch(output(), /尚未保存的原文|服务端草稿 101/);
    assert.match(output(), /当前无法查看此病例的治疗记录/);
    for (const name of ['保存治疗草稿','冻结版本供核对','审核通过','再次认证并确认签署']) {
      assert.ok(!button(name) || button(name).props.disabled, name + ' must be unavailable after access was denied');
    }
    assert.deepEqual(writeCalls(), []); assert.equal(stored.size, 0);
  });
}

test('refreshing the same row while a draft PATCH is in flight preserves its signal, receipt and original editor', async () => {
  await openChart(); edit('治疗评估', localText);
  let resolveSave, notifyStarted, sending;
  const started = new Promise(resolve => { notifyStarted = resolve; });
  let saveSignal;
  onSave = async (options, id) => {
    saveSignal = options.signal;
    const reply = await pendingSave(options, id);
    notifyStarted();
    return new Promise(resolve => { resolveSave = () => resolve(reply); });
  };
  await act(async () => {
    sending = button('保存治疗草稿').props.onClick();
    await started;
  });
  const receipt = [...stored.entries()];
  assert.equal(receipt.length, 1);
  const before = calls.length;
  await act(async () => { await rowClick(101); });
  assert.equal(prompts.length, 0); assert.equal(editor(), localText); assert.equal(saveSignal.aborted, false);
  assert.deepEqual(calls.slice(before).map(c => c.url), ['/api/v2/organizations/org/clinics/A/cases/101?projection=clinical']);
  assert.deepEqual([...stored.entries()], receipt);
  await act(async () => { resolveSave(); await sending; });
  assert.ok(button('查询原请求')); assert.deepEqual(commandCalls(), []);
  assert.equal(writeCalls().length, 1);
});

test('treatment-only session expiry after same-case reread preserves the raw copy, with no signing controls', async () => {
  await openChart(); edit('治疗评估', localText);
  onTreatment = () => response({code:'SESSION_EXPIRED'}, 401);
  await act(async () => { await rowClick(101); });
  assert.equal(detailHeading(), '病例 #101 · 合成病例 101'); assert.equal(prompts.length, 0);
  assert.ok(renderer.root.findAllByType('dd').some(node => node.children.join('') === localText));
  assert.match(output(), /未保存原文 · 只读保留/);
  assert.equal(button('保存治疗草稿'), undefined); assert.equal(button('再次认证并确认签署'), undefined);
  assert.deepEqual(writeCalls(), []);
});

test('a denied explicit treatment read never removes an unresolved save receipt', async () => {
  await openChart(); edit('治疗评估', localText);
  onSave = pendingSave;
  await click('保存治疗草稿');
  const receipt = [...stored.entries()]; assert.equal(receipt.length, 1);
  onTreatment = () => response({}, 403);
  await click('重新读取治疗记录');
  assert.equal(detailHeading(), '病例 #101 · 合成病例 101');
  assert.doesNotMatch(output(), /尚未保存的原文|服务端草稿 101/);
  assert.deepEqual([...stored.entries()], receipt); assert.equal(prompts.length, 0);
  assert.deepEqual(commandCalls(), []); assert.equal(writeCalls().length, 1);
});
