import React from 'react';
import TestRenderer, {act} from 'react-test-renderer';
import {test,beforeEach,afterEach} from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
import CaseAttachments from '../src/components/CaseAttachments';
import {verifyAttachmentBytes} from '../src/caseAttachments';
import api from '../src/api';
let renderer,adapter,requests,token,items,props;
const id='b'.repeat(64), version='a'.repeat(64);
const item={id,name:'synthetic.png',mime:'image/png',size:3,sha256:'c'.repeat(64),state:'active',metadata:{title:'合成检验',kind:'lab',taken_at:'',reported_at:'',source:'',note:''}};
const button=label=>renderer.root.findAllByType('button').find(n=>n.children.join('')===label);
const click=async label=>{assert(button(label)&&!button(label).props.disabled,label);await act(async()=>{await button(label).props.onClick();});};
const text=()=>JSON.stringify(renderer.toJSON());
const input=type=>renderer.root.findAllByType('input').find(n=>n.props.type===type);
const change=(node,value)=>act(()=>node.props.onChange({target:{value}}));
const check=()=>act(()=>input('checkbox').props.onChange({target:{checked:true}}));
const deferred=()=>{let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};};
const response=(c,data)=>({config:c,status:200,data});
const select=async(name='synthetic.png',size=3)=>act(()=>input('file').props.onChange({target:{files:[{name,size}]}}));
async function stage(){await select();await click('上传待核对原件');}
beforeEach(async()=>{
 token='synthetic-owner';items=[];requests=[];props={caseId:1,requestToken:token};
 Object.defineProperty(globalThis,'crypto',{configurable:true,value:webcrypto});
 global.localStorage={getItem:()=>token};
 adapter=async c=>{
  if(c.url.endsWith('/attachments'))return response(c,{case_id:props.caseId,patient_name:'合成病例-'+props.caseId,species:'dog',case_token:version,items,legacy_count:0});
  if(c.url.endsWith('/preview')){const body=JSON.parse(c.data);return response(c,{case_id:props.caseId,patient_name:'合成病例-'+props.caseId,species:'dog',operation:body.operation,preview_token:'d'.repeat(64),proposed:{...item,metadata:body.metadata}});}
  if(c.url.endsWith('/confirm')){items=[item];return response(c,{state:'committed',attachment:item});}
  if(c.url.includes('/requests/'))return response(c,{state:'committed',attachment:item});
  if(c.url.endsWith('/cancel'))return response(c,{state:'cancelled'});
  if(c.url.includes('/uploads/'))return response(c,{state:'pending',attachment:item});
  throw Error('Unexpected request '+c.url);
 };
 api.defaults.adapter=async c=>{requests.push(c);return adapter(c);};
 await act(async()=>{renderer=TestRenderer.create(<CaseAttachments {...props}/>);});
});
afterEach(()=>{act(()=>renderer.unmount());});

