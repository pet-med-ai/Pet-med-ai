import React from 'react';
import TestRenderer, {act} from 'react-test-renderer';
import {MemoryRouter} from 'react-router-dom';
import {test,beforeEach,afterEach} from 'node:test';
import assert from 'node:assert/strict';
import api from '../src/api';
import Queue from '../src/pages/FollowupPlanQueue';
import {schema,shanghaiDate,dateBounds,validQueue,query,initialFilter,planLocation} from '../src/followupPlanQueue';
import fixture from '../../tests/fixtures/clinical_followup_plan_queue_cw_b18_cases.json';

let renderer,requests,adapter,listeners,token,original;
const output=()=>JSON.stringify(renderer.toJSON());
const button=name=>renderer.root.findAllByType('button').find(n=>n.children.join('')===name);
const click=async name=>act(async()=>{assert(button(name),name);await button(name).props.onClick();});
const change=async(label,value)=>act(async()=>renderer.root.findByProps({'aria-label':label}).props.onChange({target:{value}}));
const emit=async key=>act(async()=>{for(const fn of [...(listeners[key]||[])])fn({key:'token'});});
function response(config,total=1) {
 const p=config.params||{}, filter={...initialFilter(),...p}, page=Number(p.page||1),size=Number(p.page_size||20),today=shanghaiDate();
 const start=(page-1)*size,items=Array.from({length:Math.min(size,Math.max(0,total-start))},(_,i)=>({case:{id:start+i+1,patient_name:'合成犬猫 '+(start+i+1),species:i%2?'cat':'dog',sex:null,age_info:null,breed:null,owner_name:'合成宠主'},plan:{id:start+i+1,root_id:start+i+1,version:1,state:p.state==='needs_review'?'needs_review':'planned',data:{...fixture.plan,planned_date:p.range==='past'?'2024-02-29':p.start||today},reviewed_by:'1',reviewed_at:'2024-02-29T12:00:00+00:00',reason:''}}));
 return {schema,as_of_date:today,timezone:'Asia/Shanghai',read_at:new Date().toISOString(),filters:dateBounds(filter,today),page,page_size:size,total,items,snapshot:'a'.repeat(64),limits:{cases:200,versions:10000,per_case:50},writes_database:false};
}
beforeEach(()=>{
 token='synthetic-owner';requests=[];listeners={};global.localStorage={getItem:()=>token};
 const target={addEventListener:(k,f)=>(listeners[k]??=new Set()).add(f),removeEventListener:(k,f)=>listeners[k]?.delete(f)};
 global.window={...target};global.document={...target,visibilityState:'visible'};
 original=api.defaults.adapter;adapter=async c=>({config:c,status:200,data:response(c)});
 api.defaults.adapter=async c=>{requests.push(c);return adapter(c);};
});
afterEach(()=>{if(renderer)act(()=>renderer.unmount());renderer=null;api.defaults.adapter=original;});
async function mount(){await act(async()=>{renderer=TestRenderer.create(<MemoryRouter><Queue/></MemoryRouter>);});}

