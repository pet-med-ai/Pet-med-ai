import React from 'react';
import TestRenderer, {act} from 'react-test-renderer';
import {MemoryRouter, Routes, Route, useNavigate} from 'react-router-dom';
import {test, beforeEach, afterEach} from 'node:test';
import assert from 'node:assert/strict';
import CaseDetail from '../src/pages/CaseDetail';
import api from '../src/api';

const mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document';
const record=id=>({id,patient_name:`合成病例-${id}`,history:`病史-${id}`,treatment:`更正治疗-${id}`});
const deferred=()=>{let resolve,reject;const promise=new Promise((r,j)=>{resolve=r;reject=j;});return {promise,resolve,reject};};
let renderer,navigate,requests,downloads,alerts,storage,adapter,listeners;
const originalCreate=URL.createObjectURL, originalRevoke=URL.revokeObjectURL;
const text=()=>JSON.stringify(renderer.toJSON());
const button=label=>renderer.root.findAllByType('button').find(n=>n.children.join('')===label);
const click=async label=>act(async()=>{assert(button(label),label);await button(label).props.onClick();});
const exports=()=>requests.filter(c=>c.url==='/api/clinical-docs/render');
const docResponse=c=>({config:c,status:200,headers:{'content-disposition':'attachment; filename="visit.docx"'},data:new Blob(['PK-synthetic'],{type:mime})});
function Nav(){navigate=useNavigate();return <Routes><Route path='/cases/:id' element={<CaseDetail/>}/><Route path='/' element={<div>首页</div>}/></Routes>;}
async function mount(){await act(async()=>{renderer=TestRenderer.create(<MemoryRouter initialEntries={['/cases/1']}><Nav/></MemoryRouter>);});}
const move=async path=>act(async()=>navigate(path));
beforeEach(()=>{
 storage='synthetic-owner';requests=[];downloads=[];alerts=[];listeners={};
 global.localStorage={getItem:()=>storage};global.alert=s=>alerts.push(s);
 global.window={addEventListener:(k,fn)=>{listeners[k]=fn;},removeEventListener:(k)=>{delete listeners[k];},print(){},location:{}};
 global.document={body:{appendChild(){}},createElement:()=>({click(){downloads.push(this.download);},remove(){}})};
 URL.createObjectURL=()=> 'blob:synthetic';URL.revokeObjectURL=()=>{};
 adapter=async c=>c.method==='post'?docResponse(c):({config:c,status:200,data:/^\/api\/cases\/\d+$/.test(c.url)?record(Number(c.url.split('/').at(-1))):{}});
 api.defaults.adapter=async c=>{requests.push(c);return adapter(c);};
});
afterEach(()=>{if(renderer)act(()=>renderer.unmount());renderer=null;URL.createObjectURL=originalCreate;URL.revokeObjectURL=originalRevoke;});

test('detail shows server history and corrected treatment',async()=>{await mount();assert.match(text(),/病史-1/);assert.match(text(),/更正治疗-1/);});
test('route change immediately removes previous case until current GET completes',async()=>{await mount();const gate=deferred();const original=adapter;adapter=c=>c.url==='/api/cases/2'?gate.promise:original(c);await move('/cases/2');assert.doesNotMatch(text(),/合成病例-1/);assert.match(text(),/加载中/);assert.equal(button('打印病例'),undefined);await act(async()=>gate.resolve({data:record(2)}));assert.match(text(),/合成病例-2/);});
test('late old detail response cannot replace the new case',async()=>{const gate=deferred(),original=adapter;adapter=c=>c.url==='/api/cases/1'?gate.promise:original(c);await mount();await move('/cases/2');await act(async()=>gate.resolve({data:record(1)}));assert.match(text(),/合成病例-2/);assert.doesNotMatch(text(),/合成病例-1/);});
test('late old failure cannot hide the new case',async()=>{const gate=deferred(),original=adapter;adapter=c=>c.url==='/api/cases/1'?gate.promise:original(c);await mount();await move('/cases/2');await act(async()=>gate.reject(Error('old-failure')));assert.match(text(),/合成病例-2/);assert.doesNotMatch(text(),/old-failure/);});
test('failed read can retry GET without any write',async()=>{const original=adapter;adapter=c=>c.url==='/api/cases/1'?Promise.reject(Error('temporary')):original(c);await mount();assert.match(text(),/temporary/);adapter=original;await click('重试读取病例');assert.match(text(),/合成病例-1/);assert.doesNotMatch(text(),/temporary/);assert(requests.every(c=>c.method==='get'));});
test('mismatched response ID is refused before edit print or export',async()=>{const original=adapter;adapter=c=>c.url==='/api/cases/1'?{data:record(2)}:original(c);await mount();assert.match(text(),/返回的病例与当前页面不一致/);assert.equal(button('打印病例'),undefined);assert.equal(exports().length,0);});
test('anonymous detail does not request a case',async()=>{storage='';await mount();assert.match(text(),/请先登录/);assert.equal(requests.length,0);});
test('cross-tab account change clears visible case while next account loads',async()=>{await mount();const gate=deferred(),original=adapter;adapter=c=>c.url==='/api/cases/1'?gate.promise:original(c);storage='synthetic-other';await act(async()=>listeners.storage({key:'token'}));assert.doesNotMatch(text(),/合成病例-1/);await act(async()=>gate.reject(Error('not-owned')));assert.match(text(),/not-owned/);});
test('both document buttons use the loaded case and existing read-only endpoint',async()=>{await mount();await click('导出入院/住院记录 DOCX');await click('导出出院小结 DOCX');assert.deepEqual(exports().map(c=>JSON.parse(c.data)),[{case_id:1,template_id:'admission_hospitalization_record_bilingual',output:'docx'},{case_id:1,template_id:'discharge_summary_bilingual',output:'docx'}]);assert.equal(downloads.length,2);assert(exports().every(c=>c.responseType==='blob'));});
test('same-tick double export submits once',async()=>{await mount();const gate=deferred(),original=adapter;adapter=async c=>{if(c.method==='post')await gate.promise;return original(c);};const submit=button('导出出院小结 DOCX').props.onClick;await act(async()=>{const a=submit(),b=submit();gate.resolve();await Promise.all([a,b]);});assert.equal(exports().length,1);assert.equal(downloads.length,1);});
test('leaving a case discards an outstanding document response',async()=>{await mount();const gate=deferred(),original=adapter;adapter=async c=>{if(c.method==='post')await gate.promise;return original(c);};let pending;act(()=>{pending=button('导出出院小结 DOCX').props.onClick();});await move('/cases/2');await act(async()=>{gate.resolve();await pending;});assert.equal(downloads.length,0);assert.doesNotMatch(text(),/已生成/);assert.match(text(),/合成病例-2/);});
test('credential change discards document even before a storage event',async()=>{await mount();const gate=deferred(),original=adapter;adapter=async c=>{if(c.method==='post')await gate.promise;return original(c);};let pending;act(()=>{pending=button('导出出院小结 DOCX').props.onClick();});storage='synthetic-other';await act(async()=>{gate.resolve();await pending;});assert.equal(downloads.length,0);});
test('blob JSON export failure explains the error and permits a deliberate retry',async()=>{await mount();const original=adapter;adapter=c=>{if(c.method==='post')throw {response:{data:new Blob([JSON.stringify({detail:'Case not found'})],{type:'application/json'})}};return original(c);};await click('导出出院小结 DOCX');assert(alerts.some(a=>a.includes('Case not found')));assert.equal(downloads.length,0);assert.equal(button('导出出院小结 DOCX').props.disabled,false);adapter=original;await click('导出出院小结 DOCX');assert.equal(exports().length,2);assert.equal(downloads.length,1);});
test('HTML success or empty response cannot be downloaded as DOCX',async()=>{await mount();const original=adapter;for(const blob of [new Blob(['<html>error</html>'],{type:'text/html'}),new Blob([],{type:mime})]){adapter=c=>c.method==='post'?{data:blob,headers:{}}:original(c);await click('导出出院小结 DOCX');}assert.equal(downloads.length,0);assert(alerts.every(a=>a.includes('未收到有效 DOCX')));});
test('malformed filename encoding falls back instead of losing a valid document',async()=>{await mount();const original=adapter;adapter=c=>c.method==='post'?{...docResponse(c),headers:{'content-disposition':'attachment; filename="bad%ZZ.docx"'}}:original(c);await click('导出出院小结 DOCX');assert.equal(downloads.length,1);assert.match(downloads[0],/case-1.*\.docx$/);});


