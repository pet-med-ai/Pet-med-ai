import React from 'react';
import TestRenderer,{act} from 'react-test-renderer';
import {MemoryRouter,Routes,Route} from 'react-router-dom';
import {test,beforeEach,afterEach} from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
import CaseDetail from '../src/pages/CaseDetail';
import api from '../src/api';
import {documentContactSelection} from '../src/followupContactDocuments';
import fixture from '../../tests/fixtures/clinical_followup_contact_owner_documents_cw_b22_cases.json';
let renderer,requests,adapter,listeners,downloads,listing,token;
const hash='a'.repeat(64),reply=(c,data,headers={})=>({config:c,status:200,data,headers});
const button=s=>renderer.root.findAllByType('button').find(n=>n.children.join('')===s);
const click=async s=>act(async()=>{assert(button(s),s);await button(s).props.onClick();});
const change=async(label,value)=>act(async()=>renderer.root.findByProps({'aria-label':label}).props.onChange({target:{value}}));
const text=()=>JSON.stringify(renderer.toJSON());
const confirm=async()=>act(async()=>{const b=renderer.root.findAllByType('input').find(n=>n.props.type==='checkbox'&&!n.props['aria-label']);assert(b&&!b.props.disabled);b.props.onChange({target:{checked:true}});});
beforeEach(()=>{
 requests=[];listeners={};downloads=0;listing=structuredClone(fixture.contact_listing);token='synthetic-owner';Object.defineProperty(globalThis,'crypto',{configurable:true,value:webcrypto});
 global.localStorage={getItem:()=>token};global.alert=()=>{};
 global.window={confirm:()=>true,addEventListener:(k,f)=>(listeners[k]??=new Set()).add(f),removeEventListener:(k,f)=>listeners[k]?.delete(f)};
 global.document={hidden:false,addEventListener(){},removeEventListener(){},body:{appendChild(){}},createElement:()=>({click(){downloads++;},remove(){}})};
 adapter=async c=>{
  if(c.url==='/api/cases/1')return reply(c,listing.case);
  if(c.url.endsWith('/followup-contacts'))return reply(c,structuredClone(listing));
  if(c.url.endsWith('/followup-plan'))return reply(c,structuredClone(fixture.plan_listing));
  if(c.url.endsWith('/manual-lab')||c.url.endsWith('/manual-imaging'))return reply(c,{case_id:1,case_token:hash,sources:[],reports:[],patient_name:listing.case.patient_name,species:'dog'});
  if(c.url.endsWith('render-preview')){
   const b=JSON.parse(c.data),context={};for(const k of ['case_id','pet_name','owner_name','coat_color','species','age','sex','weight','complaint','history','exam','assessment','plan','notes','follow_up'])context['visit.'+k]='未填写';context['visit.case_id']='1';context['export.account_id']='1';
   return reply(c,{...b,context,content_snapshot:hash,missing_required_keys:[],writes_database:false,...(b.manual_followup_contact?{manual_followup_contact:{...documentContactSelection(listing,listing.records[0],'owner_visit_summary_zh').expected,audit_token:hash}}:{})});
  }
  if(c.url.endsWith('/render'))return reply(c,new Blob(['synthetic docx'],{type:'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}),{'x-pmai-content-snapshot':hash});
  return reply(c,{});
 };
 api.defaults.adapter=async c=>{requests.push(c);return adapter(c);};
});
afterEach(()=>{if(renderer)act(()=>renderer.unmount());renderer=null;});
async function mount(){await act(async()=>renderer=TestRenderer.create(<MemoryRouter initialEntries={['/cases/1']}><Routes><Route path='/cases/:id' element={<CaseDetail/>}/></Routes></MemoryRouter>));}
async function open(){await click('导出宠主说明草稿 DOCX');await click('选择人工随访记录附节');}
async function selected(){await open();await click('将此随访纳入本次文书');await click('重新读取草稿');}
for(const source of [false,true])test(`exact ${source?'source plan':'contact'} navigation preserves lab and plan drafts`,async()=>{
 await mount();await click('打开检验项目');await click('录入检验报告');await change('报告标题','CW22 保留检验草稿');
 await click('打开复查计划');await click('更正复查计划');await change('复查目的','CW22 保留复查草稿');
 await open();await click(source?'回看此随访来源计划':'回看此随访版本');
 assert.equal(renderer.root.findByProps({'aria-label':'报告标题'}).props.value,'CW22 保留检验草稿');assert.equal(renderer.root.findByProps({'aria-label':'复查目的'}).props.value,'CW22 保留复查草稿');
 assert.match(text(),source?/正在回看计划 #1 版本 1/:/正在回看随访 #2 版本 1/);assert(!requests.some(c=>c.url.endsWith('/confirm')||c.url.endsWith('/render')));
});
test('real CaseDetail passes five selection fields and full snapshot only after review',async()=>{
 await mount();await selected();assert(button('确认并下载草稿 DOCX').props.disabled);assert.equal(downloads,0);await confirm();await click('确认并下载草稿 DOCX');assert.equal(downloads,1);
 const b=JSON.parse(requests.find(c=>c.url.endsWith('/render')).data);assert.equal(b.template_id,'owner_visit_summary_zh');assert.equal(b.expected_content_snapshot,hash);assert.deepEqual(b.manual_followup_contact,documentContactSelection(listing,listing.records[0],'owner_visit_summary_zh').request);assert.equal(b.manual_followup_plan,undefined);
});
test('late CaseDetail download is discarded after focus invalidation',async()=>{
 await mount();await selected();await confirm();const normal=adapter;let release,arrive,pending;const seen=new Promise(r=>arrive=r),gate=new Promise(r=>release=r);
 adapter=async c=>{if(c.url.endsWith('/render')){arrive();await gate;}return normal(c);};await act(async()=>{pending=button('确认并下载草稿 DOCX').props.onClick();await seen;});
 await act(async()=>{for(const fn of [...listeners.focus])fn();});await act(async()=>{release();await pending;});assert.equal(downloads,0);assert(!button('确认并下载草稿 DOCX'));assert.doesNotMatch(text(),/已生成本次核对/);
});
test('contact write lost reply preserves existing doctor input and invalidates document',async()=>{
 await mount();await click('打开复查计划');await click('更正复查计划');await change('复查目的','CW22 丢回包仍保留');await selected();await confirm();
 const normal=adapter;adapter=async c=>c.url.endsWith('/followup-contacts/confirm')?Promise.reject({config:c,response:{status:503}}):normal(c);
 await act(async()=>{await api.post('/api/cases/1/followup-contacts/confirm',{}).catch(()=>{});});assert(!button('确认并下载草稿 DOCX'));assert.equal(renderer.root.findByProps({'aria-label':'复查目的'}).props.value,'CW22 丢回包仍保留');assert.equal(downloads,0);
});
test('switching owner to clinical and back never reuses contact selection or confirmation',async()=>{
 await mount();await selected();await confirm();await click('关闭草稿核对');
 for(const label of ['导出门诊病历草稿 DOCX','导出宠主说明草稿 DOCX']){
  await click(label);assert.doesNotMatch(text(),/文书人工随访附节/);assert(button('确认并下载草稿 DOCX').props.disabled);
  assert.equal(JSON.parse(requests.filter(c=>c.url.endsWith('render-preview')).at(-1).data).manual_followup_contact,undefined);await click('关闭草稿核对');
 }
 assert.equal(downloads,0);
});
