import React from "react";
import TestRenderer, { act } from "react-test-renderer";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { test, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import api from "../src/api";
import CaseEditReview, { caseEditFields } from "../src/components/CaseEditReview";
import CaseEditorLite from "../src/pages/CaseEditorLite";

global.localStorage = { getItem: () => null };
const fields = Object.fromEntries(caseEditFields.map(([key]) => [key, null]));
const before = { ...fields, patient_name: "合成犬", species: "dog", chief_complaint: "医生主诉", history: "  病史🐾\r\n保留尾部空格。  \n", treatment: "原治疗" };
const baseline = { case_id: 7, before, case_token: "a".repeat(64) };
const defer = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };
const response = (config, data) => ({ config, data, status: 200 });
let renderer, requests, adapter, props, verified, reloaded, alerts;
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