test('anonymous queue performs no protected reads; account change clears prior data',async()=>{
 token='';await mount();assert.match(output(),/请先登录/);assert.equal(requests.length,0);
 token='owner';await emit('storage');assert.match(output(),/合成犬猫/);
 token='';await emit('storage');assert.doesNotMatch(output(),/合成犬猫/);assert.equal(requests.length,1);
});
test('all filters, dates, original text and safe exact navigation remain GET-only',async()=>{
 await mount();assert.match(output(),/复查总览原文/);assert.match(output(),/展开完整计划原文/);
 const link=renderer.root.findAllByType('a').find(n=>n.props.href.includes('followup_plan'));
 assert.equal(link.props.href,'/cases/1?followup_plan=1&followup_version=1');assert(!link.props.href.includes('snapshot'));
 for(const range of ['next7','past','all']){await change('计划日期范围',range);assert.equal(requests.at(-1).params.range,range);}
 await change('计划有效状态','needs_review');assert.match(output(),/需重新核对/);
 await change('计划日期范围','custom');let count=requests.length;assert.match(output(),/请选择有效/);
 await change('计划开始日期','2028-02-29');assert.equal(requests.length,count);
 await change('计划结束日期','2028-03-06');assert.equal(requests.at(-1).params.end,'2028-03-06');
 assert(requests.every(r=>r.method==='get'));assert(!output().includes('确认保存'));
});
test('continuous paging carries snapshot; changed snapshot resets first page without mixing',async()=>{
 adapter=async c=>{if(c.params.page===2)throw {response:{status:409,data:{detail:'followup_queue_snapshot_changed'}}};return {config:c,status:200,data:response(c,23)};};
 await mount();await click('下一页');assert.equal(requests[1].params.snapshot,'a'.repeat(64));assert.equal(requests.at(-1).params.page,1);assert(!requests.at(-1).params.snapshot);assert.match(output(),/正在重新读取第 1 页/);
 adapter=async c=>({config:c,status:200,data:response(c,23)});await click('下一页');assert.match(output(),/合成犬猫 23/);assert.doesNotMatch(output(),/合成犬猫 1"/);assert.equal(button('下一页').props.disabled,true);
 await click('上一页');assert.equal(requests.at(-1).params.snapshot,'a'.repeat(64));
 await change('每页条数','50');assert.equal(requests.at(-1).params.page_size,50);assert(!requests.at(-1).params.snapshot);
});
test('empty disabled corrupt and cap errors are distinct; retry retains filter',async()=>{
 adapter=async c=>({config:c,status:200,data:response(c,0)});await mount();assert.match(output(),/空清单不等于无需复查/);
 for(const [code,label] of [['followup_plan_queue_disabled','暂未启用'],['followup_invalid_saved_data','结构异常'],['followup_queue_scale_limit','规模上限']]){
  adapter=async()=>{throw {response:{status:409,data:{detail:code}}};};await click('刷新清单');assert.match(output(),new RegExp(label));assert.doesNotMatch(output(),/空清单不等于/);
 }
 await change('计划日期范围','all');adapter=async c=>({config:c,status:200,data:response(c)});await click('重试读取清单');assert.equal(requests.at(-1).params.range,'all');assert.match(output(),/合成犬猫/);
});
test('late old filter and late other-account responses never restore stale entries',async()=>{
 await mount();let release;adapter=c=>new Promise(resolve=>{release=()=>resolve({config:c,status:200,data:response(c)});});
 await click('刷新清单');const old=release;assert.doesNotMatch(output(),/合成犬猫/);
 adapter=async c=>({config:c,status:200,data:response(c,0)});await change('计划日期范围','all');await act(async()=>old());assert.doesNotMatch(output(),/合成犬猫/);
 adapter=c=>new Promise(resolve=>{release=()=>resolve({config:c,status:200,data:response(c)});});await click('刷新清单');const late=release;
 token='';await emit('storage');await act(async()=>late());assert.doesNotMatch(output(),/合成犬猫/);assert.match(output(),/请先登录/);
});
test('focus, hidden state and malformed replies invalidate list; failed requests keep only filters',async()=>{
 await mount();await emit('blur');assert.doesNotMatch(output(),/合成犬猫/);await emit('focus');assert.match(output(),/合成犬猫/);
 document.visibilityState='hidden';await emit('visibilitychange');assert.doesNotMatch(output(),/合成犬猫/);
 document.visibilityState='visible';await emit('visibilitychange');assert.match(output(),/合成犬猫/);
 adapter=async c=>({config:c,status:200,data:{...response(c),total:999}});await click('刷新清单');assert.match(output(),/读取失败/);assert.doesNotMatch(output(),/合成犬猫/);
 adapter=async()=>{throw Error('synthetic network failure');};await click('重试读取清单');assert.match(output(),/读取失败/);assert(requests.every(c=>c.method==='get'));
});
test('calendar obeys Shanghai across UTC and Los Angeles, leap/month/year/min/max',()=>{
 for(const t of ['2028-02-28T16:00:00Z','2028-02-28T08:00:00-08:00'])assert.equal(shanghaiDate(new Date(t)),'2028-02-29');
 assert.equal(dateBounds({...initialFilter(),range:'next7'},'2028-02-29').end,'2028-03-06');
 assert.equal(dateBounds({...initialFilter(),range:'next7'},'2026-12-31').end,'2027-01-06');
 assert.equal(dateBounds({...initialFilter(),range:'next7'},'9999-12-31').end,'9999-12-31');
 assert(dateBounds({...initialFilter(),range:'custom',start:'0001-01-01',end:'9999-12-31'},'2028-02-29'));
 for(const start of fixture.invalid_dates)assert.equal(dateBounds({...initialFilter(),range:'custom',start,end:'9999-12-31'},'2028-02-29'),null);
});
test('versioned protocol rejects extra sensitive identity, dates, states, duplicate cases and mismatched pages',()=>{
 const f=initialFilter(),v=response({params:query(f)});assert(validQueue(v,f,1,20));assert.equal(planLocation(v.items[0]),'/cases/1?followup_plan=1&followup_version=1');
 for(const bad of [{...v,schema:'old'},{...v,writes_database:true},{...v,page:2},{...v,snapshot:'x'},{...v,filters:{...v.filters,state:'done'}},{...v,read_at:'invalid'},{...v,total:2}])assert(!validQueue(bad,f,1,20));
 for(const mutate of [x=>x.items[0].case.owner_phone='secret',x=>x.items[0].plan.state='withdrawn',x=>x.items[0].plan.version=51,x=>x.items[0].plan.data.items=[],x=>x.items[0].plan.data.planned_date='2027-02-29']){const bad=structuredClone(v);mutate(bad);assert(!validQueue(bad,f,1,20));}
 const duplicates={...v,total:2,items:[v.items[0],v.items[0]]};assert(!validQueue(duplicates,f,1,20));
});
