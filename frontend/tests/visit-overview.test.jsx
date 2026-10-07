import React from 'react';
import TestRenderer, {act} from 'react-test-renderer';
import {MemoryRouter} from 'react-router-dom';
import {test, beforeEach, afterEach} from 'node:test';
import assert from 'node:assert/strict';
import CaseVisitOverview from '../src/components/CaseVisitOverview';
import {validateOverview} from '../src/visitOverview';
import api from '../src/api';
import fixture from '../../tests/fixtures/clinical_case_overview_cw_b10_cases.json';

let renderer, token, adapter, requests, props, listeners, navigations;
const payload = id => ({...structuredClone(fixture.overview), case_id:id});
const deferred = () => { let resolve, reject; const promise = new Promise((r,j) => { resolve=r; reject=j; }); return {promise,resolve,reject}; };
const text = () => JSON.stringify(renderer.toJSON());
const button = label => renderer.root.findAllByType('button').find(n => n.children.join('') === label);
const click = async label => act(async () => { assert(button(label),label); await button(label).props.onClick(); });
const tree = () => <MemoryRouter><CaseVisitOverview {...props}/></MemoryRouter>;
const update = async change => act(async () => { props={...props,...change}; renderer.update(tree()); });
const emit = async (name,event={}) => act(async () => { await Promise.all([...(listeners[name]||[])].map(fn => fn(event))); });
beforeEach(() => {
  token='synthetic-owner'; requests=[]; listeners={}; navigations=[];
  global.localStorage={getItem:()=>token,removeItem:()=>{token='';},setItem(){throw Error('Must not persist overview');}};
  global.sessionStorage={setItem(){throw Error('Must not persist overview');}}; global.alert=()=>{};
  global.window={addEventListener:(k,f)=>(listeners[k]??=new Set()).add(f),removeEventListener:(k,f)=>listeners[k]?.delete(f)};
  props={caseId:1,requestToken:token,onNavigate:target=>navigations.push(target)};
  adapter=async c=>({config:c,status:200,data:payload(Number(c.url.split('/')[3]))});
  api.defaults.adapter=async c=>{requests.push(c);return adapter(c);};
});
afterEach(()=>{if(renderer)act(()=>renderer.unmount());renderer=null;});
async function mount(){await act(async()=>{renderer=TestRenderer.create(tree());});}

