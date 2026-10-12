import React from 'react';
import TestRenderer,{act} from 'react-test-renderer';
import {MemoryRouter,Routes,Route,useNavigate} from 'react-router-dom';
import {test,beforeEach,afterEach} from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
import CaseDetail from '../src/pages/CaseDetail';
import CaseFollowupPlan from '../src/components/CaseFollowupPlan';
import api from '../src/api';
import fixture from '../../tests/fixtures/clinical_followup_plan_overview_cw_b17_cases.json';
let renderer,requests,adapter,token,listeners,navigate,original;
const output=()=>JSON.stringify(renderer.toJSON());
const button=name=>renderer.root.findAllByType('button').find(n=>n.children.join('')===name);
const click=async name=>act(async()=>{assert(button(name),name);await button(name).props.onClick();});
const change=async(label,value)=>act(async()=>renderer.root.findByProps({'aria-label':label}).props.onChange({target:{value}}));
function Navigation(){navigate=useNavigate();return null;}
beforeEach(()=>{
 token='synthetic-owner';requests=[];listeners={};Object.defineProperty(globalThis,'crypto',{configurable:true,value:webcrypto});
 global.localStorage={getItem:()=>token};global.alert=()=>{};
 const events={addEventListener:(k,f)=>(listeners[k]??=new Set()).add(f),removeEventListener:(k,f)=>listeners[k]?.delete(f)};
 global.window={...events,confirm:()=>false};global.document={...events};original=api.defaults.adapter;
 adapter=async c=>{let data={};if(c.url==='/api/cases/1')data={id:1,...fixture.case};if(c.url.endsWith('/followup-plan'))data=structuredClone(fixture.listing);if(c.url.endsWith('/manual-lab'))data={case_id:1,case_token:'a'.repeat(64),sources:[],reports:[]};return {config:c,status:200,data};};
 api.defaults.adapter=async c=>{requests.push(c);return adapter(c);};
});
afterEach(()=>{if(renderer)act(()=>renderer.unmount());renderer=null;api.defaults.adapter=original;});
async function mount(path='/cases/1?followup_plan=1&followup_version=1'){await act(async()=>{renderer=TestRenderer.create(<MemoryRouter initialEntries={[path]}><Navigation/><Routes><Route path='/cases/:id' element={<CaseDetail/>}/><Route path='/followup-plans' element={<p>清单</p>}/></Routes></MemoryRouter>);});}

test('queue deep link independently reads case and exact plan; carries no text or tokens',async()=>{
 await mount();assert.match(output(),/正在回看计划 #/);const target=renderer.root.findByType(CaseFollowupPlan).props.inspectTarget;assert.equal(target.id,1);assert.equal(target.version,1);
 assert(requests.some(c=>c.url==='/api/cases/1'));assert(requests.some(c=>c.url==='/api/cases/1/followup-plan'));assert(requests.every(c=>c.method==='get'));
 assert(renderer.root.findAllByType('a').some(n=>n.props.href==='/followup-plans'));
});
test('same-case target changes preserve unsaved plan and lab drafts; cross-case links retain leave protection',async()=>{
 await mount();await click('更正复查计划');await change('复查目的','CW-B18 未保存计划');await click('打开检验项目');await click('录入检验报告');await change('报告标题','CW-B18 未保存检验');
 await act(async()=>navigate('/cases/1?followup_plan=1&followup_version=1'));
 assert.equal(renderer.root.findByProps({'aria-label':'复查目的'}).props.value,'CW-B18 未保存计划');assert.equal(renderer.root.findByProps({'aria-label':'报告标题'}).props.value,'CW-B18 未保存检验');
 let prevented=0;await act(async()=>{for(const fn of [...listeners.click])fn({target:{closest:()=>({href:'/cases/2'})},preventDefault:()=>prevented++,stopPropagation(){}});});assert(prevented>0);assert(requests.every(c=>c.method==='get'));
});
for(const suffix of ['followup_plan=0&followup_version=1','followup_plan=1&followup_version=51','followup_plan=1','followup_plan=1&followup_plan=2&followup_version=1','followup_plan=9007199254740992&followup_version=1'])test('rejects malformed target '+suffix,async()=>{
 await mount('/cases/1?'+suffix);assert.match(output(),/计划定位信息无效/);assert(!requests.some(c=>c.url.endsWith('/followup-plan')));
});
test('missing or another-case target cannot fall back to a current plan',async()=>{
 await mount('/cases/1?followup_plan=9999&followup_version=1');assert.match(output(),/指定计划版本当前无法读取/);assert(!renderer.root.findAllByType('details').some(n=>n.props.open===true));assert(requests.every(c=>c.method==='get'));
});
test('withdrawn exact target remains visible with its state and original text',async()=>{
 const normal=adapter;adapter=async c=>{const r=await normal(c);if(c.url.endsWith('/followup-plan')){const p=r.data.plans[0];p.state='withdrawn';p.stored_state='withdrawn';p.withdrawal={reason:'合成撤销',by:'1',at:'2028-02-29T08:00:00+00:00'};}return r;};
 await mount();assert.match(output(),/正在回看计划 #/);assert.match(output(),/已撤销/);assert(!button('更正复查计划'));
});
test('expired account response cannot expose the requested case or trigger writes',async()=>{
 adapter=async()=>{throw {response:{status:401,data:{detail:'Invalid token'}}};};await mount();assert.match(output(),/加载失败/);assert(!requests.some(c=>c.url.endsWith('/followup-plan')));assert(requests.every(c=>c.method==='get'));
});