test('doctor checkbox required; editing metadata invalidates reviewed preview',async()=>{
 await stage();await click('核对资料关联');assert(button('确认资料操作').props.disabled);check();
 const title=renderer.root.findAllByType('input').find(n=>n.props.maxLength===150);
 change(title,'更正合成标题');assert.equal(button('确认资料操作'),undefined);
 await click('核对资料关联');check();await click('确认资料操作');
 const write=requests.filter(c=>c.url.endsWith('/confirm'));assert.equal(write.length,1);assert(JSON.parse(write[0].data).reviewed);
 assert.equal(JSON.parse(write[0].data).metadata.title,'更正合成标题');
 assert.equal(JSON.parse(write[0].data).metadata.taken_at,'');
});
test('lost upload reply resolves with GET and never repeats binary POST',async()=>{
 const normal=adapter;adapter=c=>c.url.includes('/uploads/')&&c.method==='post'?Promise.reject(Error('lost')):normal(c);
 await stage();assert.match(text(),/上传已核实/);
 assert.equal(requests.filter(c=>c.url.includes('/uploads/')&&c.method==='post').length,1);
 assert.equal(requests.filter(c=>c.url.includes('/uploads/')&&c.method==='get').length,1);
});
test('lost confirm reply resolves with GET and same-tick clicks commit only once',async()=>{
 await stage();await click('核对资料关联');check();
 const normal=adapter;adapter=c=>c.url.endsWith('/confirm')?Promise.reject(Error('lost')):normal(c);
 const submit=button('确认资料操作').props.onClick;await act(async()=>{await Promise.all([submit(),submit()]);});
 assert.equal(requests.filter(c=>c.url.endsWith('/confirm')).length,1);
 assert.equal(requests.filter(c=>c.url.includes('/requests/')).length,1);
 assert.match(text(),/操作结果已回读/);
});
test('unknown result locks writes until explicit readback succeeds',async()=>{
 await stage();await click('核对资料关联');check();const normal=adapter;
 adapter=c=>c.url.endsWith('/confirm')||c.url.includes('/requests/')?Promise.reject(Error('offline')):normal(c);
 await click('确认资料操作');assert(button('核对资料关联').props.disabled);assert.match(text(),/保存结果未知/);
 adapter=normal;await click('核对操作结果');assert.match(text(),/操作结果已回读/);
 assert.equal(requests.filter(c=>c.url.endsWith('/confirm')).length,1);
});
test('case change discards late old upload and loads new case',async()=>{
 await select();const gate=deferred(),normal=adapter;
 adapter=c=>c.url.includes('/uploads/')?gate.promise.then(()=>normal(c)):normal(c);
 let pending;await act(async()=>{pending=button('上传待核对原件').props.onClick();await new Promise(r=>setTimeout(r,0));});
 await act(async()=>{props={...props,caseId:2};renderer.update(<CaseAttachments {...props}/>);});
 await act(async()=>{gate.resolve();await pending;});
 assert.match(text(),/合成病例-2/);assert.equal(button('核对资料关联'),undefined);
});
test('account changes suppress late result before any repaint',async()=>{
 await select();const gate=deferred(),normal=adapter;
 adapter=c=>c.url.includes('/uploads/')?gate.promise.then(()=>normal(c)):normal(c);
 let pending;await act(async()=>{pending=button('上传待核对原件').props.onClick();await new Promise(r=>setTimeout(r,0));});
 token='other-account';await act(async()=>{gate.resolve();await pending;});
 assert.equal(button('核对资料关联'),undefined);
});
test('invalid file and excessive size never send binary data',async()=>{
 for(const [name,size] of [['report.exe',3],['report.pdf',10485761],['empty.jpg',0]]){await select(name,size);assert.equal(button('上传待核对原件'),undefined);}
 assert(requests.every(c=>c.method==='get'));
});
test('metadata edits and withdrawal require new review; PDF has no inline preview',async()=>{
 items=[{...item,mime:'application/pdf',name:'synthetic.pdf'}];await click('刷新资料列表');
 assert.equal(button('查看图片'),undefined);await click('更正资料信息');await click('核对资料关联');
 assert.equal(JSON.parse(requests.at(-1).data).operation,'update');await click('取消本次操作');
 await click('撤销关联');change(renderer.root.findByType('textarea'),'合成误关联');await click('核对资料关联');
 assert.equal(JSON.parse(requests.at(-1).data).reason,'合成误关联');assert(button('确认资料操作').props.disabled);
});
test('download bytes reject mismatched size or SHA256',async()=>{
 const bytes=new Uint8Array([1,2,3]).buffer;
 const sha=[...new Uint8Array(await webcrypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');
 await verifyAttachmentBytes(bytes,{size:3,sha256:sha});
 await assert.rejects(verifyAttachmentBytes(bytes,{size:2,sha256:sha}));
 await assert.rejects(verifyAttachmentBytes(bytes,{size:3,sha256:'0'.repeat(64)}));
});


test('expired upload result unlocks selection without automatically resending',async()=>{
 const normal=adapter;adapter=c=>c.url.includes('/uploads/')?(c.method==='post'?Promise.reject(Error('lost')):response(c,{state:'expired'})):normal(c);
 await stage();assert.match(text(),/暂存已取消或到期/);assert.equal(input('file').props.disabled,false);
 assert.equal(button('核对操作结果'),undefined);assert.equal(button('上传待核对原件'),undefined);
 assert.equal(requests.filter(c=>c.url.includes('/uploads/')&&c.method==='post').length,1);
});
