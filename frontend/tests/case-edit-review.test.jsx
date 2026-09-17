import React from "react";
import TestRenderer, { act } from "react-test-renderer";
import { MemoryRouter, Routes, Route, useNavigate } from "react-router-dom";
import { test, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import api from "../src/api";
import CaseEditReview, { caseEditFields } from "../src/components/CaseEditReview";
import CaseEditorLite from "../src/pages/CaseEditorLite";
import { CASE_EDIT_DRAFT_PREFIX, CASE_EDIT_DRAFT_MAX_AGE, readCaseEditDraft, writeCaseEditDraft, clearCaseEditDrafts } from "../src/caseEditDraft";

global.localStorage = { getItem: () => null };
const fields = Object.fromEntries(caseEditFields.map(([key]) => [key, null]));
const before = { ...fields, patient_name: "合成犬", species: "dog", chief_complaint: "医生主诉", history: "  病史🐾\r\n保留尾部空格。  \n", treatment: "原治疗" };
const baseline = { case_id: 7, before, case_token: "a".repeat(64) };
const defer = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };
const response = (config, data) => ({ config, data, status: 200 });
let renderer, requests, adapter, props, verified, reloaded, alerts, sessionStorage, events;
const memory = () => {
  const data = new Map();
  return { get length() { return data.size; }, key: i => [...data.keys()][i] ?? null, getItem: k => data.get(k) ?? null, setItem: (k, v) => data.set(k, String(v)), removeItem: k => data.delete(k) };
};
const loginToken = owner => "synthetic." + Buffer.from(JSON.stringify({ sub: owner, exp: 4102444800 })).toString("base64url") + ".signature";
const draftKey = CASE_EDIT_DRAFT_PREFIX + "7";
const button = name => renderer.root.findAllByType("button").find(n => n.children.join("") === name);
const output = () => JSON.stringify(renderer.toJSON());
const click = async name => { const n = button(name); assert(n, name); assert(!n.props.disabled, name); await act(async () => { await n.props.onClick(); }); };
const checkbox = () => renderer.root.findAllByType("input").find(n => n.props.type === "checkbox");
const check = () => act(() => checkbox().props.onChange({ target: { checked: true } }));
const writes = () => requests.filter(r => r.url.endsWith("/confirm-edit"));
const render = () => <MemoryRouter><CaseEditReview {...props} /></MemoryRouter>;
const revise = change => act(() => { props = { ...props, ...change }; renderer.update(render()); });
function preview(config) {
  const request = JSON.parse(config.data);
  return response(config, { ...baseline, changes: request.changes, proposed: { ...before, ...request.changes }, preview_token: "b".repeat(64) });
}
beforeEach(() => {
  requests = []; verified = []; reloaded = []; alerts = [];
  const storage = new Map();
  global.localStorage = { getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value), removeItem: key => storage.delete(key) };
  global.alert = message => alerts.push(message);
  sessionStorage = memory(); events = new Map();
  global.window = { sessionStorage, addEventListener: (name, fn) => events.set(name, fn), removeEventListener: (name, fn) => { if(events.get(name) === fn) events.delete(name); }, location: { reload() {} } };
  props = { caseId: 7, baseline, changes: { treatment: "  新治疗🐾\r\n " }, onVerified: s => verified.push(s), onReload: s => reloaded.push(s) };
  adapter = async config => config.url.endsWith("/preview-edit") ? preview(config) : response(config, { ...baseline, case_token: "c".repeat(64), before: { ...before, ...props.changes } });
  api.defaults.adapter = async config => { requests.push({ method: config.method, url: config.url, data: config.data }); return adapter(config); };
  act(() => { renderer = TestRenderer.create(render()); });
});
afterEach(() => { act(() => renderer.unmount()); });

