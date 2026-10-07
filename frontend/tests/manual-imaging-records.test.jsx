import React from 'react';
import TestRenderer, {act} from 'react-test-renderer';
import {test,beforeEach,afterEach} from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
import CaseImagingRecords from '../src/components/CaseImagingRecords';
import {newImagingData,editableImagingData} from '../src/manualImagingRecords';
import api from '../src/api';

let renderer,adapter,requests,token,props,records,listeners,dirty;
const aid='a'.repeat(64),version='b'.repeat(64);
const source={id:aid,name:'synthetic.pdf',mime:'application/pdf',size:3,sha256:'c'.repeat(64),metadata:{title:'合成原件'}};
const button=label=>renderer.root.findAllByType('button').find(n=>n.children.join('')===label);
const click=async label=>{assert(button(label)&&!button(label).props.disabled,label);await act(async()=>button(label).props.onClick());};
const field=label=>renderer.root.findByProps({'aria-label':label});
const change=(label,value)=>act(()=>field(label).props.onChange({target:{value}}));
const check=label=>act(()=>field(label).props.onChange({target:{checked:true}}));
const text=()=>JSON.stringify(renderer.toJSON());
const response=(c,data)=>({config:c,status:200,data});
const deferred=()=>{let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};};
async function draft(){await click('录入影像报告');change('影像原件',aid);change('报告标题','合成报告');change('检查部位','胸部');change('检查时间（含时区）','2026-10-07T09:30:00+08:00');change('所见原文','未见异常，仍保留限定描述。');change('页码或原件位置','第1页');check('已核对所见原文');check('已核对结论原文');}
async function review(){await draft();await click('核对整份影像记录');check('已核对整份影像记录');}
beforeEach(async()=>{
 token='synthetic-owner';records=[];requests=[];listeners={};dirty=false;
 Object.defineProperty(globalThis,'crypto',{configurable:true,value:webcrypto});
 global.localStorage={getItem:()=>token,setItem(){throw Error('No persistence');}};
 global.sessionStorage={setItem(){throw Error('No persistence');}};
 global.window={confirm:()=>true,addEventListener:(k,f)=>listeners[k]=f,removeEventListener:k=>delete listeners[k]};
 global.document={addEventListener:(k,f)=>listeners[k]=f,removeEventListener:k=>delete listeners[k]};
 props={caseId:1,requestToken:token,onDirtyChange:v=>dirty=v};
 adapter=async c=>{
  const current={case_id:props.caseId,case_token:version,patient_name:'合成病例-'+props.caseId,species:'dog'};
  if(c.url.endsWith('/manual-imaging'))return response(c,{...current,sources:[source],reports:records});
  if(c.url.endsWith('/preview')){const b=JSON.parse(c.data);return response(c,{case:current,identity:{},source,operation:b.operation,data:b.data,before:b.report_id?records[0]:null,reason:b.reason,preview_token:version});}
  if(c.url.endsWith('/confirm')){const b=JSON.parse(c.data);records=[{id:1,attachment_id:aid,token:version,source,data:b.data,version:1,state:'confirmed',reviewed_by:'1',reviewed_at:'synthetic'}];return response(c,{state:'committed',report:records[0]});}
  if(c.url.includes('/requests/'))return response(c,{state:'committed'});
  throw Error('Unexpected '+c.url);
 };
 api.defaults.adapter=async c=>{requests.push(c);return adapter(c);};
 await act(async()=>renderer=TestRenderer.create(<CaseImagingRecords {...props}/>));
});
afterEach(()=>act(()=>renderer.unmount()));

