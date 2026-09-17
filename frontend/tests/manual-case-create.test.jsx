import React from "react";
import TestRenderer, { act } from "react-test-renderer";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { test, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import api from "../src/api";
import ManualCaseCreateReview, { manualCasePayload } from "../src/components/ManualCaseCreateReview";
import CaseEditorLite from "../src/pages/CaseEditorLite";
import { Home } from "../src/App";

const key = "pmai.manual-create-attempt.v1";
const memory = () => { const map = new Map(); return { getItem:k=>map.get(k)??null,setItem:(k,v)=>map.set(k,String(v)),removeItem:k=>map.delete(k),get length(){return map.size;},key:i=>[...map.keys()][i]??null }; };
const token = owner => "synthetic." + Buffer.from(JSON.stringify({sub:owner,exp:4102444800})).toString("base64url") + ".signature";
const values = {patient_name:"合成犬",species:"dog",sex:"M",age_info:"2y",breed:"虚构",weight:"5.2kg",coat_color:"",owner_name:"虚构主人",owner_phone:"",chief_complaint:"  合成主诉\r\n ",history:"  病史🐾\r\n\t ",exam_findings:"合成检查",analysis:"手工分析",treatment:"手工处理",prognosis:"随访 <script>literal</script>"};
const response = (config,data) => ({config,data,status:config.method==="post"?201:200});
const defer = () => {let resolve; const promise=new Promise(r=>resolve=r);return {promise,resolve};};
let renderer,requests,adapter,current,locked;
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
  global.window={sessionStorage:memory(),addEventListener(){},removeEventListener(){},location:{reload(){}}};
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