test("case edit preview is read-only, requires confirmation and reads all fifteen fields", async () => {
  await click("核对修改内容"); assert.equal(writes().length, 0); assert(button("确认并保存修改").props.disabled);
  check(); await click("确认并保存修改"); assert.equal(writes().length, 1); assert.equal(verified.length, 1);
  assert.deepEqual(JSON.parse(writes()[0].data), { changes: props.changes, expected_case_token: baseline.case_token, expected_preview_token: "b".repeat(64) });
  assert.equal(verified[0].before.history, before.history); assert.match(output(), /15 项病例内容/);
});
test("changed inputs invalidate edit confirmation and discard late previews", async () => {
  await click("核对修改内容"); check(); revise({ changes: { treatment: "修改后" } }); assert.equal(button("确认并保存修改"), undefined);
  const gate = defer(); adapter = async config => { await gate.promise; return preview(config); };
  let inflight; await act(async () => { inflight = button("重新核对修改").props.onClick(); await new Promise(setImmediate); });
  revise({ changes: { treatment: "更晚输入" } }); await act(async () => { gate.resolve(); await inflight; });
  assert.equal(button("确认并保存修改"), undefined); assert.equal(writes().length, 0);
});
test("pending editor confirmation cannot be sent twice", async () => {
  await click("核对修改内容"); check(); const gate = defer();
  adapter = async config => { if(config.method === "post") await gate.promise; return response(config, { ...baseline, before: { ...before, ...props.changes } }); };
  const submit = button("确认并保存修改").props.onClick; let inflight;
  await act(async () => { inflight = submit(); await new Promise(setImmediate); await submit(); }); assert.equal(writes().length, 1);
  await act(async () => { gate.resolve(); await inflight; }); assert.equal(verified.length, 1);
});
test("stale edit is rejected without automatic read or second write", async () => {
  await click("核对修改内容"); check(); adapter = async () => { throw { response: { status: 409 } }; };
  await click("确认并保存修改"); assert.equal(writes().length, 1); assert.equal(requests.filter(r => r.method === "get").length, 0); assert.equal(verified.length, 0);
  assert.match(output(), /原确认失效/); assert(button("读取最新病例并保留本次修改"));
});
test("lost edit response is resolved by GET without another write", async () => {
  await click("核对修改内容"); check(); adapter = async config => { if(config.method === "post") throw Error("response lost"); return response(config, { ...baseline, before: { ...before, ...props.changes } }); };
  await click("确认并保存修改"); assert.equal(writes().length, 1); assert.equal(verified.length, 1);
});
test("failed edit readback keeps preview; retry uses GET only and checks unchanged fields too", async () => {
  await click("核对修改内容"); check(); adapter = async config => { if(config.method === "get") throw Error("GET failed"); return response(config, {}); };
  await click("确认并保存修改"); assert.match(output(), /保存结果待核对/); assert.equal(button("确认并保存修改"), undefined);
  adapter = async config => response(config, { ...baseline, before: { ...before, ...props.changes, history: "另一次更新" } });
  await click("核对保存结果"); assert.equal(verified.length, 0); assert.match(output(), /不一致/);
  adapter = async config => response(config, { ...baseline, before: { ...before, ...props.changes } });
  await click("核对保存结果"); assert.equal(verified.length, 1); assert.equal(writes().length, 1);
});
test("wrong case or proposed values cannot authorize an edit", async () => {
  adapter = async config => response(config, { ...baseline, case_id: 8, proposed: { ...before, ...props.changes }, preview_token: "b".repeat(64) });
  await click("核对修改内容"); assert.equal(button("确认并保存修改"), undefined); assert.equal(writes().length, 0);
});
test("latest case reload is read-only and invalidates previous preview", async () => {
  adapter = async () => { throw { response: { status: 409 } }; }; await click("核对修改内容");
  adapter = async config => response(config, { ...baseline, case_token: "d".repeat(64), before: { ...before, history: "他人新增病史" } });
  await click("读取最新病例并保留本次修改"); assert.equal(reloaded.length, 1); assert.equal(writes().length, 0); assert.equal(button("确认并保存修改"), undefined);
});

