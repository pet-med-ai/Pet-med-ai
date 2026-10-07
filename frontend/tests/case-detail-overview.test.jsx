import React from 'react';
import TestRenderer, {act} from 'react-test-renderer';
import {MemoryRouter, Routes, Route} from 'react-router-dom';
import {test,beforeEach,afterEach} from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
import CaseDetail from '../src/pages/CaseDetail';
import CaseLabResults from '../src/components/CaseLabResults';
import CaseImagingRecords from '../src/components/CaseImagingRecords';
import CaseAttachments from '../src/components/CaseAttachments';
import api from '../src/api';
import fixture from '../../tests/fixtures/clinical_case_overview_cw_b10_cases.json';

let renderer,requests,adapter,listeners;
const button=label=>renderer.root.findAllByType('button').find(n=>n.children.join('')===label);
const click=async label=>act(async()=>{assert(button(label),label);await button(label).props.onClick();});
const text=()=>JSON.stringify(renderer.toJSON());
beforeEach(()=>{
  requests=[];listeners={};Object.defineProperty(globalThis,'crypto',{configurable:true,value:webcrypto});
  global.localStorage={getItem:()=> 'synthetic-owner'};global.alert=()=>{};
  global.window={confirm:()=>true,addEventListener:(k,f)=>(listeners[k]??=new Set()).add(f),removeEventListener:(k,f)=>listeners[k]?.delete(f)};
  global.document={addEventListener(){},removeEventListener(){}};
  adapter=async c=>{
    if(c.url.endsWith('/visit-overview'))return {data:structuredClone(fixture.overview)};
    if(c.url==='/api/cases/1')return {data:{id:1,...fixture.case}};
    if(c.url.endsWith('/manual-lab')||c.url.endsWith('/manual-imaging'))return {data:{case_id:1,case_token:'b'.repeat(64),patient_name:fixture.case.patient_name,species:'dog',sources:[],reports:[]}};
    if(c.url.endsWith('/attachments'))return {data:{case_id:1,case_token:'b'.repeat(64),items:[],legacy_count:0}};
    if(c.url.endsWith('render-preview')){
      const body=JSON.parse(c.data),context={};
      for(const key of ['case_id','pet_name','species','age','sex','weight','complaint','history','exam','assessment','plan','notes','follow_up','owner_name','coat_color'])context['visit.'+key]='未填写';
      context['visit.case_id']='1';context['export.account_id']='1';
      return {data:{...body,context,content_snapshot:'a'.repeat(64),missing_required_keys:[],writes_database:false}};
    }
    return {data:{}};
  };
  api.defaults.adapter=async c=>{requests.push(c);return adapter(c);};
});
afterEach(()=>{if(renderer)act(()=>renderer.unmount());renderer=null;});
async function mount(){await act(async()=>{renderer=TestRenderer.create(<MemoryRouter initialEntries={['/cases/1']}><Routes><Route path='/cases/:id' element={<CaseDetail/>}/></Routes></MemoryRouter>);});}

test('overview stays lazy until explicitly opened; inspecting it only uses GET',async()=>{
  await mount();assert(!requests.some(c=>c.url.endsWith('/visit-overview')));await click('打开就诊资料总览');assert.match(text(),/就诊资料总览/);assert(requests.every(c=>c.method==='get'));
});
test('navigating between existing panels and overview preserves unfinished lab draft',async()=>{
  await mount();await click('打开检验项目');await click('录入检验报告');
  await act(async()=>renderer.root.findByProps({'aria-label':'报告标题'}).props.onChange({target:{value:'未保存检验草稿'}}));
  await click('打开就诊资料总览');await click('前往影像记录');await click('前往检查资料');await click('前往检验项目');
  assert.equal(renderer.root.findByProps({'aria-label':'报告标题'}).props.value,'未保存检验草稿');
  const edit=renderer.root.findAllByType('a').find(n=>n.props.target==='_blank');assert.equal(edit.props.href,'/cases/1/edit');assert.equal(edit.props.rel,'noopener noreferrer');
  assert(requests.every(c=>c.method==='get'));await click('收起就诊资料总览');assert.equal(renderer.root.findByProps({'aria-label':'报告标题'}).props.value,'未保存检验草稿');
});
test('existing source, lab and imaging completion callbacks refresh overview independently',async()=>{
  await mount();await click('打开就诊资料总览');await click('前往检查资料');await click('前往检验项目');await click('前往影像记录');
  let expected=requests.filter(c=>c.url.endsWith('/visit-overview')).length;
  for(const Component of [CaseAttachments,CaseLabResults,CaseImagingRecords]){
    await act(async()=>renderer.root.findByType(Component).props.onChanged());
    assert.equal(requests.filter(c=>c.url.endsWith('/visit-overview')).length,++expected);
  }
  assert(requests.every(c=>c.method==='get'));
});
test('both overview document entrances preserve whole-document review and do not export',async()=>{
  await mount();await click('打开就诊资料总览');
  for(const label of ['核对门诊病历草稿','核对宠主说明草稿']){
    await click(label);assert(button('确认并下载草稿 DOCX').props.disabled);await click('关闭草稿核对');
  }
  assert.equal(requests.filter(c=>c.url.endsWith('render-preview')).length,2);
  assert(!requests.some(c=>c.url==='/api/clinical-docs/render'));
  assert(requests.every(c=>c.method==='get'||c.url.endsWith('render-preview')));
});
