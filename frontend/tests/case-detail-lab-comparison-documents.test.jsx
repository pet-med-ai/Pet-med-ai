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
import {documentSelection} from '../src/labComparisonDocuments';
import overviewFixture from '../../tests/fixtures/clinical_case_overview_cw_b10_cases.json';
import fixture from '../../tests/fixtures/clinical_lab_comparison_cw_b12_cases.json';

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
    if(c.url.endsWith('/lab-comparison/preview')){const b=JSON.parse(c.data);return {config:c,data:comparisonResult(b)};}
    if(c.url.endsWith('/lab-comparison'))return {config:c,data:structuredClone(fixture.review)};
    if(c.url.endsWith('/visit-overview'))return {data:structuredClone(overviewFixture.overview)};
    if(c.url==='/api/cases/1')return {data:{id:1,...fixture.case}};
    if(c.url.endsWith('/manual-lab'))return {config:c,data:{case_id:1,case_token:'b'.repeat(64),sources:[fixture.review.reports[0].source],reports:fixture.review.reports.map(r=>({...r,data:{report:r.report,items:r.items}}))}};
    if(c.url.endsWith('/manual-imaging'))return {data:{case_id:1,case_token:'b'.repeat(64),patient_name:fixture.case.patient_name,species:'dog',sources:[],reports:[]}};
    if(c.url.endsWith('/attachments'))return {data:{case_id:1,case_token:'b'.repeat(64),items:[],legacy_count:0}};
    if(c.url.endsWith('render-preview')){
      const body=JSON.parse(c.data),context={};
      for(const key of ['case_id','pet_name','species','age','sex','weight','complaint','history','exam','assessment','plan','notes','follow_up','owner_name','coat_color'])context['visit.'+key]='未填写';
      context['visit.case_id']='1';context['export.account_id']='1';
      return {config:c,data:{...body,...(body.manual_lab_comparison?{manual_lab_comparison:documentSelection(fixture.review,body.manual_lab_comparison,comparisonResult(body.manual_lab_comparison)).expected}:{}),context,content_snapshot:'a'.repeat(64),missing_required_keys:[],writes_database:false}};
    }
    return {data:{}};
  };
  api.defaults.adapter=async c=>{requests.push(c);return adapter(c);};
});
afterEach(()=>{if(renderer)act(()=>renderer.unmount());renderer=null;});
async function mount(){await act(async()=>{renderer=TestRenderer.create(<MemoryRouter initialEntries={['/cases/1']}><Routes><Route path='/cases/:id' element={<CaseDetail/>}/></Routes></MemoryRouter>);});}


function comparisonResult(b){return {...b,schema:fixture.review.schema,rules:fixture.review.rules,case_id:1,read_at:fixture.review.read_at,read_only:true,writes_database:false,includes_unsaved_drafts:false,can_calculate:true,reasons:[],reference_changed:true,delta:{value:fixture.expected_deltas[3],state:'increase',unit:'mmol/L'}};}
async function open(){await click('打开就诊资料总览');await click('核对门诊病历草稿');await click('选择检验前后对照附节');}
async function choose(){for(const [label,value] of [['对照报告 A','1'],['对照报告 B','2'],['对照项目 A','4'],['对照项目 B','4']])await act(async()=>renderer.root.findByProps({'aria-label':label}).props.onChange({target:{value}}));await act(async()=>renderer.root.findByProps({'aria-label':'确认方法与采样条件可比'}).props.onChange({target:{checked:true}}));await click('核对条件并预览数值差');await click('纳入本次文书核对');await click('重新读取草稿');}
test('document selection navigation uses exact version and preserves existing unsaved lab draft',async()=>{
 await mount();await click('打开检验项目');await click('录入检验报告');await act(async()=>renderer.root.findByProps({'aria-label':'报告标题'}).props.onChange({target:{value:'CW-B13 未保存草稿'}}));
 await open();await act(async()=>renderer.root.findByProps({'aria-label':'对照报告 A'}).props.onChange({target:{value:'1'}}));await click('回看检验记录 #1 版本 1');
 assert.equal(renderer.root.findByProps({'aria-label':'报告标题'}).props.value,'CW-B13 未保存草稿');assert.match(text(),/已定位检验记录 #1 版本 1/);assert(!requests.some(c=>c.url.endsWith('/render')));
});
test('CaseDetail passes the one pair and snapshot only after whole-document confirmation',async()=>{
 await mount();await open();await choose();assert(button('确认并下载草稿 DOCX').props.disabled);assert(!requests.some(c=>c.url.endsWith('/render')));
 const normal=adapter;adapter=async c=>c.url.endsWith('/render')?Promise.reject({config:c,response:{status:409}}):normal(c);
 await act(async()=>renderer.root.findAllByType('input').find(n=>n.props.type==='checkbox'&&!n.props['aria-label']).props.onChange({target:{checked:true}}));await click('确认并下载草稿 DOCX');
 const render=requests.filter(c=>c.url.endsWith('/render'));assert.equal(render.length,1);const b=JSON.parse(render[0].data);assert.equal(b.expected_content_snapshot,'a'.repeat(64));assert.equal(b.manual_lab_comparison.a.id,1);assert.equal(b.manual_lab_comparison.b.id,2);assert.equal(b.manual_lab_report_ids,undefined);assert.match(text(),/原确认已失效/);
});
