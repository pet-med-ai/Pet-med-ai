import React from 'react';
import TestRenderer, {act} from 'react-test-renderer';
import {MemoryRouter} from 'react-router-dom';
import {test,beforeEach,afterEach} from 'node:test';
import assert from 'node:assert/strict';
import api from '../src/api';
import Queue from '../src/pages/FollowupPlanQueue';
import {schema,limits,validQueue,query,contactLocation,sourceLocation} from '../src/followupContactQueue';
import {schema as oldSchema,shanghaiDate,dateBounds,initialFilter} from '../src/followupPlanQueue';
import fixture from '../../tests/fixtures/clinical_followup_contact_queue_cw_b23_cases.json';

let renderer,requests,adapter,listeners,token,original;
const output=()=>JSON.stringify(renderer.toJSON());
const input=label=>renderer.root.findByProps({'aria-label':label});
const button=name=>renderer.root.findAllByType('button').find(n=>n.children.join('')===name);
const click=async name=>act(async()=>{assert(button(name),name);await button(name).props.onClick();});
const change=async(label,value)=>act(async()=>input(label).props.onChange({target:{value}}));
const toggle=async checked=>act(async()=>input('显示人工随访记录').props.onChange({target:{checked}}));
const emit=async key=>act(async()=>{for(const fn of [...(listeners[key]||[])])fn({key:'token'});});
function response(config,total=1){
  const p=config.params||{},filter={...initialFilter(),...p},page=Number(p.page||1),size=Number(p.page_size||20),today=shanghaiDate();
  const included=p.include_followup_contacts==='true',state=p.contact_state||'all',start=(page-1)*size;
  const items=Array.from({length:Math.min(size,Math.max(0,total-start))},(_,n)=>{
    const cid=start+n+1,identity={id:cid,patient_name:'CW23 合成犬猫 '+cid,species:n%2?'cat':'dog',sex:null,age_info:null,breed:null,owner_name:'合成宠主'};
    const plan={id:cid*100,root_id:cid*100,version:1,state:p.state==='needs_review'?'needs_review':'planned',data:{...fixture.plan,planned_date:p.range==='past'?'2024-02-29':p.start||today},reviewed_by:'1',reviewed_at:'2024-03-01T00:00:00Z',reason:''};
    const item={case:identity,plan};if(!included)return item;
    const contact={id:cid*100+2,root_id:cid*100+2,version:1,state:'recorded',token:'c'.repeat(64),data:fixture.long_contact,recorded_by:'1',recorded_at:'2024-03-01T00:00:00Z',reason:'',case:{...identity},
      source:{id:plan.id,root_id:plan.root_id,version:plan.version,data:plan.data,reviewed_by:plan.reviewed_by,reviewed_at:plan.reviewed_at,case:{...identity},state:plan.state}};
    if(state==='historical_only'){contact.source={...contact.source,id:plan.id-1,root_id:plan.id-1,state:'superseded'};}
    item.contacts={counts:{current:state==='none'||state==='historical_only'?0:1,historical:state==='historical_only'?1:0},latest:{current:state==='none'||state==='historical_only'?null:contact,historical:state==='historical_only'?contact:null}};return item;
  });
  return {schema:included?schema:oldSchema,as_of_date:today,timezone:'Asia/Shanghai',read_at:new Date().toISOString(),filters:{...dateBounds(filter,today),...(included?{contact_state:state}:{})},page,page_size:size,total,items,snapshot:(included?'b':'a').repeat(64),limits:included?limits:{cases:200,versions:10000,per_case:50},writes_database:false};
}
beforeEach(()=>{
  renderer=null;token='synthetic-owner';requests=[];listeners={};global.localStorage={getItem:()=>token,setItem(){throw Error('no cache');}};
  const target={addEventListener:(k,f)=>(listeners[k]??=new Set()).add(f),removeEventListener:(k,f)=>listeners[k]?.delete(f)};
  global.window={...target};global.document={...target,visibilityState:'visible'};original=api.defaults.adapter;
  adapter=async c=>({config:c,status:200,data:response(c)});api.defaults.adapter=async c=>{requests.push(c);return adapter(c);};
});
afterEach(()=>{if(renderer)act(()=>renderer.unmount());renderer=null;api.defaults.adapter=original;});
async function mount(){await act(async()=>{renderer=TestRenderer.create(<MemoryRouter><Queue/></MemoryRouter>);});}

