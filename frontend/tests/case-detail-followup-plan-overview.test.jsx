import React from 'react';
import TestRenderer,{act} from 'react-test-renderer';
import {MemoryRouter,Routes,Route} from 'react-router-dom';
import {test,beforeEach,afterEach} from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
import CaseDetail from '../src/pages/CaseDetail';
import CaseFollowupPlan from '../src/components/CaseFollowupPlan';
import api from '../src/api';
import fixture from '../../tests/fixtures/clinical_followup_plan_overview_cw_b17_cases.json';

let renderer,requests,listeners,token,adapter;
const button=name=>renderer.root.findAllByType('button').find(n=>n.children.join('')===name);
const click=async name=>act(async()=>{assert(button(name),name);await button(name).props.onClick();});
const change=async(label,value)=>act(async()=>renderer.root.findByProps({'aria-label':label}).props.onChange({target:{value}}));
const text=()=>JSON.stringify(renderer.toJSON());
beforeEach(()=>{
 requests=[];listeners={};token='synthetic-owner';Object.defineProperty(globalThis,'crypto',{configurable:true,value:webcrypto});
 global.localStorage={getItem:()=>token};global.alert=()=>{};global.window={confirm:()=>false,addEventListener:(k,f)=>(listeners[k]??=new Set()).add(f),removeEventListener:(k,f)=>listeners[k]?.delete(f)};global.document={addEventListener(){},removeEventListener(){}};
 adapter=async c=>{
  let data={};
  if(c.url==='/api/cases/1')data={id:1,...fixture.case};
  if(c.url.endsWith('/visit-overview'))data=structuredClone(fixture.overview);
  if(c.url.endsWith('/followup-plan'))data=structuredClone(fixture.listing);
  if(c.url.endsWith('/manual-lab')||c.url.endsWith('/manual-imaging'))data={case_id:1,case_token:'a'.repeat(64),sources:[],reports:[]};
  return {config:c,status:200,data};
 };api.defaults.adapter=async c=>{requests.push(c);return adapter(c);};
});
afterEach(()=>{if(renderer)act(()=>renderer.unmount());renderer=null;});
async function mount(){await act(async()=>{renderer=TestRenderer.create(<MemoryRouter initialEntries={['/cases/1']}><Routes><Route path='/cases/:id' element={<CaseDetail/>}/></Routes></MemoryRouter>);});}
test('overview is lazy and exact plan inspection preserves unsaved lab and plan drafts',async()=>{
 await mount();assert(!requests.some(c=>c.url.endsWith('/visit-overview')));
 await click('打开检验项目');await click('录入检验报告');await change('报告标题','CW-B17 未保存检验');
 await click('打开复查计划');await click('更正复查计划');await change('复查目的','CW-B17 未保存计划');
 await click('打开就诊资料总览');await click('回看计划 #1 版本 1');
 const target=renderer.root.findByType(CaseFollowupPlan).props.inspectTarget;assert.equal(target.id,1);assert.equal(target.version,1);
 assert.equal(renderer.root.findByProps({'aria-label':'复查目的'}).props.value,'CW-B17 未保存计划');
 assert.equal(renderer.root.findByProps({'aria-label':'报告标题'}).props.value,'CW-B17 未保存检验');
 assert.match(text(),/正在回看计划 #/);await click('收起就诊资料总览');await click('打开就诊资料总览');
 assert.equal(renderer.root.findByProps({'aria-label':'复查目的'}).props.value,'CW-B17 未保存计划');assert(requests.every(c=>c.method==='get'));
});
test('missing exact target is reported and never substituted with another plan',async()=>{
 const normal=adapter;adapter=async c=>{const r=await normal(c);if(c.url.endsWith('/followup-plan'))r.data.plans=[];return r;};
 await mount();await click('打开就诊资料总览');await click('回看计划 #1 版本 1');assert.match(text(),/指定计划版本当前无法读取/);assert(!button('更正复查计划'));
 assert(!requests.some(c=>c.method==='post'));
});
test('account changes clear both panels without writing or exporting',async()=>{
 await mount();await click('打开就诊资料总览');await click('回看计划 #1 版本 1');await click('更正复查计划');await change('复查目的','账号 A 的未保存原文');
 token='other-account';await act(async()=>{for(const fn of [...(listeners.storage||[])])fn({key:'token'});});
 assert(!text().includes('账号 A 的未保存原文'));assert(!button('回看计划 #1 版本 1'));assert(requests.every(c=>c.method==='get'));
});
