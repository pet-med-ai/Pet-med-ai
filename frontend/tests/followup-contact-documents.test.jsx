import React from 'react';
import TestRenderer,{act} from 'react-test-renderer';
import {MemoryRouter} from 'react-router-dom';
import {test,beforeEach,afterEach} from 'node:test';
import assert from 'node:assert/strict';
import ClinicalDocReview from '../src/components/ClinicalDocReview';
import {documentContactSelection,validDocumentContact} from '../src/followupContactDocuments';
import api from '../src/api';
import fixture from '../../tests/fixtures/clinical_followup_contact_documents_cw_b21_cases.json';
let renderer,props,token,requests,adapter,listeners,downloads,listing;
const hash='a'.repeat(64),reply=(c,data)=>({config:c,status:200,data});
const button=s=>renderer.root.findAllByType('button').find(n=>n.children.join('')===s);
const click=async s=>act(async()=>{assert(button(s),s);await button(s).props.onClick();});
const text=()=>JSON.stringify(renderer.toJSON());
const row=()=>listing.records.find(r=>r.state==='recorded');
const payload=()=>({...documentContactSelection(listing,row()).expected,audit_token:hash});
const confirm=async()=>act(async()=>{const b=renderer.root.findAllByType('input').find(n=>n.props.type==='checkbox'&&!n.props['aria-label']);assert(b&&!b.props.disabled);b.props.onChange({target:{checked:true}});});
const fire=async(name,e={})=>act(async()=>{for(const fn of [...(listeners[name]||[])])fn(e);});
const deferred=()=>{let resolve,reject;const promise=new Promise((r,j)=>{resolve=r;reject=j;});return{promise,resolve,reject};};
const view=()=> <MemoryRouter><ClinicalDocReview {...props}/></MemoryRouter>;
function preview(c){const b=JSON.parse(c.data),context={};for(const k of ['case_id','pet_name','owner_name','coat_color','species','age','sex','weight','complaint','history','exam','assessment','plan','notes','follow_up'])context['visit.'+k]='未填写';context['visit.case_id']=String(b.case_id);context['export.account_id']='1';return reply(c,{...b,context,content_snapshot:hash,missing_required_keys:[],writes_database:false,...(b.manual_followup_contact?{manual_followup_contact:payload()}:{})});}
beforeEach(async()=>{
 listing=structuredClone(fixture.contact_listing);token='synthetic';requests=[];listeners={};downloads=[];
 global.localStorage={getItem:()=>token,setItem(){throw Error('No persistence');}};global.sessionStorage={setItem(){throw Error('No persistence');}};
 global.window={addEventListener:(k,f)=>(listeners[k]??=new Set()).add(f),removeEventListener:(k,f)=>listeners[k]?.delete(f)};
 global.document={hidden:false,addEventListener:window.addEventListener,removeEventListener:window.removeEventListener};
 props={caseId:1,templateId:'outpatient_record_zh',label:'门诊病历',requestToken:token,onClose(){},onDownload:async(snapshot,current,labs,images,comparison,signal,plan,contact)=>{downloads.push({snapshot,current:current(),labs,images,comparison,signal,plan,contact});return{ok:true};}};
 adapter=async c=>c.url.endsWith('/followup-contacts')?reply(c,structuredClone(listing)):preview(c);
 api.defaults.adapter=async c=>{requests.push(c);return adapter(c);};await act(async()=>renderer=TestRenderer.create(view()));
});
afterEach(()=>act(()=>renderer.unmount()));
async function select(){await click('选择人工随访记录附节');const b=renderer.root.findAllByType('button').find(n=>n.children.join('')==='将此随访纳入本次文书'&&!n.props.disabled);assert(b);await act(async()=>b.props.onClick());}
async function selected(){await select();await click('重新读取草稿');}
test('explicit current contact selection, original history, full review and single export',async()=>{
 assert.equal(requests.length,1);assert.equal(JSON.parse(requests[0].data).manual_followup_contact,undefined);
 await selected();assert(button('确认并下载草稿 DOCX').props.disabled);for(const value of [row().data.note,row().data.next_action,row().source.data.purpose,row().token])assert(text().includes(JSON.stringify(value).slice(1,-1)));
 await confirm();await act(async()=>Promise.all([button('确认并下载草稿 DOCX').props.onClick(),button('确认并下载草稿 DOCX').props.onClick()]));
 assert.equal(downloads.length,1);assert.deepEqual(downloads[0].contact,documentContactSelection(listing,row()).request);assert.equal(downloads[0].plan,undefined);
});
test('strict full response rejects altered source, case, record, audit and extra fields',()=>{
 const choice=documentContactSelection(listing,row());assert(validDocumentContact(payload(),choice,1));assert(!validDocumentContact(payload(),null,1));assert(validDocumentContact(undefined,null,1));
 for(const key of ['case','record','selection','timezone','schema','audit_token']){const p=payload();p[key]={};assert(!validDocumentContact(p,choice,1));}
 assert(!validDocumentContact({...payload(),extra:true},choice,1));assert(!validDocumentContact(payload(),choice,2));
 assert.throws(()=>documentContactSelection(listing,{...row(),state:'withdrawn'}));
});
for(const action of ['clear','refresh','focus','blur','hidden','revision','template','account'])test(`invalidates full confirmation on ${action}`,async()=>{
 await selected();await confirm();
 if(action==='clear')await click('移除本次人工随访附节');else if(action==='refresh')await click('刷新可选人工随访');else if(['focus','blur'].includes(action))await fire(action);else if(action==='hidden'){document.hidden=true;await fire('visibilitychange');}else await act(async()=>{if(action==='revision')props={...props,sourceRevision:1};if(action==='template')props={...props,templateId:'owner_visit_summary_zh'};if(action==='account'){token='other';props={...props,requestToken:token};}renderer.update(view());});
 assert(!button('确认并下载草稿 DOCX')||button('确认并下载草稿 DOCX').props.disabled);assert.doesNotMatch(text(),/文书人工随访附节/);assert.equal(downloads.length,0);
});
for(const action of ['followup-contacts','followup-plan','attachments','manual-lab','manual-imaging','body'])for(const failed of [false,true])test(`${action} ${failed?'lost reply':'success'} resets at request start and independently rereads with closed selector`,async()=>{
 await selected();await click('收起人工随访选择');await confirm();const gate=deferred(),normal=adapter;let pending;
 const url=action==='body'?'/api/cases/1':`/api/cases/1/${action}/confirm`;
 adapter=c=>c.url===url?gate.promise.then(()=>reply(c,{}),()=>Promise.reject({config:c,response:{status:503}})):normal(c);
 const reads=requests.filter(c=>c.url.endsWith('/followup-contacts')).length;
 await act(async()=>{pending=api.request({method:action==='body'?'put':'post',url,data:{}}).catch(()=>{});});assert(!button('确认并下载草稿 DOCX'));
 await act(async()=>{failed?gate.reject():gate.resolve();await pending;});assert(requests.filter(c=>c.url.endsWith('/followup-contacts')).length>reads);assert.equal(downloads.length,0);
});
for(const action of ['clear','focus','case','account'])test(`late complete preview ignored after ${action}`,async()=>{
 await select();const gate=deferred(),normal=adapter;let pending;adapter=async c=>{if(c.url.endsWith('render-preview'))await gate.promise;return normal(c);};
 await act(async()=>{pending=button('重新读取草稿').props.onClick();});
 if(action==='clear')await click('移除本次人工随访附节');else if(action==='focus')await fire('focus');else await act(async()=>{if(action==='case')props={...props,caseId:2};else{token='other';props={...props,requestToken:token};}renderer.update(view());});
 await act(async()=>{gate.resolve();await pending;});assert.doesNotMatch(text(),/文书人工随访附节/);assert.equal(downloads.length,0);
});
test('unknown list and forged original stay failures, not empty or confirmable',async()=>{
 const normal=adapter;adapter=async c=>c.url.endsWith('/followup-contacts')?reply(c,{records:[]}):normal(c);
 await click('选择人工随访记录附节');assert.match(text(),/不完整/);assert.doesNotMatch(text(),/尚无保存记录/);assert(!button('将此随访纳入本次文书'));
 adapter=normal;await click('刷新可选人工随访');const b=renderer.root.findAllByType('button').find(n=>n.children.join('')==='将此随访纳入本次文书'&&!n.props.disabled);await act(async()=>b.props.onClick());
 adapter=async c=>{const r=await normal(c);if(c.url.endsWith('render-preview'))r.data.manual_followup_contact.record.data.note='forged';return r;};
 await click('重新读取草稿');assert(!button('确认并下载草稿 DOCX'));assert.match(text(),/完整草稿/);
});
test('owner template never offers contact selection',async()=>{props={...props,templateId:'owner_visit_summary_zh'};await act(async()=>renderer.update(view()));assert(!button('选择人工随访记录附节'));assert(!requests.some(c=>c.url.endsWith('/followup-contacts')));});
