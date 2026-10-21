import React from 'react';
import TestRenderer,{act} from 'react-test-renderer';
import {test,beforeEach,afterEach} from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
import CaseFollowupPlan from '../src/components/CaseFollowupPlan';
import {schema,validData,validDate,validList,validPreview,validReceipt} from '../src/followupPlan';
import api from '../src/api';
import {syntheticSessionStorage} from './syntheticSessionStorage';
import fixture from '../../tests/fixtures/clinical_followup_plans_cw_b14_cases.json';

const caseFields=['patient_name','species','sex','age_info','breed','weight','coat_color','owner_name','owner_phone','chief_complaint','history','exam_findings','analysis','treatment','prognosis'];
const animal={id:1,owner_id:1,...Object.fromEntries(caseFields.map(k=>[k,fixture.case[k]??null]))};
const empty=()=>({schema,case_id:1,case:structuredClone(animal),as_of_date:'2026-10-08',timezone:'Asia/Shanghai',plans:[],limits:{items:10,versions:50},writes_database:false,case_token:'a'.repeat(64),state_token:'b'.repeat(64)});
const plan=data=>({id:1,root_id:1,version:1,state:'planned',stored_state:'planned',token:'c'.repeat(64),data,reviewed_by:'1',reviewed_at:'2026-10-08T05:00:00+00:00',reason:'',withdrawal:null,case_snapshot:structuredClone(animal)});
const preview=(b,l)=>({schema,case_id:1,case:l.case,as_of_date:l.as_of_date,timezone:l.timezone,before:l.plans.find(p=>p.id===b.plan_id)||null,data:b.data,operation:b.operation,reason:b.reason,request_id:b.request_id,writes_database:false,case_token:b.expected_case_token,state_token:b.expected_state_token,preview_token:'d'.repeat(64)});
let renderer,requests,listeners,adapter,listing,token;
const button=label=>renderer.root.findAllByType('button').find(n=>n.children.join('')===label);
const click=async label=>act(async()=>{assert(button(label),label);await button(label).props.onClick();});
const input=label=>renderer.root.findByProps({'aria-label':label});
const change=async(label,value)=>act(async()=>input(label).props.onChange({target:{value}}));
const text=()=>JSON.stringify(renderer.toJSON());
const fire=async name=>act(async()=>{for(const f of listeners[name]||[])f({key:'token'});});
beforeEach(()=>{
  listing=empty();token='synthetic-owner';requests=[];listeners={};Object.defineProperty(globalThis,'crypto',{configurable:true,value:webcrypto});
  global.localStorage={getItem:()=>token};global.window={confirm:()=>true,addEventListener:(k,f)=>(listeners[k]??=new Set()).add(f),removeEventListener:(k,f)=>listeners[k]?.delete(f)};
  global.window.sessionStorage=syntheticSessionStorage();
  global.document={hidden:false,addEventListener:(k,f)=>(listeners[k]??=new Set()).add(f),removeEventListener:(k,f)=>listeners[k]?.delete(f)};
  adapter=async c=>{
    const b=c.data?JSON.parse(c.data):null;let data;
    if(c.url.endsWith('/preview'))data=preview(b,listing);
    else if(c.url.endsWith('/confirm')){listing={...listing,plans:[plan(b.data)]};data={schema,case_id:1,request_id:b.request_id,state:'committed',operation:b.operation,plan:listing.plans[0],writes_database:true};}
    else data=structuredClone(listing);
    return {config:c,status:200,data};
  };
  api.defaults.adapter=async c=>{requests.push(c);return adapter(c);};
});
afterEach(()=>{if(renderer)act(()=>renderer.unmount());renderer=null;});
async function mount(){await act(async()=>{renderer=TestRenderer.create(<CaseFollowupPlan caseId={1} requestToken={token}/>);});}
async function fill(){await click('新增复查计划');for(const [label,value] of [['计划复查日期',fixture.plan.planned_date],['复查目的',fixture.plan.purpose],['复查项目 1',fixture.plan.items[0]],['提前返回条件',fixture.plan.return_conditions],['复查备注',fixture.plan.note]])await change(label,value);await click('添加复查项目');await change('复查项目 2',fixture.plan.items[1]);}
async function review(){await click('预览并核对复查计划');await act(async()=>input('已核对复查计划').props.onChange({target:{checked:true}}));}