test('row and report checkboxes; exact strings and edited preview invalidation',async()=>{
 await draft();assert.equal(dirty,true);await click('核对整份影像记录');assert(button('确认保存影像记录').props.disabled);
 check('已核对整份影像记录');change('所见原文','更正原文 <tag> & {{visit.history}}');assert.equal(button('确认保存影像记录'),undefined);assert(button('核对整份影像记录').props.disabled);
 check('已核对所见原文');check('已核对结论原文');await click('核对整份影像记录');check('已核对整份影像记录');await click('确认保存影像记录');
 assert.equal(dirty,false);const writes=requests.filter(c=>c.url.endsWith('/confirm'));assert.equal(writes.length,1);assert.equal(JSON.parse(writes[0].data).data.findings,'更正原文 <tag> & {{visit.history}}');
});
test('lost reply uses only status GET; simultaneous confirm sends once',async()=>{
 await review();const normal=adapter;adapter=c=>c.url.endsWith('/confirm')?Promise.reject(Error('lost')):normal(c);
 const submit=button('确认保存影像记录').props.onClick;await act(async()=>Promise.all([submit(),submit()]));
 assert.equal(requests.filter(c=>c.url.endsWith('/confirm')).length,1);assert.equal(requests.filter(c=>c.url.includes('/requests/')).length,1);assert.match(text(),/已回读保存结果/);
});
test('unknown outcome freezes edits until GET resolves, never retries POST',async()=>{
 await review();const normal=adapter;adapter=c=>c.url.endsWith('/confirm')||c.url.includes('/requests/')?Promise.reject(Error('offline')):normal(c);
 await click('确认保存影像记录');assert.match(text(),/保存结果未知/);assert(button('核对整份影像记录').props.disabled);assert(button('放弃本页影像草稿').props.disabled);
 adapter=normal;await click('核对影像保存结果');assert.equal(requests.filter(c=>c.url.endsWith('/confirm')).length,1);
});
test('uncommitted status requires deliberate new preview',async()=>{
 await review();const normal=adapter;adapter=c=>c.url.endsWith('/confirm')?Promise.reject(Error('lost')):c.url.includes('/requests/')?response(c,{state:'not_committed'}):normal(c);
 await click('确认保存影像记录');assert.equal(button('确认保存影像记录'),undefined);assert.match(text(),/重新核对后保存/);
});
test('case switch drops unfinished draft and late preview',async()=>{
 await draft();const gate=deferred(),normal=adapter;adapter=c=>c.url.endsWith('/preview')?gate.promise.then(()=>normal(c)):normal(c);
 let pending;await act(async()=>{pending=button('核对整份影像记录').props.onClick();await new Promise(r=>setTimeout(r,0));});
 await act(async()=>{props={...props,caseId:2};renderer.update(<CaseImagingRecords {...props}/>);});
 await act(async()=>{gate.resolve();await pending;});assert.match(text(),/合成病例-2/);assert.equal(button('确认保存影像记录'),undefined);assert.equal(button('核对整份影像记录'),undefined);
});
test('account switch suppresses late response and clears memory on new owner',async()=>{
 await draft();const gate=deferred(),normal=adapter;adapter=c=>c.url.endsWith('/preview')?gate.promise.then(()=>normal(c)):normal(c);
 let pending;await act(async()=>{pending=button('核对整份影像记录').props.onClick();await new Promise(r=>setTimeout(r,0));});
 token='other';await act(async()=>{props={...props,requestToken:token};renderer.update(<CaseImagingRecords {...props}/>);gate.resolve();await pending;});
 assert.equal(button('确认保存影像记录'),undefined);assert.equal(button('核对整份影像记录'),undefined);
});
test('original change and explicit refresh invalidate whole-report confirmation',async()=>{
 await review();await act(async()=>{props={...props,sourceRevision:1};renderer.update(<CaseImagingRecords {...props}/>);});assert.equal(button('确认保存影像记录'),undefined);
 await click('核对整份影像记录');await click('刷新影像记录');assert.equal(button('确认保存影像记录'),undefined);
});
test('focus during a pending preview rejects the late preview and refreshes source state',async()=>{
 await draft();const gate=deferred(),normal=adapter;adapter=c=>c.url.endsWith('/preview')?gate.promise.then(()=>normal(c)):normal(c);
 let pending;await act(async()=>{pending=button('核对整份影像记录').props.onClick();await new Promise(r=>setTimeout(r,0));});
 await act(async()=>listeners.focus());await act(async()=>{gate.resolve();await pending;});
 assert.equal(button('确认保存影像记录'),undefined);assert.match(text(),/合成病例-1/);
 assert(requests.filter(c=>c.url.endsWith('/manual-imaging')).length>=2);
});
test('failed focus refresh does not keep showing a prior confirmed record',async()=>{
 await review();await click('确认保存影像记录');assert.match(text(),/已核对保存/);
 adapter=()=>Promise.reject(Error('offline'));await act(async()=>listeners.focus());
 assert.doesNotMatch(text(),/已核对保存/);assert.match(text(),/操作未确认/);
});
test('leaving unsaved draft warns; refused cancel retains content; no storage writes',async()=>{
 await draft();let stopped=0;listeners.beforeunload({preventDefault:()=>stopped++});assert.equal(stopped,1);
 window.confirm=()=>false;await click('放弃本页影像草稿');assert.equal(dirty,true);
 listeners.click({target:{closest:()=>true},preventDefault:()=>stopped++,stopPropagation:()=>stopped++});assert.equal(stopped,3);
 window.confirm=()=>true;await click('放弃本页影像草稿');assert.equal(dirty,false);
});
test('editing resets both section checks and never invents a date',()=>{
 const data=newImagingData();assert.equal(data.taken_at,'');data.findings='原文';data.checked_findings=data.checked_impression=true;
 const copy=editableImagingData(data);assert.equal(copy.findings,'原文');assert.equal(copy.checked_findings,false);assert.equal(copy.checked_impression,false);assert.equal(data.checked_findings,true);
});
