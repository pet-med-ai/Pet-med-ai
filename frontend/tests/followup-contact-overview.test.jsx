import React from 'react';
import TestRenderer, {act} from 'react-test-renderer';
import {MemoryRouter} from 'react-router-dom';
import {test,beforeEach,afterEach} from 'node:test';
import assert from 'node:assert/strict';
import CaseVisitOverview from '../src/components/CaseVisitOverview';
import {validateOverview} from '../src/visitOverview';
import api from '../src/api';
import fixture from '../../tests/fixtures/clinical_followup_contact_overview_cw_b20_cases.json';
import legacy from '../../tests/fixtures/clinical_followup_plan_overview_cw_b17_cases.json';

let renderer,token,adapter,requests,listeners,props,navigations,original;
const payload=()=>structuredClone(fixture.overview);
const deferred=()=>{let resolve;const promise=new Promise(r=>resolve=r);return {resolve,promise};};
const output=()=>JSON.stringify(renderer.toJSON());
const button=name=>renderer.root.findAllByType('button').find(n=>n.children.join('')===name);
const click=async name=>act(async()=>{assert(button(name),name);await button(name).props.onClick();});
const tree=()=> <MemoryRouter><CaseVisitOverview {...props}/></MemoryRouter>;
const emit=async(name,event={})=>act(async()=>{await Promise.all([...(listeners[name]||[])].map(fn=>fn(event)));});
beforeEach(()=>{
 token='synthetic-owner';requests=[];listeners={};navigations=[];
 global.localStorage={getItem:()=>token,setItem(){throw Error('No clinical cache');}};
 global.sessionStorage={setItem(){throw Error('No clinical cache');}};
 const events={addEventListener:(k,f)=>(listeners[k]??=new Set()).add(f),removeEventListener:(k,f)=>listeners[k]?.delete(f)};
 global.window={...events};global.document={hidden:false,...events};
 props={caseId:1,requestToken:token,onNavigate:(target,event,record)=>navigations.push({target,record})};
 original=api.defaults.adapter;adapter=async c=>({config:c,status:200,data:payload()});
 api.defaults.adapter=async c=>{requests.push(c);return adapter(c);};
});
afterEach(()=>{if(renderer)act(()=>renderer.unmount());renderer=null;api.defaults.adapter=original;});
async function mount(){await act(async()=>{renderer=TestRenderer.create(tree());});}

