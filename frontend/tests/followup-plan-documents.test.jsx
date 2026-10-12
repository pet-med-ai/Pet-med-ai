import React from 'react';
import TestRenderer,{act} from 'react-test-renderer';
import {MemoryRouter} from 'react-router-dom';
import {test,beforeEach,afterEach} from 'node:test';
import assert from 'node:assert/strict';
import ClinicalDocReview from '../src/components/ClinicalDocReview';
import {documentPlanSelection,validDocumentPlan} from '../src/followupPlanDocuments';
import api from '../src/api';
import fixture from '../../tests/fixtures/clinical_followup_plan_documents_cw_b15_cases.json';

let renderer,props,token,requests,adapter,listeners,downloads,listing;
const hash='a'.repeat(64),reply=(c,data)=>({config:c,status:200,data});
const button=s=>renderer.root.findAllByType('button').find(n=>n.children.join('')===s);
const click=async s=>act(async()=>{assert(button(s),s);await button(s).props.onClick();});
const text=()=>JSON.stringify(renderer.toJSON());
const confirm=async()=>act(async()=>{const box=renderer.root.findAllByType('input').find(n=>n.props.type==='checkbox'&&!n.props['aria-label']);assert(box&&!box.props.disabled);box.props.onChange({target:{checked:true}});});
const fire=async(name,e={})=>act(async()=>{for(const fn of [...(listeners[name]||[])])fn(e);});
const deferred=()=>{let resolve,reject;const promise=new Promise((r,j)=>{resolve=r;reject=j;});return{promise,resolve,reject};};
const view=()=> <MemoryRouter><ClinicalDocReview {...props}/></MemoryRouter>;
function preview(c){
  const b=JSON.parse(c.data),context={};
  for(const k of ['case_id','pet_name','owner_name','coat_color','species','age','sex','weight','complaint','history','exam','assessment','plan','notes','follow_up'])context['visit.'+k]='未填写';
  context['visit.case_id']=String(b.case_id);context['export.account_id']='1';
  return reply(c,{...b,context,content_snapshot:hash,missing_required_keys:[],writes_database:false,
    ...(b.manual_followup_plan?{manual_followup_plan:documentPlanSelection(listing,listing.plans.find(p=>p.id===b.manual_followup_plan.id)).expected}:{})});
}
beforeEach(async()=>{
  listing=structuredClone(fixture.listing);token='synthetic';requests=[];listeners={};downloads=[];
  global.localStorage={getItem:()=>token,setItem(){throw Error('No persistence');}};global.sessionStorage={setItem(){throw Error('No persistence');}};
  global.window={addEventListener:(k,f)=>(listeners[k]??=new Set()).add(f),removeEventListener:(k,f)=>listeners[k]?.delete(f)};
  props={caseId:1,templateId:'outpatient_record_zh',label:'门诊病历',requestToken:token,onClose(){},onDownload:async(snapshot,current,labs,images,comparison,signal,plan)=>{downloads.push({snapshot,current:current(),labs,images,comparison,signal,plan});return{ok:true};}};
  adapter=async c=>c.url.endsWith('/followup-plan')?reply(c,structuredClone(listing)):preview(c);
  api.defaults.adapter=async c=>{requests.push(c);return adapter(c);};
  await act(async()=>renderer=TestRenderer.create(view()));
});
afterEach(()=>act(()=>renderer.unmount()));
async function select(){await click('选择复查计划附节');await click('将此计划纳入本次文书');}
async function selected(){await select();await click('重新读取草稿');}