test('anonymous and default mode do not request contact facts; explicit toggle shows literal content',async()=>{
  token='';await mount();assert.equal(requests.length,0);token='owner';await emit('storage');
  assert(requests.every(c=>!c.params.include_followup_contacts));assert.equal(input('显示人工随访记录').props.checked,false);
  await toggle(true);assert.equal(requests.at(-1).params.include_followup_contacts,'true');assert.match(output(),/本版计划有效登记/);
  const paragraphs=renderer.root.findAllByType('p');assert(paragraphs.some(p=>p.children.includes(fixture.long_contact.note)));
  assert.match(output(),/不表示已复诊/);assert(!renderer.root.findAll(n=>n.props.dangerouslySetInnerHTML).length);
  const links=renderer.root.findAllByType('a').map(n=>n.props.href);assert(links.includes('/cases/1?followup_contact=102&followup_contact_version=1'));assert(links.includes('/cases/1?followup_plan=100&followup_version=1'));
  await toggle(false);assert(!requests.at(-1).params.include_followup_contacts);assert.doesNotMatch(output(),/本版计划有效登记/);assert(requests.every(c=>c.method==='get'));
});
test('four registration filters, plan dates, page sizes and source groups stay distinct',async()=>{
  await mount();await toggle(true);
  for(const state of ['current','historical_only','none','all']){await change('随访登记情况',state);assert.equal(requests.at(-1).params.contact_state,state);assert(!requests.at(-1).params.snapshot);}
  await change('随访登记情况','historical_only');assert.match(output(),/来源计划已更正/);
  await change('随访登记情况','none');assert.match(output(),/不表示从未联系/);
  for(const range of ['past','next7','all']){await change('计划日期范围',range);assert.equal(requests.at(-1).params.range,range);}
  await change('计划日期范围','custom');await change('计划开始日期','2028-02-29');await change('计划结束日期','2028-03-01');assert.equal(requests.at(-1).params.end,'2028-03-01');
  await change('每页条数','50');assert.equal(requests.at(-1).params.page_size,50);
});
test('snapshot conflict returns to first page and never combines old mode and new contacts',async()=>{
  adapter=async c=>({config:c,status:200,data:response(c,23)});await mount();await toggle(true);await click('下一页');assert.equal(requests.at(-1).params.snapshot,'b'.repeat(64));assert.match(output(),/CW23 合成犬猫 23/);
  const normal=adapter;adapter=async c=>{if(c.params.page===1&&c.params.snapshot)throw {response:{data:{detail:'followup_queue_snapshot_changed'}}};return normal(c);};
  await click('上一页');assert.equal(requests.at(-1).params.page,1);assert(!requests.at(-1).params.snapshot);assert.match(output(),/正在重新读取第 1 页/);
  await toggle(false);assert(!requests.at(-1).params.snapshot);assert.doesNotMatch(output(),/本版计划有效登记/);
});
test('late response after mode close, filter, focus and account change cannot restore facts',async()=>{
  await mount();let release;adapter=c=>new Promise(resolve=>{release=()=>resolve({config:c,data:response(c)});});
  await toggle(true);const old=release;adapter=async c=>({config:c,data:response(c)});await toggle(false);await act(async()=>old());assert.doesNotMatch(output(),/本版计划有效登记/);
  await toggle(true);await emit('blur');assert.doesNotMatch(output(),/CW23 合成犬猫/);await emit('focus');assert.match(output(),/本版计划有效登记/);
  adapter=c=>new Promise(resolve=>{release=()=>resolve({config:c,data:response(c)});});await click('刷新清单');const prior=release;
  token='';await emit('storage');await act(async()=>prior());assert.match(output(),/请先登录/);assert.doesNotMatch(output(),/CW23 合成犬猫/);
});
test('disabled, unreadable and cap states are not rendered as empty or silently downgraded',async()=>{
  await mount();await toggle(true);
  for(const [code,label] of [['followup_contact_queue_disabled','暂未启用'],['contact_invalid_saved_data','审计记录异常'],['followup_contact_queue_scale_limit','规模上限']]){
    adapter=async()=>{throw {response:{data:{detail:code}}};};await click('刷新清单');assert.match(output(),new RegExp(label));assert.doesNotMatch(output(),/暂无有效登记；/);assert.equal(input('显示人工随访记录').props.checked,true);
  }
  adapter=async c=>({config:c,data:response(c)});await click('重试读取清单');assert.match(output(),/本版计划有效登记/);
});
test('strict response rejects mismatched source, identity, counts, time, schema, filter and extra fields',()=>{
  const filter=initialFilter(),v=response({params:query(filter)});assert(validQueue(v,filter,'all',1,20));
  const changes=[v=>v.schema='old',v=>v.writes_database=true,v=>v.extra=true,v=>v.filters.contact_state='none',v=>v.total=2,
    v=>v.items[0].case.owner_phone='secret',v=>v.items[0].contacts.counts.current=0,v=>v.items[0].contacts.counts.current=51,
    v=>v.items[0].contacts.latest.current.case.id=2,v=>v.items[0].contacts.latest.current.version=51,
    v=>v.items[0].contacts.latest.current.source.id=999,v=>v.items[0].contacts.latest.current.source.version=2,
    v=>v.items[0].contacts.latest.current.source.data={...v.items[0].plan.data,note:'wrong'},v=>v.items[0].contacts.latest.current.source.state='withdrawn',
    v=>v.items[0].contacts.latest.current.data={...fixture.contact,outcome:'completed'},v=>v.items[0].contacts.latest.current.data={...fixture.contact,occurred_at:'2025-02-29T12:00+08:00'},
    v=>v.items[0].contacts.latest.current.state='withdrawn',v=>v.items[0].contacts.latest.current.token='',v=>v.items[0].contacts.latest.current.recorded_by='other'];
  for(const mutate of changes){const bad=structuredClone(v);mutate(bad);assert(!validQueue(bad,filter,'all',1,20),String(mutate));}
  const r=v.items[0].contacts.latest.current;assert.equal(contactLocation(1,r),'/cases/1?followup_contact=102&followup_contact_version=1');assert.equal(sourceLocation(1,r),'/cases/1?followup_plan=100&followup_version=1');
});

test('Shanghai midnight discards a contact page snapshot and restarts page one',async()=>{
 const RealDate=global.Date,interval=global.setInterval,clear=global.clearInterval;let instant=RealDate.parse('2028-02-29T15:59:59Z'),tick;
 class Clock extends RealDate{constructor(...a){super(...(a.length?a:[instant]));}static now(){return instant;}}
 global.Date=Clock;global.setInterval=fn=>{tick=fn;return {unref(){}};};global.clearInterval=()=>{};
 try{adapter=async c=>({config:c,data:response(c,23)});await mount();await toggle(true);await click('下一页');assert.equal(requests.at(-1).params.page,2);
 instant+=2000;await act(async()=>tick());assert.equal(requests.at(-1).params.page,1);assert(!requests.at(-1).params.snapshot);assert.match(output(),/2028-03-01/);assert.doesNotMatch(output(),/CW23 合成犬猫 23/);
 }finally{if(renderer)act(()=>renderer.unmount());renderer=null;global.Date=RealDate;global.setInterval=interval;global.clearInterval=clear;}
});
