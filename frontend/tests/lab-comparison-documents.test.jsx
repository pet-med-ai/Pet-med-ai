import React from 'react';
import TestRenderer,{act} from 'react-test-renderer';
import {MemoryRouter} from 'react-router-dom';
import {test,beforeEach,afterEach} from 'node:test';
import assert from 'node:assert/strict';
import ClinicalDocReview from '../src/components/ClinicalDocReview';
import {documentSelection,validDocumentComparison} from '../src/labComparisonDocuments';
import {itemSelection} from '../src/labComparison';
import api from '../src/api';
import fixture from '../../tests/fixtures/clinical_lab_comparison_cw_b12_cases.json';
let renderer,props,token,requests,adapter,listeners,downloads;
const hash='a'.repeat(64),saved=()=>structuredClone(fixture.review);
const result=b=>({...b,schema:fixture.review.schema,rules:fixture.review.rules,case_id:1,read_at:fixture.review.read_at,read_only:true,writes_database:false,includes_unsaved_drafts:false,can_calculate:true,reasons:[],reference_changed:true,delta:{value:fixture.expected_deltas[b.a.index-1],state:b.a.index===1?'same':b.a.index===2?'decrease':'increase',unit:'mmol/L'}});
const button=s=>renderer.root.findAllByType('button').find(n=>n.children.join('')===s);
const click=async s=>act(async()=>{assert(button(s),s);await button(s).props.onClick();});
const text=()=>JSON.stringify(renderer.toJSON());
const select=async(label,value)=>act(async()=>renderer.root.findByProps({'aria-label':label}).props.onChange({target:{value}}));
const whole=()=>renderer.root.findAllByType('input').find(n=>n.props.type==='checkbox'&&!n.props['aria-label']);
const confirm=async()=>act(async()=>whole().props.onChange({target:{checked:true}}));
const emit=async(name,e={})=>act(async()=>{await Promise.all([...(listeners[name]||[])].map(fn=>fn(e)));});
const deferred=()=>{let resolve,reject;const promise=new Promise((r,j)=>{resolve=r;reject=j;});return{promise,resolve,reject};};
const view=()=> <MemoryRouter><ClinicalDocReview {...props}/></MemoryRouter>;
const reply=(c,data)=>({config:c,status:200,data});
function preview(c){const b=JSON.parse(c.data),context={};for(const k of ['case_id','pet_name','owner_name','coat_color','species','age','sex','weight','complaint','history','exam','assessment','plan','notes','follow_up'])context['visit.'+k]='未填写';context['visit.case_id']=String(b.case_id);context['export.account_id']='1';return reply(c,{...b,context,content_snapshot:hash,missing_required_keys:[],writes_database:false,...(b.manual_lab_comparison?{manual_lab_comparison:documentSelection(saved(),b.manual_lab_comparison,result(b.manual_lab_comparison)).expected}:{})});}
beforeEach(async()=>{
 token='synthetic';requests=[];listeners={};downloads=[];
 global.localStorage={getItem:()=>token,setItem(){throw Error('No persistence');}};global.sessionStorage={setItem(){throw Error('No persistence');}};
 global.window={addEventListener:(k,f)=>(listeners[k]??=new Set()).add(f),removeEventListener:(k,f)=>listeners[k]?.delete(f)};
 props={caseId:1,templateId:'outpatient_record_zh',label:'合成门诊病历',requestToken:token,onClose(){},onDownload:async(snapshot,current,labs,images,choice,signal)=>{downloads.push({snapshot,current:current(),labs,images,choice,signal});return{ok:true};}};
 adapter=async c=>c.url.endsWith('/lab-comparison')?reply(c,saved()):c.url.endsWith('/lab-comparison/preview')?reply(c,result(JSON.parse(c.data))):preview(c);
 api.defaults.adapter=async c=>{requests.push(c);return adapter(c);};
 await act(async()=>renderer=TestRenderer.create(view()));
});
afterEach(()=>act(()=>renderer.unmount()));
async function choose(){await click('选择检验前后对照附节');for(const [l,v]of[['对照报告 A','1'],['对照报告 B','2'],['对照项目 A','4'],['对照项目 B','4']])await select(l,v);await act(async()=>renderer.root.findByProps({'aria-label':'确认方法与采样条件可比'}).props.onChange({target:{checked:true}}));await click('核对条件并预览数值差');}
async function selected(){await choose();await click('纳入本次文书核对');await click('重新读取草稿');}
test('default off, explicit inclusion and independent whole-document check with exact strings',async()=>{
 assert.equal(requests.length,1);assert.equal(JSON.parse(requests[0].data).manual_lab_comparison,undefined);
 await choose();assert.equal(button('确认并下载草稿 DOCX'),undefined);assert.equal(downloads.length,0);
 await click('纳入本次文书核对');assert.equal(button('确认并下载草稿 DOCX'),undefined);await click('重新读取草稿');
 assert(button('确认并下载草稿 DOCX').props.disabled);for(const s of [fixture.expected_deltas[3],fixture.reports[0].items[3].value,fixture.review.reports[0].source.sha256,'参考范围不同'])assert(text().includes(s));
 await confirm();await act(async()=>{await Promise.all([button('确认并下载草稿 DOCX').props.onClick(),button('确认并下载草稿 DOCX').props.onClick()]);});
 assert.equal(downloads.length,1);assert.equal(downloads[0].choice.doctor_confirmed,true);assert.deepEqual(downloads[0].labs,[]);assert.deepEqual(downloads[0].images,[]);
});
test('payload binds raw, provenance, arithmetic and selectors without coercion',()=>{
 const d=saved(),r={snapshot:d.snapshot,a:itemSelection(d.reports[0],d.reports[0].items[3]),b:itemSelection(d.reports[1],d.reports[1].items[3]),doctor_confirmed:true},choice=documentSelection(d,r,result(r));
 assert(validDocumentComparison(choice.expected,choice,1));assert(!validDocumentComparison(choice.expected,null,1));assert(validDocumentComparison(undefined,null,1));
 for(const field of ['value','source','result','selection','rules']){const p=structuredClone(choice.expected);if(field==='value')p.a.item.value='1';else if(field==='source')p.b.source.sha256='f'.repeat(64);else p[field]={};assert(!validDocumentComparison(p,choice,1));}
 assert.throws(()=>documentSelection(d,{...r,doctor_confirmed:false},result(r)));
});
for(const action of ['swap','remove','refresh','close','focus','revision','template','account'])test(`selected whole preview cleared by ${action}`,async()=>{
 await selected();await confirm();
 if(action==='swap')await click('交换 A 与 B');else if(action==='remove')await click('移除本次对照附节');else if(action==='refresh')await click('刷新检验前后对照');else if(action==='close')await click('关闭对照选择并移除');else if(action==='focus')await emit('focus');else await act(async()=>{if(action==='revision')props={...props,sourceRevision:1};if(action==='template')props={...props,templateId:'owner_visit_summary_zh'};if(action==='account'){token='other';props={...props,requestToken:token};}renderer.update(view());});
 assert.equal(downloads.length,0);assert(!button('确认并下载草稿 DOCX')||button('确认并下载草稿 DOCX').props.disabled);assert.doesNotMatch(text(),/文书检验前后对照附节/);
});
for(const kind of ['attachments','manual-lab','manual-imaging'])for(const failed of [false,true])test(`${kind} ${failed?'failed':'successful'} confirm invalidates at start even with selector closed`,async()=>{
 await selected();await click('关闭对照选择并移除');await click('重新读取草稿');await confirm();
 const gate=deferred(),normal=adapter;let operation;
 adapter=c=>c.url.endsWith('/confirm')?gate.promise.then(()=>reply(c,{}),()=>Promise.reject({config:c,response:{status:409}})):normal(c);
 const reads=requests.filter(c=>c.url.endsWith('/lab-comparison')).length;
 await act(async()=>{operation=api.post(`/api/cases/1/${kind}/confirm`,{}).catch(()=>{});});assert.equal(button('确认并下载草稿 DOCX'),undefined);
 await act(async()=>{failed?gate.reject():gate.resolve();await operation;});assert(requests.filter(c=>c.url.endsWith('/lab-comparison')).length>reads);
});
for(const action of ['selection','focus','case','account'])test(`late full preview cannot restore selection after ${action}`,async()=>{
 await choose();await click('纳入本次文书核对');const gate=deferred(),normal=adapter;let pending;
 adapter=async c=>{if(c.url.endsWith('render-preview'))await gate.promise;return normal(c);};await act(async()=>{pending=button('重新读取草稿').props.onClick();});
 if(action==='selection')await select('对照项目 A','1');else if(action==='focus')await emit('focus');else await act(async()=>{if(action==='case')props={...props,caseId:2};else{token='other';props={...props,requestToken:token};}renderer.update(view());});
 await act(async()=>{gate.resolve();await pending;});assert.doesNotMatch(text(),/文书检验前后对照附节/);assert.equal(downloads.length,0);
});
test('late download loses current predicate and aborts on focus',async()=>{
 await selected();await confirm();const gate=deferred();let current,signal,pending;props={...props,onDownload:async(_s,c,_l,_i,_p,sg)=>{current=c;signal=sg;await gate.promise;return{ok:true};}};await act(async()=>renderer.update(view()));
 await act(async()=>{pending=button('确认并下载草稿 DOCX').props.onClick();});await emit('focus');assert.equal(current(),false);assert.equal(signal.aborted,true);await act(async()=>{gate.resolve();await pending;});assert.doesNotMatch(text(),/已生成本次核对/);
});
test('same-tick comparison preview is one request; unexpected document section fails closed',async()=>{
 await choose();await act(async()=>{await Promise.all([button('核对条件并预览数值差').props.onClick(),button('核对条件并预览数值差').props.onClick()]);});assert.equal(requests.filter(c=>c.url.endsWith('/lab-comparison/preview')).length,2);
 await click('纳入本次文书核对');const normal=adapter;adapter=async c=>{const r=await normal(c);if(c.url.endsWith('render-preview'))r.data.manual_lab_comparison.a.item.value='tampered';return r;};await click('重新读取草稿');assert.equal(button('确认并下载草稿 DOCX'),undefined);assert.match(text(),/完整草稿/);
});
