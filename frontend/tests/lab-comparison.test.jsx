import React from 'react';
import TestRenderer, {act} from 'react-test-renderer';
import {test,beforeEach,afterEach} from 'node:test';
import assert from 'node:assert/strict';
import CaseLabComparison from '../src/components/CaseLabComparison';
import {itemSelection,validateComparison,validatePreview} from '../src/labComparison';
import api from '../src/api';
import fixture from '../../tests/fixtures/clinical_lab_comparison_cw_b12_cases.json';
let renderer,token,adapter,requests,props,listeners,navigations;
const payload=id=>({...structuredClone(fixture.review),case_id:id});
const deferred=()=>{let resolve,reject;const promise=new Promise((r,j)=>{resolve=r;reject=j;});return{promise,resolve,reject};};
const text=()=>JSON.stringify(renderer.toJSON());
const button=label=>renderer.root.findAllByType('button').find(n=>n.children.join('')===label);
const click=async label=>act(async()=>{assert(button(label),label);await button(label).props.onClick();});
const update=async change=>act(async()=>{props={...props,...change};renderer.update(<CaseLabComparison {...props}/>);});
const emit=async(name,event={})=>act(async()=>{await Promise.all([...(listeners[name]||[])].map(fn=>fn(event)));});
const select=async(label,value)=>act(async()=>renderer.root.findByProps({'aria-label':label}).props.onChange({target:{value}}));
const confirm=async()=>act(async()=>renderer.root.findByProps({'aria-label':'确认方法与采样条件可比'}).props.onChange({target:{checked:true}}));
const req=(data,index=3)=>({snapshot:data.snapshot,a:itemSelection(data.reports[0],data.reports[0].items[index]),b:itemSelection(data.reports[1],data.reports[1].items[index]),doctor_confirmed:true});
const result=(body,data)=>({...body,schema:data.schema,rules:data.rules,case_id:data.case_id,read_at:data.read_at,read_only:true,writes_database:false,includes_unsaved_drafts:false,can_calculate:body.doctor_confirmed,reasons:body.doctor_confirmed?[]:['doctor_confirmation_required'],reference_changed:true,delta:body.doctor_confirmed?{value:fixture.expected_deltas[body.a.index-1],state:body.a.index===1?'same':body.a.index===2?'decrease':'increase',unit:'mmol/L'}:null});
beforeEach(()=>{
 token='synthetic-owner';requests=[];listeners={};navigations=[];
 global.localStorage={getItem:()=>token,removeItem:()=>{token='';},setItem(){throw Error('No persisted comparison');}};
 global.sessionStorage={setItem(){throw Error('No persisted comparison');}};global.alert=()=>{};
 global.window={addEventListener:(k,f)=>(listeners[k]??=new Set()).add(f),removeEventListener:(k,f)=>listeners[k]?.delete(f)};
 props={caseId:1,requestToken:token,onInspect:target=>navigations.push(target)};
 adapter=async c=>({config:c,status:200,data:c.method==='post'?result(JSON.parse(c.data),payload(Number(c.url.split('/')[3]))):payload(Number(c.url.split('/')[3]))});
 api.defaults.adapter=async c=>{requests.push(c);return adapter(c);};
});
afterEach(()=>{if(renderer)act(()=>renderer.unmount());renderer=null;});
async function mount(){await act(async()=>{renderer=TestRenderer.create(<CaseLabComparison {...props}/>);});}
async function choose(index='4') {for(const [label,value] of [['对照报告 A','1'],['对照报告 B','2'],['对照项目 A',index],['对照项目 B',index]])await select(label,value);}

