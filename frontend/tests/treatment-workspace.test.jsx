import React from 'react';
import TestRenderer, { act } from 'react-test-renderer';
import { test, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import TreatmentWorkspace from '../src/pages/TreatmentWorkspace';
let renderer, handler, requests, originalFetch, originalStorage, saved;
const scope={org_id:'11111111-1111-1111-1111-111111111111',clinic_id:'22222222-2222-2222-2222-222222222222',org_name:'合成机构',clinic_name:'合成院区'};
const content={schema:'treatment-content-v1',diagnoses:[{label:'合成诊断',code_system:null,code:null}],assessment:'café 🐾\n{{literal}} literal \\n',treatment:{goals:[],management_text:'合成治疗原文',monitoring_text:'',followup_text:''},linked_orders:[],provenance:{ai_generation_ids:[],voice_transcript_revision_ids:[]}};
const ids = {
  plan: '3708b584-295b-4691-a6b4-6422cf410001', revision: '3708b584-295b-4691-a6b4-6422cf410002',
  priorRevision: '3708b584-295b-4691-a6b4-6422cf410003', signature: '3708b584-295b-4691-a6b4-6422cf410004',
  priorSignature: '3708b584-295b-4691-a6b4-6422cf410005', review: '3708b584-295b-4691-a6b4-6422cf410006',
  audit: '3708b584-295b-4691-a6b4-6422cf410007', event: '3708b584-295b-4691-a6b4-6422cf410008',
};
const caseScope = {org_id:scope.org_id, clinic_id:scope.clinic_id, case_id:1, plan_id:ids.plan};
function frozenRevision(id, revision_no, revisionContent = content,
  source_manifest = {case:{patient_name:'合成犬',clinical_epoch:1},diagnostic_reports:[]}) {
  const created_at = '2026-11-09T00:00:00Z';
  const envelope = {schema:'pmai-treatment-revision-v1', canonicalization:'pmai-canonical-json-v1', ...caseScope,
    revision_id:id, draft_version:1, content:revisionContent, source_manifest, created_by:1, created_at};
  const canonical_utf8 = JSON.stringify(envelope, (_, value) => value && typeof value === 'object' && !Array.isArray(value)
    ? Object.fromEntries(Object.keys(value).sort().map(key => [key, value[key]])) : value);
  return {id, ...caseScope, revision_no, draft_version:1, content:revisionContent, source_manifest, created_at, created_by:1, origin:'clinical',
    canonical_utf8, content_sha256:createHash('sha256').update(canonical_utf8, 'utf8').digest('hex')};
}
const rev = frozenRevision(ids.revision, 2);
const priorRevision = frozenRevision(ids.priorRevision, 1);
function data(overrides={}) {return {actor_id:1,plan:{id:ids.plan,lock_version:4,head_revision_id:rev.id,active_signature_id:null},etag:'"plan:4"',draft_etag:'"draft:1"',draft:{draft_version:1,content},revisions:[rev],reviews:[],signatures:[],events:[],profile:{display_name:'合成医生'},source_epoch:1,policy:{review_policy:'self_allowed',required_assurance:'account_attestation'},allowed_actions:{edit:true,review:true,sign:true},...overrides};}
const response=(body,status=200)=>({ok:status<400,status,json:async()=>body});
function pendingCommand() {
  const stored = saved.get(`pmai:treatment:1:${scope.org_id}:${scope.clinic_id}:1`);
  assert.ok(stored, 'the original pending command must remain in its scoped recovery slot');
  return JSON.parse(stored);
}
function receipt(fields, status) {
  const {key, operation, request_hash} = pendingCommand();
  const result = fields.state === 'committed' ? {etag:'"plan:5"', ...fields} : fields;
  return response({idempotency_key:key, operation, request_hash, ...result}, status);
}
const draftResult = version => ({
  state:'committed', plan_id:ids.plan, draft_version:version, draft_etag:'"draft:' + version + '"', audit_id:ids.audit,
});
const signResult = () => ({
  state:'committed', signature_id:ids.signature, revision_id:rev.id, assurance:'account_attestation',
});
function signedReadback(action = 'sign', state = action === 'sign' ? 'effective' : 'revoked', revision = action === 'sign' ? rev : priorRevision) {
  const id = action === 'sign' ? ids.signature : ids.priorSignature;
  const signature = {...caseScope, id, revision_id:revision.id, content_hash:revision.content_sha256, assurance:'account_attestation',
    review_id:ids.review, signer_id:1, signed_at:'2026-11-09T00:01:00Z', clinician_snapshot:{display_name:'合成医生'},
    audit_event_id:ids.audit};
  return {signature, revision, state, audit:{...caseScope, id:ids.audit, action:'sign', target_id:id}, terminal_event:state === 'effective'
    ? null : {...caseScope, id:ids.event, signature_id:id, event:state, actor_id:1, reason:'合成原因', created_at:'2026-11-09T01:00:00Z'}};
}
const output=()=>JSON.stringify(renderer.toJSON());
const button=name=>renderer.root.findAllByType('button').find(n=>n.children.join('')===name);
async function mount(props={}) {await act(async()=>{renderer=TestRenderer.create(<TreatmentWorkspace token="synthetic-token" scope={scope} caseId={1} {...props}/>);});}
async function click(name) {await act(async()=>{await button(name).props.onClick();});}
function change(label,value,checked) {act(()=>renderer.root.findByProps({'aria-label':label}).props.onChange({target:{value,checked}}));}
beforeEach(()=>{requests=[];saved=new Map();originalFetch=global.fetch;originalStorage=global.sessionStorage;
 global.sessionStorage={getItem:k=>saved.get(k)||null,setItem:(k,v)=>saved.set(k,v),removeItem:k=>saved.delete(k)};
 handler=async()=>response(data());global.fetch=async(url,options)=>{requests.push({url,options});return handler(url,options);};});
afterEach(()=>{if(renderer)act(()=>renderer.unmount());renderer=null;global.fetch=originalFetch;global.sessionStorage=originalStorage;});
test('frozen Unicode preview and server supplied clinical identity',async()=>{
 await mount();assert.match(output(),/合成医生/);assert.match(output(),/café 🐾/);assert.match(output(),/literal/);
 assert.equal(button('再次认证并确认签署').props.disabled,true);assert.equal(requests[0].options.credentials,'omit');assert.equal(requests[0].options.cache,'no-store');});
test('401 retains raw text only and invalidates checkbox/password/preview',async()=>{
 await mount();change('已核对冻结版本',null,true);change('签署认证密码','secret');handler=async()=>response({code:'SESSION_EXPIRED'},401);
 await click('重新读取治疗记录');assert.match(output(),/未保存原文 · 只读保留/);assert.match(output(),/café/);
 assert.equal(renderer.root.findAllByType('textarea').length,0);assert.equal(renderer.root.findAllByType('input').length,0);assert.doesNotMatch(output(),/secret/);});
test('late case response cannot replace a newer case',async()=>{
 let release;handler=()=>new Promise(resolve=>{release=resolve;});act(()=>{renderer=TestRenderer.create(<TreatmentWorkspace token="s" scope={scope} caseId={1}/>);});
 handler=async()=>response(data({draft:{draft_version:1,content:{...content,assessment:'新猫原文'}},revisions:[]}));
 await act(async()=>renderer.update(<TreatmentWorkspace token="s" scope={scope} caseId={2}/>));await act(async()=>release(response(data())));
 assert.match(output(),/新猫原文/);assert.doesNotMatch(output(),/café/);});
test('late 401 cannot invalidate a newer case',async()=>{
 let release;handler=()=>new Promise(resolve=>{release=resolve;});act(()=>{renderer=TestRenderer.create(<TreatmentWorkspace token="s" scope={scope} caseId={1}/>);});
 handler=async()=>response(data({revisions:[]}));await act(async()=>renderer.update(<TreatmentWorkspace token="s" scope={scope} caseId={2}/>));
 await act(async()=>release(response({code:'SESSION_EXPIRED'},401)));assert.doesNotMatch(output(),/未保存原文 · 只读保留/);assert.match(output(),/合成医生/);});
test('lost response stores only scoped key/hash and queries without a second write',async()=>{
 await mount();handler=async(url,options)=>{if(options.method==='PATCH')throw new TypeError('synthetic disconnect');return response(data());};
 await click('保存治疗草稿');assert.equal(requests.filter(r=>r.options.method==='PATCH').length,1);assert.equal(saved.size,1);
 const [key,value]=[...saved.entries()][0];assert.match(key,/pmai:treatment:1:/);assert.doesNotMatch(value,/café|token|password|management_text/);
 handler=async url=>url.includes('/commands/')?receipt(draftResult(2),201):response(storedDraft(2,content.assessment));
 await click('查询原请求');assert.equal(requests.filter(r=>r.options.method==='PATCH').length,1);assert.equal(saved.size,0);assert.match(output(),/已从服务端核对保存结果/);});
test('signature success needs independent readback; lost GET keeps original key',async()=>{
 const reviewed=data({reviews:[{id:ids.review,revision_id:rev.id,decision:'approve',reason:'核对',clinician_snapshot:{display_name:'合成医生'}}]});
 handler=async()=>response(reviewed);await mount();change('已核对冻结版本',null,true);change('签署认证密码','reauth-secret');
 handler=async(url,options)=>{if(url.endsWith('/auth/reauthenticate'))return response({challenge_id:'challenge1'});if(options.method==='POST')return receipt(signResult(),201);throw new TypeError('readback interrupted');};
 await click('再次认证并确认签署');assert.doesNotMatch(output(),/已独立回读签署|已从服务端核对保存结果/);assert.equal(saved.size,1);
 assert.equal(requests.filter(r=>r.url.endsWith('/treatment/signatures/'+ids.signature)).length,1);assert.doesNotMatch([...saved.values()].join(),/reauth-secret|challenge1|token/);});
test('different actor cannot load the previous actor pending key',async()=>{
 saved.set(`pmai:treatment:1:${scope.org_id}:${scope.clinic_id}:1`,JSON.stringify({key:'a'.repeat(64),request_hash:'b'.repeat(64),operation:'sign'}));
 handler=async()=>response(data({actor_id:2}));await mount();assert.doesNotMatch(output(),/待核对请求/);});
test('dirty draft invalidates confirmation and blocks freeze/sign',async()=>{
 await mount();change('已核对冻结版本',null,true);change('治疗评估','new text');assert.equal(renderer.root.findByProps({'aria-label':'已核对冻结版本'}).props.checked,false);
 assert.equal(button('冻结版本供核对').props.disabled,true);assert.equal(button('再次认证并确认签署').props.disabled,true);});
test('read grant exposes no editing or signing permission',async()=>{
 handler=async()=>response(data({allowed_actions:{edit:false,review:false,sign:false},profile:null}));await mount();assert.equal(renderer.root.findByType('fieldset').props.disabled,true);assert.equal(button('冻结版本供核对').props.disabled,true);});
test('certificate requirement cannot downgrade to account attestation',async()=>{
 handler=async()=>response(data({policy:{review_policy:'self_allowed',required_assurance:'certificate_signature'},allowed_actions:{edit:true,review:true,sign:false}}));await mount();assert.match(output(),/本院要求证书签名，当前不能签署/);assert.equal(button('再次认证并确认签署').props.disabled,true);});

test('stop waiting keeps original key and makes recovery available',async()=>{
 await mount();let release;handler=()=>new Promise(resolve=>{release=resolve;});let sending;
 await act(async()=>{sending=button('保存治疗草稿').props.onClick();await new Promise(resolve=>setTimeout(resolve,15));});
 assert.equal(saved.size,1);await click('停止等待（保留原请求）');assert.equal(button('查询原请求').props.disabled,false);
 await act(async()=>{release(receipt(draftResult(2),201));await sending;});
 assert.equal(saved.size,1);assert.doesNotMatch(output(),/已从服务端核对保存结果/);
});
test('a saved changed draft blocks signing its previous frozen version',async()=>{
 handler=async()=>response(data({draft:{draft_version:2,content}}));await mount();
 assert.match(output(),/草稿已修改，此冻结版本不能继续审核或签署/);
 assert.equal(renderer.root.findByProps({'aria-label':'已核对冻结版本'}).props.disabled,true);
});

const staleSourceWarning = '冻结后病例资料或签署规则已变化，请重新冻结版本后再审核或签署。';
const acknowledgement = () => renderer.root.findByProps({'aria-label':'已核对冻结版本'}).props;

test('an updated case epoch fences the old review and permits a fresh freeze using the current epoch', async () => {
  const newSource = {...rev.source_manifest, case:{...rev.source_manifest.case, clinical_epoch:2}};
  const replacement = frozenRevision('3708b584-295b-4691-a6b4-6422cf410010', 3, content, newSource);
  let record = data({source_epoch:2});
  handler = async (url, options) => {
    if (options.method === 'GET') return response(record);
    assert.ok(url.endsWith('/treatment/revisions'));
    assert.deepEqual(JSON.parse(options.body), {draft_version:1, expected_source_epoch:2});
    record = {...record, plan:{...record.plan, head_revision_id:replacement.id}, revisions:[rev, replacement]};
    return receipt({state:'committed', revision_id:replacement.id, content_hash:replacement.content_sha256}, 201);
  };
  await mount();
  assert.ok(output().includes(staleSourceWarning));
  assert.match(output(), /café 🐾/);
  assert.equal(acknowledgement().disabled, true);
  for (const action of ['审核通过','要求修订','审核拒绝','再次认证并确认签署']) assert.equal(button(action).props.disabled, true);
  assert.equal(renderer.root.findByType('fieldset').props.disabled, false);
  assert.equal(button('冻结版本供核对').props.disabled, false);
  await click('冻结版本供核对');
  assert.deepEqual(requests.map(r => r.options.method), ['GET','POST','GET']);
  assert.equal(output().includes(staleSourceWarning), false);
  assert.equal(acknowledgement().disabled, false);
  assert.equal(acknowledgement().checked, false);
  change('已核对冻结版本', null, true);
  change('操作原因', '已核对最新来源');
  assert.equal(button('审核通过').props.disabled, false);
});

test('rereading a later signing-policy version retires the approval even when the rules and case epoch look unchanged', async () => {
  const policy = {...data().policy, version:3};
  const approved = frozenRevision(rev.id, rev.revision_no, content, {...rev.source_manifest, policy});
  const review = {id:ids.review, revision_id:approved.id, decision:'approve', reason:'核对', clinician_snapshot:{display_name:'合成医生'}};
  let record = data({policy, revisions:[approved], reviews:[review]});
  handler = async () => response(record);
  await mount();
  change('已核对冻结版本', null, true);
  change('签署认证密码', 'synthetic');
  assert.equal(button('再次认证并确认签署').props.disabled, false);
  record = {...record, policy:{...policy, version:4}};
  await click('重新读取治疗记录');
  assert.ok(output().includes(staleSourceWarning));
  assert.equal(acknowledgement().checked, false);
  assert.equal(acknowledgement().disabled, true);
  assert.equal(renderer.root.findByProps({'aria-label':'签署认证密码'}).props.value, '');
  assert.equal(button('再次认证并确认签署').props.disabled, true);
  assert.equal(button('冻结版本供核对').props.disabled, false);
  assert.deepEqual(requests.map(r => r.options.method), ['GET','GET']);
});

test('a stale source preserves the effective signed record and its separate revocation acknowledgement', async () => {
  const signed = signedReadback('sign', 'effective', priorRevision);
  handler = async () => response(data({
    plan:{...data().plan, active_signature_id:signed.signature.id},
    source_epoch:2, revisions:[priorRevision,rev], signatures:[signed.signature],
  }));
  await mount();
  assert.ok(output().includes(staleSourceWarning));
  assert.equal(acknowledgement().disabled, true);
  const active = renderer.root.findByProps({'aria-label':'当前有效签署'});
  assert.ok(active.findAllByType('dd').some(node => node.children.includes(content.assessment)));
  change('操作原因','合成作废原因');
  change('签署认证密码','synthetic');
  assert.equal(button('再次认证并作废签署').props.disabled, true);
  change('已核对待作废签署', null, true);
  assert.equal(button('再次认证并作废签署').props.disabled, false);
});

test('older snapshots without policy-version evidence keep the existing clinical review flow', async () => {
  handler = async () => response(data({policy:{...data().policy, version:9}}));
  await mount();
  assert.equal(output().includes(staleSourceWarning), false);
  assert.equal(acknowledgement().disabled, false);
  change('已核对冻结版本', null, true);
  change('操作原因', '已核对历史快照');
  assert.equal(button('审核通过').props.disabled, false);
});

test('revocation has a separate acknowledgement of the effective signed version',async()=>{
 const signature={id:'sig1',revision_id:'old',content_hash:'b'.repeat(64),clinician_snapshot:{display_name:'旧签署医生'},signed_at:'2026-11-09T00:00:00Z'};
 handler=async()=>response(data({plan:{id:'p',head_revision_id:rev.id,active_signature_id:'sig1'},signatures:[signature],revisions:[rev,{...rev,id:'old',revision_no:0,content:{...content,assessment:'当前有效版本的原文'}}]}));
 await mount();assert.match(output(),/当前有效版本的原文/);change('已核对冻结版本',null,true);change('签署认证密码','secret');change('操作原因','synthetic revocation');
 assert.equal(button('再次认证并作废签署').props.disabled,true);change('已核对待作废签署',null,true);assert.equal(button('再次认证并作废签署').props.disabled,false);
});

function storedDraft(version, assessment) {
  return data({
    draft_etag: '"draft:' + version + '"',
    draft: {draft_version: version, content: {...content, assessment}},
  });
}
const assessment = () => renderer.root.findByProps({'aria-label':'治疗评估'}).props.value;
const draftWrites = () => requests.filter(r => r.options.method === 'PATCH');
const discardDraft = '放弃本页修改并载入服务器草稿';

test('refresh of an unchanged draft preserves typed text and saves against the edit-start ETag', async () => {
  await mount();
  const local = '保留新修改 café 🐾\n复查';
  change('治疗评估', local);
  await click('重新读取治疗记录');
  assert.equal(assessment(), local);
  assert.equal(button(discardDraft), undefined);
  handler = async (url, options) => options.method === 'PATCH'
    ? receipt(draftResult(2), 201)
    : response(storedDraft(2, local));
  await click('保存治疗草稿');
  assert.equal(draftWrites().length, 1);
  assert.equal(draftWrites()[0].options.headers['If-Match'], '"draft:1"');
  assert.equal(JSON.parse(draftWrites()[0].options.body).content.assessment, local);
  assert.equal(button('冻结版本供核对').props.disabled, false);
  assert.equal(button(discardDraft), undefined);
});

test('a concurrent change found by refresh preserves the local draft until explicit successful discard', async () => {
  await mount();
  const local = '本地待核对 {{犬}}\n保留原文';
  change('治疗评估', local);
  handler = async () => response(storedDraft(2, '另一位医生的修改'));
  await click('重新读取治疗记录');
  assert.equal(assessment(), local);
  await click('保存治疗草稿');
  assert.deepEqual(draftWrites().map(r => r.options.headers['If-Match']), [],
    'a dirty draft based on version 1 must not send a PATCH using the newly read version 2');
  assert.equal(button('保存治疗草稿').props.disabled, true);
  assert.equal(button('冻结版本供核对').props.disabled, true);
  assert.equal(saved.size, 0);
  handler = async () => { throw new TypeError('synthetic read interrupted'); };
  await click(discardDraft);
  assert.equal(assessment(), local);
  assert.equal(button('保存治疗草稿').props.disabled, true);
  assert.equal(button(discardDraft).props.disabled, false);
  handler = async () => response(storedDraft(3, '最新院内草稿'));
  await click(discardDraft);
  assert.equal(assessment(), '最新院内草稿');
  assert.equal(button(discardDraft), undefined);
  assert.equal(draftWrites().length, 0);
  change('治疗评估', '以最新院内版本编辑');
  handler = async (url, options) => options.method === 'PATCH'
    ? receipt(draftResult(4), 201)
    : response(storedDraft(4, '以最新院内版本编辑'));
  await click('保存治疗草稿');
  assert.equal(draftWrites()[0].options.headers['If-Match'], '"draft:3"');
});

test('first-draft creation keeps If-None-Match and a terminal 412 blocks even when the follow-up GET fails', async () => {
  handler = async () => response(data({draft:null, draft_etag:null}));
  await mount();
  change('治疗评估', '新建时的本地原文');
  await click('重新读取治疗记录');
  handler = async (url, options) => {
    if (options.method === 'PATCH') return receipt({state:'failed', code:'VERSION_MISMATCH'}, 412);
    throw new TypeError('synthetic read interrupted');
  };
  await click('保存治疗草稿');
  assert.equal(draftWrites()[0].options.headers['If-None-Match'], '*');
  assert.equal(draftWrites()[0].options.headers['If-Match'], undefined);
  assert.equal(saved.size, 0);
  assert.equal(assessment(), '新建时的本地原文');
  assert.equal(button('保存治疗草稿').props.disabled, true);
  handler = async () => response(storedDraft(1, '同事先建的草稿'));
  await click('重新读取治疗记录');
  await click('保存治疗草稿');
  assert.equal(assessment(), '新建时的本地原文');
  assert.equal(draftWrites().length, 1);
  await click(discardDraft);
  assert.equal(assessment(), '同事先建的草稿');
});

test('querying a lost draft receipt preserves local text if a subsequent revision is already present', async () => {
  await mount();
  change('治疗评估', '先前发送的本地草稿');
  handler = async () => { throw new TypeError('synthetic lost response'); };
  await click('保存治疗草稿');
  assert.equal(saved.size, 1);
  const [storedReceipt] = saved.values();
  assert.doesNotMatch(storedReceipt, /先前发送的本地草稿/);
  handler = async url => url.includes('/commands/')
    ? receipt(draftResult(2), 201)
    : response(storedDraft(3, '后续修订'));
  await click('查询原请求');
  assert.equal(saved.size, 0);
  assert.equal(assessment(), '先前发送的本地草稿');
  assert.equal(button('保存治疗草稿').props.disabled, true);
  assert.equal(draftWrites().length, 1);
});

test('late discard response for a former case cannot replace the active case draft', async () => {
  await mount();
  change('治疗评估', '旧病例本地稿');
  handler = async () => response(storedDraft(2, '旧病例服务端稿'));
  await click('重新读取治疗记录');
  let release, pendingRead;
  handler = () => new Promise(resolve => { release = resolve; });
  act(() => { pendingRead = button(discardDraft).props.onClick(); });
  handler = async () => response(storedDraft(1, '新病例服务端稿'));
  await act(async () => renderer.update(<TreatmentWorkspace token="synthetic-token" scope={scope} caseId={2}/>));
  await act(async () => { release(response(storedDraft(2, '旧病例迟到稿'))); await pendingRead; });
  assert.equal(assessment(), '新病例服务端稿');
  assert.equal(button(discardDraft), undefined);
  assert.equal(draftWrites().length, 0);
});

const inputValue = label => renderer.root.findByProps({ 'aria-label': label }).props.value;
async function checkDraftPatch(expected) {
  handler = async (_url, options) => options.method === 'PATCH'
    ? receipt(draftResult(2), 201)
    : response(data({ draft_etag: '"draft:2"', draft: { draft_version: 2, content: expected } }));
  await click('保存治疗草稿');
  const patches = requests.filter(request => request.options.method === 'PATCH');
  assert.equal(patches.length, 1);
  assert.deepEqual(JSON.parse(patches[0].options.body), { content: expected });
  assert.equal(button('冻结版本供核对').props.disabled, false);
}

test('discarding a conflict replaces an unsaved multiline list with the newer coded rows', async () => {
  await mount();
  change('治疗诊断', '本页修改\n');
  const newer = { ...content, diagnoses: [{ label: '新记录', code_system: 'local', code: 'B' }] };
  handler = async () => response(data({ draft_etag: '"draft:2"', draft: { draft_version: 2, content: newer } }));
  await click('重新读取治疗记录');
  assert.equal(inputValue('治疗诊断'), '本页修改\n');
  assert.equal(button('保存治疗草稿').props.disabled, true);
  await click(discardDraft);
  assert.equal(inputValue('治疗诊断'), '新记录');
  assert.match(output(), /local · B/);
  assert.equal(draftWrites().length, 0);
});

test('typed Enter survives the controlled fields; PATCH excludes only empty separators and preserves literal text', async () => {
  await mount();
  change('治疗诊断', inputValue('治疗诊断') + '\n');
  assert.equal(inputValue('治疗诊断'), '合成诊断\n');
  change('治疗诊断', inputValue('治疗诊断') + ' 第二项 café 🐾  \n \t \n\n');
  change('治疗目标', ' 任意  空格 ');
  change('治疗目标', inputValue('治疗目标') + '\n');
  assert.equal(inputValue('治疗目标'), ' 任意  空格 \n');
  change('治疗目标', inputValue('治疗目标') + '{{literal}} \\n\n\u3000\u00a0\t\n');
  await checkDraftPatch({ ...content,
    diagnoses: [...content.diagnoses, { label: ' 第二项 café 🐾  ', code_system: null, code: null },
      { label: ' \t ', code_system: null, code: null }],
    treatment: { ...content.treatment, goals: [' 任意  空格 ', '{{literal}} \\n', '\u3000\u00a0\t'] },
  });
});

test('coded duplicate rows keep identity across moves; a replacement or new diagnosis is uncoded', async () => {
  const first = { label: '同名', code_system: 'local', code: 'A' };
  const second = { label: '同名', code_system: 'local', code: 'B' };
  const literal = { label: '原始\r\n多行 {{text}} 🐾', code_system: 'legacy', code: 'C' };
  const original = { ...content, diagnoses: [first, second, literal],
    treatment: { ...content.treatment, goals: ['复核\r\n原文', '', '修改前'] } };
  handler = async () => response(data({ draft: { draft_version: 1, content: original } }));
  await mount();
  assert.match(output(), /local · A/);
  assert.match(output(), /local · B/);
  await act(async () => renderer.root.findByProps({ 'aria-label': '上移诊断 2' }).props.onClick());
  change('治疗诊断 2', '另一个诊断');
  assert.equal(inputValue('治疗诊断 3'), literal.label);
  await click('添加诊断');
  change('治疗诊断 4', '同名');
  await click('添加诊断'); // The unfilled row must not become a diagnosis.
  change('治疗目标 3', '新目标\n');
  assert.equal(inputValue('治疗目标 3'), '新目标\n');
  await click('添加治疗目标');
  change('治疗目标 4', '  ');
  await checkDraftPatch({ ...original,
    diagnoses: [second, { label: '另一个诊断', code_system: null, code: null }, literal,
      { label: '同名', code_system: null, code: null }],
    treatment: { ...original.treatment, goals: ['复核\r\n原文', '', '新目标\n', '  '] },
  });
});

test('editing another field preserves legal empty goals and diagnosis objects exactly in the PATCH', async () => {
  const original = { ...content,
    diagnoses: [{ label: ' 旧值\n换行 ', code_system: 'local', code: '12' }, { label: '原有记录' }],
    treatment: { ...content.treatment, goals: ['', '  ', '\n', '观察'] } };
  handler = async () => response(data({ draft: { draft_version: 1, content: original } }));
  await mount();
  change('治疗评估', '补充');
  await checkDraftPatch({ ...original, assessment: '补充' });
});

test('session expiry keeps the editable diagnosis and goal text including trailing blank lines', async () => {
  await mount();
  change('治疗诊断', '第一项\n\n');
  change('治疗目标', '保留 {{literal}} 🐾\n  \n');
  handler = async () => response({ code: 'SESSION_EXPIRED' }, 401);
  await click('重新读取治疗记录');
  const values = renderer.root.findAllByType('dd').map(directText);
  assert.ok(values.includes('第一项\n\n'));
  assert.ok(values.includes('保留 {{literal}} 🐾\n  \n'));
});

const reauthMessage = '再次认证未通过，本次操作尚未提交。请重新核对并输入当前账号密码。';
const signButton = '再次认证并确认签署';
const revokeButton = '再次认证并作废签署';

function displayContent(tag) {
  const raw = '  ' + tag + ' café 🐾\r\n{{原文}} \\n  ';
  return { ...content, assessment: raw,
    diagnoses: [
      { label: raw, code_system: '合成体系', code: ' A-01 ' },
      { label: raw, code_system: null, code: 'B-02' },
      { label: '仅有体系', code_system: '本院', code: null },
      { label: '空编码字段', code: '' },
      { label: '未编码' },
    ],
    treatment: { goals: ['相同', raw, '', ' \t ', '相同', '\\n', '\n'],
      management_text: raw + '治疗', monitoring_text: raw + '监测', followup_text: raw + '复查' },
  };
}

function directText(node) {
  return node.children.filter(child => typeof child === 'string').join('');
}

function assertContentView(section, expected) {
  function items(label) {
    const lists = section.findAllByType('ol').filter(list => list.props['aria-label'] === label);
    assert.equal(lists.length, 1, 'expected a single ordered list for ' + label);
    return lists[0].children.map(item => {
      assert.equal(item.type, 'li');
      return item;
    });
  }
  const diagnosisRows = items('诊断条目').map(item => ({
    label: directText(item.findByType('span')),
    fields: item.findAllByType('dt').map(term => {
      const siblings = term.parent.children;
      const value = siblings[siblings.indexOf(term) + 1];
      assert.equal(value.type, 'dd');
      return [directText(term), directText(value)];
    }),
  }));
  assert.deepEqual(diagnosisRows, expected.diagnoses.map(row => ({
    label: row.label,
    fields: [['编码体系', row.code_system], ['编码', row.code]].filter(([, value]) => value != null),
  })));
  const goals = items('治疗目标条目');
  assert.deepEqual(goals.map(directText), expected.treatment.goals);
  for (const [index, value] of expected.treatment.goals.entries()) {
    if (value !== '') continue;
    const children = goals[index].children;
    assert.equal(children.length, 1, 'an empty goal needs one selectable line without placeholder text');
    assert.equal(children[0].type, 'br');
    assert.equal(String(children[0].props['aria-hidden']), 'true');
  }
  for (const [label, raw] of [['评估', expected.assessment], ['治疗措施', expected.treatment.management_text],
    ['监测', expected.treatment.monitoring_text], ['复查', expected.treatment.followup_text]]) {
    const term = section.findAllByType('dt').find(node => node.children.join('') === label);
    const value = term.parent.children[term.parent.children.indexOf(term) + 1];
    assert.equal(value.type, 'dd');
    assert.equal(directText(value), raw);
  }
}

test('read-only treatment content preserves coded rows and raw text in the frozen version', async () => {
  const frozen = frozenRevision(ids.revision, 2, displayContent('冻结版本'));
  handler = async () => response(data({ revisions: [frozen], allowed_actions: {edit:false, review:false, sign:false} }));
  await mount();
  assertContentView(renderer.root.findByProps({'aria-label':'冻结版本'}), frozen.content);
  assert.equal(renderer.root.findByType('fieldset').props.disabled, true);
  assert.equal(button(signButton).props.disabled, true);
  assert.deepEqual(requests.map(r => r.options.method), ['GET']);
});

test('read-only treatment content displays the active signed revision even with a newer frozen version', async () => {
  const signed = frozenRevision(ids.priorRevision, 1, displayContent('有效签署'));
  const active = signedReadback('revoke', 'effective', signed).signature;
  handler = async () => response(data({
    plan: {id:ids.plan, head_revision_id:rev.id, active_signature_id:active.id},
    revisions: [rev, signed], signatures: [active],
  }));
  await mount();
  assertContentView(renderer.root.findByProps({'aria-label':'当前有效签署'}), signed.content);
  assert.deepEqual(requests.map(r => r.options.method), ['GET']);
});

test('read-only treatment content comes from the independently verified signature readback', async () => {
  const signed = frozenRevision(ids.revision, 2, displayContent('独立回读'));
  const independent = signedReadback('sign', 'superseded', signed);
  const successor = {...frozenRevision(ids.priorRevision, 3, displayContent('随后签署的修订')),
    predecessor_id:signed.id, amendment_of:independent.signature.id};
  const active = {...signedReadback('revoke', 'effective', successor).signature,
    review_id:'3708b584-295b-4691-a6b4-6422cf410009', audit_event_id:'3708b584-295b-4691-a6b4-6422cf410010',
    signed_at:'2026-11-09T00:02:00Z'};
  independent.terminal_event.successor_signature_id = active.id;
  const aggregate = data({
    plan: {id:ids.plan, head_revision_id:successor.id, active_signature_id:active.id},
    revisions: [successor, signed], signatures: [active, independent.signature], events:[independent.terminal_event],
  });
  const original = {key:'a'.repeat(64), operation:'sign', request_hash:'b'.repeat(64)};
  saved.set('pmai:treatment:1:' + scope.org_id + ':' + scope.clinic_id + ':1', JSON.stringify(original));
  const path = '/organizations/' + scope.org_id + '/clinics/' + scope.clinic_id + '/cases/1';
  handler = async url => {
    if (url.endsWith('/commands/' + original.key + '?operation=sign')) return receipt(signResult(), 201);
    if (url.endsWith('/treatment/signatures/' + ids.signature)) return response(independent);
    return response(aggregate);
  };
  await mount();
  assert.equal(renderer.root.findAllByProps({'aria-label':'独立回读签署'}).length, 0);
  await click('查询原请求');
  assertContentView(renderer.root.findByProps({'aria-label':'独立回读签署'}), signed.content);
  assert.deepEqual(requests.map(r => [r.options.method, r.url]), [
    '/treatment', '/commands/' + original.key + '?operation=sign',
    '/treatment/signatures/' + ids.signature, '/treatment',
  ].map(suffix => ['GET', '/api/v2' + path + suffix]));
  assert.equal(saved.size, 0);
});

// The aggregate is a separate server observation. Its terminal event and active pointer
// may already have advanced after the independent signature GET returned.
function signatureAggregate(record) {
  const { signature, revision, terminal_event: event } = record;
  const current = data({
    plan: {id:ids.plan, head_revision_id:revision.id, active_signature_id:event ? null : signature.id},
    signatures: [signature], revisions: [revision], events: event ? [event] : [],
  });
  if (record.state === 'superseded') {
    const amended = frozenRevision(ids.priorRevision, revision.revision_no + 1, {...content, assessment:'另一位医生签署的新原文'});
    const replacement = {...signedReadback('revoke', 'effective', amended).signature,
      clinician_snapshot:{display_name:'另一位合成医生'}, signer_id:2};
    current.plan = {...current.plan, head_revision_id:amended.id, active_signature_id:replacement.id};
    current.revisions.push(amended);
    current.signatures.push(replacement);
    current.events = [{...event, successor_signature_id:replacement.id}];
  }
  return current;
}

function assertVerifiedSignature(record) {
  const panel = renderer.root.findByProps({'aria-label':'独立回读签署'});
  assert.equal(directText(panel.findByType('p')), '已独立回读签署：' + record.signature.id + ' · ' + record.state + ' · 院内账号确认');
}

function historyRows() {
  return renderer.root.findAllByType('p').map(directText).filter(text => /^版本 \d+ · /.test(text));
}

function historyDetails(label) {
  const text = node => typeof node === 'string' ? node : node.children.map(text).join('');
  const summaries = renderer.root.findAllByType('summary').filter(node => text(node).includes(label));
  return Object.fromEntries(summaries.map(summary => {
    const detail = summary.parent;
    assert.equal(detail.type, 'details');
    const fields = detail.findAllByType('dt').map(term => {
      const siblings = term.parent.children;
      const value = siblings[siblings.indexOf(term) + 1];
      assert.equal(value.type, 'dd');
      return [text(term), text(value)];
    });
    return [text(summary), Object.fromEntries(fields)];
  }));
}

const revocationHistoryDetails = () => historyDetails('作废记录');

test('superseded history identifies each immediate successor even after that replacement is superseded or revoked', async () => {
  const first = signedReadback('revoke', 'superseded', priorRevision);
  const middle = signedReadback('sign', 'superseded', frozenRevision(ids.revision, 5));
  const lastRevision = frozenRevision('3708b584-295b-4691-a6b4-6422cf410010', 9);
  const last = {...signedReadback('sign', 'revoked', lastRevision).signature, id:'3708b584-295b-4691-a6b4-6422cf410011'};
  handler = async () => response(data({
    plan:{id:ids.plan, head_revision_id:lastRevision.id, active_signature_id:null},
    signatures:[middle.signature, last, first.signature],
    revisions:[lastRevision, first.revision, middle.revision],
    events:[
      {...middle.terminal_event, successor_signature_id:last.id},
      {event:'revoked', signature_id:last.id, reason:'末版已作废'},
      {...first.terminal_event, successor_signature_id:middle.signature.id},
    ],
  }));
  await mount();
  assert.deepEqual(historyDetails('替代记录'), {
    '查看版本 1 的替代记录': {'接替版本':'版本 5'},
    '查看版本 5 的替代记录': {'接替版本':'版本 9'},
  });
  assert.equal(revocationHistoryDetails()['查看版本 9 的作废记录']['作废原因'], '末版已作废');
  assert.equal(renderer.root.findAllByProps({'aria-label':'当前有效签署'}).length, 0);
  assert.deepEqual(requests.map(r => r.options.method), ['GET']);
});

test('incomplete or self-referential replacement history cannot borrow a current version or lose its original row', async () => {
  const signed = signedReadback('sign', 'superseded');
  const aggregate = signatureAggregate(signed);
  const [event] = aggregate.events;
  const [original, replacement] = aggregate.signatures;
  handler = async () => response(aggregate);
  await mount();
  const missing = {'查看版本 2 的替代记录': {'接替版本':'未提供'}};
  for (const reference of [{}, {successor_signature_id:null}, {successor_signature_id:'missing'}, {successor_signature_id:original.id}]) {
    aggregate.events = [{event:'superseded', signature_id:original.id, ...reference}];
    await click('重新读取治疗记录');
    assert.deepEqual(historyDetails('替代记录'), missing);
  }
  aggregate.events = [event];
  aggregate.revisions = [signed.revision];
  await click('重新读取治疗记录');
  assert.deepEqual(historyDetails('替代记录'), missing);
  aggregate.revisions = [frozenRevision(replacement.revision_id, 3)];
  await click('重新读取治疗记录');
  assert.deepEqual(historyDetails('替代记录'), {'查看替代记录': {'接替版本':'版本 3'}});
  assert.deepEqual(requests.map(r => r.options.method), Array(7).fill('GET'));
});

test('revoked versions display their own event actor, time and original reason in read-only history', async () => {
  const first = signedReadback('revoke', 'revoked', priorRevision);
  const second = signedReadback('sign', 'revoked', rev);
  const event1 = {...first.terminal_event, actor_id:7, created_at:'2026-11-10T13:57:13+08:00', reason:'前一版本的原因'};
  const event2 = {...second.terminal_event, id:'3708b584-295b-4691-a6b4-6422cf410099', actor_id:11,
    created_at:'2026-11-11T14:07:33.123456+08:00', reason:' 甲 <乙> & café 🐾\n{{第二行}} \\n  '};
  handler = async () => response(data({
    actor_id:5, signatures:[first.signature, second.signature], revisions:[rev, priorRevision], events:[event2, event1],
  }));
  await mount();
  assert.deepEqual(revocationHistoryDetails(), {
    '查看版本 1 的作废记录': {'作废账号 ID':'7', '作废时间':event1.created_at, '作废原因':event1.reason},
    '查看版本 2 的作废记录': {'作废账号 ID':'11', '作废时间':event2.created_at, '作废原因':event2.reason},
  });
  assert.deepEqual(requests.map(r => r.options.method), ['GET']);
  handler = async () => response({detail:'无权读取'}, 403);
  await click('重新读取治疗记录');
  assert.deepEqual(revocationHistoryDetails(), {});
  assert.doesNotMatch(output(), /前一版本的原因/);
});

test('incomplete revocation events do not borrow the original signer, signing time or a synthetic reason', async () => {
  const signed = signedReadback('sign','revoked');
  const aggregate = signatureAggregate(signed);
  aggregate.events = [{id:ids.event, signature_id:signed.signature.id, event:'revoked'}];
  handler = async () => response(aggregate);
  await mount();
  assert.deepEqual(revocationHistoryDetails(), {
    '查看版本 2 的作废记录': {'作废账号 ID':'未提供','作废时间':'未提供','作废原因':'未提供'},
  });
});

function assertSignatureAwaitingRead() {
  assert.equal(renderer.root.findAllByProps({'aria-label':'当前有效签署'}).length, 0);
  assert.equal(renderer.root.findAllByProps({'aria-label':'独立回读签署'}).length, 0);
  assert.equal(historyRows().length, 1);
  assert.match(historyRows()[0], / · 状态待核对 · 院内账号确认$/);
}

function assertLatestSignatureHistory(state) {
  const active = renderer.root.findAllByProps({'aria-label':'当前有效签署'});
  const rows = historyRows();
  if (state === 'revoked') {
    assert.equal(active.length, 0);
    assert.equal(rows.length, 1);
    assert.match(rows[0], /^版本 2 · .* · 已作废 · 院内账号确认$/);
  } else {
    assert.equal(active.length, 1);
    assert.match(directText(active[0].findByType('h3')), /版本 3/);
    assert.equal(rows.length, 2);
    assert.ok(rows.some(row => /^版本 2 · .* · 已由新签署替代 · 院内账号确认$/.test(row)));
    assert.ok(rows.some(row => /^版本 3 · .* · 有效 · 院内账号确认$/.test(row)));
    assert.deepEqual(revocationHistoryDetails(), {});
  }
}

for (const state of ['revoked', 'superseded']) {
  test('manual refresh retires the old independent readback when another clinician changes it to ' + state, async () => {
    const readback = signedReadback();
    const latest = signedReadback('sign', state);
    latest.terminal_event.actor_id = 2;
    const key = 'a'.repeat(64);
    saved.set('pmai:treatment:1:' + scope.org_id + ':' + scope.clinic_id + ':1',
      JSON.stringify({key, operation:'sign', request_hash:'b'.repeat(64)}));
    handler = async url => {
      if (url.includes('/commands/')) return receipt(signResult(), 201);
      if (url.endsWith('/signatures/' + ids.signature)) return response(readback);
      return response(signatureAggregate(readback));
    };
    await mount();
    await click('查询原请求');
    assertVerifiedSignature(readback);
    const before = requests.length;
    let finish, refresh;
    handler = () => new Promise(resolve => { finish = resolve; });
    await act(async () => { refresh = button('重新读取治疗记录').props.onClick(); });
    assertSignatureAwaitingRead();
    await act(async () => { finish(response(signatureAggregate(latest))); await refresh; });
    assertLatestSignatureHistory(state);
    assert.equal(renderer.root.findAllByProps({'aria-label':'独立回读签署'}).length, 0);
    assert.deepEqual(requests.slice(before).map(r => [r.options.method, r.url.split('/cases/1/')[1]]), [['GET', 'treatment']]);
    assert.ok(requests.every(r => r.options.method === 'GET'));
    assert.equal(saved.size, 0);
  });
}

for (const [failure, next] of [['503', 'effective'], ['disconnect', 'revoked']]) {
  test('a ' + failure + ' on refresh keeps signature actions paused until a successful reread finds ' + next, async () => {
    const signed = signedReadback();
    handler = async () => response(signatureAggregate(signed));
    await mount();
    change('操作原因', '合成复核');
    change('已核对待作废签署', null, true);
    change('签署认证密码', 'synthetic');
    assert.equal(button(revokeButton).props.disabled, false);

    handler = async () => {
      if (failure === 'disconnect') throw new TypeError('synthetic disconnect');
      return response({detail:'unavailable'}, 503);
    };
    await click('重新读取治疗记录');
    assertSignatureAwaitingRead();
    assert.match(output(), /签署状态待核对，请重新读取治疗记录。/);
    assert.equal(button('重新读取治疗记录').props.disabled, false);
    assert.equal(button('创建修订草稿'), undefined);
    assert.equal(button(revokeButton), undefined);
    assert.equal(renderer.root.findByProps({'aria-label':'签署认证密码'}).props.value, '');
    assert.equal(acknowledgement().disabled, true);
    assert.equal(renderer.root.findByType('fieldset').props.disabled, true);
    assert.equal(button('冻结版本供核对').props.disabled, true);
    await click('保存治疗草稿'); // Exercise the command guard even if a stale caller bypasses the fieldset.

    handler = async () => response(signatureAggregate(signedReadback('sign', next)));
    await click('重新读取治疗记录');
    assert.doesNotMatch(output(), /签署状态待核对/);
    if (next === 'revoked') {
      assertLatestSignatureHistory('revoked');
      assert.equal(button(revokeButton), undefined);
    } else {
      assert.equal(renderer.root.findAllByProps({'aria-label':'当前有效签署'}).length, 1);
      assert.match(historyRows()[0], / · 有效 · 院内账号确认$/);
      assert.equal(renderer.root.findByProps({'aria-label':'已核对待作废签署'}).props.checked, false);
      assert.equal(button(revokeButton).props.disabled, true);
      change('操作原因', '重新核对');
      change('已核对待作废签署', null, true);
      change('签署认证密码', 'synthetic');
      assert.equal(button(revokeButton).props.disabled, false);
    }
    assert.deepEqual(requests.map(r => [r.options.method, r.url.split('/cases/1/')[1]]), [
      ['GET','treatment'], ['GET','treatment'], ['GET','treatment'],
    ]);
    assert.equal(saved.size, 0);
  });
}

for (const state of ['revoked', 'superseded', 'missing', 'inactive pointer', 'revoked with active pointer', 'missing with active pointer']) {
  test('sign receipt completes without displaying stale effective state when latest aggregate is ' + state, async () => {
    handler = async () => response(data({reviews:reviewedTreatment().reviews}));
    await mount();
    change('已核对冻结版本', null, true);
    change('签署认证密码', 'synthetic-password');
    assert.equal(button(signButton).props.disabled, false);
    const effective = signedReadback();
    let latest = data();
    if (state === 'inactive pointer') {
      latest = signatureAggregate(effective);
      latest.plan.active_signature_id = null;
    } else if (state === 'revoked with active pointer') {
      latest = signatureAggregate(signedReadback('sign', 'revoked'));
      latest.plan.active_signature_id = effective.signature.id;
    } else if (state === 'missing with active pointer') {
      latest.plan.active_signature_id = effective.signature.id;
    } else if (state !== 'missing') {
      const record = signedReadback('sign', state);
      record.terminal_event.actor_id = 2;
      latest = signatureAggregate(record);
    }
    handler = async (url, options) => {
      if (url.endsWith('/auth/reauthenticate')) return response({challenge_id:'synthetic-challenge'});
      if (options.method === 'POST') return receipt(signResult(), 201);
      return response(url.endsWith('/signatures/' + ids.signature) ? effective : latest);
    };
    const before = requests.length;
    await click(signButton);
    assert.deepEqual(requests.slice(before).map(r => [r.options.method, r.url.replace(/^.*\/cases\/1\/|^.*\/api\/v2\//,'')]), [
      ['POST','auth/reauthenticate'], ['POST','treatment/revisions/' + rev.id + '/signatures'],
      ['GET','treatment/signatures/' + ids.signature], ['GET','treatment'],
    ]);
    assert.equal(saved.size, 0);
    assert.doesNotMatch(output(), /待核对请求/);
    if (state === 'revoked' || state === 'superseded') {
      assertLatestSignatureHistory(state);
    } else {
      assert.equal(renderer.root.findAllByProps({'aria-label':'当前有效签署'}).length, 0);
      assert.equal(button(revokeButton), undefined);
      assert.equal(button('创建修订草稿'), undefined);
      const rows = historyRows();
      if (state === 'inactive pointer' || state === 'revoked with active pointer') {
        assert.equal(rows.length, 1);
        assert.match(rows[0], /^版本 2 · .* · 状态待核对 · 院内账号确认$/);
        assert.deepEqual(revocationHistoryDetails(), {});
      } else {
        assert.deepEqual(rows, []);
      }
      if (state !== 'missing') {
        assert.equal(renderer.root.findByType('fieldset').props.disabled, true);
        assert.equal(button('冻结版本供核对').props.disabled, true);
        assert.match(output(), /状态待核对/);
      }
    }
    assert.match(output(), /最新治疗记录未确认同一签署状态/);
    assert.equal(renderer.root.findAllByProps({'aria-label':'独立回读签署'}).length, 0);
  });
}

test('read-only treatment content after expiry preserves untouched codes and removes coding from a renamed row', async () => {
  const draft = displayContent('失效前原文');
  handler = async () => response(data({draft: {draft_version:1, content:draft}}));
  await mount();
  const renamed = '新名称\n不继承编码 \\n ';
  change('治疗诊断 2', renamed);
  change('治疗目标 3', '本页修改\n\n');
  handler = async () => response({code:'SESSION_EXPIRED'}, 401);
  await click('重新读取治疗记录');
  const expired = renderer.root.findAllByType('h3').find(h => h.children.join('') === '未保存原文 · 只读保留').parent;
  assertContentView(expired, {...draft,
    diagnoses: draft.diagnoses.map((row, index) => index === 1 ? {label:renamed} : row),
    treatment: {...draft.treatment, goals:draft.treatment.goals.map((goal, index) => index === 2 ? '本页修改\n\n' : goal)},
  });
  assert.equal(renderer.root.findAllByType('textarea').length, 0);
  assert.equal(button(signButton), undefined);
  assert.deepEqual(requests.map(r => r.options.method), ['GET', 'GET']);
});

test('read-only treatment content keeps the final line break available to native selection after expiry', async () => {
  await mount();
  const diagnoses = '原文 {{诊断}}\n第二项\n\n';
  const goals = '原文 {{目标}}\n字面量 \\n';
  change('治疗诊断', diagnoses);
  change('治疗目标', goals);
  handler = async () => response({code:'SESSION_EXPIRED'}, 401);
  await click('重新读取治疗记录');
  const values = renderer.root.findAllByType('dd');
  const diagnosisValue = values.find(node => directText(node) === diagnoses);
  const goalValue = values.find(node => directText(node) === goals);
  assert.ok(diagnosisValue && goalValue, 'the original textarea values must remain verbatim');
  const tail = diagnosisValue.children.at(-1);
  assert.equal(tail.type, 'br', 'keep the trailing empty line selectable without adding text');
  assert.equal(String(tail.props['aria-hidden']), 'true');
  assert.equal(goalValue.findAllByType('br').length, 0);
  assert.deepEqual(requests.map(r => r.options.method), ['GET', 'GET']);
});

function reviewedTreatment() {
  const prior = priorRevision;
  const active = signedReadback('revoke', 'effective').signature;
  return data({
    plan: { id:ids.plan, head_revision_id:rev.id, active_signature_id:active.id },
    revisions: [{ ...rev, revision_no:2, amendment_of:active.id }, prior], signatures:[active],
    draft: { draft_version:1, amendment_of:active.id, content },
    reviews: [{ id:ids.review, revision_id:rev.id, decision:'approve', clinician_snapshot:{ display_name:'合成医生' } }],
  });
}
function acknowledgeTreatment(password) {
  change('已核对冻结版本', null, true);
  change('操作原因', '合成复核');
  change('已核对待作废签署', null, true);
  change('签署认证密码', password);
}

test('a revocation requires a nonblank reason to acknowledge and withdrawing that acknowledgement clears the password', async () => {
  handler = async () => response(reviewedTreatment());
  await mount();
  const revokeCheck = () => renderer.root.findByProps({'aria-label':'已核对待作废签署'}).props;
  assert.equal(revokeCheck().disabled, true);
  change('操作原因', '   ');
  assert.equal(revokeCheck().disabled, true);
  change('操作原因', '合成复核');
  assert.equal(revokeCheck().disabled, false);
  change('已核对待作废签署', null, true);
  change('签署认证密码', 'synthetic');
  assert.equal(button(revokeButton).props.disabled, false);
  change('已核对待作废签署', null, false);
  assert.equal(renderer.root.findByProps({'aria-label':'签署认证密码'}).props.value, '');
  assert.equal(renderer.root.findByProps({'aria-label':'操作原因'}).props.value, '合成复核');
  change('已核对待作废签署', null, true);
  assert.equal(button(revokeButton).props.disabled, true);
  assert.deepEqual(requests.map(r => r.options.method), ['GET']);
});

test('editing the exact acknowledged reason invalidates revocation even if the original text is restored', async () => {
  handler = async () => response(reviewedTreatment());
  await mount();
  acknowledgeTreatment('synthetic');
  assert.equal(button(revokeButton).props.disabled, false);
  change('操作原因', '合成复核 ');
  assert.equal(renderer.root.findByProps({'aria-label':'已核对待作废签署'}).props.checked, false);
  assert.equal(renderer.root.findByProps({'aria-label':'签署认证密码'}).props.value, '');
  assert.equal(button(revokeButton).props.disabled, true);
  assert.equal(acknowledgement().checked, true);
  change('操作原因', '合成复核');
  change('签署认证密码', 'synthetic');
  assert.equal(button(revokeButton).props.disabled, true);
  change('已核对待作废签署', null, true);
  assert.equal(button(revokeButton).props.disabled, false);
  assert.deepEqual(requests.map(r => r.options.method), ['GET']);
  assert.equal(saved.size, 0);
});

for (const [action, label, target] of [
  ['sign', signButton, '/treatment/revisions/' + rev.id + '/signatures'],
  ['revoke', revokeButton, '/treatment/signatures/' + ids.priorSignature + '/revocations'],
]) {
  test('wrong reauthentication password permits explicit retry for ' + action, async t => {
    const original = reviewedTreatment();
    handler = async () => response(original);
    await mount();
    const random = t.mock.method(globalThis.crypto, 'getRandomValues');
    acknowledgeTreatment('incorrect-password');
    handler = async () => response({code:'REAUTHENTICATION_FAILED'}, 401);
    const start = requests.length;
    await click(label);
    assert.deepEqual(requests.slice(start).map(r => r.url), ['/api/v2/auth/reauthenticate']);
    assert.equal(JSON.parse(requests.at(-1).options.body).action, action);
    assert.equal(requests.at(-1).options.headers['Idempotency-Key'], undefined);
    assert.equal(random.mock.callCount(), 0);
    assert.equal(saved.size, 0);
    assert.match(output(), new RegExp(reauthMessage));
    assert.doesNotMatch(output(), /未保存原文 · 只读保留|待核对请求|已独立回读签署|incorrect-password/);
    for (const title of ['已核对冻结版本', '已核对待作废签署']) {
      assert.equal(renderer.root.findByProps({'aria-label':title}).props.checked, false);
    }
    assert.equal(renderer.root.findByProps({'aria-label':'签署认证密码'}).props.value, '');
    assert.equal(renderer.root.findByProps({'aria-label':'治疗评估'}).props.value, content.assessment);
    assert.equal(button(label).props.disabled, true);

    const readback = signedReadback(action);
    const signature = readback.signature;
    const signatureId = signature.id;
    const final = { ...original, plan:{...original.plan, active_signature_id:action === 'sign' ? signatureId : null},
      signatures: action === 'sign' ? [...original.signatures, signature] : original.signatures,
      events:[{signature_id:ids.priorSignature, event:action === 'sign' ? 'superseded' : 'revoked'}] };
    handler = async (url, options) => {
      if (url.endsWith('/auth/reauthenticate')) return response({challenge_id:'fresh-proof'});
      if (url.endsWith(target)) {
        assert.equal(JSON.parse(options.body).challenge_id, 'fresh-proof');
        assert.match(options.headers['Idempotency-Key'], /^[a-f0-9]{64}$/);
        return receipt(action === 'sign' ? signResult() : {state:'committed', signature_id:signatureId, event_id:ids.event}, 201);
      }
      if (url.endsWith('/treatment/signatures/' + signatureId)) {
        return response(readback);
      }
      return response(final);
    };
    change('签署认证密码', 'correct-password');
    assert.equal(button(label).props.disabled, true);
    change(action === 'sign' ? '已核对冻结版本' : '已核对待作废签署', null, true);
    assert.equal(button(label).props.disabled, false);
    const retry = requests.length;
    await click(label);
    assert.deepEqual(requests.slice(retry).map(r => [r.options.method, r.url]), [
      ['POST','/api/v2/auth/reauthenticate'],
      ['POST','/api/v2/organizations/' + scope.org_id + '/clinics/' + scope.clinic_id + '/cases/1' + target],
      ['GET','/api/v2/organizations/' + scope.org_id + '/clinics/' + scope.clinic_id + '/cases/1/treatment/signatures/' + signatureId],
      ['GET','/api/v2/organizations/' + scope.org_id + '/clinics/' + scope.clinic_id + '/cases/1/treatment'],
    ]);
    assertVerifiedSignature(readback);
    assert.equal(saved.size, 0);
  });
}

for (const [kind, denied] of [
  ['expired session', () => response({code:'SESSION_EXPIRED'}, 401)],
  ['generic denial', () => response({detail:'credentials expired'}, 401)],
  ['non-JSON denial', () => ({ok:false, status:401, json:async () => { throw new SyntaxError('not JSON'); }})],
  ['receipt-shaped denial', () => response({state:'committed', challenge_id:'untrusted-proof'}, 401)],
  ['contradictory denial', () => response({code:'REAUTHENTICATION_FAILED', state:'failed'}, 401)],
]) {
  test('reauthentication fails closed for ' + kind, async () => {
    handler = async () => response(reviewedTreatment());
    await mount(); acknowledgeTreatment('synthetic-password');
    handler = denied;
    const start = requests.length;
    await click(signButton);
    assert.deepEqual(requests.slice(start).map(r => r.url), ['/api/v2/auth/reauthenticate']);
    assert.match(output(), /未保存原文 · 只读保留/);
    assert.match(output(), /重新登录，再打开本病例/);
    assert.doesNotMatch(output(), /再次认证未通过|再查询原请求|synthetic-password/);
    assert.equal(saved.size, 0);
  });
}

test('an invalid or unsuccessful challenge cannot start a treatment command', async () => {
  handler = async () => response(reviewedTreatment());
  await mount();
  for (const result of [response({}), response({challenge_id:'  '}),
    response({state:'pending', challenge_id:'untrusted'}, 202), response({state:'committed', challenge_id:'untrusted'}, 200),
    response({state:'committed', challenge_id:'untrusted'}, 409)]) {
    acknowledgeTreatment('password');
    handler = async () => result;
    const start = requests.length;
    await click(signButton);
    assert.deepEqual(requests.slice(start).map(r => r.url), ['/api/v2/auth/reauthenticate']);
    assert.equal(saved.size, 0);
    assert.equal(button(signButton).props.disabled, true);
  }
});

test('the reauthentication rejection code on a business command still expires the session', async () => {
  handler = async () => response(reviewedTreatment());
  await mount(); acknowledgeTreatment('password');
  handler = async url => url.endsWith('/auth/reauthenticate')
    ? response({challenge_id:'fresh-proof'}) : response({code:'REAUTHENTICATION_FAILED'}, 401);
  await click(signButton);
  assert.match(output(), /未保存原文 · 只读保留/);
  assert.doesNotMatch(output(), /再次认证未通过/);
  assert.match(output(), /同一账号重新登录，再查询原请求/);
  assert.equal(saved.size, 1); // The command was already attempted with this key.
});

test('a late wrong-password response cannot affect the clinician now viewing a different case', async () => {
  handler = async () => response(reviewedTreatment());
  await mount(); acknowledgeTreatment('old-case-password');
  let release, pending;
  handler = () => new Promise(resolve => { release = resolve; });
  act(() => { pending = button(signButton).props.onClick(); });
  handler = async () => response(reviewedTreatment());
  await act(async () => { renderer.update(<TreatmentWorkspace token="synthetic-token" scope={scope} caseId={2} />); });
  acknowledgeTreatment('new-case-password');
  await act(async () => { release(response({code:'REAUTHENTICATION_FAILED'}, 401)); await pending; });
  assert.equal(renderer.root.findByProps({'aria-label':'签署认证密码'}).props.value, 'new-case-password');
  assert.equal(button(signButton).props.disabled, false);
  assert.doesNotMatch(output(), /再次认证未通过|未保存原文 · 只读保留/);
  assert.equal(saved.size, 0);
});

const queryButton = '查询原请求';
const cancelButton = '取消原请求';
function assertUnconfirmed(original) {
  assert.deepEqual(pendingCommand(), original);
  assert.equal(button(queryButton).props.disabled, false);
  assert.equal(renderer.root.findByType('fieldset').props.disabled, true);
  assert.doesNotMatch(output(), /已独立回读签署|已从服务端核对保存结果/);
}
async function startDraft(commandResponse) {
  await mount();
  change('治疗评估', '待核实的原文 🐾');
  let original;
  handler = async (_url, options) => {
    if (options.method === 'PATCH') {
      original = pendingCommand();
      return commandResponse();
    }
    return response(storedDraft(2, '待核实的原文 🐾'));
  };
  await click('保存治疗草稿');
  assert.equal(draftWrites()[0].options.headers['Idempotency-Key'], original.key);
  return original;
}
async function finishOriginalDraft(original) {
  const start = requests.length;
  handler = async url => url.includes('/commands/') ? receipt(draftResult(2), 201) : response(storedDraft(2, '待核实的原文 🐾'));
  await click(queryButton);
  assert.deepEqual(requests.slice(start).map(r => [r.options.method, r.url.split('/cases/1/')[1]]), [
    ['GET', 'commands/' + original.key + '?operation=draft.save'], ['GET', 'treatment'],
  ]);
  assert.equal(draftWrites().length, 1);
  assert.equal(saved.size, 0);
  assert.equal(assessment(), '待核实的原文 🐾');
  assert.match(output(), /已从服务端核对保存结果/);
}
for (const [problem, invalid] of [
  ['response without a state', () => response({draft_version:2}, 201)],
  ['unrecognized state', () => receipt({state:'complete'}, 201)],
  ['missing command bindings', () => response(draftResult(2), 201)],
  ['different original key', () => receipt({...draftResult(2), idempotency_key:'c'.repeat(64)}, 201)],
  ['different operation', () => receipt({...draftResult(2), operation:'amend'}, 201)],
  ['different payload hash', () => receipt({...draftResult(2), request_hash:'0'.repeat(64)}, 201)],
  ['committed receipt on error status', () => receipt(draftResult(2), 409)],
  ['inconsistent saved version and ETag', () => receipt({...draftResult(2), draft_version:3}, 201)],
  ['missing committed plan ETag', () => receipt({...draftResult(2), etag:undefined}, 201)],
  ['invalid committed plan ETag', () => receipt({...draftResult(2), etag:'"plan:0"'}, 201)],
  ['missing committed plan ID', () => receipt({...draftResult(2), plan_id:undefined}, 201)],
  ['invalid committed audit ID', () => receipt({...draftResult(2), audit_id:'another-audit'}, 201)],
  ['unbound terminal failure', () => response({state:'failed', code:'VERSION_MISMATCH'}, 412)],
]) {
  test('a draft command with ' + problem + ' keeps its original key until verified lookup', async () => {
    const original = await startDraft(invalid);
    assertUnconfirmed(original);
    assert.equal(requests.filter(r => r.options.method === 'GET').length, 1, 'an invalid receipt must not start a readback');
    await finishOriginalDraft(original);
  });
}

test('lookup and cancellation keep an unresolved original key across malformed responses', async () => {
  const original = await startDraft(() => receipt({state:'pending'}, 202));
  for (const [label, reply] of [
    [queryButton, response({state:'not_observed', idempotency_key:original.key, operation:original.operation}, 202)],
    [queryButton, receipt({state:'cancelled', code:'COMMAND_CANCELLED', request_hash:'f'.repeat(64)}, 409)],
    [cancelButton, receipt({state:'cancelled', code:'COMMAND_CANCELLED', operation:'review'}, 409)],
  ]) {
    handler = async () => reply;
    await click(label);
    assertUnconfirmed(original);
    const {url, options} = requests.at(-1);
    if (label === cancelButton) {
      assert.ok(url.endsWith('/commands/' + original.key + '/cancel'));
      assert.equal(options.method, 'POST');
      const body = JSON.parse(options.body);
      assert.equal(body.request_hash, original.request_hash); assert.equal(body.operation, original.operation);
    } else {
      assert.ok(url.endsWith('/commands/' + original.key + '?operation=draft.save'));
      assert.equal(options.method, 'GET');
    }
  }
  await finishOriginalDraft(original);
});

test('a verified cancellation retires only the pending command and preserves unsaved draft text', async () => {
  const original = await startDraft(() => receipt({state:'pending'}, 202));
  handler = async url => url.endsWith('/cancel') ? receipt({state:'cancelled', code:'COMMAND_CANCELLED'}, 409) : response(data());
  await click(cancelButton);
  assert.ok(requests.some(r => r.url.endsWith('/commands/' + original.key + '/cancel')));
  assert.equal(draftWrites().length, 1); assert.equal(saved.size, 0);
  assert.equal(assessment(), '待核实的原文 🐾');
  assert.match(output(), /原请求已取消/); assert.doesNotMatch(output(), /已从服务端核对保存结果/);
});

for (const [problem, receiptChanges, modifyReadback] of [
  ['committed sign receipt without signature ID', {signature_id:undefined}],
  ['committed sign receipt with an invalid signature ID', {signature_id:'another/scope'}],
  ['independent GET receives a different signature', {}, body => { body.signature.id = ids.priorSignature; }],
  ['independent GET returns a different case', {}, body => { body.signature.case_id = 2; }],
  ['independent GET returns a different plan', {}, body => { body.revision.plan_id = ids.audit; }],
  ['independent GET returns a different signer', {}, body => { body.signature.signer_id = 2; }],
  ['independent GET returns other frozen text', {}, body => { body.revision.content.assessment = '错误回读原文'; }],
  ['independent GET returns changed canonical bytes', {}, body => { body.revision.canonical_utf8 += ' '; }],
  ['independent GET contradicts the terminal event', {}, body => { body.state = 'revoked'; }],
]) {
  test('signature reconciliation rejects ' + problem + ' and later verifies the same original command', async () => {
    const initial = reviewedTreatment();
    handler = async () => response(initial);
    await mount(); acknowledgeTreatment('test-password');
    let original;
    handler = async (url, options) => {
      if (url.endsWith('/reauthenticate')) return response({challenge_id:'fresh-proof'});
      if (options.method === 'POST') {
        original = pendingCommand();
        return receipt({...signResult(), ...receiptChanges}, 201);
      }
      if (url.endsWith('/treatment')) return response(initial);
      const readback = structuredClone(signedReadback());
      if (modifyReadback) modifyReadback(readback);
      return response(readback);
    };
    await click(signButton);
    assertUnconfirmed(original);
    assert.doesNotMatch(output(), /错误回读原文/);
    assert.equal(requests.filter(r => r.options.method === 'GET' && r.url.includes('/treatment/signatures/')).length, modifyReadback ? 1 : 0);
    const start = requests.length;
    const verified = signedReadback('sign', 'superseded');
    verified.terminal_event.successor_signature_id = ids.priorSignature;
    handler = async url => url.includes('/commands/') ? receipt(signResult(), 201)
      : response(url.endsWith('/treatment/signatures/' + ids.signature) ? verified : signatureAggregate(verified));
    await click(queryButton);
    assert.deepEqual(requests.slice(start).map(r => [r.options.method, r.url.split('/cases/1/')[1]]), [
      ['GET', 'commands/' + original.key + '?operation=sign'], ['GET', 'treatment/signatures/' + ids.signature], ['GET', 'treatment'],
    ]);
    assert.equal(saved.size, 0); assertVerifiedSignature(verified);
    assert.equal(requests.filter(r => r.options.method === 'POST' && r.url.endsWith('/signatures')).length, 1);
  });
}

test('recovering a revocation requires the original terminal event, even when the signature is already revoked', async () => {
  const key = '1'.repeat(64), original = {key, operation:'revoke', request_hash:'2'.repeat(64)};
  saved.set(`pmai:treatment:1:${scope.org_id}:${scope.clinic_id}:1`, JSON.stringify(original));
  const initial = reviewedTreatment();
  handler = async () => response(initial); await mount();
  const result = {state:'committed', signature_id:ids.priorSignature, event_id:ids.event};
  for (const invalid of ['event', 'actor', 'state', null]) {
    const body = signedReadback('revoke');
    if (invalid === 'event') body.terminal_event.id = ids.audit;
    if (invalid === 'actor') body.terminal_event.actor_id = 2;
    if (invalid === 'state') { body.state = 'effective'; body.terminal_event = null; }
    handler = async url => url.includes('/commands/') ? receipt(result, 201)
      : response(url.endsWith('/treatment/signatures/' + ids.priorSignature) ? body : signatureAggregate(body));
    await click(queryButton);
    if (invalid) assertUnconfirmed(original);
  }
  assert.equal(saved.size, 0); assertVerifiedSignature(signedReadback('revoke'));
  assert.equal(requests.filter(r => r.options.method !== 'GET').length, 0);
});

for (const [operation, result, missing] of [
  ['revision.freeze', {revision_id:rev.id, content_hash:rev.content_sha256}, 'content_hash'],
  ['review', {review_id:ids.review, revision_id:rev.id, decision:'approve'}, 'decision'],
  ['amend', {base_signature_id:ids.priorSignature, draft_version:2}, 'base_signature_id'],
]) {
  test('recovering ' + operation + ' requires its committed outcome before clearing the original request', async () => {
    const original = {key:'a'.repeat(64), operation, request_hash:'c'.repeat(64)};
    saved.set(`pmai:treatment:1:${scope.org_id}:${scope.clinic_id}:1`, JSON.stringify(original));
    await mount();
    const incomplete = {...result};
    delete incomplete[missing];
    handler = async url => url.includes('/commands/') ? receipt({...incomplete, state:'committed'}, 201) : response(data());
    await click(queryButton);
    assertUnconfirmed(original);
    handler = async url => url.includes('/commands/') ? receipt({...result, state:'committed'}, 201) : response(data());
    await click(queryButton);
    assert.equal(saved.size, 0);
    assert.match(output(), /已从服务端核对保存结果/);
    assert.ok(requests.every(r => r.options.method === 'GET'));
    assert.ok(requests.filter(r => r.url.includes('/commands/')).every(r => r.url.endsWith('/' + original.key + '?operation=' + operation)));
  });
}

test('a verified signature stays unconfirmed until its aggregate reread succeeds', async () => {
  const original = {key:'a'.repeat(64), operation:'sign', request_hash:'c'.repeat(64)};
  saved.set(`pmai:treatment:1:${scope.org_id}:${scope.clinic_id}:1`, JSON.stringify(original));
  const initial = reviewedTreatment();
  handler = async () => response(initial);
  await mount();
  let notifyAggregate, releaseAggregate, checking;
  const waiting = new Promise(resolve => { notifyAggregate = resolve; });
  handler = async url => {
    if (url.includes('/commands/')) return receipt(signResult(), 201);
    if (url.endsWith('/treatment/signatures/' + ids.signature)) return response(signedReadback());
    notifyAggregate();
    return new Promise(resolve => { releaseAggregate = resolve; });
  };
  await act(async () => { checking = button(queryButton).props.onClick(); await waiting; });
  assert.deepEqual(pendingCommand(), original);
  assert.doesNotMatch(output(), /已独立回读签署|已从服务端核对保存结果/);
  await act(async () => { releaseAggregate(response({detail:'unavailable'}, 503)); await checking; });
  assertUnconfirmed(original);
  assertSignatureAwaitingRead();
  assert.equal(button(cancelButton).props.disabled, false);
  handler = async url => url.includes('/commands/') ? receipt(signResult(), 201)
    : response(url.endsWith('/treatment') ? signatureAggregate(signedReadback()) : signedReadback());
  await click(queryButton);
  assert.equal(saved.size, 0); assertVerifiedSignature(signedReadback());
  assert.ok(requests.every(r => r.options.method === 'GET'));
});

for (const [problem, operation, label, altered] of [
  ['a different reviewed revision', 'review', '审核通过', {revision_id:ids.priorRevision}],
  ['a different review decision', 'review', '审核通过', {decision:'reject'}],
  ['a different amendment base', 'amend', '创建修订草稿', {base_signature_id:ids.signature}],
]) {
  test('direct response for ' + problem + ' keeps the submitted command available for query', async () => {
    const initial = operation === 'review' ? data() : reviewedTreatment();
    if (operation === 'amend') initial.draft.amendment_of = null;
    handler = async () => response(initial);
    await mount();
    change('已核对冻结版本', null, true); change('操作原因', '已核对本次范围');
    const result = operation === 'review'
      ? {review_id:ids.review, revision_id:rev.id, decision:'approve'}
      : {base_signature_id:ids.priorSignature, draft_version:2};
    let original;
    handler = async (_url, options) => {
      if (options.method === 'GET') return response(initial);
      original = pendingCommand();
      return receipt({...result, ...altered, state:'committed'}, 201);
    };
    assert.equal(!!button(label).props.disabled, false);
    await click(label);
    assertUnconfirmed(original);
    handler = async url => url.includes('/commands/') ? receipt({...result, state:'committed'}, 201) : response(initial);
    await click(queryButton);
    assert.equal(saved.size, 0); assert.match(output(), /已从服务端核对保存结果/);
    assert.equal(requests.filter(r => r.options.method !== 'GET').length, 1);
  });
}
