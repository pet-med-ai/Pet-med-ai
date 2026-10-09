import React from 'react';
import TestRenderer,{act} from 'react-test-renderer';
import {MemoryRouter,Routes,Route,useNavigate} from 'react-router-dom';
import {test,beforeEach,afterEach} from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
import CaseDetail from '../src/pages/CaseDetail';
import CaseFollowupContacts from '../src/components/CaseFollowupContacts';
import CaseFollowupPlan from '../src/components/CaseFollowupPlan';
import api from '../src/api';
import fixture from '../../tests/fixtures/clinical_followup_contact_queue_cw_b23_cases.json';

let renderer,requests,listeners,token,adapter,original,navigate;
function Navigation(){navigate=useNavigate();return null;}
const button=name=>renderer.root.findAllByType('button').find(n=>n.children.join('')===name);
const click=async name=>act(async()=>{assert(button(name),name);await button(name).props.onClick();});
const input=label=>renderer.root.findByProps({'aria-label':label});
const change=async(label,value)=>act(async()=>input(label).props.onChange({target:{value}}));
const output=()=>JSON.stringify(renderer.toJSON());
beforeEach(()=>{
 requests=[];listeners={};token='synthetic-owner';Object.defineProperty(globalThis,'crypto',{configurable:true,value:webcrypto});
 global.localStorage={getItem:()=>token};global.alert=()=>{};
 const events={addEventListener:(k,f)=>(listeners[k]??=new Set()).add(f),removeEventListener:(k,f)=>listeners[k]?.delete(f)};
 global.window={confirm:()=>true,...events};global.document={hidden:false,...events};
 adapter=async c=>{
  if(token==='other-account'&&c.url.startsWith('/api/cases/'))throw {response:{status:404,data:{detail:'Not found'}}};
  let data={};
  if(c.url==='/api/cases/1')data={id:1,...fixture.case};
  if(c.url.endsWith('/visit-overview'))data=structuredClone(fixture.overview);
  if(c.url.endsWith('/followup-plan'))data=structuredClone(fixture.plan_listing);
  if(c.url.endsWith('/followup-contacts'))data=structuredClone(fixture.contact_listing);
  if(c.url.endsWith('/manual-lab'))data={case_id:1,case_token:'a'.repeat(64),sources:[],reports:[]};
  return {config:c,status:200,data};
 };original=api.defaults.adapter;api.defaults.adapter=async c=>{requests.push(c);return adapter(c);};
});
afterEach(()=>{if(renderer)act(()=>renderer.unmount());renderer=null;api.defaults.adapter=original;});
async function mount(suffix='followup_contact=2&followup_contact_version=1'){await act(async()=>{renderer=TestRenderer.create(<MemoryRouter initialEntries={['/cases/1?'+suffix]}><Navigation/><Routes><Route path='/cases/:id' element={<CaseDetail/>}/></Routes></MemoryRouter>);});}

