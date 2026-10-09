import React from 'react';
import TestRenderer, {act} from 'react-test-renderer';
import {MemoryRouter} from 'react-router-dom';
import {test, beforeEach, afterEach} from 'node:test';
import assert from 'node:assert/strict';
import CaseVisitOverview from '../src/components/CaseVisitOverview';
import {validateOverview} from '../src/visitOverview';
import api from '../src/api';
import fixture from '../../tests/fixtures/clinical_followup_plan_overview_cw_b17_cases.json';
import legacy from '../../tests/fixtures/clinical_case_overview_cw_b10_cases.json';

let renderer, token, adapter, requests, listeners, props, navigations;
const payload=()=>structuredClone(fixture.overview);
const deferred=()=>{let resolve,reject;const promise=new Promise((r,j)=>{resolve=r;reject=j;});return {resolve,reject,promise};};
const text=()=>JSON.stringify(renderer.toJSON());
const button=name=>renderer.root.findAllByType('button').find(n=>n.children.join('')===name);
const click=async name=>act(async()=>{assert(button(name),name);await button(name).props.onClick();});
const tree=()=> <MemoryRouter><CaseVisitOverview {...props}/></MemoryRouter>;
const emit=async(name,event={})=>act(async()=>{await Promise.all([...(listeners[name]||[])].map(fn=>fn(event)));});
beforeEach(()=>{
 token='synthetic-owner';requests=[];listeners={};navigations=[];
 global.localStorage={getItem:()=>token,setItem(){throw Error('No cache');},removeItem:()=>{token='';}};
 global.sessionStorage={setItem(){throw Error('No cache');}};
 global.window={addEventListener:(k,fn)=>(listeners[k]??=new Set()).add(fn),removeEventListener:(k,fn)=>listeners[k]?.delete(fn)};
 props={caseId:1,requestToken:token,onNavigate:(target,event,plan)=>navigations.push({target,plan})};
 adapter=async c=>({config:c,status:200,data:payload()});api.defaults.adapter=async c=>{requests.push(c);return adapter(c);};
});
afterEach(()=>{if(renderer)act(()=>renderer.unmount());renderer=null;});
async function mount(){await act(async()=>{renderer=TestRenderer.create(tree());});}

