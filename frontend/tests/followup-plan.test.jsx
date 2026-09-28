import React from 'react';
import TestRenderer, {act} from 'react-test-renderer';
import {test, beforeEach, afterEach} from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
import api from '../src/api';
import FollowUpPlan from '../src/components/FollowUpPlan';
import {loadPlanLocal, savePlanDraft, savePlanAttempt, clearPlanDrafts} from '../src/followUpPlanState';

const memory=()=>{const m=new Map();return {getItem:k=>m.get(k)??null,setItem:(k,v)=>m.set(k,String(v)),removeItem:k=>m.delete(k),key:i=>[...m.keys()][i]??null,get length(){return m.size;}};};
const token=owner=>'synthetic.'+Buffer.from(JSON.stringify({sub:owner,exp:4102444800})).toString('base64url')+'.signature';
const h=n=>n.toString(16).padStart(64,'0');
const defer=()=>{let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};};
const input={due_date:'2028-02-29',note:'  医生原文：未见异常，不排除其他原因。🐾\n<literal> & {{literal}}\t  '};
let renderer,requests,adapter,state,receipts,changed,listeners,requestToken;
const button=name=>renderer.root.findAllByType('button').find(n=>n.children.join('')===name);
const output=()=>JSON.stringify(renderer.toJSON());
const click=async name=>{const b=button(name);assert(b,name);assert(!b.props.disabled,name);await act(async()=>b.props.onClick());};
const check=()=>act(()=>renderer.root.findByProps({type:'checkbox'}).props.onChange({target:{checked:true}}));
const set=async (label,value)=>act(()=>renderer.root.findByProps({'aria-label':label}).props.onChange({target:{value}}));
const fills=async(value=input)=>{await set('复查日期',value.due_date);await set('医生复查说明',value.note);};
const saves=()=>requests.filter(c=>c.url.endsWith('/confirm'));
const base='/api/cases/1/follow-up';
const view=()=> <FollowUpPlan caseId={1} requestToken={requestToken} onChanged={()=>changed++} onClose={()=>{}} />;
const mount=async()=>act(async()=>{renderer=TestRenderer.create(view());});
const remount=async()=>{act(()=>renderer.unmount());await mount();};
function response(config,data){return {config,data,status:200};}
function normal(c){
 const r=c.data?JSON.parse(c.data):{};
 if(c.method==='get'&&c.url===base)return response(c,structuredClone(state));
 if(c.url.includes('/receipts/')){const id=c.url.split('/').at(-1);return response(c,{case_id:1,request_id:id,status:receipts.has(id)?'committed':'not_found',receipt:receipts.get(id)||null,writes_database:false});}
 if(c.url.endsWith('/preview'))return response(c,{case_id:1,patient_name:'合成犬',action:r.action,state_token:state.state_token,before:state.current,proposed:r.action==='cancel'?null:{due_date:r.due_date,note:r.note},preview_token:h(99),writes_database:false});
 if(c.url.endsWith('/confirm')){
  if(receipts.has(r.request_id))return response(c,{receipt:receipts.get(r.request_id),replayed:true,writes_database:false});
  const old=state.current?{...state.current,status:'cancelled'}:null;
  const next=r.action==='cancel'?null:{id:state.items.length+1,case_id:1,due_date:r.due_date,due_at_stored:r.due_date+'T00:00:00',note:r.note,status:'due',managed:true};
  const receipt={case_id:1,account_id:'7',request_id:r.request_id,action:r.action,before_state_token:r.expected_state_token,after_state_token:h(state.items.length+2),after:next,cancelled:old};
  state={...state,state_token:receipt.after_state_token,current:next,items:state.items.map(i=>i.id===old?.id?old:i).concat(next?[next]:[])};
  receipts.set(r.request_id,receipt);return response(c,{receipt,replayed:false,writes_database:true});
 }
 throw Error('Unexpected request '+c.url);
}
beforeEach(()=>{
 global.localStorage=memory();localStorage.setItem('token',token('owner'));requestToken=token('owner');
 listeners=new Map();global.window={sessionStorage:memory(),addEventListener(k,f){if(!listeners.has(k))listeners.set(k,new Set());listeners.get(k).add(f);},removeEventListener(k,f){listeners.get(k)?.delete(f);}};
 if(!global.crypto)global.crypto=webcrypto;
 global.alert=()=>{};requests=[];receipts=new Map();changed=0;
 state={case_id:1,account_id:'7',patient_name:'合成犬',state_token:h(1),items:[],current:null,can_write:true,conflict:'',writes_database:false};
 adapter=normal;api.defaults.adapter=async c=>{requests.push(c);return adapter(c);};
});
afterEach(()=>{if(renderer){act(()=>renderer.unmount());renderer=null;}});