test('exact contact and plan navigation preserves three existing drafts and performs GET only',async()=>{
 await mount();assert(requests.some(c=>c.url.endsWith('/followup-contacts')));assert(!requests.some(c=>c.url.endsWith('/visit-overview')));
 await click('打开检验项目');await click('录入检验报告');await change('报告标题','CW-B20 未保存检验');
 await click('打开复查计划');await click('更正复查计划');await change('复查目的','CW-B20 未保存计划');
 await click('更正人工随访记录');await change('随访记录原文','CW-B20 未保存联系');
 const reads=requests.filter(c=>c.url.endsWith('/followup-contacts')).length;
 await act(async()=>navigate('/cases/1?followup_contact=2&followup_contact_version=1'));
 const target=renderer.root.findByType(CaseFollowupContacts).props.inspectTarget;assert.equal(target.id,2);assert.equal(target.version,1);
 assert(requests.filter(c=>c.url.endsWith('/followup-contacts')).length>reads);assert.match(output(),/正在回看随访 #/);
 assert.equal(input('随访记录原文').props.value,'CW-B20 未保存联系');assert.equal(input('复查目的').props.value,'CW-B20 未保存计划');assert.equal(input('报告标题').props.value,'CW-B20 未保存检验');
 await act(async()=>navigate('/cases/1?followup_plan=1&followup_version=1'));assert.equal(renderer.root.findByType(CaseFollowupPlan).props.inspectTarget.version,1);
 assert.equal(input('随访记录原文').props.value,'CW-B20 未保存联系');assert(requests.every(c=>c.method==='get'));
});
test('missing exact contact never substitutes another root or begins editing',async()=>{
 const normal=adapter;adapter=async c=>{const r=await normal(c);if(c.url.endsWith('/followup-contacts'))r.data.records=[{...r.data.records[0],id:9,root_id:9}];return r;};
 await mount();await act(async()=>navigate('/cases/1?followup_contact=2&followup_contact_version=1'));
 assert.match(output(),/指定随访版本当前无法读取/);assert.equal(renderer.root.findAllByProps({'aria-label':'人工随访草稿'}).length,0);
 const details=renderer.root.findAllByType('details');assert(!details.some(n=>n.props.open===true));
 assert(requests.every(c=>c.method==='get'));
});
test('navigation preserves unknown save outcome and never repeats its POST',async()=>{
 const normal=adapter;
 adapter=async c=>{
  if(c.url.endsWith('/followup-contacts/preview')){
   const b=JSON.parse(c.data),l=fixture.contact_listing,r=l.records[0];
   return {config:c,data:{schema:l.schema,case_id:1,case:l.case,as_of_date:l.as_of_date,timezone:l.timezone,
    before:structuredClone(r),source:structuredClone(r.source),source_state:r.source_state,data:b.data,operation:b.operation,reason:b.reason,
    request_id:b.request_id,writes_database:false,case_token:b.expected_case_token,state_token:b.expected_state_token,preview_token:'e'.repeat(64)}};
  }
  if(c.url.endsWith('/followup-contacts/confirm')||c.url.includes('/followup-contacts/requests/'))throw {config:c,response:{status:503}};
  return normal(c);
 };
 await mount();await click('更正人工随访记录');await change('随访更正或撤销原因','合成未知结果测试');
 await click('预览并核对人工随访');await act(async()=>input('已核对人工随访').props.onChange({target:{checked:true}}));
 await click('确认保存人工随访');assert.match(output(),/保存结果待核对/);
 await act(async()=>navigate('/cases/1?followup_contact=2&followup_contact_version=1'));
 assert.match(output(),/保存结果待核对/);assert(button('预览并核对人工随访').props.disabled);
 assert.equal(input('随访记录原文').props.value,fixture.contact.note);
 assert.equal(requests.filter(c=>c.url.endsWith('/followup-contacts/confirm')).length,1);
});
test('account transition clears the inspected contact and private draft without writing',async()=>{
 await mount();await act(async()=>navigate('/cases/1?followup_contact=2&followup_contact_version=1'));await click('更正人工随访记录');await change('随访记录原文','账号 A 未保存联系');
 token='other-account';await act(async()=>{for(const fn of [...(listeners.storage||[])])fn({key:'token'});});
 assert(!output().includes('账号 A 未保存联系'));assert(!output().includes('正在回看随访 #'));assert(requests.every(c=>c.method==='get'));
});

for(const suffix of ['followup_contact=0&followup_contact_version=1','followup_contact=2','followup_contact=2&followup_contact_version=51','followup_contact=2&followup_contact=3&followup_contact_version=1','followup_contact=9007199254740992&followup_contact_version=1','followup_contact=2&followup_contact_version=1&followup_plan=1&followup_version=1'])test('strict contact queue target '+suffix,async()=>{
 await mount(suffix);assert.match(output(),/随访定位信息无效/);assert(!requests.some(c=>c.url.endsWith('/followup-contacts')||c.url.endsWith('/followup-plan')));assert(requests.every(c=>c.method==='get'));
});