test('strict protocol validates raw Unicode, calendar, limits and chain independently',()=>{
 assert(validData(fixture.plan));assert(validDate('2000-02-29'));for(const d of fixture.invalid_dates)assert(!validDate(d),d);
 for(const changed of [{items:[]},{items:Array(11).fill('x')},{purpose:' \t'},{purpose:'x'.repeat(1001)},{note:'\x00'},{note:'\ud800'},{extra:1}])assert(!validData({...fixture.plan,...changed}));
 assert(validData({...fixture.plan,purpose:'🐾'.repeat(1000),items:Array(10).fill('x'.repeat(300))}));
 const l=empty();assert(validList(l,1));assert(!validList({...l,case_id:2},1));assert(!validList({...l,plans:[plan(fixture.plan),plan(fixture.plan)]},1));
 assert(!validList({...l,plans:[{...plan(fixture.plan),version:2}]},1));assert(!validList({...l,plans:[{...plan(fixture.plan),state:'needs_review'}]},1));
 assert(!validReceipt({schema,case_id:1,request_id:'x',state:'not_committed',writes_database:true},1,'x',true));
 const b={request_id:'f'.repeat(32),operation:'create',plan_id:null,expected_case_token:l.case_token,expected_state_token:l.state_token,data:fixture.plan,reason:''};
 const p=preview(b,l);assert(validPreview(p,l,b));assert(!validPreview({...p,data:{...p.data,note:'changed'}},l,b));
});
test('explicit review sends exact raw fields once and performs independent readback',async()=>{
 await mount();await fill();await click('预览并核对复查计划');assert(button('确认保存复查计划').props.disabled);assert.match(text(),/计划日期已过/);
 await act(async()=>input('已核对复查计划').props.onChange({target:{checked:true}}));
 await act(async()=>{const save=button('确认保存复查计划').props.onClick;await Promise.all([save(),save()]);});
 const writes=requests.filter(c=>c.url.endsWith('/confirm'));assert.equal(writes.length,1);assert.deepEqual(JSON.parse(writes[0].data).data,fixture.plan);
 assert(requests.indexOf(writes[0])<requests.length-1);assert.match(text(),/已保存并独立回读/);assert.equal(renderer.root.findAllByProps({'aria-label':'复查计划草稿'}).length,0);
});
test('field edits, refresh and focus remove old preview and never auto-write',async()=>{
 await mount();await fill();await review();await change('复查备注','更正');assert.equal(renderer.root.findAllByProps({'aria-label':'已核对复查计划'}).length,0);
 await review();await fire('focus');assert.equal(renderer.root.findAllByProps({'aria-label':'已核对复查计划'}).length,0);assert.equal(input('复查备注').props.value,'更正');
 await review();await click('刷新复查计划');assert(!button('确认保存复查计划'));assert(!requests.some(c=>c.url.endsWith('/confirm')));
});
test('lost commit reply checks request ID, preserves one write and fresh-reads before success',async()=>{
 const normal=adapter;let saved;
 adapter=async c=>{if(c.url.endsWith('/confirm')){saved=(await normal(c)).data;throw Error('reply lost');}if(c.url.includes('/requests/'))return {config:c,data:{...saved,writes_database:false}};return normal(c);};
 await mount();await fill();await review();await click('确认保存复查计划');
 assert.equal(requests.filter(c=>c.url.endsWith('/confirm')).length,1);assert.match(text(),/已核对服务端保存结果/);assert.equal(requests.at(-1).method,'get');
});
test('unreadable or wrong saved-result payload remains uncertain and locks writes',async()=>{
 const normal=adapter;let body;
 adapter=async c=>{if(c.url.endsWith('/confirm')){body=JSON.parse(c.data);throw Error('lost');}if(c.url.includes('/requests/'))return {config:c,data:{schema,case_id:1,request_id:body.request_id,state:'committed',operation:'create',plan:plan({...body.data,note:'wrong original'}),writes_database:false}};return normal(c);};
 await mount();await fill();await review();await click('确认保存复查计划');assert.match(text(),/保存结果待核对/);assert(button('预览并核对复查计划').props.disabled);
 await click('核对复查保存结果');assert.equal(requests.filter(c=>c.url.endsWith('/confirm')).length,1);assert.equal(input('复查目的').props.value,fixture.plan.purpose);
 adapter=async c=>c.url.includes('/requests/')?{config:c,data:{schema,case_id:1,request_id:body.request_id,state:'not_committed',writes_database:false}}:normal(c);
 await click('核对复查保存结果');assert.match(text(),/不会自动重发/);await review();assert.equal(JSON.parse(requests.filter(c=>c.url.endsWith('/preview')).at(-1).data).request_id,body.request_id);
});
test('late preview after focus and account switch cannot revive confirmation',async()=>{
 await mount();await fill();const normal=adapter;let resolve,arrived;const started=new Promise(r=>arrived=r);
 adapter=async c=>c.url.endsWith('/preview')?new Promise(r=>{resolve=()=>r({config:c,data:preview(JSON.parse(c.data),listing)});arrived();}):normal(c);
 let pending;await act(async()=>{pending=button('预览并核对复查计划').props.onClick();await started;});
 await fire('focus');await act(async()=>{resolve();await pending;});assert(!button('确认保存复查计划'));
 token='other';await fire('storage');assert(!button('新增复查计划'));assert(!requests.some(c=>c.url.endsWith('/confirm')));
});
test('case correction request invalidates preview before its response',async()=>{
 await mount();await fill();await review();const normal=adapter;let finish,arrive;const started=new Promise(r=>arrive=r);
 adapter=async c=>c.url==='/api/cases/1/confirm-edit'?new Promise(r=>{finish=()=>r({config:c,data:{}});arrive();}):normal(c);
 let operation;await act(async()=>{operation=api.post('/api/cases/1/confirm-edit',{});await started;});assert(!button('确认保存复查计划'));
 await act(async()=>{finish();await operation;});assert.equal(input('复查目的').props.value,fixture.plan.purpose);
});
test('malformed preview is rejected while input remains available',async()=>{
 const normal=adapter;adapter=async c=>{const r=await normal(c);if(c.url.endsWith('/preview'))r.data.data={...r.data.data,purpose:'silently changed'};return r;};
 await mount();await fill();await click('预览并核对复查计划');assert(!button('确认保存复查计划'));assert.equal(input('复查目的').props.value,fixture.plan.purpose);assert.match(text(),/预览与本次输入不一致/);
});