test('explicit pair and temporary physician check, exact raw and delta without auto-download',async()=>{
 await mount();assert.equal(requests.length,1);assert.equal(button('核对条件并预览数值差').props.disabled,true);
 assert.equal(renderer.root.findByProps({'aria-label':'对照报告 A'}).props.value,'');
 await choose();await click('核对条件并预览数值差');assert.match(text(),/尚未确认项目/);assert.doesNotMatch(text(),/差值 B−A/);
 await confirm();await click('核对条件并预览数值差');
 for(const s of [fixture.reports[0].items[3].value,fixture.reports[1].items[3].value,fixture.expected_deltas[3],fixture.reports[0].report.collected_at,fixture.review.reports[1].source.sha256,'参考范围不同'])assert(text().includes(s),s);
 assert(!renderer.root.findAll(n=>n.props.dangerouslySetInnerHTML).length);
 assert.deepEqual(JSON.parse(requests.at(-1).data),req(payload(1)));
 await click('回看检验记录 #1 版本 1');assert.deepEqual(navigations,[{caseId:1,id:1,version:1,token:'c'.repeat(64)}]);assert(!requests.some(c=>c.url.includes('/content')||c.url.includes('/render')));
});
test('swap and new selection clear delta and doctor confirmation without choosing replacement items',async()=>{
 await mount();await choose();await confirm();await click('核对条件并预览数值差');
 await click('交换 A 与 B');assert.doesNotMatch(text(),/差值 B−A/);assert.equal(renderer.root.findByProps({'aria-label':'对照报告 A'}).props.value,'2');assert.equal(renderer.root.findByProps({'aria-label':'确认方法与采样条件可比'}).props.checked,false);
 await select('对照报告 A','1');assert.equal(renderer.root.findByProps({'aria-label':'对照项目 A'}).props.value,'');
});
test('all long Unicode text retained and excluded versions never selected',async()=>{
 const data=payload(1),excluded={...data.reports[0],id:3,version:2,state:'withdrawn'};delete excluded.items;data.excluded=[excluded];adapter=async c=>({config:c,data});
 await mount();await choose('9');assert(renderer.root.findAllByType('dd').flatMap(n=>n.children).includes(fixture.reports[0].items[8].value));assert(text().includes(fixture.reports[0].items[8].name));assert.match(text(),/已撤销/);
 const options=renderer.root.findByProps({'aria-label':'对照报告 A'}).findAllByType('option');assert.equal(options.length,3);
});
test('invalid read contracts, mismatched preview selections or units fail closed',()=>{
 for(const change of [{schema:'future'},{rules:'future'},{case_id:2},{snapshot:''},{writes_database:true},{reports:[]}])assert.throws(()=>validateComparison({...payload(1),...change},1));
 const d=payload(1),r=req(d),p=result(r,d);assert.equal(validatePreview(p,d,r),p);
 for(const change of [{snapshot:'f'.repeat(64)},{b:r.a},{doctor_confirmed:false},{can_calculate:false},{delta:{...p.delta,unit:'mg/dL'}},{delta:{...p.delta,value:1}},{delta:{...p.delta,state:'decrease'}},{reasons:['unknown']},{reference_changed:false}])assert.throws(()=>validatePreview({...p,...change},d,r));
});
test('server microsecond ordering is retained without JS Date truncation',()=>{
 const d=payload(1);d.reports[1].report.collected_at='2026-10-07T01:30:00.000002Z';const r=req(d),p=result(r,d);assert.equal(validatePreview(p,d,r).can_calculate,true);
});
test('blocked comparison exposes reasons and never accepts a delta',async()=>{
 const data=payload(1);data.reports[1].report.laboratory='另一实验室';
 adapter=async c=>({config:c,data:c.method==='post'?{...result(JSON.parse(c.data),data),can_calculate:false,reasons:['laboratory_mismatch'],delta:null}:data});
 await mount();await choose();await confirm();await click('核对条件并预览数值差');assert.match(text(),/实验室不一致/);assert.doesNotMatch(text(),/差值 B−A/);
});
for(const scenario of ['revision','focus','case','selection','account'])test(`late preview discarded after ${scenario}`,async()=>{
 await mount();await choose();await confirm();const gate=deferred(),normal=adapter;let operation,config;
 adapter=c=>c.method==='post'?(config=c,gate.promise):normal(c);
 await act(async()=>{operation=button('核对条件并预览数值差').props.onClick();});
 if(scenario==='revision')await update({sourceRevision:1});else if(scenario==='focus')await emit('focus');else if(scenario==='case')await update({caseId:2});else if(scenario==='selection')await select('对照项目 A','1');else{token='other';await emit('storage',{key:'token'});}
 await act(async()=>{gate.resolve({config,data:result(JSON.parse(config.data),payload(1))});await operation;});
 assert.doesNotMatch(text(),/差值 B−A/);if(scenario!=='account')assert.equal(renderer.root.findByProps({'aria-label':'确认方法与采样条件可比'}).props.checked,false);
});
test('late catalog response cannot replace refreshed catalog',async()=>{
 const gate=deferred();let reads=0;adapter=c=>++reads===1?gate.promise:Promise.resolve({config:c,data:{...payload(1),identity:{...payload(1).identity,patient_name:'新对照快照'}}});
 await mount();await emit('focus');await act(async()=>gate.resolve({data:payload(1)}));assert.match(text(),/新对照快照/);assert.doesNotMatch(text(),/CW-B12 合成病例/);
});
for(const failed of [false,true])test(`confirm ${failed?'failure':'success'} clears pair at start and reloads without editor callback`,async()=>{
 await mount();await choose();await confirm();await click('核对条件并预览数值差');const gate=deferred(),normal=adapter;let operation;
 adapter=c=>c.url.endsWith('/confirm')?gate.promise.then(()=>({config:c,data:{state:'committed'}}),()=>Promise.reject({config:c,response:{status:409}})):normal(c);
 await act(async()=>{operation=api.post('/api/cases/1/manual-lab/confirm',{}).catch(()=>{});});assert.doesNotMatch(text(),/差值 B−A/);assert.match(text(),/资料操作已开始/);
 await act(async()=>{failed?gate.reject():gate.resolve();await operation;});assert.equal(renderer.root.findByProps({'aria-label':'对照报告 A'}).props.value,'');assert.equal(requests.filter(c=>c.url.endsWith('/lab-comparison')).length,2);
});
test('stale preview and failed reads never retain a previously calculated value',async()=>{
 await mount();await choose();await confirm();await click('核对条件并预览数值差');
 adapter=c=>Promise.reject({config:c,response:{status:409}});await click('核对条件并预览数值差');assert.match(text(),/请刷新并重新选择/);assert.doesNotMatch(text(),/差值 B−A/);
 for(const status of [401,404,503]){adapter=()=>Promise.reject({response:{status}});await click('刷新检验前后对照');assert.doesNotMatch(text(),/没有当前可选择/);}
});
