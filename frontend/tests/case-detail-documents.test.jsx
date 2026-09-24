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
const previews=()=>requests.filter(c=>c.url==='/api/clinical-docs/render-preview');
const snapshot='a'.repeat(64);
const previewResponse=c=>{
 const body=JSON.parse(c.data), context={};
 for(const k of ['case_id','pet_name','species','age','sex','weight','complaint','history','exam','assessment','plan','notes','follow_up'])context['visit.'+k]='未填写';
 context['visit.case_id']=String(body.case_id);context['visit.pet_name']='合成病例-'+body.case_id;context['visit.history']='预览原文\n未见呕吐 < & {{literal}}';context['export.account_id']='1';
 return {config:c,status:200,data:{...body,context,content_snapshot:snapshot,missing_required_keys:[],writes_database:false}};
};
const docResponse=c=>({config:c,status:200,headers:{'content-disposition':'attachment; filename="visit.docx"','x-pmai-content-snapshot':JSON.parse(c.data).expected_content_snapshot},data:new Blob(['PK-synthetic'],{type:mime})});
const check=async()=>act(async()=>renderer.root.findByProps({'aria-label':'文书草稿内容核对'}).findByType('input').props.onChange({target:{checked:true}}));
const confirm=async()=>{await check();await click('确认并下载草稿 DOCX');};
function Nav(){navigate=useNavigate();return <Routes><Route path='/cases/:id' element={<CaseDetail/>}/><Route path='/' element={<div>首页</div>}/></Routes>;}
async function mount(){await act(async()=>{renderer=TestRenderer.create(<MemoryRouter initialEntries={['/cases/1']}><Nav/></MemoryRouter>);});}
const move=async path=>act(async()=>navigate(path));
beforeEach(()=>{
 storage='synthetic-owner';requests=[];downloads=[];alerts=[];listeners={};
 global.localStorage={getItem:()=>storage};global.alert=s=>alerts.push(s);
 global.window={addEventListener:(k,fn)=>{listeners[k]=fn;},removeEventListener:(k)=>{delete listeners[k];},print(){},location:{}};
 global.document={body:{appendChild(){}},createElement:()=>({click(){downloads.push(this.download);},remove(){}})};
 URL.createObjectURL=()=> 'blob:synthetic';URL.revokeObjectURL=()=>{};
 adapter=async c=>c.url==='/api/clinical-docs/render-preview'?previewResponse(c):c.method==='post'?docResponse(c):({config:c,status:200,data:/^\/api\/cases\/\d+$/.test(c.url)?record(Number(c.url.split('/').at(-1))):{}});
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
    assert.equal(exports().length,0); await confirm();
    assert.deepEqual(JSON.parse(exports()[0].data), {case_id: 1, template_id: template, output: 'docx',expected_content_snapshot:snapshot});
    assert.equal(exports()[0].responseType, 'blob'); assert.equal(downloads.length, 1);
  });
  test(`${template}: simultaneous other-template click cannot duplicate export`, async () => {
    await mount(); await click(label); await check(); const gate=deferred(), original=adapter;
    adapter=async c=>{if(c.url==='/api/clinical-docs/render')await gate.promise;return original(c);};
    const first=button('确认并下载草稿 DOCX').props.onClick, second=button('导出出院小结 DOCX').props.onClick;
    await act(async()=>{const a=first(),b=second();gate.resolve();await Promise.all([a,b]);});
    assert.equal(exports().length,1); assert.equal(downloads.length,1);
  });
  test(`${template}: changing case suppresses late draft`, async () => {
    await mount(); await click(label); await check(); const gate=deferred(), original=adapter;
    adapter=async c=>{if(c.method==='post')await gate.promise;return original(c);};
    let pending; act(()=>{pending=button('确认并下载草稿 DOCX').props.onClick();}); await move('/cases/2');
    await act(async()=>{gate.resolve();await pending;}); assert.equal(downloads.length,0);
  });
  test(`${template}: account change suppresses late draft`, async () => {
    await mount(); await click(label); await check(); const gate=deferred(), original=adapter;
    adapter=async c=>{if(c.method==='post')await gate.promise;return original(c);};
    let pending; act(()=>{pending=button('确认并下载草稿 DOCX').props.onClick();}); storage='synthetic-other';
    await act(async()=>{gate.resolve();await pending;}); assert.equal(downloads.length,0);
  });
  test(`${template}: navigation away suppresses late draft`, async () => {
    await mount(); await click(label); await check(); const gate=deferred(), original=adapter;
    adapter=async c=>{if(c.method==='post')await gate.promise;return original(c);};
    let pending; act(()=>{pending=button('确认并下载草稿 DOCX').props.onClick();}); await move('/');
    await act(async()=>{gate.resolve();await pending;}); assert.equal(downloads.length,0);
  });
  test(`${template}: failed draft can retry without a case write`, async () => {
    await mount(); await click(label); const original=adapter;
    adapter=c=>{if(c.url==='/api/clinical-docs/render')throw {response:{data:new Blob([JSON.stringify({detail:'Case not found'})],{type:'application/json'})}};return original(c);};
    await confirm(); assert.equal(downloads.length,0); assert.equal(button('重新读取草稿').props.disabled,false);
    assert.match(text(),/Case not found/); adapter=original; await click('重新读取草稿'); await confirm();
    assert.equal(downloads.length,1); assert.equal(exports().length,2);
    assert(requests.every(c=>c.method==='get'||['/api/clinical-docs/render','/api/clinical-docs/render-preview'].includes(c.url)));
  });
}

