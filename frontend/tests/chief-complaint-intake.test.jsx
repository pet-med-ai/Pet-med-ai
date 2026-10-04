import React, { useState } from "react";
import TestRenderer, { act } from "react-test-renderer";
import { MemoryRouter, Routes, Route, useLocation } from "react-router-dom";
import { test, describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import api from "../src/api";
import DiarrheaIntake from "../src/components/DiarrheaIntake";
import { Home } from "../src/App";
import { cleanIntakeDraft as cleanDiarrheaDraft, intakeReviewed as diarrheaReviewed, appendIntakeHistory as appendDiarrheaHistory } from "../src/chiefComplaintIntakeState";
import { DRAFT_KEY, cleanDraft, writeDraft, readDraft } from "../src/consultDraft";
import { readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";
const templates = ["appetite_weight", "polyuria_polydipsia", "cough_breathing"].map(k => {
  const rel = "knowledge-base/companion/intake/"+k+".json";
  return [resolve(rel),resolve("..",rel)].find(existsSync);
}).filter(Boolean).map(p=>JSON.parse(readFileSync(p,"utf8")));
assert(templates.length);

for (const config of templates) describe(config.key, () => {
const title=config.label.replace(/^犬猫/, "").replace(/问诊$/, "");
const memory = () => { const m = new Map(); return { getItem: k => m.get(k) ?? null, setItem: (k,v) => m.set(k,String(v)), removeItem: k => m.delete(k) }; };
const token = owner => "synthetic."+Buffer.from(JSON.stringify({sub:owner,exp:4102444800})).toString("base64url")+".signature";
const template = species => ({ ...config, species, fingerprint: "a".repeat(64) });
const ctx = { owner: "owner", patientName: "合成犬", species: "dog", sessionId: null, intakeKey: config.key };
const response = (config, data) => ({ config, status: 200, data });
const defer = () => { let resolve; const promise = new Promise(r => resolve=r); return {promise, resolve}; };
let renderer, raw, reviewed, context, requests, adapter, archived, destination, listeners;
function Harness() {
  const [d, setD] = useState(raw), [r, setR] = useState(null); raw=d; reviewed=r;
  return <DiarrheaIntake intakeKey={config.key} draft={d} review={r} context={context} disabled={false} onChange={setD} onReview={setR} onArchive={x=>archived.push(x)} />;
}
const out = () => JSON.stringify(renderer.toJSON());
const button = name => renderer.root.findAllByType("button").find(n=>n.children.join("")===name);
const click = async name => { const b=button(name); assert(b,name); assert(!b.props.disabled,name); await act(async()=>{ await b.props.onClick(); }); };
const change = async (key, type, value) => {
  const row=renderer.root.findAll(n=>n.props["data-intake-question"]===key)[0];
  await act(async()=>row.findByType(type).props.onChange({target:{value}}));
};
const texts=config.questions.filter(q=>q.kind==="text"&&!q.when&&!["onset","notes"].includes(q.key));
const branch=config.questions.find(q=>q.when);
const confirm = async () => { await click(`核对${title}问卷汇总`); await click(`确认当前${title}问卷`); };
const remount = async element => { act(()=>renderer.unmount()); await act(async()=>{renderer=TestRenderer.create(element||<Harness/>);}); };
beforeEach(async()=>{
  global.localStorage=memory(); localStorage.setItem("token",token("owner"));
  listeners=new Map(); global.window={sessionStorage:memory(),location:{reload(){}},addEventListener(k,f){if(!listeners.has(k))listeners.set(k,new Set());listeners.get(k).add(f);},removeEventListener(k,f){listeners.get(k)?.delete(f);}};
  global.alert=()=>{}; global.confirm=()=>true;
  context={...ctx}; raw=null; reviewed=null; requests=[]; archived=[]; destination=null;
  adapter=async c=>{
    if(c.url.includes("intake/"+config.key) && c.method==="get") return response(c,template(c.params.species));
    if(c.url.endsWith("intake/"+config.key+"/preview")) {
      const input=JSON.parse(c.data); return response(c,{snapshot:{version:input.version+"+"+input.fingerprint,template_key:input.species},history_block:"医生采集 · 临床草稿\n"+Object.entries(input.answers).map(([k,a])=>k+"："+a.state+"\n"+a.text).join("\n")});
    }
    return response(c,{items:[],total:0});
  };
  api.defaults.adapter=async c=>{requests.push({method:c.method,url:c.url,data:c.data});return adapter(c);};
  await act(async()=>{renderer=TestRenderer.create(<Harness/>);});
});
afterEach(()=>act(()=>renderer.unmount()));

test("B1 explicit start and missing states do not synthesize absence or zero",async()=>{
  assert.equal(raw,null); assert.equal(requests.length,0); await click(`开始${title}问诊`);
  assert.equal(raw.template.species,"dog"); assert(Object.values(raw.answers).every(a=>a.state==="unfilled"&&a.text===""));
  assert.equal(renderer.root.findAllByType("select").length,config.questions.length); assert.equal(reviewed,null);
  const onset=renderer.root.findAll(n=>n.props["data-intake-question"]==="onset")[0];
  assert(!onset.findAllByType("option").some(n=>n.props.value==="absent"));
});
test("B1 all states and original Unicode remain distinct; inactive branch is read-only",async()=>{
  await click(`开始${title}问诊`); await change(branch.when,"select","observed");
  const original="  不是确诊🐾\r\n<5 & {{literal}}\t尾部  \n";
  await change(branch.key,"select","observed"); await change(branch.key,"textarea",original);
  await change(branch.when,"select","absent");
  assert.equal(raw.answers[branch.key].text,original);
  assert(renderer.root.findAll(n=>n.props["data-intake-question"]===branch.key)[0].findByType("textarea").props.readOnly);
  for(const state of ["not_asked","uncertain","unobservable","unfilled"]) { await change(texts[0].key,"select",state); assert.equal(raw.answers[texts[0].key].state,state); }
  await confirm(); assert(diarrheaReviewed(raw,reviewed,context)); assert(reviewed.historyBlock.includes(original));
});
test("B1 any text or branch edit invalidates review before another save",async()=>{
  await click(`开始${title}问诊`); await confirm(); assert(reviewed);
  await change("notes","textarea","医生补充"); assert.equal(reviewed,null); assert.equal(button(`确认当前${title}问卷`),undefined);
  await confirm(); await change(texts[0].key,"select","observed"); assert.equal(reviewed,null);
});
test("B1 changing animal, species or session retains old raw and refuses application",async()=>{
  await click(`开始${title}问诊`); await change("notes","textarea","原犬问卷"); await confirm();
  for(const changed of [{patientName:"另一只犬"},{species:"cat"},{sessionId:"another"}]) {
    context={...ctx,...changed}; await act(async()=>renderer.update(<Harness/>));
    assert.equal(reviewed,null); assert.equal(raw.answers.notes.text,"原犬问卷");
    assert(button(`核对${title}问卷汇总`).props.disabled); assert.match(out(),/只读|旧确认已失效/);
  }
  await click(`为当前病例开始${title}问卷`); assert.equal(archived.length,1); assert(archived[0].includes("原犬问卷")); assert.equal(raw.answers.notes.text,"");
});
test("B1 stale template preserves input and refreshed template archives previous raw",async()=>{
  await click(`开始${title}问诊`); await change("notes","textarea","旧版本原文");
  const originalAdapter=adapter; adapter=async c=>{if(c.method==="post")throw {response:{status:409,data:{detail:"模板已变化，请重新核对"}}};return originalAdapter(c);};
  await click(`核对${title}问卷汇总`); assert.match(out(),/模板已变化/); assert.equal(raw.answers.notes.text,"旧版本原文"); assert.equal(reviewed,null);
  adapter=async c=>response(c,{...template("dog"),version:`${config.key}-intake-v2`,fingerprint:"b".repeat(64)});
  await click(`重新读取${title}模板`); assert.equal(archived.length,1); assert(archived[0].includes("旧版本原文")); assert.equal(raw.template.version,`${config.key}-intake-v2`); assert.equal(reviewed,null);
});
test("B1 a late preview for another consultation cannot restore confirmation",async()=>{
  await click(`开始${title}问诊`); const gate=defer(), original=adapter;
  adapter=async c=>{await gate.promise;return original(c);}; let pending;
  await act(async()=>{pending=button(`核对${title}问卷汇总`).props.onClick();});
  context={...ctx,sessionId:"other"}; await act(async()=>renderer.update(<Harness/>));
  await act(async()=>{gate.resolve();await pending;}); assert.equal(button(`确认当前${title}问卷`),undefined); assert.equal(reviewed,null);
});
test("B1 account change hides raw and rejects retained callbacks before dispatch",async()=>{
  await click(`开始${title}问诊`); await change("notes","textarea","前账号私有原文");
  const summarize=button(`核对${title}问卷汇总`).props.onClick, before=requests.length;
  localStorage.setItem("token",token("other"));
  await act(async()=>{for(const f of listeners.get("storage")||[])f({key:"token"});});
  assert.doesNotMatch(out(),/前账号私有原文/); await act(async()=>summarize()); assert.equal(requests.length,before);
});
test("B1 manual history joining keeps original and avoids duplicate whole blocks",()=>{
  const original="  医生病史🐾\r\n  ", block="医生采集\n否认便血";
  const combined=appendDiarrheaHistory(original,block); assert(combined.startsWith(original)); assert.equal(appendDiarrheaHistory(combined,block),combined);
});

function Destination(){destination=useLocation().state;return <p>手工病例核对入口</p>;}
const home=()=> <MemoryRouter><Routes><Route path="/" element={<Home/>}/><Route path="/cases/new/edit" element={<Destination/>}/></Routes></MemoryRouter>;
const homeField=label=>renderer.root.findAllByType("label").find(n=>n.findAllByType("div").some(d=>d.children.join("")===label)).findAll(n=>["input","select","textarea"].includes(n.type))[0];
test("B1 AI failure preserves confirmed raw and passes history to existing manual path",async()=>{
  await remount(home()); await act(async()=>renderer.root.findByProps({"aria-label":"选择主诉问诊"}).props.onChange({target:{value:config.key}}));
  await act(async()=>{homeField("病例名 / 宠物名").props.onChange({target:{value:"M7合成犬"}});homeField("主诉（必填）").props.onChange({target:{value:"原主诉"}});homeField("既往史").props.onChange({target:{value:"  原病史🐾\n  "}});});
  await click(`使用犬猫${title}问诊`); await click(`开始${title}问诊`); await change("notes","textarea","原问卷🐾\n尾部  "); await confirm();
  const original=adapter; adapter=async c=>{if(c.url==="/api/ai/consult/session")throw Error("synthetic AI failure");return original(c);};
  await act(async()=>renderer.root.findAllByType("form").find(f=>f.findAllByType("textarea").length===3).props.onSubmit({preventDefault(){}}));
  assert.match(out(),/分析请求失败/); assert(out().includes("原问卷🐾"));
  await click("手工新建（核对后保存）"); assert.equal(destination,null);
  await confirm(); await click("手工新建（核对后保存）");
  assert.equal(destination.manualCase.owner,"owner"); assert.equal(destination.manualCase.values.chief_complaint,"原主诉");
  assert(destination.manualCase.values.history.startsWith("  原病史🐾\n  ")); assert(destination.manualCase.values.history.includes("原问卷🐾\n尾部  "));
  assert.equal(requests.filter(r=>r.url==="/api/cases"&&r.method==="post").length,0);
});
test("B1 refresh restores questionnaire input but not its confirmation",async()=>{
  await remount(home()); await act(async()=>renderer.root.findByProps({"aria-label":"选择主诉问诊"}).props.onChange({target:{value:config.key}})); await click(`使用犬猫${title}问诊`); await click(`开始${title}问诊`); await change("notes","textarea","待恢复🐾"); await confirm();
  const saved=JSON.parse(window.sessionStorage.getItem(DRAFT_KEY)); assert.equal(saved.data.chiefComplaint.answers.notes.text,"待恢复🐾"); assert(!saved.data.chiefComplaint.review);
  await remount(home()); await act(async()=>renderer.root.findByProps({"aria-label":"选择主诉问诊"}).props.onChange({target:{value:config.key}})); await click("恢复本页草稿"); assert(out().includes("待恢复🐾")); assert.doesNotMatch(out(),new RegExp("当前"+title+"问卷已核对"));
  assert(button(`核对${title}问卷汇总`));
});

test("B1 chief complaint switch invalidates confirmation and keeps the old raw",async()=>{
  await remount(home());
  const choose=async key=>act(async()=>renderer.root.findByProps({"aria-label":"选择主诉问诊"}).props.onChange({target:{value:key}}));
  await choose(config.key);await click(`使用犬猫${title}问诊`);await click(`开始${title}问诊`);await change("notes","textarea","原主诉独立原文🐾");await confirm();
  await choose("diarrhea");
  assert(out().includes("原主诉独立原文🐾"));assert(button("核对腹泻问卷汇总").props.disabled);
  assert.equal(button("确认当前腹泻问卷"),undefined);
  await choose(config.key);assert(out().includes("原主诉独立原文🐾"));assert.equal(button(`确认当前${title}问卷`),undefined);
  await confirm();await click("收起问卷并保留输入");assert.equal(button(`核对${title}问卷汇总`),undefined);
  await click(`使用犬猫${title}问诊`);assert(out().includes("原主诉独立原文🐾"));assert.equal(button(`确认当前${title}问卷`),undefined);
});
test("B1 cross-family and cross-owner drafts are rejected without restoring review",async()=>{
  await click(`开始${title}问诊`);await confirm();
  assert(!diarrheaReviewed(raw,reviewed,{...context,intakeKey:"diarrhea"}));
  assert.throws(()=>cleanDiarrheaDraft({...raw,binding:{...raw.binding,intakeKey:"diarrhea"}}));
  const base={fields:{},sessionId:null,followupAnswer:"",sessionContext:"",structuredAnswers:{},recoveredNotes:"",chiefComplaint:raw};
  assert.equal(writeDraft("other",base,window.sessionStorage),false);
  assert.equal(writeDraft("owner",base,window.sessionStorage),true);
  const restored=readDraft("owner",window.sessionStorage).draft.data.chiefComplaint;
  assert.deepEqual(restored,raw);assert(!restored.review);
  assert.equal(readDraft("other",window.sessionStorage).draft,null);
});

});
