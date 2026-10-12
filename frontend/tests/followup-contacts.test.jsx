import React from 'react';
import TestRenderer,{act} from 'react-test-renderer';
import {test,beforeEach,afterEach} from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
import CaseFollowupContacts from '../src/components/CaseFollowupContacts';
import {schema,validData,validTime,validList,validPreview,validReceipt,frozenSource} from '../src/followupContacts';
import api from '../src/api';
import fixture from '../../tests/fixtures/clinical_followup_contacts_cw_b19_cases.json';
import baseline from '../../tests/fixtures/clinical_followup_plan_overview_cw_b17_cases.json';
const empty=()=>{const p=structuredClone(baseline.listing);p.plans[0].data=structuredClone(fixture.plan);return {...p,schema,records:[],limits:{versions:50}};};
const record=(data,l)=>({id:2,root_id:2,version:1,state:'recorded',token:'c'.repeat(64),source:frozenSource(l.plans[0]),source_state:l.plans[0].state,data,case_snapshot:l.case,recorded_by:String(l.case.owner_id),recorded_at:'2026-10-09T03:00:00+00:00',reason:'',withdrawal:null});
const preview=(b,l)=>({schema,case_id:1,case:l.case,as_of_date:l.as_of_date,timezone:l.timezone,before:l.records.find(r=>r.id===b.contact_id)||null,source:frozenSource(l.plans.find(p=>p.id===b.source_plan_id)),source_state:l.plans[0].state,data:b.data,operation:b.operation,reason:b.reason,request_id:b.request_id,writes_database:false,case_token:b.expected_case_token,state_token:b.expected_state_token,preview_token:'d'.repeat(64)});
let renderer,requests,listeners,adapter,listing,token,original;
const button=label=>renderer.root.findAllByType('button').find(n=>n.children.join('')===label);
const click=async label=>act(async()=>{assert(button(label),label);await button(label).props.onClick();});
const input=label=>renderer.root.findByProps({'aria-label':label});
const change=async(label,value)=>act(async()=>input(label).props.onChange({target:{value}}));
const output=()=>JSON.stringify(renderer.toJSON());
const fire=async name=>act(async()=>{for(const fn of listeners[name]||[])fn({key:'token'});});
beforeEach(()=>{
  listing=empty();token='synthetic-owner';requests=[];listeners={};Object.defineProperty(globalThis,'crypto',{configurable:true,value:webcrypto});
  global.localStorage={getItem:()=>token};const events={addEventListener:(k,f)=>(listeners[k]??=new Set()).add(f),removeEventListener:(k,f)=>listeners[k]?.delete(f)};
  global.window={confirm:()=>true,...events};global.document={hidden:false,...events};original=api.defaults.adapter;
  adapter=async c=>{const b=c.data?JSON.parse(c.data):null;let data;
    if(c.url.endsWith('/preview'))data=preview(b,listing);
    else if(c.url.endsWith('/confirm')){listing={...listing,records:[record(b.data,listing)]};data={schema,case_id:1,request_id:b.request_id,state:'committed',operation:b.operation,record:listing.records[0],writes_database:true};}
    else data=structuredClone(listing);return {config:c,status:200,data};};
  api.defaults.adapter=async c=>{requests.push(c);return adapter(c);};
});
afterEach(()=>{if(renderer)act(()=>renderer.unmount());renderer=null;api.defaults.adapter=original;});
async function mount(){await act(async()=>{renderer=TestRenderer.create(<CaseFollowupContacts caseId={1} requestToken={token}/>);});}
async function fill(){await click('新增人工随访记录');await change('随访来源计划','1');for(const [label,v] of [['随访联系时间',fixture.contact.occurred_at.slice(0,16)],['随访联系方式',fixture.contact.method],['随访联系结果',fixture.contact.outcome],['随访记录原文',fixture.contact.note],['随访后续安排',fixture.contact.next_action]])await change(label,v);}
async function review(){await click('预览并核对人工随访');await act(async()=>input('已核对人工随访').props.onChange({target:{checked:true}}));}