test('review shows literal saved text and blocks unchecked confirmation',async()=>{
 await mount();await click('导出门诊病历草稿 DOCX');
 assert.match(text(),/预览原文/);assert.match(text(),/未填写/);assert.match(text(),/未签署/);
 assert.equal(button('确认并下载草稿 DOCX').props.disabled,true);
 await click('确认并下载草稿 DOCX');assert.equal(exports().length,0);assert.equal(previews().length,1);
 assert(!renderer.root.findAll(n=>n.props.dangerouslySetInnerHTML).length);
});
test('same-tick double confirm exports one reviewed document',async()=>{
 await mount();await click('导出门诊病历草稿 DOCX');await check();
 const submit=button('确认并下载草稿 DOCX').props.onClick;
 await act(async()=>{await Promise.all([submit(),submit()]);});
 assert.equal(exports().length,1);assert.equal(downloads.length,1);
 assert.equal(button('确认并下载草稿 DOCX'),undefined);
});
test('reload discards both checked state and previous content until complete',async()=>{
 await mount();await click('导出门诊病历草稿 DOCX');await check();
 const gate=deferred(),original=adapter;adapter=c=>c.url.endsWith('render-preview')?gate.promise:original(c);
 let pending;act(()=>{pending=button('重新读取草稿').props.onClick();});
 assert.doesNotMatch(text(),/预览原文/);assert.equal(button('确认并下载草稿 DOCX'),undefined);
 await act(async()=>{gate.resolve(previewResponse(previews().at(-1)));await pending;});
 assert.equal(button('确认并下载草稿 DOCX').props.disabled,true);assert.equal(exports().length,0);
});
test('conflict invalidates confirmation and requires a fresh review',async()=>{
 await mount();await click('导出门诊病历草稿 DOCX');const original=adapter;
 adapter=c=>{if(c.url.endsWith('/render'))throw {response:{status:409,data:new Blob([JSON.stringify({detail:'changed'})],{type:'application/json'})}};return original(c);};
 await confirm();assert.match(text(),/原确认已失效/);assert.equal(downloads.length,0);assert.equal(button('确认并下载草稿 DOCX'),undefined);
 adapter=original;await click('重新读取草稿');assert.equal(button('确认并下载草稿 DOCX').props.disabled,true);await confirm();
 assert.equal(downloads.length,1);assert.equal(exports().length,2);assert.equal(previews().length,2);
});
test('closed review discards an outstanding download',async()=>{
 await mount();await click('导出门诊病历草稿 DOCX');await check();const gate=deferred(),original=adapter;
 adapter=async c=>{if(c.url.endsWith('/render'))await gate.promise;return original(c);};
 let pending;act(()=>{pending=button('确认并下载草稿 DOCX').props.onClick();});await click('关闭草稿核对');
 await act(async()=>{gate.resolve();await pending;});assert.equal(downloads.length,0);assert.doesNotMatch(text(),/已生成/);
});
test('closed slow preview cannot replace another template preview',async()=>{
 await mount();const gate=deferred(),original=adapter;
 adapter=c=>c.url.endsWith('render-preview')&&JSON.parse(c.data).template_id==='outpatient_record_zh'?gate.promise:original(c);
 await click('导出门诊病历草稿 DOCX');const old=previews()[0];await click('关闭草稿核对');await click('导出宠主说明草稿 DOCX');
 await act(async()=>gate.resolve({...previewResponse(old),data:{...previewResponse(old).data,context:{...previewResponse(old).data.context,'visit.history':'过期预览'}}}));
 assert.doesNotMatch(text(),/过期预览/);await confirm();assert.equal(JSON.parse(exports()[0].data).template_id,'owner_visit_summary_zh');
});
for(const transition of ['case','account','unmount'])test(`late preview after ${transition} is discarded`,async()=>{
 await mount();const gate=deferred(),original=adapter;adapter=c=>c.url.endsWith('render-preview')?gate.promise:original(c);
 await click('导出门诊病历草稿 DOCX');const request=previews()[0];
 if(transition==='case')await move('/cases/2');else if(transition==='unmount')await move('/');else{storage='synthetic-other';await act(async()=>listeners.storage({key:'token'}));}
 await act(async()=>gate.resolve(previewResponse(request)));
 assert.doesNotMatch(text(),/预览原文/);assert.equal(button('确认并下载草稿 DOCX'),undefined);assert.equal(downloads.length,0);
});
for(const malformed of ['old-server','case','template','field','missing-required','writes'])test(`invalid ${malformed} preview cannot enable confirmation`,async()=>{
 await mount();const original=adapter;adapter=c=>{
  if(!c.url.endsWith('render-preview'))return original(c);
  const r=previewResponse(c);
  if(malformed==='old-server')delete r.data.content_snapshot;
  if(malformed==='case')r.data.case_id=2;
  if(malformed==='template')r.data.template_id='other';
  if(malformed==='field')delete r.data.context['visit.history'];
  if(malformed==='missing-required')r.data.missing_required_keys=['visit.history'];
  if(malformed==='writes')r.data.writes_database=true;
  return r;
 };
 await click('导出门诊病历草稿 DOCX');assert.match(text(),/暂不能确认下载/);assert.equal(button('确认并下载草稿 DOCX'),undefined);assert.equal(downloads.length,0);
});
test('preview failure permits deliberate read retry without export',async()=>{
 await mount();const original=adapter;adapter=c=>c.url.endsWith('render-preview')?Promise.reject(Error('offline-preview')):original(c);
 await click('导出门诊病历草稿 DOCX');assert.match(text(),/offline-preview/);adapter=original;await click('重新读取草稿');
 assert.equal(previews().length,2);assert.equal(exports().length,0);await confirm();assert.equal(downloads.length,1);
});
test('rolled-back server or mismatched render snapshot is refused before download',async()=>{
 await mount();const original=adapter;
 for(const value of [undefined,'b'.repeat(64)]){
  await click('导出门诊病历草稿 DOCX');
  adapter=c=>c.url.endsWith('/render')?{...docResponse(c),headers:{'x-pmai-content-snapshot':value}}:original(c);
  await confirm();assert.match(text(),/服务未确认/);assert.equal(downloads.length,0);await click('关闭草稿核对');
 }
});
test('changing credentials before confirmation cannot dispatch a new account request',async()=>{
 await mount();await click('导出门诊病历草稿 DOCX');await check();storage='synthetic-other';await click('确认并下载草稿 DOCX');
 assert.equal(exports().length,0);assert.equal(downloads.length,0);
});
