import React from "react";
import TestRenderer, { act } from "react-test-renderer";
import { MemoryRouter, Routes, Route, useLocation } from "react-router-dom";
import { test, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import api from "../src/api";
import ManualCaseCreateReview, { manualCasePayload } from "../src/components/ManualCaseCreateReview";
import CaseEditorLite from "../src/pages/CaseEditorLite";
import { Home } from "../src/App";
import { MANUAL_DRAFT_KEY, MANUAL_DRAFT_MAX_AGE, readManualCaseDraft, writeManualCaseDraft, clearManualCaseDraft } from "../src/manualCaseDraft";

const key = "pmai.manual-create-attempt.v1";
const memory = () => { const map = new Map(); return { getItem:k=>map.get(k)??null,setItem:(k,v)=>map.set(k,String(v)),removeItem:k=>map.delete(k),get length(){return map.size;},key:i=>[...map.keys()][i]??null }; };
const token = owner => "synthetic." + Buffer.from(JSON.stringify({sub:owner,exp:4102444800})).toString("base64url") + ".signature";
const values = {patient_name:"合成犬",species:"dog",sex:"M",age_info:"2y",breed:"虚构",weight:"5.2kg",coat_color:"",owner_name:"虚构主人",owner_phone:"",chief_complaint:"  合成主诉\r\n ",history:"  病史🐾\r\n\t ",exam_findings:"合成检查",analysis:"手工分析",treatment:"手工处理",prognosis:"随访 <script>literal</script>"};
const response = (config,data) => ({config,data,status:config.method==="post"?201:200});
const defer = () => {let resolve; const promise=new Promise(r=>resolve=r);return {promise,resolve};};
let renderer,requests,adapter,current,locked,listeners;
const button = name => renderer.root.findAllByType("button").find(n=>n.children.join("")===name);
const output = () => JSON.stringify(renderer.toJSON());
const click = async name => {const b=button(name);assert(b,name);assert(!b.props.disabled,name);await act(async()=>b.props.onClick());};
const checkbox = () => renderer.root.findAllByType("input").find(n=>n.props.type==="checkbox");
const check = () => act(()=>checkbox().props.onChange({target:{checked:true}}));
const posts = () => requests.filter(r=>r.method==="post");
const render = () => <MemoryRouter><ManualCaseCreateReview values={current} onLockChange={value=>{locked=value;}} /></MemoryRouter>;
const revise = change => act(()=>{current={...current,...change};renderer.update(render());});
const remount = async element => {act(()=>renderer.unmount());await act(async()=>{renderer=TestRenderer.create(element||render());});};
function field(label) {
  const l=renderer.root.findAllByType("label").find(n=>n.findAllByType("div").some(d=>d.children.join("")===label));
  assert(l,label);return l.findAll(n=>["input","select","textarea"].includes(n.type))[0];
}
beforeEach(()=>{
  global.localStorage=memory();localStorage.setItem("token",token("owner"));
  listeners=new Map();
  global.window={sessionStorage:memory(),addEventListener(k,fn){if(!listeners.has(k))listeners.set(k,new Set());listeners.get(k).add(fn);},removeEventListener(k,fn){listeners.get(k)?.delete(fn);},location:{reload(){}}};
  global.alert=()=>{};
  current={...values};requests=[];locked=false;
  adapter=async config=>response(config,config.method==="post"?{id:77}:{id:77,...manualCasePayload(current)});
  api.defaults.adapter=async config=>{requests.push({method:config.method,url:config.url,data:config.data});return adapter(config);};
  act(()=>{renderer=TestRenderer.create(render());});
});
afterEach(()=>act(()=>renderer.unmount()));

test("manual preview is read-only and preserves all clinical whitespace and literal HTML",async()=>{
  await click("核对新建内容");assert.equal(requests.length,0);assert(button("确认并创建病例").props.disabled);
  const texts=renderer.root.findAllByType("pre").map(n=>n.children.join(""));
  for(const value of [values.history,values.chief_complaint,values.prognosis])assert(texts.includes(value));
  await act(async()=>button("确认并创建病例").props.onClick());assert.equal(posts().length,0);
});
test("manual creation submits the reviewed fifteen fields once then independently reads them",async()=>{
  await click("核对新建内容");check();await click("确认并创建病例");
  assert.equal(posts().length,1);assert.deepEqual(JSON.parse(posts()[0].data),manualCasePayload(values));
  assert.equal(requests.at(-1).url,"/api/cases/77");assert.equal(requests.at(-1).method,"get");
  assert.match(output(),/十五项内容一致/);assert.equal(locked,true);assert.equal(button("确认并创建病例"),undefined);
});
test("editing even one input invalidates confirmation until a fresh preview",async()=>{
  await click("核对新建内容");check();revise({history:"修改后病史"});
  assert.equal(checkbox().props.checked,false);assert(button("确认并创建病例").props.disabled);
  await click("重新核对新建内容");assert(button("确认并创建病例").props.disabled);check();await click("确认并创建病例");
  assert.equal(JSON.parse(posts()[0].data).history,"修改后病史");
});
test("empty required values and anonymous users cannot create",async()=>{
  revise({patient_name:"  "});await click("核对新建内容");assert.equal(button("确认并创建病例"),undefined);
  localStorage.removeItem("token");revise({patient_name:"合成犬"});assert(button("核对新建内容").props.disabled);assert.equal(posts().length,0);
});
test("two immediate clicks share one in-flight creation",async()=>{
  const gate=defer();adapter=async c=>{if(c.method==="post")await gate.promise;return response(c,c.method==="post"?{id:77}:{id:77,...manualCasePayload(values)});};
  await click("核对新建内容");check();const submit=button("确认并创建病例").props.onClick;
  await act(async()=>{const first=submit();const second=submit();gate.resolve();await Promise.all([first,second]);});
  assert.equal(posts().length,1);
});
test("a lost creation response survives remount without a second POST",async()=>{
  adapter=async()=>{throw Error("response lost");};await click("核对新建内容");check();await click("确认并创建病例");
  assert.match(output(),/创建结果待核实/);assert(window.sessionStorage.getItem(key));
  await remount();assert.equal(button("核对新建内容"),undefined);assert.equal(button("确认并创建病例"),undefined);assert.equal(posts().length,1);
});
test("failed readback retries GET only, including after page remount",async()=>{
  adapter=async c=>{if(c.method==="get")throw Error("readback unavailable");return response(c,{id:77});};
  await click("核对新建内容");check();await click("确认并创建病例");await remount();
  adapter=async c=>response(c,{id:77,...manualCasePayload(values)});await click("核对保存结果");
  assert.match(output(),/十五项内容一致/);assert.equal(posts().length,1);assert.equal(requests.filter(r=>r.method==="get").length,2);
});
test("readback mismatch in a clinical field cannot produce a success receipt",async()=>{
  adapter=async c=>response(c,c.method==="post"?{id:77}:{id:77,...manualCasePayload(values),analysis:null});
  await click("核对新建内容");check();await click("确认并创建病例");
  assert.match(output(),/回读内容与预览不一致/);assert.doesNotMatch(output(),/十五项内容一致/);assert(button("核对保存结果"));
});
test("wrong case ID on GET is rejected without displaying another case",async()=>{
  adapter=async c=>response(c,c.method==="post"?{id:77}:{id:78,...manualCasePayload(values),patient_name:"错误病例"});
  await click("核对新建内容");check();await click("确认并创建病例");assert.doesNotMatch(output(),/错误病例/);assert.doesNotMatch(output(),/十五项内容一致/);
});
test("definite validation rejection allows corrected fresh confirmation",async()=>{
  adapter=async()=>{throw {response:{status:422}};};await click("核对新建内容");check();await click("确认并创建病例");
  assert.equal(window.sessionStorage.getItem(key),null);assert.equal(checkbox().props.checked,false);assert(button("确认并创建病例").props.disabled);
});
test("storage failure blocks dispatch before creating an untrackable case",async()=>{
  window.sessionStorage.setItem=()=>{throw Error("quota");};await click("核对新建内容");check();await click("确认并创建病例");
  assert.equal(posts().length,0);assert.match(output(),/尚未提交/);
});
test("switching account before click invalidates review and prevents submission",async()=>{
  await click("核对新建内容");check();localStorage.setItem("token",token("other"));revise({});
  assert.equal(checkbox().props.checked,false);assert(button("确认并创建病例").props.disabled);assert.equal(posts().length,0);
});
test("account switching between click and Axios dispatch is blocked",async()=>{
  await click("核对新建内容");check();const submit=button("确认并创建病例").props.onClick;
  await act(async()=>{const pending=submit();localStorage.setItem("token",token("other"));await pending;});assert.equal(posts().length,0);
});
test("account switching during POST hides the old response and skips readback",async()=>{
  adapter=async c=>{localStorage.setItem("token",token("other"));return response(c,{id:77});};
  await click("核对新建内容");check();await click("确认并创建病例");revise({});
  assert.equal(requests.length,1);assert.match(output(),/登录账号已变化/);assert.doesNotMatch(output(),/本次病例编号/);
});
test("another owner cannot restore the first owner's attempt",async()=>{
  adapter=async()=>{throw Error("lost");};await click("核对新建内容");check();await click("确认并创建病例");
  localStorage.setItem("token",token("other"));await remount();assert(button("核对新建内容"));assert.equal(window.sessionStorage.getItem(key),null);
});
test("an expired login and remount retain an uncertain receipt until the same owner logs in",async()=>{
  adapter=async()=>{throw Error("lost");};await click("核对新建内容");check();await click("确认并创建病例");
  const saved=window.sessionStorage.getItem(key);
  localStorage.setItem("token","synthetic."+Buffer.from(JSON.stringify({sub:"owner",exp:1})).toString("base64url")+".signature");
  await remount();assert.equal(window.sessionStorage.getItem(key),saved);
  assert.equal(button("确认并创建病例"),undefined);assert.doesNotMatch(output(),/手工分析/);
  localStorage.setItem("token",token("owner"));await remount();
  assert.equal(window.sessionStorage.getItem(key),saved);assert.equal(button("确认并创建病例"),undefined);assert.equal(posts().length,1);
});
test("actual standalone editor exposes preview, not either former direct-save button",async()=>{
  await remount(<MemoryRouter initialEntries={["/cases/new/edit"]}><Routes><Route path="/cases/:id/edit" element={<CaseEditorLite/>}/></Routes></MemoryRouter>);
  assert.equal(button("保存"),undefined);assert.equal(button("保存并查看详情"),undefined);
  for(const [label,value] of [["病例名 / 宠物名（必填）","合成犬"],["主诉（必填）","合成主诉"],["AI 分析","手工分析"],["治疗建议","手工治疗"],["风险提示 / 后续随访","手工随访"]])await act(async()=>field(label).props.onChange({target:{value}}));
  await click("核对新建内容");assert.equal(posts().length,0);check();
  adapter=async c=>{if(c.method==="post"){current=JSON.parse(c.data);return response(c,{id:77});}return response(c,{id:77,...current});};
  await click("确认并创建病例");assert.equal(JSON.parse(posts()[0].data).treatment,"手工治疗");assert.match(output(),/十五项内容一致/);
  await click("新建另一个病例");assert.equal(field("病例名 / 宠物名（必填）").props.value,"");assert(button("核对新建内容"));
});
test("actual homepage transfers exact input to the shared editor without creating a case or AI session",async()=>{
  adapter=async c=>response(c,{items:[],total:0});
  await remount(<MemoryRouter initialEntries={["/"]}><Routes><Route path="/" element={<Home/>}/><Route path="/cases/:id/edit" element={<CaseEditorLite/>}/></Routes></MemoryRouter>);
  for(const [label,value] of [["病例名 / 宠物名","首页合成犬"],["主诉（必填）","首页主诉"],["既往史",values.history]])await act(async()=>field(label).props.onChange({target:{value}}));
  await click("手工新建（核对后保存）");assert.equal(posts().length,0);assert(button("核对新建内容"));
  assert.equal(field("病例名 / 宠物名（必填）").props.value,"首页合成犬");assert.equal(field("既往史 / 动态问诊追问记录").props.value,values.history);
  await click("核对新建内容");assert.equal(posts().length,0);
});

const labels = {patient_name:"病例名 / 宠物名（必填）",species:"物种",sex:"性别",age_info:"年龄信息",breed:"品种 / 宠物信息",weight:"体重",coat_color:"毛色",owner_name:"主人姓名",owner_phone:"主人电话",chief_complaint:"主诉（必填）",history:"既往史 / 动态问诊追问记录",exam_findings:"体检 / 化验 / 来源信息",analysis:"AI 分析",treatment:"治疗建议",prognosis:"风险提示 / 后续随访"};
function NavigationState() { const location=useLocation();return <output data-navigation-state={JSON.stringify(location.state)}/>; }
const editor = seed => <MemoryRouter initialEntries={[{pathname:"/cases/new/edit",state:seed?{manualCase:{owner:"owner",values:seed}}:null}]}><NavigationState/><Routes><Route path="/cases/:id/edit" element={<CaseEditorLite/>}/></Routes></MemoryRouter>;
const fill = async data => {for(const [key,value] of Object.entries(data))await act(async()=>field(labels[key]).props.onChange({target:{value}}));};
const emit = async (name,event={}) => act(async()=>{for(const fn of listeners.get(name)||[])fn(event);});

test("M4 fifteen raw fields survive remount but require explicit restore and fresh review",async()=>{
  await remount(editor());await fill(values);
  assert.equal(requests.length,0);assert.equal(listeners.get("beforeunload").size,1);
  await click("核对新建内容");check();await remount(editor());
  assert.equal(field(labels.history).props.value,"");assert(button("核对新建内容").props.disabled);assert.equal(checkbox(),undefined);
  await click("恢复新建输入");for(const [key,value] of Object.entries(values))assert.equal(field(labels[key]).props.value,value);
  assert.equal(requests.length,0);await click("核对新建内容");assert.equal(checkbox().props.checked,false);assert(button("确认并创建病例").props.disabled);
});
test("M4 restoring long text, zero text, empty fields and literal markup is lossless",async()=>{
  const raw={...values,history:" 未呕吐\n🐾 <script>literal</script> {{history}}\t".repeat(1000),weight:"0",owner_phone:""};
  assert(writeManualCaseDraft("owner",raw));await remount(editor());await click("恢复新建输入");
  for(const [key,value]of Object.entries(raw))assert.equal(field(labels[key]).props.value,value);assert.equal(requests.length,0);
});
test("M4 draft discard clears only unsent input and never creates a case",async()=>{
  writeManualCaseDraft("owner",values);await remount(editor());await click("丢弃新建输入");
  assert.equal(window.sessionStorage.getItem(MANUAL_DRAFT_KEY),null);assert.equal(field(labels.patient_name).props.value,"");assert.equal(requests.length,0);
});
test("M4 route seed conflict requires an explicit choice and supports either source",async()=>{
  for(const [choice,expected]of [["恢复新建输入",values.patient_name],["使用首页带入输入","新的首页输入"]]){
    writeManualCaseDraft("owner",values);await remount(editor({...values,patient_name:"新的首页输入"}));
    assert.equal(field(labels.patient_name).props.value,"");assert.match(output(),/不会自动合并或覆盖/);
    assert.equal(JSON.parse(window.sessionStorage.getItem(MANUAL_DRAFT_KEY)).values.patient_name,values.patient_name);
    await click(choice);assert.equal(field(labels.patient_name).props.value,expected);
    assert.equal(JSON.parse(window.sessionStorage.getItem(MANUAL_DRAFT_KEY)).values.patient_name,expected);
  }
  assert.equal(requests.length,0);
});
test("M4 homepage seed is cached on arrival and removed from navigation state",async()=>{
  await remount(editor(values));assert.equal(JSON.parse(window.sessionStorage.getItem(MANUAL_DRAFT_KEY)).values.history,values.history);
  assert.equal(JSON.parse(renderer.root.findByType("output").props["data-navigation-state"])?.manualCase,undefined);
  await fill({history:"更改后的原文"});
  // The consumed seed is absent from history; a subsequent visit offers only the updated draft.
  await remount(editor());await click("恢复新建输入");assert.equal(field(labels.history).props.value,"更改后的原文");
});
test("M4 expired, future, malformed, unknown and oversized drafts are not offered",async()=>{
  for(const raw of [JSON.stringify({version:1,owner:"owner",updatedAt:Date.now()-MANUAL_DRAFT_MAX_AGE,values}),JSON.stringify({version:1,owner:"owner",updatedAt:Date.now()+120000,values}),"broken",JSON.stringify({version:1,owner:"owner",updatedAt:Date.now(),values:{...values,confirmed:true}}),"x".repeat(252001)]){
    window.sessionStorage.setItem(MANUAL_DRAFT_KEY,raw);await remount(editor());
    assert.equal(button("恢复新建输入"),undefined);assert.equal(field(labels.history).props.value,"");assert.match(output(),/不可读取或已过期/);
  }
  assert.equal(requests.length,0);
});
test("M4 draft expiring while offered cannot restore stale values",async()=>{
  writeManualCaseDraft("owner",values);await remount(editor());
  writeManualCaseDraft("owner",values,window.sessionStorage,Date.now()-MANUAL_DRAFT_MAX_AGE);
  await click("恢复新建输入");assert.equal(field(labels.history).props.value,"");assert(button("核对新建内容").props.disabled);assert.match(output(),/不可读取或已过期/);
});
test("M4 local draft failures warn without presenting an older copy as latest",async()=>{
  await remount(editor());await fill({history:"原值"});
  window.sessionStorage.setItem=()=>{throw Error("quota");};await fill({history:"最新原文"});
  assert.equal(field(labels.history).props.value,"最新原文");assert.equal(window.sessionStorage.getItem(MANUAL_DRAFT_KEY),null);assert.match(output(),/无法暂存最新输入/);assert.equal(requests.length,0);
});
test("M4 an unreadable store does not claim recovery or allow untracked creation",async()=>{
  window.sessionStorage.getItem=()=>{throw Error("denied");};await remount(editor());
  assert.equal(button("恢复新建输入"),undefined);assert.match(output(),/不可读取或已过期/);assert.equal(button("核对新建内容"),undefined);assert.equal(requests.length,0);
});
test("M4 failed discard keeps the offer and leaves server and attempt untouched",async()=>{
  writeManualCaseDraft("owner",values);await remount(editor());window.sessionStorage.removeItem=()=>{throw Error("denied");};
  await click("丢弃新建输入");assert(button("恢复新建输入"));assert(button("核对新建内容").props.disabled);assert(window.sessionStorage.getItem(MANUAL_DRAFT_KEY));assert.equal(requests.length,0);
});
test("M4 another account and an expired login never reveal cached input",async()=>{
  writeManualCaseDraft("owner",values);localStorage.setItem("token",token("other"));await remount(editor());
  assert.equal(field(labels.history).props.value,"");assert.equal(button("恢复新建输入"),undefined);
  writeManualCaseDraft("owner",values);localStorage.removeItem("token");await remount(editor());assert.doesNotMatch(output(),/手工分析|病史🐾/);assert.equal(button("核对新建内容"),undefined);
});
test("M4 storage account switch hides current input and blocks retained field callbacks",async()=>{
  await remount(editor());await fill(values);const change=field(labels.history).props.onChange;
  localStorage.setItem("token",token("other"));await emit("storage",{key:"token"});
  assert.doesNotMatch(output(),/手工分析|病史🐾/);assert.match(output(),/登录账号已变化/);
  await act(async()=>change({target:{value:"错误账号输入"}}));assert.equal(JSON.parse(window.sessionStorage.getItem(MANUAL_DRAFT_KEY)).values.history,values.history);assert.equal(requests.length,0);
});
test("M4 a renewed token still hides unsaved text at its actual expiry",async()=>{
  const now=Math.floor(Date.now()/1000),jwt=exp=>"synthetic."+Buffer.from(JSON.stringify({sub:"owner",exp})).toString("base64url")+".signature";
  localStorage.setItem("token",jwt(now+1));await remount(editor());await fill({patient_name:"短期登录合成输入"});
  localStorage.setItem("token",jwt(now+2));await emit("storage",{key:"token"});
  await act(async()=>{await new Promise(resolve=>setTimeout(resolve,Math.max(0,(now+2)*1000-Date.now()+30)));});
  assert.match(output(),/登录已过期/);assert.doesNotMatch(output(),/短期登录合成输入/);assert.equal(requests.length,0);
});
test("M4 successful readback clears draft and starting another case stays empty",async()=>{
  await remount(editor());await fill(values);await click("核对新建内容");check();await click("确认并创建病例");
  assert.equal(window.sessionStorage.getItem(MANUAL_DRAFT_KEY),null);assert(window.sessionStorage.getItem(key));assert.equal(posts().length,1);
  await click("新建另一个病例");assert.equal(field(labels.history).props.value,"");assert.equal(window.sessionStorage.getItem(key),null);
  await remount(editor());assert.equal(button("恢复新建输入"),undefined);assert.equal(field(labels.history).props.value,"");assert.equal(posts().length,1);
});
test("M4 draft cleanup failure retains verified receipt and prevents a fresh create",async()=>{
  await remount(editor());await fill(values);const remove=window.sessionStorage.removeItem;
  window.sessionStorage.removeItem=k=>{if(k===MANUAL_DRAFT_KEY)throw Error("blocked");remove(k);};
  await click("核对新建内容");check();await click("确认并创建病例");await click("新建另一个病例");
  assert(window.sessionStorage.getItem(key));assert.equal(button("核对新建内容"),undefined);assert.match(output(),/未能清除旧输入/);assert.equal(posts().length,1);
});
test("M4 losing a create response and deleting or expiring input never unlocks the attempt",async()=>{
  await remount(editor());await fill(values);adapter=async()=>{throw Error("lost");};await click("核对新建内容");check();await click("确认并创建病例");
  for(const invalid of ["clear","expire"]){
    if(invalid==="clear")clearManualCaseDraft();else writeManualCaseDraft("owner",values,window.sessionStorage,Date.now()-MANUAL_DRAFT_MAX_AGE);
    await remount(editor());assert(window.sessionStorage.getItem(key));assert.equal(button("恢复新建输入"),undefined);assert.equal(button("核对新建内容"),undefined);assert.equal(posts().length,1);
  }
});
test("M4 failed readback recovery remains GET-only and then removes input draft",async()=>{
  await remount(editor());await fill(values);adapter=async c=>{if(c.method==="get")throw Error("offline");return response(c,{id:77});};
  await click("核对新建内容");check();await click("确认并创建病例");await remount(editor());assert.equal(button("恢复新建输入"),undefined);
  adapter=async c=>response(c,{id:77,...manualCasePayload(values)});await click("核对保存结果");assert.equal(posts().length,1);assert.equal(window.sessionStorage.getItem(MANUAL_DRAFT_KEY),null);
});
test("M4 logout clears new input and no draft flag can forge a confirmed create",async()=>{
  writeManualCaseDraft("owner",values);adapter=async c=>response(c,{items:[],total:0});await remount(<MemoryRouter><Home/></MemoryRouter>);await click("退出");assert.equal(window.sessionStorage.getItem(MANUAL_DRAFT_KEY),null);
  assert.equal(writeManualCaseDraft("owner",{...values,confirmed:true}),false);assert.equal(writeManualCaseDraft("owner",{...values,history:"x".repeat(100001)}),false);
  assert.equal(writeManualCaseDraft("owner",{...values,history:"x".repeat(100000),analysis:"x".repeat(100000),treatment:"x".repeat(100000)}),false);
  assert.equal(readManualCaseDraft(null).draft,null);assert.equal(posts().length,0);
});
