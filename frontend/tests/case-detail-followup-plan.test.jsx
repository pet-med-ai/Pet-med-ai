import React from 'react';
import TestRenderer,{act} from 'react-test-renderer';
import {MemoryRouter,Routes,Route} from 'react-router-dom';
import {test,beforeEach,afterEach} from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
import CaseDetail from '../src/pages/CaseDetail';
import CaseFollowupPlan from '../src/components/CaseFollowupPlan';
import CaseLabResults from '../src/components/CaseLabResults';
import api from '../src/api';
import fixture from '../../tests/fixtures/clinical_followup_plans_cw_b14_cases.json';

let renderer,requests,listeners,token,allow;
const button=name=>renderer.root.findAllByType('button').find(n=>n.children.join('')===name);
const click=async name=>act(async()=>{assert(button(name),name);await button(name).props.onClick();});
const change=async(label,value)=>act(async()=>renderer.root.findByProps({'aria-label':label}).props.onChange({target:{value}}));
const animal={id:1,owner_id:1,...Object.fromEntries(['patient_name','species','sex','age_info','breed','weight','coat_color','owner_name','owner_phone','chief_complaint','history','exam_findings','analysis','treatment','prognosis'].map(k=>[k,fixture.case[k]??null]))};
beforeEach(()=>{
 requests=[];listeners={};token='synthetic-owner';allow=true;Object.defineProperty(globalThis,'crypto',{configurable:true,value:webcrypto});
 global.localStorage={getItem:()=>token};global.alert=()=>{};global.window={confirm:()=>allow,addEventListener:(k,f)=>(listeners[k]??=new Set()).add(f),removeEventListener:(k,f)=>listeners[k]?.delete(f)};global.document={addEventListener(){},removeEventListener(){}};
 api.defaults.adapter=async c=>{requests.push(c);let data={};
 if(c.url==='/api/cases/1')data=animal;
 if(c.url.endsWith('/manual-lab'))data={case_id:1,case_token:'a'.repeat(64),sources:[],reports:[]};
 if(c.url.endsWith('/followup-plan'))data={schema:'clinical-followup-plans-cw-b14-v1',case_id:1,case:animal,as_of_date:'2026-10-08',timezone:'Asia/Shanghai',plans:[],limits:{items:10,versions:50},writes_database:false,case_token:'a'.repeat(64),state_token:'b'.repeat(64)};
 return {config:c,status:200,data};};
});
afterEach(()=>{if(renderer)act(()=>renderer.unmount());renderer=null;});
async function mount(){await act(async()=>{renderer=TestRenderer.create(<MemoryRouter initialEntries={['/cases/1']}><Routes><Route path='/cases/:id' element={<CaseDetail/>}/></Routes></MemoryRouter>);});}
test('lazy plan entry preserves pre-existing unsaved lab input and protects closing plan',async()=>{
 await mount();assert(!requests.some(c=>c.url.includes('/followup-plan')));
 await click('打开检验项目');await click('录入检验报告');await change('报告标题','CW-B14 未保存的旧检验草稿');
 await click('打开复查计划');await click('新增复查计划');await change('复查目的','未保存计划目的');
 assert.equal(renderer.root.findByProps({'aria-label':'报告标题'}).props.value,'CW-B14 未保存的旧检验草稿');
 allow=false;await click('收起复查计划');assert(button('收起复查计划'));allow=true;await click('收起复查计划');await click('打开复查计划');
 assert.equal(renderer.root.findAllByProps({'aria-label':'复查目的'}).length,0);assert.equal(renderer.root.findByProps({'aria-label':'报告标题'}).props.value,'CW-B14 未保存的旧检验草稿');
 assert(!requests.some(c=>c.url.endsWith('/confirm')||c.url.endsWith('/render')));
});
test('account transition clears the in-memory plan and sends no automatic writes',async()=>{
 await mount();await click('打开复查计划');await click('新增复查计划');await change('复查目的','账号 A 的未保存原文');
 token='other-account';await act(async()=>{for(const f of [...(listeners.storage||[])])f({key:'token'});});
 assert(!JSON.stringify(renderer.toJSON()).includes('账号 A 的未保存原文'));assert(!requests.some(c=>c.method==='post'));
});