test('strict raw protocol, source version, calendar and independent receipt validation',()=>{
 assert(validData(fixture.contact));for(const t of fixture.invalid_times)assert(!validTime(t),t);
 for(const value of [{note:' '},{note:'x'.repeat(2001)},{outcome:'done'},{method:'sms'},{extra:1}])assert(!validData({...fixture.contact,...value}));
 assert(validData({...fixture.contact,note:'🐾'.repeat(2000),next_action:'é'.repeat(1000)}));
 const l=empty();assert(validList(l,1));const r=record(fixture.contact,l);assert(validList({...l,records:[r]},1));
 for(const changed of [{version:2},{source:{...r.source,version:2}},{source_state:'withdrawn'},{recorded_by:'other'},{extra:1}])assert(!validList({...l,records:[{...r,...changed}]},1));
 assert(!validList({...l,records:[r,r]},1));assert(!validReceipt({schema,case_id:1,request_id:'x',state:'not_committed',writes_database:true},1,'x',true));
});
test('source/result are explicit; double confirm posts once then independently reads',async()=>{
 await mount();await click('新增人工随访记录');assert.equal(input('随访来源计划').props.value,'');assert.equal(input('随访联系结果').props.value,'');await click('放弃人工随访草稿');
 await fill();await click('预览并核对人工随访');assert(button('确认保存人工随访').props.disabled);
 await act(async()=>input('已核对人工随访').props.onChange({target:{checked:true}}));
 await act(async()=>{const fn=button('确认保存人工随访').props.onClick;await Promise.all([fn(),fn()]);});
 const posts=requests.filter(c=>c.url.endsWith('/confirm'));assert.equal(posts.length,1);assert.deepEqual(JSON.parse(posts[0].data).data,fixture.contact);
 assert.match(output(),/已保存并独立回读/);assert.equal(requests.at(-1).method,'get');
});
test('input, focus, visibility and source plan writes invalidate review and preserve draft',async()=>{
 await mount();await fill();await review();await change('随访记录原文','尚未保存');assert(!button('确认保存人工随访'));
 for(const event of ['focus','visibilitychange']){await review();await fire(event);assert(!button('确认保存人工随访'));assert.equal(input('随访记录原文').props.value,'尚未保存');}
 await review();const normal=adapter;adapter=async c=>c.url.endsWith('/followup-plan/confirm')?{config:c,data:{}}:normal(c);
 await act(async()=>api.post('/api/cases/1/followup-plan/confirm',{}));assert(!button('确认保存人工随访'));assert(!requests.some(c=>c.url.endsWith('/followup-contacts/confirm')));
});
test('lost reply checks same request and no repeat POST',async()=>{
 const normal=adapter;let saved;adapter=async c=>{if(c.url.endsWith('/confirm')){saved=(await normal(c)).data;throw Error('lost');}if(c.url.includes('/requests/'))return {config:c,data:{...saved,writes_database:false}};return normal(c);};
 await mount();await fill();await review();await click('确认保存人工随访');assert.match(output(),/已核对服务端保存结果/);assert.equal(requests.filter(c=>c.url.endsWith('/confirm')).length,1);
});
test('uncertain or wrong-source receipt locks writes until verified not committed',async()=>{
 const normal=adapter;let body;adapter=async c=>{if(c.url.endsWith('/confirm')){body=JSON.parse(c.data);throw Error('lost');}if(c.url.includes('/requests/'))return {config:c,data:{schema,case_id:1,request_id:body.request_id,state:'committed',operation:'create',record:{...record(body.data,listing),source:{...frozenSource(listing.plans[0]),id:999}},writes_database:false}};return normal(c);};
 await mount();await fill();await review();await click('确认保存人工随访');assert.match(output(),/保存结果待核对/);assert(button('预览并核对人工随访').props.disabled);
 await click('核对随访保存结果');assert.equal(requests.filter(c=>c.url.endsWith('/confirm')).length,1);
 adapter=async c=>c.url.includes('/requests/')?{config:c,data:{schema,case_id:1,request_id:body.request_id,state:'not_committed',writes_database:false}}:normal(c);
 await click('核对随访保存结果');await review();assert.equal(JSON.parse(requests.filter(c=>c.url.endsWith('/preview')).at(-1).data).request_id,body.request_id);
});
test('late preview after focus and account change cannot restore private content',async()=>{
 await mount();await fill();const normal=adapter;let release,arrive;const started=new Promise(r=>arrive=r);
 adapter=async c=>c.url.endsWith('/preview')?new Promise(r=>{release=()=>r({config:c,data:preview(JSON.parse(c.data),listing)});arrive();}):normal(c);
 let pending;await act(async()=>{pending=button('预览并核对人工随访').props.onClick();await started;});await fire('focus');await act(async()=>{release();await pending;});assert(!button('确认保存人工随访'));
 token='other';await fire('storage');assert(!button('新增人工随访记录'));assert.equal(renderer.root.findAllByProps({'aria-label':'人工随访草稿'}).length,0);
});
test('malformed preview or missing independent readback cannot report a confirmed save',async()=>{
 const normal=adapter;adapter=async c=>{const r=await normal(c);if(c.url.endsWith('/preview'))r.data.source.version=49;return r;};
 await mount();await fill();await click('预览并核对人工随访');assert(!button('确认保存人工随访'));assert.match(output(),/预览与本次输入不一致/);
 adapter=normal;await review();let receipt;
 adapter=async c=>{if(c.url.endsWith('/confirm')){receipt=(await normal(c)).data;listing.records=[];return {config:c,data:receipt};}if(c.url.includes('/requests/'))return {config:c,data:{...receipt,writes_database:false}};return normal(c);};
 await click('确认保存人工随访');assert.match(output(),/保存结果待核对/);assert.equal(input('随访记录原文').props.value,fixture.contact.note);
});
test('empty, disabled and damaged lists remain distinct and refresh is GET only',async()=>{
 listing.plans=[];await mount();assert.match(output(),/暂无当前有效/);assert(button('新增人工随访记录').props.disabled);
 adapter=async()=>{throw {response:{status:503,data:{detail:'followup_contacts_disabled'}}};};await click('刷新人工随访记录');assert.match(output(),/暂未启用/);assert(!button('新增人工随访记录'));
 adapter=async c=>({config:c,data:{...empty(),records:[{bad:true}]}});await click('刷新人工随访记录');assert.match(output(),/未收到完整/);assert(requests.every(c=>c.method==='get'));
});