test('only saved values are shown literally, no clinical claim, write or download',async()=>{
  await mount();assert.match(text(),/未见呕吐/);assert.match(text(),/未填写/);assert.match(text(),/本地未保存草稿未纳入/);
  assert.match(text(),/读取时的快照/);assert.match(text(),/不代表已确认诊断/);
  const value=renderer.root.findAllByType('div').find(n=>n.children.length===1&&n.children[0]===fixture.case.history);
  assert(value);assert(!renderer.root.findAll(n=>n.props.dangerouslySetInnerHTML).length);
  assert.equal(requests.length,1);assert(requests.every(c=>c.method==='get'&&c.url.endsWith('/visit-overview')));
});
test('navigation is internal and edit preserves drafts in a new tab',async()=>{
  await mount();await click('前往检验项目');await click('核对宠主说明草稿');assert.deepEqual(navigations,['lab','owner_summary']);
  for(const link of renderer.root.findAllByType('a')){assert.equal(link.props.href,'/cases/1/edit');assert.equal(link.props.target,'_blank');assert.equal(link.props.rel,'noopener noreferrer');}
  assert.equal(requests.length,1);
});
test('foreign id, unsupported schema, flags, status and navigation are rejected',()=>{
  for(const change of [{case_id:2},{schema:'unknown'},{writes_database:true},{includes_unsaved_drafts:true},{read_at:'bad'},{snapshot:''},{navigation_targets:['https://invalid.example']}])assert.throws(()=>validateOverview({...payload(1),...change},1));
  const data=payload(1);data.fields[0].state='diagnosed';assert.throws(()=>validateOverview(data,1));
  data.fields[0].state='recorded';data.groups.lab.counts.confirmed=1;assert.throws(()=>validateOverview(data,1));
});
test('disabled group is not represented as zero or a normal empty group',async()=>{
  adapter=async c=>{const data=payload(1);data.groups.lab={status:'disabled',records:null,counts:null,legacy_count:null};return {data};};
  await mount();assert.match(text(),/模块未启用，无法判断记录有无/);
  const invalid=payload(1);invalid.groups.lab={status:'disabled',records:[],counts:{},legacy_count:0};assert.throws(()=>validateOverview(invalid,1));
});
test('explicit refresh clears old snapshot before a response or error',async()=>{
  await mount();const gate=deferred();adapter=()=>gate.promise;let reading;await act(async()=>{reading=button('刷新就诊资料总览').props.onClick();});
  assert.doesNotMatch(text(),/CW-B10 合成病例/);assert.match(text(),/正在读取总览/);
  await act(async()=>{gate.reject({response:{status:503}});await reading;});assert.match(text(),/总览读取失败/);assert.doesNotMatch(text(),/CW-B10 合成病例/);
});
test('source revision clears old data; stale in-flight response cannot replace the new one',async()=>{
  const gate=deferred();let reads=0;adapter=c=>++reads===1?gate.promise:Promise.resolve({data:{...payload(1),identity:{...payload(1).identity,patient_name:'更正后的病例'}}});
  await mount();await update({sourceRevision:1});assert.match(text(),/更正后的病例/);
  await act(async()=>gate.resolve({data:payload(1)}));assert.match(text(),/更正后的病例/);assert.doesNotMatch(text(),/CW-B10 合成病例/);
});
test('a source operation invalidates immediately and refreshes without an editor callback',async()=>{
  await mount();const gate=deferred();const normal=adapter;
  adapter=c=>c.method==='post'?gate.promise.then(()=>({config:c,status:200,data:{state:'committed'}})):normal(c);
  let operation;await act(async()=>{operation=api.post('/api/cases/1/manual-lab/confirm',{});});
  assert.doesNotMatch(text(),/CW-B10 合成病例/);assert.match(text(),/资料操作已开始/);
  await act(async()=>{gate.resolve();await operation;});assert.match(text(),/CW-B10 合成病例/);
  assert.equal(requests.filter(c=>c.url.endsWith('/visit-overview')).length,2);
});
test('focus invalidates saved and pending snapshots and issues a fresh GET',async()=>{
  await mount();const gate=deferred();let reads=0;adapter=()=>++reads===1?gate.promise:Promise.resolve({data:{...payload(1),identity:{...payload(1).identity,patient_name:'重新读取病例'}}});
  let reading;await act(async()=>{reading=button('刷新就诊资料总览').props.onClick();});await emit('focus');
  await act(async()=>{gate.resolve({data:payload(1)});await reading;});assert.match(text(),/重新读取病例/);assert.equal(requests.length,3);
});
test('case change discards a late old response',async()=>{
  const gate=deferred();adapter=c=>c.url.includes('/1/')?gate.promise:Promise.resolve({data:{...payload(2),identity:{...payload(2).identity,patient_name:'病例二'}}});
  await mount();await update({caseId:2});await act(async()=>gate.resolve({data:payload(1)}));assert.match(text(),/病例二/);assert.doesNotMatch(text(),/CW-B10 合成病例/);
});
test('credential change and logout clear data even without parent remount',async()=>{
  await mount();token='other';await emit('storage',{key:'token'});assert.doesNotMatch(text(),/CW-B10 合成病例/);assert.match(text(),/登录已变化/);assert.equal(requests.length,1);
});
test('anonymous read sends no request; 401, 404 and unreadable data never become empty',async()=>{
  token='';props.requestToken='';await mount();assert.equal(requests.length,0);assert.match(text(),/登录已变化/);
  token='synthetic-owner';await update({requestToken:token});
  for(const status of [401,404,409]){adapter=()=>Promise.reject({response:{status}});await click('刷新就诊资料总览');assert.doesNotMatch(text(),/暂无本流程/);assert.doesNotMatch(text(),/CW-B10 合成病例/);}
});