test('default omitted, explicit selection, complete raw preview and independent confirmation; double click exports once',async()=>{
  assert.equal(requests.length,1);assert.equal(JSON.parse(requests[0].data).manual_followup_plan,undefined);
  await select();assert(!button('确认并下载草稿 DOCX'));await click('重新读取草稿');
  assert(button('确认并下载草稿 DOCX').props.disabled);
  for(const value of [fixture.plan.purpose,fixture.plan.note,fixture.plan.planned_date,fixture.listing.plans[0].token])assert(text().includes(JSON.stringify(value).slice(1,-1)));
  await confirm();await act(async()=>{await Promise.all([button('确认并下载草稿 DOCX').props.onClick(),button('确认并下载草稿 DOCX').props.onClick()]);});
  assert.equal(downloads.length,1);assert.deepEqual(downloads[0].plan,{id:1,version:1,token:'c'.repeat(64)});assert.equal(downloads[0].snapshot,hash);assert.deepEqual(downloads[0].labs,[]);
});
test('exact protocol rejects changed originals, dates, account, provenance, version and unexpected sections',()=>{
  const row=listing.plans[0],choice=documentPlanSelection(listing,row);
  assert(validDocumentPlan(choice.expected,choice,1));assert(!validDocumentPlan(choice.expected,null,1));assert(validDocumentPlan(undefined,null,1));
  for(const key of ['data','reviewed_by','reviewed_at','token','version','case_snapshot']){const payload=structuredClone(choice.expected);payload.plan[key]={};assert(!validDocumentPlan(payload,choice,1));}
  assert(!validDocumentPlan(choice.expected,choice,2));assert.throws(()=>documentPlanSelection(listing,{...row,id:true}));
  for(const state of ['superseded','withdrawn','needs_review'])assert.throws(()=>documentPlanSelection(listing,{...row,state}));
});
for(const action of ['clear','refresh','focus','revision','template','account'])test(`old confirmation invalidated by ${action}`,async()=>{
  await selected();await confirm();
  if(action==='clear')await click('移除本次复查计划附节');else if(action==='refresh')await click('刷新可选复查计划');else if(action==='focus')await fire('focus');else await act(async()=>{
    if(action==='revision')props={...props,sourceRevision:1};if(action==='template')props={...props,templateId:'owner_visit_summary_zh'};if(action==='account'){token='other';props={...props,requestToken:token};}renderer.update(view());
  });
  assert(!button('确认并下载草稿 DOCX')||button('确认并下载草稿 DOCX').props.disabled);assert.doesNotMatch(text(),/文书复查计划附节/);assert.equal(downloads.length,0);
});
for(const action of ['followup-plan','attachments','manual-lab','manual-imaging','body'])for(const failed of [false,true])test(`${action} ${failed?'failure':'success'} invalidates at request start with closed selector and rereads`,async()=>{
  await selected();await click('收起复查计划选择');await confirm();
  const gate=deferred(),normal=adapter;let pending;
  const url=action==='body'?'/api/cases/1':`/api/cases/1/${action}/confirm`;
  adapter=c=>c.url===url?gate.promise.then(()=>reply(c,{}),()=>Promise.reject({config:c,response:{status:503}})):normal(c);
  const reads=requests.filter(c=>c.url.endsWith('/followup-plan')).length;
  await act(async()=>{pending=api.request({method:action==='body'?'put':'post',url,data:{}}).catch(()=>{});});
  assert(!button('确认并下载草稿 DOCX'));
  await act(async()=>{failed?gate.reject():gate.resolve();await pending;});
  assert(requests.filter(c=>c.url.endsWith('/followup-plan')).length>reads);assert.equal(downloads.length,0);
});
for(const action of ['clear','focus','case','account'])test(`late complete preview ignored after ${action}`,async()=>{
  await select();const gate=deferred(),normal=adapter;let pending;
  adapter=async c=>{if(c.url.endsWith('render-preview'))await gate.promise;return normal(c);};
  await act(async()=>{pending=button('重新读取草稿').props.onClick();});
  if(action==='clear')await click('移除本次复查计划附节');else if(action==='focus')await fire('focus');else await act(async()=>{
    if(action==='case')props={...props,caseId:2};else{token='other';props={...props,requestToken:token};}renderer.update(view());
  });
  await act(async()=>{gate.resolve();await pending;});assert.doesNotMatch(text(),/文书复查计划附节/);assert.equal(downloads.length,0);
});
test('late download after plan save attempt loses current predicate and is aborted',async()=>{
  await selected();await confirm();const gate=deferred(),normal=adapter;let current,signal,pending;
  props={...props,onDownload:async(_s,c,_l,_i,_x,s)=>{current=c;signal=s;await gate.promise;return{ok:true};}};await act(async()=>renderer.update(view()));
  await act(async()=>{pending=button('确认并下载草稿 DOCX').props.onClick();});
  adapter=async c=>c.url.endsWith('/confirm')?reply(c,{}):normal(c);
  await act(async()=>{await api.post('/api/cases/1/followup-plan/confirm',{});});assert.equal(current(),false);assert.equal(signal.aborted,true);
  await act(async()=>{gate.resolve();await pending;});assert.doesNotMatch(text(),/已生成本次核对/);
});
test('unreadable list is distinct from no plan; forged full preview cannot be confirmed',async()=>{
  const normal=adapter;adapter=async c=>c.url.endsWith('/followup-plan')?reply(c,{plans:[]}):normal(c);
  await click('选择复查计划附节');assert.match(text(),/数据不完整/);assert.doesNotMatch(text(),/尚无已保存计划/);assert(!button('将此计划纳入本次文书'));
  adapter=normal;await click('刷新可选复查计划');await click('将此计划纳入本次文书');
  adapter=async c=>{const r=await normal(c);if(c.url.endsWith('render-preview'))r.data.manual_followup_plan.plan.data.note='changed';return r;};
  await click('重新读取草稿');assert(!button('确认并下载草稿 DOCX'));assert.match(text(),/完整草稿/);
});
test('old and withdrawn versions are visibly nonselectable, current is not selected automatically',async()=>{
  listing.plans=[{...listing.plans[0],state:'withdrawn',stored_state:'withdrawn',withdrawal:{by:'1',at:'2026-10-08T10:01:00Z',reason:'已撤销'}}];
  await click('选择复查计划附节');assert(button('将此计划纳入本次文书').props.disabled);assert.match(text(),/已撤销/);assert.equal(JSON.parse(requests[0].data).manual_followup_plan,undefined);
});