async function renderEditor() {
  act(() => renderer.unmount());
  await act(async () => { renderer = TestRenderer.create(<MemoryRouter initialEntries={["/cases/7/edit"]}><Routes><Route path="/cases/:id/edit" element={<CaseEditorLite />} /></Routes></MemoryRouter>); });
}
function field(label) {
  const n=renderer.root.findAllByType("label").find(n => n.findAllByType("div").some(d => d.children.join("") === label));
  return n.findAll(n => ["input","textarea","select"].includes(n.type))[0];
}
test("actual editor sends only changed treatment and preserves untouched raw history and nulls", async () => {
  adapter = async config => config.url.endsWith("/preview-edit") ? preview(config) : response(config, baseline);
  await renderEditor(); await act(async () => field("治疗建议").props.onChange({ target: { value: "  新处理\r\n " } }));
  await click("核对修改内容"); const payload=JSON.parse(requests.at(-1).data);
  assert.deepEqual(payload.changes,{ treatment: "  新处理\r\n " }); assert.equal(field("既往史 / 动态问诊追问记录").props.value,before.history);
  assert.equal(button("保存"),undefined); assert.equal(button("保存并查看详情"),undefined);
});
test("actual editor preserves own changes and adopts untouched server changes after conflict reload", async () => {
  adapter = async config => response(config, baseline); await renderEditor();
  await act(async () => field("治疗建议").props.onChange({ target: { value: "本次治疗" } }));
  adapter = async () => { throw { response: { status: 409 } }; }; await click("核对修改内容");
  adapter = async config => response(config,{...baseline,case_token:"d".repeat(64),before:{...before,history:"另一医生补记"}});
  await click("读取最新病例并保留本次修改"); assert.equal(field("治疗建议").props.value,"本次治疗"); assert.equal(field("既往史 / 动态问诊追问记录").props.value,"另一医生补记"); assert.equal(writes().length,0);
});
test("verified editor shows unsaved changes separately from its saved readback", async () => {
  let saved={...baseline};
  adapter=async config=>{
    if(config.url.endsWith("/preview-edit"))return preview(config);
    if(config.url.endsWith("/confirm-edit")){saved={...baseline,case_token:"c".repeat(64),before:{...before,...JSON.parse(config.data).changes}};}
    return response(config,saved);
  };
  await renderEditor();await act(async()=>field("治疗建议").props.onChange({target:{value:"已核对治疗"}}));
  await click("核对修改内容");check();await click("确认并保存修改");
  assert.doesNotMatch(output(),/当前输入另有修改/);assert.equal(field("治疗建议").props.value,"已核对治疗");
  await act(async()=>field("治疗建议").props.onChange({target:{value:"未保存的新治疗"}}));
  assert.match(output(),/当前输入另有修改/);assert.equal(writes().length,1);
});
test("failed initial editor load cannot fall back to unreviewed writes", async () => {
  adapter = async () => { throw Error("load failure"); }; await renderEditor();
  assert.equal(renderer.root.findByType("fieldset").props.disabled,true); assert.equal(button("核对修改内容"),undefined); assert(button("重新读取病例")); assert.equal(writes().length,0);
});

// Exercise the actual Axios request/response interceptors with controlled response
// ordering. The adapter supplies only a synthetic HTTP failure, not login success.
test("late anonymous 401 cannot erase a token saved by a newer login", async () => {
  const started=defer(),gate=defer();let sent;
  adapter=async config=>{sent=config;started.resolve();await gate.promise;throw {config,response:{status:401}};};
  const outcome=api.get("/api/cases").catch(error=>error);
  await started.promise;assert.equal(sent.headers.get("Authorization"),undefined);
  localStorage.setItem("token","synthetic-new-login");gate.resolve();const error=await outcome;
  assert.equal(error.response.status,401);assert.equal(localStorage.getItem("token"),"synthetic-new-login");assert.deepEqual(alerts,[]);
});
test("late 401 for an old credential cannot clear a newer credential or show expiry", async () => {
  const started=defer(),gate=defer();let sent;
  localStorage.setItem("token","synthetic-old-login");
  adapter=async config=>{sent=config;started.resolve();await gate.promise;throw {config,response:{status:401}};};
  const outcome=api.get("/api/cases/7").catch(error=>error);
  await started.promise;assert.equal(sent.headers.get("Authorization"),"Bearer synthetic-old-login");
  localStorage.setItem("token","synthetic-new-login");gate.resolve();const error=await outcome;
  assert.equal(error.response.status,401);assert.equal(localStorage.getItem("token"),"synthetic-new-login");assert.deepEqual(alerts,[]);
});
test("401 using the current credential still clears it and preserves expiry handling", async () => {
  adapter=async config=>{throw {config,response:{status:401}};};
  for(const url of ["/api/cases/7","/api/cases?page=1"]){
    localStorage.setItem("token","synthetic-current");alerts=[];
    await assert.rejects(api.get(url));assert.equal(localStorage.getItem("token"),null);
    assert.equal(alerts.length,url==="/api/cases/7"?1:0);
  }
});
test("login rejection remains visible to caller without expiring an existing credential", async () => {
  localStorage.setItem("token","synthetic-current");let sent;
  adapter=async config=>{sent=config;throw {config,response:{status:401}};};
  await assert.rejects(api.post("/auth/login",{}));
  assert.equal(sent.headers.get("Authorization"),undefined);assert.equal(localStorage.getItem("token"),"synthetic-current");assert.deepEqual(alerts,[]);
});