test('opt-in GET displays exact raw data, provenance, counts and internal version target',async()=>{
 await mount();assert.equal(requests.length,1);assert.deepEqual(requests[0].params,{include_followup_plan:true,include_followup_contacts:true});
 const dataNodes=renderer.root.findAllByType('dd').map(n=>n.children[0]);
 for(const raw of [fixture.plan.purpose,fixture.plan.note,fixture.plan.return_conditions])assert(dataNodes.includes(raw));
 assert.match(text(),/2028-02-29/);assert.match(text(),/计划不代表已复查/);assert.match(text(),/版本/);
 await click('回看计划 #1 版本 1');assert.deepEqual(navigations,[{target:'followup',plan:{id:1,version:1}}]);
 assert(!renderer.root.findAll(n=>n.props.dangerouslySetInnerHTML).length);assert(requests.every(c=>c.method==='get'));
});
test('legacy, disabled and confirmed empty have different presentations',async()=>{
 adapter=async()=>({data:structuredClone(legacy.overview)});await mount();assert.match(text(),/本次总览未提供复查计划信息/);assert(!button('前往复查计划'));
 const empty=payload();empty.groups.followup.records=[];empty.groups.followup.counts.planned=0;
 adapter=async()=>({data:empty});await click('刷新就诊资料总览');assert.match(text(),/暂无本流程复查计划记录；不代表无需复查/);
 const disabled=payload();disabled.groups.followup={status:'disabled',records:null,counts:null,case:null,timezone:'Asia/Shanghai'};
 adapter=async()=>({data:disabled});await click('刷新就诊资料总览');assert.match(text(),/复查计划模块未启用，无法判断记录有无/);assert.doesNotMatch(text(),/暂无本流程复查计划记录/);
});
test('unknown schema, count, case, state, chain, root, attribution and disabled shape fail closed',()=>{
 const changes=[d=>d.schema='unknown',d=>d.groups.followup.counts.planned=2,d=>d.groups.followup.records[0].state='completed',
  d=>d.groups.followup.records[0].version=2,d=>d.groups.followup.records[0].root_id=2,d=>d.groups.followup.case.id=2,
  d=>d.groups.followup.case.patient_name='wrong',d=>d.groups.followup.records[0].case_snapshot.id=2,
  d=>d.groups.followup.records[0].reviewed_by='other',d=>d.groups.followup.records[0].token='',
  d=>d.groups.followup.records[0].data.items=[],d=>d.groups.followup.records[0].data.planned_date='2027-02-29',
  d=>d.groups.followup.records[0].state='needs_review',d=>d.groups.followup.records.push(structuredClone(d.groups.followup.records[0])),
  d=>d.navigation_targets.push('https://example.invalid'),d=>d.groups.followup.status='disabled'];
 for(const change of changes){const data=payload();change(data);assert.throws(()=>validateOverview(data,1));}
 assert.equal(validateOverview(payload(),1).schema,fixture.overview.schema);
});
test('fifty complete versions and separate roots preserve raw data and states',()=>{
 const data=payload(),group=data.groups.followup,first=group.records[0];group.records=[];
 for(let i=1;i<=50;i++)group.records.push({...structuredClone(first),id:i,version:i,reason:i>1?'更正原文':'',state:i===50?'planned':'superseded',stored_state:i===50?'planned':'superseded'});
 group.counts={planned:1,needs_review:0,superseded:49,withdrawn:0};validateOverview(data,1);
 group.records.push({...structuredClone(first),id:51,version:51});assert.throws(()=>validateOverview(data,1));
 group.records.pop();group.records[1].version=3;assert.throws(()=>validateOverview(data,1));
});
test('changed case is needs-review, never silently active; withdrawn provenance is rendered',async()=>{
 const data=payload(),group=data.groups.followup;group.case.history='更正';data.fields.find(f=>f.key==='history').value='更正';
 group.records[0].state='needs_review';group.counts={planned:0,needs_review:1,superseded:0,withdrawn:0};
 adapter=async()=>({data});await mount();assert.match(text(),/病例资料已变化/);
 const row=group.records[0];row.stored_state=row.state='withdrawn';row.withdrawal={reason:'撤销原因\n原文',by:'1',at:'2026-10-09T00:00:00+08:00'};
 group.counts={planned:0,needs_review:0,superseded:0,withdrawn:1};await click('刷新就诊资料总览');assert.match(text(),/已撤销/);assert.match(text(),/撤销原因/);
});
for(const method of ['post','put','patch','delete'])for(const failed of [false,true])test(`${method} write start clears snapshot and ${failed?'lost response':'success'} triggers independent GET`,async()=>{
 await mount();const gate=deferred();const normal=adapter;
 adapter=c=>c.method===method?gate.promise.then(()=>{if(failed)throw {config:c,response:{status:503}};return {config:c,status:200,data:{}};}):normal(c);
 let operation;await act(async()=>{operation=api.request({method,url:method==='post'?'/api/cases/1/followup-plan/confirm':'/api/cases/1',data:{}}).catch(()=>{});});
 assert(!button('回看计划 #1 版本 1'));assert.match(text(),/资料操作已开始/);
 await act(async()=>{gate.resolve();await operation;});assert(button('回看计划 #1 版本 1'));
 assert.equal(requests.filter(c=>c.method===method).length,1);assert.equal(requests.filter(c=>c.method==='get').length,2);
});
test('unrelated writes do not refresh; focus invalidates and stale reads cannot restore records',async()=>{
 await mount();await act(async()=>api.post('/api/cases/2/followup-plan/confirm',{}));assert.equal(requests.filter(c=>c.method==='get').length,1);
 const gate=deferred();let n=0;adapter=async()=>++n===1?gate.promise:{data:structuredClone(legacy.overview)};
 let reading;await act(async()=>{reading=button('刷新就诊资料总览').props.onClick();});assert(!button('回看计划 #1 版本 1'));
 await emit('focus');await act(async()=>{gate.resolve({data:payload()});await reading;});assert(!button('回看计划 #1 版本 1'));assert.match(text(),/本次总览未提供复查计划信息/);
});
test('failure and account change never turn a missing result into zero plans',async()=>{
 await mount();for(const status of [401,404,409,503]){
  adapter=async()=>{throw {response:{status}};};await click('刷新就诊资料总览');assert(!button('回看计划 #1 版本 1'));assert.doesNotMatch(text(),/暂无本流程复查计划/);
 }
 token='other';await emit('storage',{key:'token'});assert.match(text(),/登录已变化/);
});