test('unknown plan save survives remount and same-account login without another POST',async()=>{
 const normal=adapter;let saved,offline=true;
 adapter=async c=>{if(c.url.endsWith('/confirm')){saved=(await normal(c)).data;throw Error('reply lost');}
  if(c.url.includes('/requests/')){if(offline)throw Error('offline');return {config:c,data:{...saved,writes_database:false}};}return normal(c);};
 await mount();await fill();await review();await click('确认保存复查计划');
 assert.match(text(),/保存结果待核对/);
 const raw=Array.from({length:window.sessionStorage.length},(_,i)=>window.sessionStorage.getItem(window.sessionStorage.key(i))).join('');
 assert(raw.includes(saved.request_id));assert(!raw.includes(fixture.plan.purpose));assert(!raw.includes(token));
 await act(async()=>renderer.unmount());token='same-owner-new-login';await mount();
 assert(button('核对复查保存结果'));assert(button('更正复查计划').props.disabled);
 offline=false;await click('核对复查保存结果');assert.match(text(),/已核对服务端保存结果/);
 assert.equal(requests.filter(c=>c.url.endsWith('/confirm')).length,1);assert.equal(window.sessionStorage.length,0);
});
test('a plan receipt absent from independent readback cannot unlock an unknown write',async()=>{
 const normal=adapter;let saved;
 adapter=async c=>{if(c.url.endsWith('/confirm')){saved=(await normal(c)).data;listing.plans=[];return {config:c,data:saved};}
  if(c.url.includes('/requests/'))return {config:c,data:{...saved,writes_database:false}};return normal(c);};
 await mount();await fill();await review();await click('确认保存复查计划');
 assert.match(text(),/保存结果待核对/);assert(!text().includes('已保存并独立回读'));assert(button('预览并核对复查计划').props.disabled);
 assert.equal(requests.filter(c=>c.url.endsWith('/confirm')).length,1);
});
test('unavailable recovery storage prevents the first plan POST',async()=>{
 await mount();await fill();await review();window.sessionStorage.setItem=()=>{throw Error('quota');};
 await click('确认保存复查计划');assert(!requests.some(c=>c.url.endsWith('/confirm')));assert.match(text(),/恢复标识/);
});

