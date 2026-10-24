import React from 'react';
import TestRenderer, {act} from 'react-test-renderer';
import {test,beforeEach,afterEach} from 'node:test';
import assert from 'node:assert/strict';
import CaseLabRangeReview from '../src/components/CaseLabRangeReview';
import {validateRangeReview} from '../src/labRangeReview';
import api from '../src/api';
import fixture from '../../tests/fixtures/clinical_lab_range_review_cw_b11_cases.json';
let renderer,token,adapter,requests,props,listeners,navigations;
const payload=id=>({...structuredClone(fixture.review),case_id:id});
const deferred=()=>{let resolve,reject;const promise=new Promise((r,j)=>{resolve=r;reject=j;});return{promise,resolve,reject};};
const text=()=>JSON.stringify(renderer.toJSON());
const button=label=>renderer.root.findAllByType('button').find(n=>n.children.join('')===label);
const click=async label=>act(async()=>{assert(button(label),label);await button(label).props.onClick();});
const tree=()=> <CaseLabRangeReview {...props}/>;
const update=async change=>act(async()=>{props={...props,...change};renderer.update(tree());});
const emit=async(name,event={})=>act(async()=>{await Promise.all([...(listeners[name]||[])].map(fn=>fn(event)));});
beforeEach(()=>{
 token='synthetic-owner';requests=[];listeners={};navigations=[];
 global.localStorage={getItem:()=>token,removeItem:()=>{token='';},setItem(){throw Error('No saved snapshot');}};
 global.sessionStorage={setItem(){throw Error('No saved snapshot');}};global.alert=()=>{};
 global.window={addEventListener:(k,f)=>(listeners[k]??=new Set()).add(f),removeEventListener:(k,f)=>listeners[k]?.delete(f)};
 props={caseId:1,requestToken:token,onInspect:target=>navigations.push(target)};
 adapter=async c=>({config:c,status:200,data:payload(Number(c.url.split('/')[3]))});
 api.defaults.adapter=async c=>{requests.push(c);return adapter(c);};
});
afterEach(()=>{if(renderer)act(()=>renderer.unmount());renderer=null;});
async function mount(){await act(async()=>{renderer=TestRenderer.create(tree());});}

test('all raw strings, exact decimals and provenance render without clinical inference or requests beyond GET',async()=>{
 await mount();for(const value of ['0.0100','2.001e-8','2026-10-07T09:30:00+08:00','边界','不代表健康或排除疾病',fixture.review.snapshot,fixture.review.reports[0].source.sha256])assert(text().includes(value),value);
 const cells=renderer.root.findAllByType('td').flatMap(n=>n.children);
 for(const item of fixture.data.items){assert(cells.some(v=>typeof v==='string'&&v.includes(item.name)));if(item.value)assert(cells.includes(item.value));if(item.flag)assert(cells.includes(item.flag));}
 assert(!renderer.root.findAll(n=>n.props.dangerouslySetInnerHTML).length);
 assert.equal(requests.length,1);assert(requests.every(c=>c.method==='get'&&c.url.endsWith('/lab-range-review')));
});
test('filters preserve source order, exact numbers and counts without writing or downloading',async()=>{
 await mount();const select=renderer.root.findByProps({'aria-label':'检验区间项目筛选'});
 for(const [filter,count] of [['out',fixture.review.counts.out_of_range],['unable',fixture.review.counts.unable],['all',fixture.review.counts.items]]){
  await act(async()=>select.props.onChange({target:{value:filter}}));
  assert.equal(renderer.root.findByType('tbody').findAllByType('tr').length,count);
 }
 await click('回看检验记录 #1 版本 1');assert.deepEqual(navigations,[{caseId:1,id:1,version:1,token:'c'.repeat(64)}]);assert.equal(requests.length,1);
});
test('malformed contract, counts, ambiguous result and inconsistent flags fail closed',()=>{
 for(const change of [{case_id:2},{schema:'future'},{rules:'future'},{writes_database:true},{includes_unsaved_drafts:true},{read_at:'bad'},{snapshot:''},{reports:[]}])assert.throws(()=>validateRangeReview({...payload(1),...change},1));
 for(const mutate of [d=>d.reports.push(d.reports[0]),d=>d.reports[0].token='',d=>d.reports[0].items[0].comparison.state='normal',d=>d.reports[0].items[0].comparison.flag_state='uninterpreted',d=>d.reports[0].items[0].value=0,d=>d.reports[0].items[0].reference_unit='mg/dL',d=>d.reports[0].state='superseded']){const d=payload(1);mutate(d);assert.throws(()=>validateRangeReview(d,1));}
});
test('refresh immediately removes old snapshot, errors are distinct from empty success',async()=>{
 await mount();const gate=deferred();adapter=()=>gate.promise;let reading;
 await act(async()=>{reading=button('刷新检验区间核对').props.onClick();});assert.doesNotMatch(text(),/CW-B11 合成病例/);
 await act(async()=>{gate.reject({response:{status:503}});await reading;});assert.match(text(),/读取失败/);assert.doesNotMatch(text(),/区间报告/);
 for(const status of [401,404,409]){adapter=()=>Promise.reject({response:{status}});await click('刷新检验区间核对');assert.doesNotMatch(text(),/没有当前可比较/);}
});
for(const kind of ['revision','focus','case'])test(`late response discarded after ${kind}`,async()=>{
 const gate=deferred();let reads=0;
 adapter=c=>++reads===1?gate.promise:Promise.resolve({data:{...payload(kind==='case'?2:1),identity:{...payload(1).identity,patient_name:'新病例快照'}}});
 await mount();if(kind==='revision')await update({sourceRevision:1});else if(kind==='case')await update({caseId:2});else await emit('focus');
 await act(async()=>gate.resolve({data:payload(1)}));assert.match(text(),/新病例快照/);assert.doesNotMatch(text(),/CW-B11 合成病例/);
});
test('account storage change clears visible and pending snapshots, anonymous read sends no request',async()=>{
 await mount();token='other';await emit('storage',{key:'token'});assert.doesNotMatch(text(),/CW-B11 合成病例/);assert.match(text(),/登录已变化/);assert.equal(requests.length,1);
 token='';await update({requestToken:''});assert.equal(requests.length,1);
});
for(const failed of [false,true])test(`confirm ${failed?'failure':'success'} invalidates at start and refreshes even without editor callback`,async()=>{
 await mount();const gate=deferred(),normal=adapter;
 adapter=c=>c.method==='post'?gate.promise.then(()=>({config:c,data:{state:'committed'}}),()=>Promise.reject({config:c,response:{status:409}})):normal(c);
 let operation;await act(async()=>{operation=api.post('/api/cases/1/manual-lab/confirm',{}).catch(()=>{});});
 assert.doesNotMatch(text(),/CW-B11 合成病例/);assert.match(text(),/资料操作已开始/);
 await act(async()=>{failed?gate.reject():gate.resolve();await operation;});assert.match(text(),/CW-B11 合成病例/);assert.equal(requests.filter(c=>c.url.endsWith('/lab-range-review')).length,2);
});
test('excluded versions remain separate and navigable, never contribute item counts',async()=>{
 const data=payload(1),row={...data.reports[0],id:2,version:2,state:'withdrawn'};delete row.items;data.excluded=[row];
 adapter=async c=>({config:c,data});await mount();assert.match(text(),/已撤销/);assert.equal(renderer.root.findByType('tbody').findAllByType('tr').length,fixture.data.items.length);
 await click('回看检验记录 #2 版本 2');assert.equal(navigations[0].id,2);
});
