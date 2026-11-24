import React from 'react';
import TestRenderer, { act } from 'react-test-renderer';
import { test, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import TreatmentWorkspace from '../src/pages/TreatmentWorkspace';
let renderer, handler, requests, originalFetch, originalStorage, saved;
const scope={org_id:'11111111-1111-1111-1111-111111111111',clinic_id:'22222222-2222-2222-2222-222222222222',org_name:'合成机构',clinic_name:'合成院区'};
const content={schema:'treatment-content-v1',diagnoses:[{label:'合成诊断',code_system:null,code:null}],assessment:'café 🐾\n{{literal}} literal \\n',treatment:{goals:[],management_text:'合成治疗原文',monitoring_text:'',followup_text:''},linked_orders:[],provenance:{ai_generation_ids:[],voice_transcript_revision_ids:[]}};
const rev={id:'revision1',revision_no:1,draft_version:1,content,source_manifest:{case:{patient_name:'合成犬',clinical_epoch:1},diagnostic_reports:[]},content_sha256:'a'.repeat(64),origin:'clinical'};
function data(overrides={}) {return {actor_id:1,plan:{id:'p',lock_version:4,head_revision_id:'revision1',active_signature_id:null},etag:'"plan:4"',draft_etag:'"draft:1"',draft:{draft_version:1,content},revisions:[rev],reviews:[],signatures:[],events:[],profile:{display_name:'合成医生'},source_epoch:1,policy:{review_policy:'self_allowed',required_assurance:'account_attestation'},allowed_actions:{edit:true,review:true,sign:true},...overrides};}
const response=(body,status=200)=>({ok:status<400,status,json:async()=>body});
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
 const p=JSON.parse(value);handler=async url=>url.includes('/commands/')?response({state:'committed',operation:'draft.save',idempotency_key:p.key,request_hash:p.request_hash}):response(data());
 await click('查询原请求');assert.equal(requests.filter(r=>r.options.method==='PATCH').length,1);assert.equal(saved.size,0);assert.match(output(),/已从服务端核对保存结果/);});
test('signature success needs independent readback; lost GET keeps original key',async()=>{
 const reviewed=data({reviews:[{id:'review1',revision_id:'revision1',decision:'approve',reason:'核对',clinician_snapshot:{display_name:'合成医生'}}]});
 handler=async()=>response(reviewed);await mount();change('已核对冻结版本',null,true);change('签署认证密码','reauth-secret');
 handler=async(url,options)=>{if(url.endsWith('/auth/reauthenticate'))return response({challenge_id:'challenge1'});if(options.method==='POST')return response({state:'committed',signature_id:'sig1'},201);throw new TypeError('readback interrupted');};
 await click('再次认证并确认签署');assert.doesNotMatch(output(),/已独立回读签署|已从服务端核对保存结果/);assert.equal(saved.size,1);
 assert.equal(requests.filter(r=>r.url.endsWith('/treatment/signatures/sig1')).length,1);assert.doesNotMatch([...saved.values()].join(),/reauth-secret|challenge1|token/);});
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
 await act(async()=>{release(response({state:'committed'},201));await sending;});
 assert.equal(saved.size,1);assert.doesNotMatch(output(),/已从服务端核对保存结果/);
});
test('a saved changed draft blocks signing its previous frozen version',async()=>{
 handler=async()=>response(data({draft:{draft_version:2,content}}));await mount();
 assert.match(output(),/草稿已修改，此冻结版本不能继续审核或签署/);
 assert.equal(renderer.root.findByProps({'aria-label':'已核对冻结版本'}).props.disabled,true);
});

test('revocation has a separate acknowledgement of the effective signed version',async()=>{
 const signature={id:'sig1',revision_id:'old',content_hash:'b'.repeat(64),clinician_snapshot:{display_name:'旧签署医生'},signed_at:'2026-11-09T00:00:00Z'};
 handler=async()=>response(data({plan:{id:'p',head_revision_id:'revision1',active_signature_id:'sig1'},signatures:[signature],revisions:[rev,{...rev,id:'old',revision_no:0,content:{...content,assessment:'当前有效版本的原文'}}]}));
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
    ? response({state:'committed', draft_etag:'"draft:2"'}, 201)
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
  handler = async () => response(storedDraft(3, '最新院内草稿'));
  await click(discardDraft);
  assert.equal(assessment(), '最新院内草稿');
  assert.equal(button(discardDraft), undefined);
  assert.equal(draftWrites().length, 0);
  change('治疗评估', '以最新院内版本编辑');
  handler = async (url, options) => options.method === 'PATCH'
    ? response({state:'committed', draft_etag:'"draft:4"'}, 201)
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
    if (options.method === 'PATCH') return response({state:'failed', code:'VERSION_MISMATCH'}, 412);
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
  const [receipt] = saved.values();
  assert.doesNotMatch(receipt, /先前发送的本地草稿/);
  handler = async url => url.includes('/commands/')
    ? response({state:'committed', draft_etag:'"draft:2"'})
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
    ? response({ state: 'committed', operation: 'draft.save', draft_etag: '"draft:2"' }, 201)
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
  const values = renderer.root.findAllByType('dd').map(node => node.children.join(''));
  assert.ok(values.includes('第一项\n\n'));
  assert.ok(values.includes('保留 {{literal}} 🐾\n  \n'));
});