test('recovered not-committed result needs a fresh read and never replays a lost draft',async()=>{
 const normal=adapter;let requestId,offline=true;
 adapter=async c=>{if(c.url.endsWith('/confirm')){requestId=JSON.parse(c.data).request_id;throw Error('not sent');}
  if(c.url.includes('/requests/')){if(offline)throw Error('offline');return {config:c,data:{schema,case_id:1,request_id:requestId,state:'not_committed',writes_database:false}};}return normal(c);};
 await mount();await fill();await review();await click('确认保存复查计划');await act(async()=>renderer.unmount());await mount();
 assert(button('新增复查计划').props.disabled);assert.equal(renderer.root.findAllByProps({'aria-label':'复查计划草稿'}).length,0);
 offline=false;await click('核对复查保存结果');assert.match(text(),/原草稿未缓存/);assert.equal(requests.at(-1).method,'get');
 assert(!button('新增复查计划').props.disabled);assert.equal(window.sessionStorage.length,0);assert.equal(requests.filter(c=>c.url.endsWith('/confirm')).length,1);
});

test('malformed recovery locator stays blocked and is not silently deleted',async()=>{
 const normal=adapter;adapter=async c=>{if(c.url.endsWith('/confirm')||c.url.includes('/requests/'))throw Error('offline');return normal(c);};
 await mount();await fill();await review();await click('确认保存复查计划');
 const key=window.sessionStorage.key(0);window.sessionStorage.setItem(key,'{broken');
 await act(async()=>renderer.unmount());await mount();assert.match(text(),/恢复标识无法读取/);
 assert(button('新增复查计划').props.disabled);assert.equal(window.sessionStorage.getItem(key),'{broken');assert.equal(requests.filter(c=>c.url.endsWith('/confirm')).length,1);
});

for(const operation of ['correct','withdraw'])test(operation+' recovery binds the saved version after refresh',async()=>{
 listing.plans=[plan(fixture.plan)];const normal=adapter;let saved,offline=true;
 adapter=async c=>{
  if(c.url.endsWith('/confirm')){
   const b=JSON.parse(c.data),old=listing.plans[0];
   const row=operation==='correct'?{...old,id:2,version:2,data:b.data,reason:b.reason}:{...old,state:'withdrawn',stored_state:'withdrawn',withdrawal:{reason:b.reason,by:'1',at:'2026-10-09T05:00:00+00:00'}};
   listing.plans=operation==='correct'?[{...old,state:'superseded',stored_state:'superseded'},row]:[row];
   saved={schema,case_id:1,request_id:b.request_id,state:'committed',operation,plan:row,writes_database:false};throw Error('reply lost');
  }
  if(c.url.includes('/requests/')){if(offline)throw Error('offline');return {config:c,data:saved};}return normal(c);
 };
 await mount();await click(operation==='correct'?'更正复查计划':'撤销复查计划');await change('复查更正或撤销原因','合成原因 {{literal}}');
 await review();await click('确认保存复查计划');await act(async()=>renderer.unmount());await mount();
 assert(button('核对复查保存结果'));offline=false;await click('核对复查保存结果');assert.match(text(),/已核对服务端保存结果/);
 assert.equal(window.sessionStorage.length,0);assert.equal(requests.filter(c=>c.url.endsWith('/confirm')).length,1);
});

test('late commit after account replacement keeps only a recoverable locator',async()=>{
 const normal=adapter;let release,arrive,saved;const started=new Promise(r=>arrive=r);
 adapter=async c=>{if(c.url.endsWith('/confirm')){saved=(await normal(c)).data;return new Promise(r=>{release=()=>r({config:c,data:saved});arrive();});}
  if(c.url.includes('/requests/'))return {config:c,data:{...saved,writes_database:false}};return normal(c);};
 await mount();await fill();await review();let pending;
 await act(async()=>{pending=button('确认保存复查计划').props.onClick();await started;});
 await act(async()=>renderer.unmount());token='other-account';const ownerListing=listing;listing={...empty(),case:{...animal,owner_id:2}};await mount();
 await act(async()=>{release();await pending;});assert(!button('核对复查保存结果'));assert(!text().includes('已保存并独立回读'));
 await act(async()=>renderer.unmount());token='owner-relogin';listing=ownerListing;await mount();await click('核对复查保存结果');
 assert.match(text(),/已核对服务端保存结果/);assert.equal(requests.filter(c=>c.url.endsWith('/confirm')).length,1);
});

