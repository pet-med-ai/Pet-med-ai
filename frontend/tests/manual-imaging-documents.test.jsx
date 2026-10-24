import React from 'react';
import TestRenderer,{act} from 'react-test-renderer';
import {MemoryRouter} from 'react-router-dom';
import {test,beforeEach,afterEach} from 'node:test';
import assert from 'node:assert/strict';
import ClinicalDocReview from '../src/components/ClinicalDocReview';
import api from '../src/api';
import data from '../../tests/fixtures/manual_imaging_cw_b9_cases.json';

let renderer,props,token,requests,adapter,rows,listeners,downloads,inspect;
const hash='a'.repeat(64);
const report=id=>({id,root_id:id,version:1,state:'confirmed',reviewed_by:'1',reviewed_at:'2026-10-07T00:00:00Z',source:{name:'合成原件.pdf',sha256:hash},data:structuredClone(data)});
const button=s=>renderer.root.findAllByType('button').find(n=>n.children.join('')===s);
const click=async s=>act(async()=>{assert(button(s),s);await button(s).props.onClick();});
const text=()=>JSON.stringify(renderer.toJSON());
const select=async (id,checked=true)=>act(async()=>renderer.root.findByProps({'aria-label':'纳入影像 '+rows.find(r=>r.id===id).data.title}).props.onChange({target:{checked}}));
const confirm=async()=>act(async()=>renderer.root.findAllByType('input').find(n=>!n.props['aria-label']).props.onChange({target:{checked:true}}));
const render=()=> <MemoryRouter><ClinicalDocReview {...props}/></MemoryRouter>;
const deferred=()=>{let resolve;const promise=new Promise(r=>resolve=r);return{promise,resolve};};
const reply=(c,data)=>({config:c,status:200,data});
function preview(c){const b=JSON.parse(c.data),context={};for(const k of ['case_id','pet_name','owner_name','coat_color','species','age','sex','weight','complaint','history','exam','assessment','plan','notes','follow_up'])context['visit.'+k]='未填写';context['visit.case_id']=String(b.case_id);context['export.account_id']='1';return reply(c,{...b,context,content_snapshot:hash,missing_required_keys:[],writes_database:false,...(b.manual_imaging_report_ids?.length?{manual_imaging_reports:rows.filter(r=>b.manual_imaging_report_ids.includes(r.id))}:{})});}
beforeEach(async()=>{
 token='synthetic';requests=[];rows=[report(1)];listeners={};downloads=[];inspect=0;
 global.localStorage={getItem:()=>token,setItem(){throw Error('No persistence');}};
 global.window={addEventListener:(k,f)=>listeners[k]=f,removeEventListener:k=>delete listeners[k]};
 props={caseId:1,templateId:'outpatient_record_zh',label:'合成文书',requestToken:token,onClose(){},onInspectImaging:()=>inspect++,onDownload:async(s,current,_labs,ids)=>{downloads.push({s,current:current(),ids});return{ok:true};}};
 adapter=async c=>c.method==='get'?reply(c,{case_id:props.caseId,reports:rows,writes_database:false}):preview(c);
 api.defaults.adapter=async c=>{requests.push(c);return adapter(c);};
 await act(async()=>renderer=TestRenderer.create(render()));
});
afterEach(()=>act(()=>renderer.unmount()));
async function selected(){await click('选择已核对影像报告');await select(1);await click('重新读取草稿');}
test('default preview does not request or include reports',()=>{assert.equal(requests.length,1);assert.equal(JSON.parse(requests[0].data).manual_imaging_report_ids,undefined);assert.doesNotMatch(text(),/所见原文/);});
test('both templates select whole reports, preserve literals and pass reviewed ids',async()=>{
 for(const templateId of ['outpatient_record_zh','owner_visit_summary_zh']){await act(async()=>{props={...props,templateId};renderer.update(render());});await selected();assert.match(text(),/所见原文/);assert.match(text(),/体位限制/);assert.match(text(),/2026-10-07/);assert(button('确认并下载草稿 DOCX').props.disabled);await confirm();await click('确认并下载草稿 DOCX');assert.deepEqual(downloads.at(-1),{s:hash,current:true,ids:[1]});}
 assert(!renderer.root.findAll(n=>n.props.dangerouslySetInnerHTML).length);
});
test('deselect or refresh immediately invalidates preview and checked state',async()=>{await selected();await confirm();await select(1,false);assert.equal(button('确认并下载草稿 DOCX'),undefined);await click('重新读取草稿');assert(button('确认并下载草稿 DOCX').props.disabled);await confirm();await click('刷新可选影像记录');assert.equal(button('确认并下载草稿 DOCX'),undefined);assert.equal(downloads.length,0);});
test('focus rereads sources and removes reports on failed refresh',async()=>{await selected();await confirm();adapter=()=>Promise.reject(Error('offline'));await act(async()=>listeners.focus());assert.equal(button('确认并下载草稿 DOCX'),undefined);assert.doesNotMatch(text(),/所见原文/);assert.match(text(),/旧确认已失效/);});
for(const scenario of ['case','account','template','selection','focus'])test(`late preview rejected after ${scenario}`,async()=>{
 await click('选择已核对影像报告');await select(1);const gate=deferred(),normal=adapter;adapter=async c=>{if(c.method==='post')await gate.promise;return normal(c);};let pending;
 await act(async()=>{pending=button('重新读取草稿').props.onClick();await new Promise(r=>setTimeout(r,0));});
 if(scenario==='selection')await select(1,false);else if(scenario==='focus')await act(async()=>listeners.focus());else await act(async()=>{if(scenario==='case')props={...props,caseId:2};if(scenario==='template')props={...props,templateId:'owner_visit_summary_zh'};if(scenario==='account'){token='other';props={...props,requestToken:token};}renderer.update(render());});
 await act(async()=>{gate.resolve();await pending;});assert.doesNotMatch(text(),/所见原文/);assert.equal(downloads.length,0);
});
for(const defect of ['missing','source','state','extra','case'])test(`malformed ${defect} response cannot be confirmed`,async()=>{
 await click('选择已核对影像报告');await select(1);const normal=adapter;adapter=async c=>{const r=await normal(c);if(c.method==='post'){if(defect==='missing')delete r.data.manual_imaging_reports;if(defect==='source')r.data.manual_imaging_reports[0].source.sha256='bad';if(defect==='state')r.data.manual_imaging_reports[0].state='withdrawn';if(defect==='extra')r.data.manual_imaging_reports.push(report(99));if(defect==='case')r.data.case_id=99;}return r;};await click('重新读取草稿');assert.equal(button('确认并下载草稿 DOCX'),undefined);assert.match(text(),/完整草稿/);
});
test('limits reject complete reports above 20000 Unicode characters or five reports',async()=>{
 rows=Array.from({length:6},(_,i)=>({...report(i+1),data:{...structuredClone(data),title:'影像'+i,findings:'😀'.repeat(5000),impression:'',limitations:'',note:''}}));
 await click('选择已核对影像报告');for(let id=1;id<=4;id++)await select(id);await select(5);assert.match(text(),/未截断原文/);await click('重新读取草稿');assert.deepEqual(JSON.parse(requests.at(-1).data).manual_imaging_report_ids,[1,2,3,4]);
 rows=rows.map(r=>({...r,data:{...r.data,findings:'短原文'}}));await click('刷新可选影像记录');for(let id=1;id<=5;id++)await select(id);await select(6);assert.match(text(),/未截断原文/);await click('重新读取草稿');assert.deepEqual(JSON.parse(requests.at(-1).data).manual_imaging_report_ids,[1,2,3,4,5]);
});
test('return to existing lab workflow invalidates current confirmation',async()=>{await selected();await confirm();await click('返回影像记录与原件');await click('确认并下载草稿 DOCX');assert.equal(downloads.length,0);assert.equal(inspect,1);});
test('service disabled still permits original draft after opting out',async()=>{const normal=adapter;adapter=c=>c.method==='get'?Promise.reject({response:{data:{detail:'manual_imaging_disabled'}}}):normal(c);await click('选择已核对影像报告');assert.match(text(),/暂未启用/);await click('不纳入影像报告');await click('重新读取草稿');await confirm();await click('确认并下载草稿 DOCX');assert.deepEqual(downloads[0].ids,[]);});

test('source revision clears all selected reports and confirmation',async()=>{await selected();await confirm();await act(async()=>{props={...props,sourceRevision:1};renderer.update(render());});assert.equal(button('确认并下载草稿 DOCX'),undefined);await click('重新读取草稿');assert.equal(JSON.parse(requests.at(-1).data).manual_imaging_report_ids,undefined);});