test("editor drafts retain exact changed text and remain separate by case", () => {
  const changes={history:"  修改🐾\r\n ",treatment:""};
  assert(writeCaseEditDraft("owner",7,changes,sessionStorage));
  assert(writeCaseEditDraft("owner",8,{treatment:"另一病例"},sessionStorage));
  assert.deepEqual(readCaseEditDraft("owner",7,sessionStorage).draft.changes,changes);
  assert.deepEqual(readCaseEditDraft("owner",8,sessionStorage).draft.changes,{treatment:"另一病例"});
  const raw=JSON.parse(sessionStorage.getItem(draftKey));
  assert.deepEqual(Object.keys(raw).sort(),["caseId","changes","owner","updatedAt","version"]);
  assert.equal(writeCaseEditDraft("owner",7,{...changes,preview_token:"forbidden"},sessionStorage),false);
  assert.equal(readCaseEditDraft("owner",7,sessionStorage).draft,null);
  assert(readCaseEditDraft("owner",8,sessionStorage).draft);
});
test("editor drafts reject a different account, expiry, corruption and a mismatched case", () => {
  writeCaseEditDraft("owner",7,{history:"私有草稿"},sessionStorage);
  assert.equal(readCaseEditDraft("other",7,sessionStorage).draft,null);assert.equal(sessionStorage.getItem(draftKey),null);
  writeCaseEditDraft("owner",7,{history:"旧草稿"},sessionStorage,1000);
  assert.equal(readCaseEditDraft("owner",7,sessionStorage,1001+CASE_EDIT_DRAFT_MAX_AGE).draft,null);
  for(const raw of ["{broken",JSON.stringify({version:1,owner:"owner",caseId:8,updatedAt:Date.now(),changes:{history:"错误病例"}}),JSON.stringify({version:1,owner:"owner",caseId:7,updatedAt:Date.now(),changes:{history:4}})]){
    sessionStorage.setItem(draftKey,raw);const result=readCaseEditDraft("owner",7,sessionStorage);assert.equal(result.draft,null);assert(result.error);assert.equal(sessionStorage.getItem(draftKey),null);
  }
});
test("editor quota failure removes stale copies and account cleanup leaves unrelated storage", () => {
  writeCaseEditDraft("owner",7,{history:"旧输入"},sessionStorage);
  sessionStorage.setItem=()=>{throw Error("quota");};
  assert.equal(writeCaseEditDraft("owner",7,{history:"新输入"},sessionStorage),false);assert.equal(sessionStorage.getItem(draftKey),null);
  const storage=memory();writeCaseEditDraft("owner",7,{history:"七"},storage);writeCaseEditDraft("owner",8,{history:"八"},storage);storage.setItem("unrelated","keep");
  assert(clearCaseEditDrafts(storage));assert.equal(storage.length,1);assert.equal(storage.getItem("unrelated"),"keep");
});
async function mountDraftEditor(changes) {
  localStorage.setItem("token",loginToken("owner"));
  if(changes)writeCaseEditDraft("owner",7,changes,sessionStorage);
  adapter=async config=>response(config,baseline);await renderEditor();
}
test("actual editor immediately caches changed fields including explicit clearing", async () => {
  await mountDraftEditor();
  await act(async()=>field("治疗建议").props.onChange({target:{value:""}}));
  assert.deepEqual(readCaseEditDraft("owner",7,sessionStorage).draft.changes,{treatment:""});
  await act(async()=>field("既往史 / 动态问诊追问记录").props.onChange({target:{value:"  输入🐾\r\n "}}));
  assert.deepEqual(readCaseEditDraft("owner",7,sessionStorage).draft.changes,{history:"  输入🐾\r\n ",treatment:""});
  assert.equal(requests.filter(r=>r.method!=="get").length,0);
});
test("editor refresh recovery fetches fresh state, preserves untouched fields and restores no confirmation", async () => {
  await mountDraftEditor({treatment:"恢复治疗"});
  assert(renderer.root.findByType("fieldset").props.disabled);assert.equal(button("核对修改内容"),undefined);
  const initial=sessionStorage.getItem(draftKey);
  assert.equal(field("治疗建议").props.value,"原治疗");assert.equal(sessionStorage.getItem(draftKey),initial);
  const fresh={...baseline,case_token:"e".repeat(64),before:{...before,history:"服务器新增病史"}};
  adapter=async config=>response(config,fresh);const gets=requests.length;
  await click("恢复本病例编辑草稿");assert.equal(requests.length,gets+1);assert.equal(requests.at(-1).method,"get");
  assert.equal(field("治疗建议").props.value,"恢复治疗");assert.equal(field("既往史 / 动态问诊追问记录").props.value,"服务器新增病史");
  assert.equal(button("确认并保存修改"),undefined);assert(button("核对修改内容"));assert.equal(writes().length,0);
});
test("failed or wrong-case editor recovery keeps the offer and draft for a read-only retry", async () => {
  await mountDraftEditor({treatment:"不能丢失"});const raw=sessionStorage.getItem(draftKey);
  adapter=async()=>{throw Error("offline");};await click("恢复本病例编辑草稿");
  assert(button("恢复本病例编辑草稿"));assert.equal(sessionStorage.getItem(draftKey),raw);
  adapter=async config=>response(config,{...baseline,case_id:8});await click("恢复本病例编辑草稿");assert(button("恢复本病例编辑草稿"));
  adapter=async config=>response(config,baseline);await click("恢复本病例编辑草稿");
  assert.equal(field("治疗建议").props.value,"不能丢失");assert.equal(writes().length,0);
});
test("editor refresh after a committed save recognizes matching server fields without another POST", async () => {
  await mountDraftEditor({treatment:"实际已保存"});
  adapter=async config=>response(config,{...baseline,before:{...before,treatment:"实际已保存",history:"保存后别人补记"}});
  await click("恢复本病例编辑草稿");assert.equal(sessionStorage.getItem(draftKey),null);assert.equal(writes().length,0);
  assert.equal(field("治疗建议").props.value,"实际已保存");assert.equal(field("既往史 / 动态问诊追问记录").props.value,"保存后别人补记");
  assert(button("核对修改内容").props.disabled);assert.match(output(),/草稿中的修改与服务器一致/);
});
test("verified editor save clears its draft and a later edit creates a new draft", async () => {
  await mountDraftEditor();let saved=baseline;
  adapter=async config=>{
    if(config.url.endsWith("/preview-edit"))return preview(config);
    if(config.url.endsWith("/confirm-edit"))saved={...baseline,before:{...before,...JSON.parse(config.data).changes}};
    return response(config,saved);
  };
  await act(async()=>field("治疗建议").props.onChange({target:{value:"核对后保存"}}));assert(sessionStorage.getItem(draftKey));
  await click("核对修改内容");check();await click("确认并保存修改");assert.equal(sessionStorage.getItem(draftKey),null);
  await act(async()=>field("治疗建议").props.onChange({target:{value:"保存后的新输入"}}));
  assert.deepEqual(readCaseEditDraft("owner",7,sessionStorage).draft.changes,{treatment:"保存后的新输入"});assert.equal(writes().length,1);
});
test("editor discard removes only the offered case draft without a server write", async () => {
  await mountDraftEditor({treatment:"丢弃输入"});writeCaseEditDraft("owner",8,{history:"保留另例"},sessionStorage);
  await click("丢弃编辑草稿");assert.equal(sessionStorage.getItem(draftKey),null);assert(readCaseEditDraft("owner",8,sessionStorage).draft);
  assert.equal(field("治疗建议").props.value,"原治疗");assert.equal(writes().length,0);assert(button("核对修改内容").props.disabled);
});
test("editor storage failure keeps current input and warns instead of claiming a draft exists", async () => {
  await mountDraftEditor();await act(async()=>field("治疗建议").props.onChange({target:{value:"旧输入"}}));
  sessionStorage.setItem=()=>{throw Error("quota");};
  await act(async()=>field("治疗建议").props.onChange({target:{value:"最新输入"}}));
  assert.equal(field("治疗建议").props.value,"最新输入");assert.equal(sessionStorage.getItem(draftKey),null);assert.match(output(),/浏览器无法暂存最新修改/);
});
test("editor recovery cannot apply a late response after account identity changes", async () => {
  await mountDraftEditor({treatment:"旧账号输入"});const gate=defer();adapter=async config=>{await gate.promise;return response(config,baseline);};
  let pending;await act(async()=>{pending=button("恢复本病例编辑草稿").props.onClick();await new Promise(setImmediate);});
  localStorage.setItem("token",loginToken("other"));await act(async()=>{gate.resolve();await pending;});
  assert.equal(field("治疗建议").props.value,"原治疗");assert(renderer.root.findByType("fieldset").props.disabled);assert.equal(button("核对修改内容"),undefined);
  let reloads=0;window.location.reload=()=>reloads++;act(()=>events.get("storage")({key:"token"}));assert.equal(sessionStorage.getItem(draftKey),null);assert.equal(reloads,1);
});
test("editor unload protection follows unsaved input and disappears when input is reverted", async () => {
  await mountDraftEditor();assert.equal(events.has("beforeunload"),false);
  await act(async()=>field("治疗建议").props.onChange({target:{value:"未保存"}}));assert(events.has("beforeunload"));
  let warned=false;const event={preventDefault(){warned=true;}};events.get("beforeunload")(event);assert(warned);assert.equal(event.returnValue,"");
  await act(async()=>field("治疗建议").props.onChange({target:{value:"原治疗"}}));assert.equal(events.has("beforeunload"),false);assert.equal(sessionStorage.getItem(draftKey),null);
});
test("unmount during editor recovery keeps the draft and ignores the late response", async () => {
  await mountDraftEditor({treatment:"稍后恢复"});const gate=defer();adapter=async config=>{await gate.promise;return response(config,baseline);};
  let pending;await act(async()=>{pending=button("恢复本病例编辑草稿").props.onClick();await new Promise(setImmediate);});
  act(()=>renderer.unmount());await act(async()=>{gate.resolve();await pending;});
  assert.deepEqual(readCaseEditDraft("owner",7,sessionStorage).draft.changes,{treatment:"稍后恢复"});assert.equal(writes().length,0);
});