test('new explicit GET shows literal contact and plan facts and exact read-only destinations',async()=>{
 await mount();assert.deepEqual(requests[0].params,{include_followup_plan:true,include_followup_contacts:true});
 const literals=renderer.root.findAllByType('dd').map(n=>n.children[0]);
 for(const value of [fixture.contact.note,fixture.contact.next_action,fixture.plan.purpose,fixture.plan.note])assert(literals.includes(value));
 assert.match(output(),/2024-02-29T16:35/);assert.match(output(),/不代表已复诊/);assert.match(output(),/历史版本数/);
 await click('回看随访 #2 版本 1');await click('回看计划 #1 版本 1');
 assert.deepEqual(navigations,[{target:'contacts',record:{id:2,version:1}},{target:'followup',record:{id:1,version:1}}]);
 assert(requests.every(c=>c.method==='get'));assert(!renderer.root.findAll(n=>n.props.dangerouslySetInnerHTML).length);
});
test('legacy, disabled and empty are distinguished without inventing contact facts',async()=>{
 adapter=async c=>({config:c,data:structuredClone(legacy.overview)});await mount();
 assert.match(output(),/本次总览未提供人工随访/);assert(!button('前往人工随访记录'));
 const disabled=payload();disabled.groups.contacts={status:'disabled',records:null,counts:null,case:null,timezone:'Asia/Shanghai'};
 adapter=async c=>({config:c,data:disabled});await click('刷新就诊资料总览');assert.match(output(),/无法判断记录有无/);
 assert.doesNotMatch(output(),/暂无本流程人工随访记录/);
 const empty=payload();empty.groups.contacts.records=[];empty.groups.contacts.counts.recorded=0;
 adapter=async c=>({config:c,data:empty});await click('刷新就诊资料总览');assert.match(output(),/不代表从未联系或无需复查/);
});
test('invalid schema, current case, counts, source, chain and attribution fail closed',()=>{
 const changes=[d=>d.schema='unknown',d=>d.case_id=2,d=>d.groups.contacts.case.id=2,
  d=>d.groups.contacts.counts.recorded=0,d=>d.groups.contacts.records[0].state='completed',
  d=>d.groups.contacts.records[0].source.id=99,d=>d.groups.contacts.records[0].source.version=2,
  d=>d.groups.contacts.records[0].source.data.note='changed',d=>d.groups.contacts.records[0].source_state='withdrawn',
  d=>d.groups.contacts.records[0].case_snapshot.id=2,d=>d.groups.contacts.records[0].recorded_by='other',
  d=>d.groups.contacts.records[0].version=2,d=>d.groups.contacts.records[0].root_id=3,
  d=>d.groups.contacts.records[0].data.outcome='completed',d=>d.groups.contacts.records[0].data.note=' ',
  d=>d.groups.contacts.records[0].token='',d=>d.groups.contacts.records.push(structuredClone(d.groups.contacts.records[0])),
  d=>d.groups.contacts.status='disabled',d=>d.navigation_targets.push('https://example.invalid'),
  d=>d.groups.contacts.extra=true,d=>d.groups.contacts.case.history='other',d=>d.groups.followup.status='disabled'];
 for(const change of changes){const data=payload();change(data);assert.throws(()=>validateOverview(data,1));}
 assert.equal(validateOverview(payload(),1).schema,'clinical-case-overview-cw-b20-v1');
});
test('fifty complete versions and separate roots do not count corrections as contacts',()=>{
 const data=payload(),group=data.groups.contacts,first=group.records[0];group.records=[];
 for(let i=0;i<50;i++)group.records.push({...structuredClone(first),id:i+2,version:i+1,state:i===49?'recorded':'superseded',reason:i?'合成更正':''});
 group.counts={recorded:1,superseded:49,withdrawn:0};validateOverview(data,1);
 group.records.push({...structuredClone(first),id:99,root_id:99});group.counts.recorded=2;assert.throws(()=>validateOverview(data,1));
 group.records.pop();group.counts.recorded=1;group.records[1].version=4;assert.throws(()=>validateOverview(data,1));
 const multiple=payload();multiple.groups.contacts.records.push({...structuredClone(first),id:3,root_id:3});multiple.groups.contacts.counts.recorded=2;
 validateOverview(multiple,1);
});
test('source changes and withdrawal preserve frozen raw text and show separate states',async()=>{
 const data=payload();data.groups.followup.case.history='CW-B20 已更正正文';data.groups.contacts.case.history='CW-B20 已更正正文';
 data.fields.find(f=>f.key==='history').value='CW-B20 已更正正文';data.groups.followup.records[0].state='needs_review';
 data.groups.followup.counts={planned:0,needs_review:1,superseded:0,withdrawn:0};
 const row=data.groups.contacts.records[0];row.source_state='needs_review';row.state='withdrawn';
 row.withdrawal={reason:fixture.withdrawal_reason,by:'1',at:'2026-10-09T04:00:00+00:00'};
 data.groups.contacts.counts={recorded:0,superseded:0,withdrawn:1};adapter=async c=>({config:c,data});await mount();
 assert.match(output(),/计划待重新核对/);assert.match(output(),/已撤销/);assert(output().includes(fixture.withdrawal_reason));
 assert(renderer.root.findAllByType('dd').some(n=>n.children[0]===fixture.contact.note));assert(button('回看随访 #2 版本 1'));
});
for(const failed of [false,true])test(`contact write start hides stale snapshot and ${failed?'lost':'successful'} response rereads without another write`,async()=>{
 await mount();const gate=deferred(),normal=adapter;
 adapter=c=>c.method==='post'?gate.promise.then(()=>{if(failed)throw {config:c,response:{status:503}};return {config:c,data:{}};}):normal(c);
 let operation;await act(async()=>{operation=api.post('/api/cases/1/followup-contacts/confirm',{}).catch(()=>{});});
 assert(!button('回看随访 #2 版本 1'));
 await act(async()=>{gate.resolve();await operation;});assert(button('回看随访 #2 版本 1'));
 assert.equal(requests.filter(c=>c.method==='post').length,1);assert.equal(requests.filter(c=>c.method==='get').length,2);
});
for(const event of ['focus','visibilitychange'])test(`${event} discards late snapshots; other case writes do not refresh`,async()=>{
 await mount();await act(async()=>api.post('/api/cases/99/followup-contacts/confirm',{}));assert.equal(requests.filter(c=>c.method==='get').length,1);
 const gate=deferred();let count=0;adapter=async c=>++count===1?gate.promise:{config:c,data:structuredClone(legacy.overview)};
 let pending;await act(async()=>{pending=button('刷新就诊资料总览').props.onClick();});
 await emit(event);await act(async()=>{gate.resolve({data:payload()});await pending;});
 assert(!button('回看随访 #2 版本 1'));assert.match(output(),/未提供人工随访/);
});
test('errors, account transition and case transition never display old contact content',async()=>{
 await mount();for(const status of [401,404,409,503]){
  adapter=async()=>{throw {response:{status}};};await click('刷新就诊资料总览');assert(!button('回看随访 #2 版本 1'));
  assert.doesNotMatch(output(),/暂无本流程人工随访记录/);
 }
 token='other';await emit('storage',{key:'token'});assert.match(output(),/登录已变化/);
 props={...props,caseId:2,requestToken:token};await act(async()=>renderer.update(tree()));assert(!output().includes(fixture.contact.note));
});
