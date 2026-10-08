// CW-B16 owner template exercises shared guards with independent frozen expectations.
import React from 'react';
import TestRenderer,{act} from 'react-test-renderer';
import {MemoryRouter,Routes,Route} from 'react-router-dom';
import {test,beforeEach,afterEach} from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
import CaseDetail from '../src/pages/CaseDetail';
import api from '../src/api';
import {documentPlanSelection} from '../src/followupPlanDocuments';
import fixture from '../../tests/fixtures/clinical_followup_plan_owner_documents_cw_b16_cases.json';

let renderer,requests,adapter,listeners,downloads,listing,token;
const hash='a'.repeat(64),reply=(c,data,headers={})=>({config:c,status:200,data,headers});
const button=s=>renderer.root.findAllByType('button').find(n=>n.children.join('')===s);
const click=async s=>act(async()=>{assert(button(s),s);await button(s).props.onClick();});
const change=async(label,value)=>act(async()=>renderer.root.findByProps({'aria-label':label}).props.onChange({target:{value}}));
const text=()=>JSON.stringify(renderer.toJSON());
const confirm=async()=>act(async()=>renderer.root.findAllByType('input').find(n=>n.props.type==='checkbox'&&!n.props['aria-label']).props.onChange({target:{checked:true}}));
beforeEach(()=>{
  requests=[];listeners={};downloads=0;listing=structuredClone(fixture.listing);token='synthetic-owner';Object.defineProperty(globalThis,'crypto',{configurable:true,value:webcrypto});
  global.localStorage={getItem:()=>token};global.alert=()=>{};
  global.window={confirm:()=>true,addEventListener:(k,f)=>(listeners[k]??=new Set()).add(f),removeEventListener:(k,f)=>listeners[k]?.delete(f)};
  global.document={addEventListener(){},removeEventListener(){},body:{appendChild(){}},createElement:()=>({click(){downloads++;},remove(){}})};
  adapter=async c=>{
    if(c.url==='/api/cases/1')return reply(c,listing.case);
    if(c.url.endsWith('/followup-plan'))return reply(c,structuredClone(listing));
    if(c.url.endsWith('/manual-lab')||c.url.endsWith('/manual-imaging'))return reply(c,{case_id:1,case_token:hash,sources:[],reports:[],patient_name:fixture.case.patient_name,species:'dog'});
    if(c.url.endsWith('render-preview')){
      const b=JSON.parse(c.data),context={};for(const k of ['case_id','pet_name','owner_name','coat_color','species','age','sex','weight','complaint','history','exam','assessment','plan','notes','follow_up'])context['visit.'+k]='未填写';context['visit.case_id']='1';context['export.account_id']='1';
      return reply(c,{...b,context,content_snapshot:hash,missing_required_keys:[],writes_database:false,...(b.manual_followup_plan?{manual_followup_plan:documentPlanSelection(listing,listing.plans[0]).expected}:{})});
    }
    if(c.url.endsWith('/render'))return reply(c,new Blob(['synthetic docx'],{type:'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}),{'x-pmai-content-snapshot':hash});
    return reply(c,{});
  };
  api.defaults.adapter=async c=>{requests.push(c);return adapter(c);};
});
afterEach(()=>{if(renderer)act(()=>renderer.unmount());renderer=null;});
async function mount(){await act(async()=>renderer=TestRenderer.create(<MemoryRouter initialEntries={['/cases/1']}><Routes><Route path='/cases/:id' element={<CaseDetail/>}/></Routes></MemoryRouter>));}
async function open(){await click('导出宠主说明草稿 DOCX');await click('选择复查计划附节');}
async function selected(){await open();await click('将此计划纳入本次文书');await click('重新读取草稿');}
test('source navigation locates exact saved version and preserves unsaved lab, imaging and plan inputs',async()=>{
  await mount();await click('打开检验项目');await click('录入检验报告');await change('报告标题','保留检验草稿');
  await click('打开影像记录');await click('录入影像报告');await change('所见原文','保留影像草稿');
  await click('打开复查计划');await click('更正复查计划');await change('复查目的','保留复查编辑草稿');
  await open();await click('回看此复查计划版本');
  assert.equal(renderer.root.findByProps({'aria-label':'检验项目人工录入'}).findByProps({'aria-label':'报告标题'}).props.value,'保留检验草稿');assert.equal(renderer.root.findByProps({'aria-label':'所见原文'}).props.value,'保留影像草稿');assert.equal(renderer.root.findByProps({'aria-label':'复查目的'}).props.value,'保留复查编辑草稿');
  assert.match(text(),/正在回看计划 #1 版本 1/);assert(!requests.some(c=>c.url.endsWith('/confirm')||c.url.endsWith('/render')));
});
test('CaseDetail sends exact plan and snapshot only after whole review and permits one download',async()=>{
  await mount();await selected();assert(button('确认并下载草稿 DOCX').props.disabled);assert.equal(downloads,0);
  await confirm();await click('确认并下载草稿 DOCX');assert.equal(downloads,1);
  const b=JSON.parse(requests.find(c=>c.url.endsWith('/render')).data);assert.equal(b.template_id,'owner_visit_summary_zh');assert.equal(b.manual_lab_comparison,undefined);assert.equal(b.expected_content_snapshot,hash);assert.deepEqual(b.manual_followup_plan,{id:1,version:1,token:'c'.repeat(64)});assert.equal(b.manual_lab_report_ids,undefined);
});
test('real CaseDetail download continuation creates no browser download after focus invalidation',async()=>{
  await mount();await selected();await confirm();const normal=adapter;let release,arrive,pending;const seen=new Promise(r=>arrive=r),gate=new Promise(r=>release=r);
  adapter=async c=>{if(c.url.endsWith('/render')){arrive();await gate;}return normal(c);};
  await act(async()=>{pending=button('确认并下载草稿 DOCX').props.onClick();await seen;});
  await act(async()=>{for(const fn of [...listeners.focus])fn();});await act(async()=>{release();await pending;});
  assert.equal(downloads,0);assert(!button('确认并下载草稿 DOCX'));assert.doesNotMatch(text(),/已生成本次核对/);
});
test('plan save failure clears a selected document immediately and preserves editor input',async()=>{
  await mount();await click('打开复查计划');await click('更正复查计划');await change('复查目的','保存失败也保留');await selected();await confirm();
  const normal=adapter;adapter=async c=>c.url.endsWith('/followup-plan/confirm')?Promise.reject({config:c,response:{status:503}}):normal(c);
  await act(async()=>{await api.post('/api/cases/1/followup-plan/confirm',{}).catch(()=>{});});
  assert(!button('确认并下载草稿 DOCX'));assert.equal(renderer.root.findByProps({'aria-label':'复查目的'}).props.value,'保存失败也保留');assert.equal(downloads,0);
});
