import React from 'react';
import TestRenderer, {act} from 'react-test-renderer';
import {test, beforeEach, afterEach} from 'node:test';
import assert from 'node:assert/strict';
import Gate from '../src/components/ClinicalDoctorTrialGate';
import api from '../src/api';

const config = {enabled:true, api:'http://127.0.0.1:18027', session:'a'.repeat(64),
  head:'b'.repeat(40), source_sha256:'c'.repeat(64)};
const identity = {schema:'clinical-doctor-trial-cw-b26-v1', synthetic_only:true, ...config,
  cases:[{id:1,name:'CW26 合成犬'},{id:2,name:'CW26 合成猫'}],
  steps:['先核对，再保存'], sample_files:[{name:'合成 PNG',path:'/trial-samples/synthetic.png'}]};
const headers = {'x-pmai-trial-session':config.session, 'x-pmai-trial-head':config.head,
  'x-pmai-trial-source':config.source_sha256};
let renderer, listeners, calls, originalAdapter, originalBase, read, sent;
const output=()=>JSON.stringify(renderer.toJSON());
beforeEach(()=>{
  listeners=new Set();calls=0;sent=[];
  global.window={addEventListener:(name,fn)=>listeners.add(fn),removeEventListener:(name,fn)=>listeners.delete(fn)};
  global.localStorage={getItem:()=>null,removeItem:()=>{}};global.alert=()=>{};
  originalAdapter=api.defaults.adapter;originalBase=api.defaults.baseURL;
  api.defaults.baseURL=config.api;
  api.defaults.adapter=async value=>{sent.push(value);return {config:value,data:{ok:true},headers,status:200};};
  read=async()=>{calls++;return structuredClone(identity);};
});
afterEach(()=>{
  if(renderer)act(()=>renderer.unmount());renderer=null;
  api.defaults.adapter=originalAdapter;api.defaults.baseURL=originalBase;
  assert.equal(listeners.size,0);
});
async function mount(settings=config,reader=(...args)=>read(...args)){
  await act(async()=>{renderer=TestRenderer.create(<Gate config={settings} readIdentity={reader}><button>保存病例</button></Gate>);});
}
test('normal mode passes through without identity requests, banners or interceptors',async()=>{
  await mount({enabled:false});assert.equal(calls,0);assert.match(output(),/保存病例/);
  assert(!output().includes('合成病例练习'));await api.get('/ordinary');assert.equal(calls,0);
  assert(!sent[0].headers['X-PMAI-Trial-Session']);
});
test('matching session exposes fixed local cases, warning and sample downloads',async()=>{
  await mount();assert.match(output(),/合成病例练习，不录入真实资料/);assert.match(output(),/保存病例/);
  const links=renderer.root.findAllByType('a').map(n=>n.props.href);
  assert(links.includes('/cases/1')&&links.includes('/cases/2')&&links.includes('/trial-samples/synthetic.png'));
  await api.post('/api/cases',{patient_name:'synthetic'});assert.equal(calls,2);
  assert.equal(sent[0].headers['X-PMAI-Trial-Session'],config.session);
});
for(const change of [{session:'d'.repeat(64)},{head:'e'.repeat(40)},{source_sha256:'f'.repeat(64)},
  {synthetic_only:false},{sample_files:[{name:'foreign',path:'https://example.com/file'}]}]){
  test('mismatched identity blocks rendering and writes '+Object.keys(change)[0],async()=>{
    read=async()=>({...identity,...change});await mount();assert.match(output(),/试用环境未通过核对/);
    assert(!output().includes('保存病例'));await assert.rejects(api.post('/api/cases',{}));assert.equal(sent.length,0);
  });
}
test('remote API configuration is rejected before even requesting identity',async()=>{
  await mount({...config,api:'https://example.com'});assert.equal(calls,0);assert(!output().includes('保存病例'));
});
test('write is refused if backend identity changes after the page became ready',async()=>{
  await mount();read=async()=>({...identity,session:'f'.repeat(64)});
  await act(async()=>{await assert.rejects(api.post('/api/cases',{}));});
  assert.equal(sent.length,0);assert.match(output(),/试用环境未通过核对/);
});
test('a response from a different backend blocks subsequent actions',async()=>{
  await mount();api.defaults.adapter=async value=>({config:value,data:{},status:200,headers:{}});
  await act(async()=>{await assert.rejects(api.get('/api/cases'));});
  assert(!output().includes('保存病例'));
});
test('loss of connection on focus blocks the page without automatic retry of a write',async()=>{
  await mount();read=async()=>{throw new Error('offline');};
  await act(async()=>{for(const fn of listeners)fn();});
  assert.match(output(),/连接已断开/);assert(!output().includes('保存病例'));assert.equal(sent.length,0);
});
test('cancelling a superseded page read preserves the verified session',async()=>{
  await mount();api.defaults.adapter=async value=>{throw {config:value,code:'ERR_CANCELED'};};
  await act(async()=>{await assert.rejects(api.get('/api/cases'));});
  assert.match(output(),/保存病例/);assert(!output().includes('试用环境未通过核对'));
});
test('pending initial identity never mounts children and late completion after close is ignored',async()=>{
  let finish;read=()=>new Promise(resolve=>{finish=resolve;});
  await mount();assert(!output().includes('保存病例'));
  act(()=>renderer.unmount());renderer=null;
  await act(async()=>finish(identity));assert.equal(listeners.size,0);assert.equal(sent.length,0);
});