test("SPA case navigation cannot reuse another case form, draft offer or confirmation", async () => {
  localStorage.setItem("token",loginToken("owner"));let navigate;
  function Host(){navigate=useNavigate();return <CaseEditorLite/>;}
  adapter=async config=>response(config,config.url.includes('/8/')?{...baseline,case_id:8,before:{...before,treatment:"病例八原治疗"}}:baseline);
  act(()=>renderer.unmount());
  await act(async()=>{renderer=TestRenderer.create(<MemoryRouter initialEntries={["/cases/7/edit"]}><Routes><Route path="/cases/:id/edit" element={<Host/>}/></Routes></MemoryRouter>);});
  await act(async()=>field("治疗建议").props.onChange({target:{value:"病例七新输入"}}));
  await act(async()=>navigate("/cases/8/edit"));assert.equal(field("治疗建议").props.value,"病例八原治疗");assert.equal(button("恢复本病例编辑草稿"),undefined);
  await act(async()=>navigate("/cases/7/edit"));assert(button("恢复本病例编辑草稿"));await click("恢复本病例编辑草稿");
  assert.equal(field("治疗建议").props.value,"病例七新输入");assert.equal(button("确认并保存修改"),undefined);assert.equal(writes().length,0);
});
test("an initial editor read failure cannot overwrite a cached draft before recovery", async () => {
  localStorage.setItem("token",loginToken("owner"));writeCaseEditDraft("owner",7,{history:"初始读取失败仍保留"},sessionStorage);const raw=sessionStorage.getItem(draftKey);
  adapter=async()=>{throw Error("initial offline");};await renderEditor();assert.equal(sessionStorage.getItem(draftKey),raw);assert(button("恢复本病例编辑草稿"));assert(renderer.root.findByType("fieldset").props.disabled);
  adapter=async config=>response(config,baseline);await click("恢复本病例编辑草稿");assert.equal(field("既往史 / 动态问诊追问记录").props.value,"初始读取失败仍保留");assert.equal(writes().length,0);
});