test('preview is read-only, preserves raw text and unchecked confirmation cannot save',async()=>{
 await mount();await fills();await click('核对复查计划');
 assert.equal(saves().length,0);assert(button('确认并保存复查操作').props.disabled);
 assert(renderer.root.findAllByType('pre').some(n=>n.children.join('')===input.note));
 assert(!renderer.root.findAll(n=>n.props.dangerouslySetInnerHTML).length);
 await act(async()=>button('确认并保存复查操作').props.onClick());assert.equal(saves().length,0);
});
test('one confirmed write is followed by receipt GET and independent current-state GET',async()=>{
 await mount();await fills();await click('核对复查计划');check();await click('确认并保存复查操作');
 assert.equal(saves().length,1);assert.equal(receipts.size,1);assert.equal(changed,1);
 assert(requests.at(-2).url.includes('/receipts/'));assert.equal(requests.at(-1).url,base);
 assert.equal(requests.at(-1).method,'get');assert.match(output(),/已保存并核实/);assert.equal(state.current.note,input.note);
 assert.equal(loadPlanLocal('owner',1).attempt,null);assert.equal(loadPlanLocal('owner',1).draft,null);
});
test('editing input invalidates the checked preview',async()=>{
 await mount();await fills();await click('核对复查计划');check();await set('医生复查说明','新原文');
 assert.equal(button('确认并保存复查操作'),undefined);assert.equal(saves().length,0);
 await click('核对复查计划');assert(button('确认并保存复查操作').props.disabled);
});
test('same-tick double confirmation dispatches one POST',async()=>{
 await mount();await fills();await click('核对复查计划');check();const submit=button('确认并保存复查操作').props.onClick;
 await act(async()=>Promise.all([submit(),submit()]));assert.equal(saves().length,1);assert.equal(receipts.size,1);
});
test('lost POST response is resolved from receipt without another POST',async()=>{
 await mount();await fills();await click('核对复查计划');check();
 adapter=c=>{const r=normal(c);if(c.url.endsWith('/confirm'))throw Error('lost response');return r;};
 await click('确认并保存复查操作');assert.equal(saves().length,1);assert.equal(changed,1);assert.match(output(),/已保存并核实/);
});
test('failed receipt lookup survives remount and recovers using GET only',async()=>{
 await mount();await fills();await click('核对复查计划');check();
 adapter=c=>{if(c.url.includes('/receipts/'))throw Error('offline');return normal(c);};
 await click('确认并保存复查操作');assert(loadPlanLocal('owner',1).attempt);
 await remount();assert.equal(button('核对复查计划'),undefined);assert.equal(saves().length,1);
 adapter=normal;await click('核对复查保存结果');assert.equal(saves().length,1);assert.equal(changed,1);
});
test('not-found is not success and deliberate retry preserves the exact request ID and body',async()=>{
 await mount();await fills();await click('核对复查计划');check();
 adapter=c=>{if(c.url.endsWith('/confirm'))throw Error('request did not reach server');return normal(c);};
 await click('确认并保存复查操作');assert.equal(changed,0);assert.match(output(),/结果仍待核对/);
 const first=saves()[0].data;assert(button('使用同一请求重试').props.disabled);check();adapter=normal;
 await click('使用同一请求重试');assert.equal(saves().length,2);assert.equal(saves()[1].data,first);assert.equal(receipts.size,1);
});
test('definite conflict plus absent receipt reloads state and requires fresh confirmation',async()=>{
 await mount();await fills();await click('核对复查计划');check();
 adapter=c=>{if(c.url.endsWith('/confirm'))throw {response:{status:409,data:{detail:'计划已变化'}}};return normal(c);};
 await click('确认并保存复查操作');assert.equal(changed,0);assert.match(output(),/请求已被服务拒绝/);
 assert.equal(loadPlanLocal('owner',1).attempt,null);assert.equal(button('确认并保存复查操作'),undefined);
 assert.equal(renderer.root.findByProps({'aria-label':'医生复查说明'}).props.value,input.note);
});
test('a mismatched receipt cannot clear the pending request or claim success',async()=>{
 await mount();await fills();await click('核对复查计划');check();
 adapter=c=>{const result=normal(c);if(c.url.includes('/receipts/'))result.data.receipt={...result.data.receipt,case_id:2};return result;};
 await click('确认并保存复查操作');assert.equal(changed,0);assert(loadPlanLocal('owner',1).attempt);assert.match(output(),/回执与本次核对请求不一致/);
});
test('storage refusal blocks dispatch before an untrackable write',async()=>{
 await mount();await fills();await click('核对复查计划');check();
 window.sessionStorage.setItem=()=>{throw Error('quota');};await click('确认并保存复查操作');
 assert.equal(saves().length,0);assert.match(output(),/尚未发出保存请求/);
});
test('unsubmitted input is offered after refresh and restored without confirmation',async()=>{
 await mount();await fills();await click('核对复查计划');check();await remount();
 assert.equal(button('确认并保存复查操作'),undefined);assert.equal(renderer.root.findByProps({'aria-label':'医生复查说明'}).props.value,'');
 await click('恢复复查输入');assert.equal(renderer.root.findByProps({'aria-label':'医生复查说明'}).props.value,input.note);
 assert.equal(saves().length,0);await click('核对复查计划');assert(button('确认并保存复查操作').props.disabled);
});
test('draft expiry or explicit draft cleanup does not clear pending attempts',async()=>{
 await mount();await fills();await click('核对复查计划');check();adapter=()=>{throw Error('offline');};
 await click('确认并保存复查操作');const pending=loadPlanLocal('owner',1).attempt;assert(pending);
 const later=loadPlanLocal('owner',1,Date.now()+9*60*60*1000);assert(later.attempt);assert.equal(later.draft,null);
 clearPlanDrafts();assert.deepEqual(loadPlanLocal('owner',1).attempt,pending);
});
test('account/case partitions and corrupt pending state fail closed',()=>{
 savePlanDraft('owner',1,input);assert.equal(loadPlanLocal('other',1).draft,null);assert.equal(loadPlanLocal('owner',2).draft,null);
 const s=window.sessionStorage;s.setItem('pmai.follow-up-attempt.v1.owner.1','broken');
 const result=loadPlanLocal('owner',1);assert(result.blocked);assert.equal(s.getItem('pmai.follow-up-attempt.v1.owner.1'),'broken');
});
test('switching account between click and Axios dispatch sends no mutation',async()=>{
 await mount();await fills();await click('核对复查计划');check();const submit=button('确认并保存复查操作').props.onClick;
 await act(async()=>{const p=submit();localStorage.setItem('token',token('other'));await p;});
 assert.equal(saves().length,0);assert.equal(changed,0);
});
test('old account response is ignored and its receipt stays partitioned',async()=>{
 await mount();await fills();await click('核对复查计划');check();
 adapter=c=>{const result=normal(c);if(c.url.endsWith('/confirm'))localStorage.setItem('token',token('other'));return result;};
 await click('确认并保存复查操作');assert.equal(changed,0);assert(!requests.some(c=>c.url.includes('/receipts/')));
 requestToken=token('other');state={...state,account_id:'8',items:[],current:null};await remount();
 assert.doesNotMatch(output(),/医生原文/);assert(loadPlanLocal('owner',1).attempt);assert.equal(loadPlanLocal('other',1).attempt,null);
});
test('leaving during a response does not report success or clear unresolved local state',async()=>{
 await mount();await fills();await click('核对复查计划');check();const gate=defer();
 adapter=async c=>{if(c.url.endsWith('/confirm'))await gate.promise;return normal(c);};
 let task;act(()=>{task=button('确认并保存复查操作').props.onClick();});act(()=>renderer.unmount());renderer=null;
 await act(async()=>{gate.resolve();await task;});assert.equal(changed,0);assert(loadPlanLocal('owner',1).attempt);
});
test('legacy or malformed state cannot enable editing',async()=>{
 state={...state,can_write:false,conflict:'历史记录需核对'};await mount();assert(button('核对复查计划').props.disabled);assert.match(output(),/历史记录需核对/);
 state={...state,can_write:true,state_token:'bad'};await click('重新读取复查计划');assert(button('核对复查计划').props.disabled);assert.match(output(),/未收到完整复查记录/);
});
test('replacement and cancellation display original text and preserve history',async()=>{
 await mount();await fills();await click('核对复查计划');check();await click('确认并保存复查操作');
 await click('填入当前计划进行更正');await set('医生复查说明','更正内容');await click('核对复查计划');
 assert(renderer.root.findAllByType('pre').some(n=>n.children.join('')===input.note));check();await click('确认并保存复查操作');
 assert.equal(state.items.length,2);assert.equal(state.items[0].status,'cancelled');
 await click('核对撤销当前计划');check();await click('确认并保存复查操作');assert.equal(state.current,null);
 assert.match(output(),/当前无有效复查计划/);assert.equal(state.items.length,2);assert.equal(changed,3);
});