for(const [boundary,nextToken] of [['storage','other-owner'],['storage',null],['focus','other-owner'],['visibilitychange',null],['refresh','other-owner'],['confirm',null]])test('account retirement clears 复查计划 at '+boundary+' with '+String(nextToken),async()=>{
 await mount();await fill();await review();const previousToken=token,count=requests.length;
 token=nextToken;
 if(boundary==='refresh')await click('刷新复查计划');
 else if(boundary==='confirm')await click('确认保存复查计划');
 else await fire(boundary);
 for(const label of ['复查计划草稿','复查计划核对','复查保存结果待核对'])assert.equal(renderer.root.findAllByProps({'aria-label':label}).length,0,label);
 assert(text().includes('账号已变化'),'account change must be explicit');assert(!text().includes('正在处理'));
 assert(button('刷新复查计划').props.disabled);assert.equal(requests.length,count);
 token=previousToken;await fire('focus');assert.equal(requests.length,count,'a retired panel must not revive when the token returns');
});

test('late 复查计划 preview detects same-tab account loss without a storage event',async()=>{
 await mount();await fill();const normal=adapter;let release,arrive;const started=new Promise(r=>arrive=r);
 adapter=async c=>c.url.endsWith('/preview')?new Promise(r=>{release=()=>r({config:c,data:preview(JSON.parse(c.data),listing)});arrive();}):normal(c);
 let pending;await act(async()=>{pending=button('预览并核对复查计划').props.onClick();await started;});
 token=null;await act(async()=>{release();await pending;});
 assert(text().includes('账号已变化'),'account change must be explicit');assert(!text().includes('正在处理'));
 assert.equal(renderer.root.findAllByProps({'aria-label':'复查计划草稿'}).length,0);
 assert(!button('确认保存复查计划'));assert(!requests.some(c=>c.url.endsWith('/confirm')));
});

test('current-account 401 clears 复查计划 content and settles busy state',async()=>{
 await mount();await fill();const normal=adapter;
 global.localStorage.removeItem=()=>{token=null;};global.alert=()=>{};
 adapter=async c=>{if(c.url.endsWith('/preview'))throw {config:c,response:{status:401}};return normal(c);};
 await click('预览并核对复查计划');
 assert.equal(token,null);assert(text().includes('账号已变化'),'account change must be explicit');assert(!text().includes('正在处理'));
 assert.equal(renderer.root.findAllByProps({'aria-label':'复查计划草稿'}).length,0);
 assert(button('刷新复查计划').props.disabled);assert(!requests.some(c=>c.url.endsWith('/confirm')));
});

test('retiring an in-flight 复查计划 save preserves its locator for the original owner',async()=>{
 const normal=adapter;let saved,release,arrive;const started=new Promise(r=>arrive=r);
 adapter=async c=>{
  if(c.url.endsWith('/confirm')){saved=(await normal(c)).data;return new Promise(r=>{release=()=>r({config:c,data:saved});arrive();});}
  if(c.url.includes('/requests/'))return {config:c,data:{...saved,writes_database:false}};
  return normal(c);
 };
 await mount();await fill();await review();let pending;const previousToken=token;
 await act(async()=>{pending=button('确认保存复查计划').props.onClick();await started;});
 const key=window.sessionStorage.key(0),locator=window.sessionStorage.getItem(key),count=requests.length;
 token='other-owner';await fire('focus');
 assert(text().includes('账号已变化'),'account change must be explicit');assert(!text().includes('正在处理'));
 for(const label of ['复查计划草稿','复查计划核对','复查保存结果待核对'])assert.equal(renderer.root.findAllByProps({'aria-label':label}).length,0,label);
 assert.equal(window.sessionStorage.getItem(key),locator);assert.equal(requests.length,count);
 token=previousToken;await fire('focus');await act(async()=>{release();await pending;});
 assert.equal(requests.length,count);assert.equal(window.sessionStorage.getItem(key),locator);
 await act(async()=>renderer.unmount());token='same-owner-relogin';await mount();
 assert(button('核对复查保存结果'));await click('核对复查保存结果');
 assert.match(text(),/已核对服务端保存结果/);assert.equal(window.sessionStorage.length,0);
 assert.equal(requests.filter(c=>c.url.endsWith('/confirm')).length,1);
 assert(requests.slice(count).every(c=>c.method==='get'),'recovery is GET only');
});