for (const [label, template] of [
  ['导出门诊病历草稿 DOCX', 'outpatient_record_zh'],
  ['导出宠主说明草稿 DOCX', 'owner_visit_summary_zh'],
]) {
  test(`${template}: loaded case uses draft template on existing endpoint`, async () => {
    await mount(); await click(label);
    assert.deepEqual(JSON.parse(exports()[0].data), {case_id: 1, template_id: template, output: 'docx'});
    assert.equal(exports()[0].responseType, 'blob'); assert.equal(downloads.length, 1);
  });
  test(`${template}: simultaneous other-template click cannot duplicate export`, async () => {
    await mount(); const gate=deferred(), original=adapter;
    adapter=async c=>{if(c.method==='post')await gate.promise;return original(c);};
    const first=button(label).props.onClick, second=button('导出出院小结 DOCX').props.onClick;
    await act(async()=>{const a=first(),b=second();gate.resolve();await Promise.all([a,b]);});
    assert.equal(exports().length,1); assert.equal(downloads.length,1);
  });
  test(`${template}: changing case suppresses late draft`, async () => {
    await mount(); const gate=deferred(), original=adapter;
    adapter=async c=>{if(c.method==='post')await gate.promise;return original(c);};
    let pending; act(()=>{pending=button(label).props.onClick();}); await move('/cases/2');
    await act(async()=>{gate.resolve();await pending;}); assert.equal(downloads.length,0);
  });
  test(`${template}: account change suppresses late draft`, async () => {
    await mount(); const gate=deferred(), original=adapter;
    adapter=async c=>{if(c.method==='post')await gate.promise;return original(c);};
    let pending; act(()=>{pending=button(label).props.onClick();}); storage='synthetic-other';
    await act(async()=>{gate.resolve();await pending;}); assert.equal(downloads.length,0);
  });
  test(`${template}: navigation away suppresses late draft`, async () => {
    await mount(); const gate=deferred(), original=adapter;
    adapter=async c=>{if(c.method==='post')await gate.promise;return original(c);};
    let pending; act(()=>{pending=button(label).props.onClick();}); await move('/');
    await act(async()=>{gate.resolve();await pending;}); assert.equal(downloads.length,0);
  });
  test(`${template}: failed draft can retry without a case write`, async () => {
    await mount(); const original=adapter;
    adapter=c=>{if(c.method==='post')throw {response:{data:new Blob([JSON.stringify({detail:'Case not found'})],{type:'application/json'})}};return original(c);};
    await click(label); assert.equal(downloads.length,0); assert.equal(button(label).props.disabled,false);
    assert(alerts.some(a=>a.includes('Case not found'))); adapter=original; await click(label);
    assert.equal(downloads.length,1); assert.equal(exports().length,2);
    assert(requests.every(c=>c.method==='get'||c.url==='/api/clinical-docs/render'));
  });
}
