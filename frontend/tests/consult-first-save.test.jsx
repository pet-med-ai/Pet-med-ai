import React from "react";
import TestRenderer, { act } from "react-test-renderer";
import { MemoryRouter } from "react-router-dom";
import { test, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import api from "../src/api";
import ConsultSaveReview from "../src/components/ConsultSaveReview";

global.localStorage = { getItem: () => null };
let renderer, requests, adapter, props, receipts, boundCalls;
const input = { patient_name: "合成犬", species: "dog", sex: "M", age_info: "4岁", breed: "合成品种", weight: "5kg", coat_color: "白", owner_name: "合成主人", owner_phone: "合成电话", chief_complaint: "最新主诉", history: "医生补充🐾\r\n保留原文。  ", exam_findings: "合成体检" };
const preview = { ...input, session_id: "synthetic", case_id: null, history: input.history + "\n\n合成问诊记录", analysis: "AI 分析", treatment: "合成建议", prognosis: "合成风险", preview_token: "a".repeat(64) };
const saved = { ...preview, id: 7 };
const response = (config, data) => ({ config, data, status: 200 });
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };
const nodes = () => renderer.root.findAllByType("button");
const button = label => nodes().find(n => n.children.join("") === label);
const checkbox = () => renderer.root.findByType("input");
const output = () => JSON.stringify(renderer.toJSON());
const click = async label => { const node = button(label); assert.ok(node, label); assert.ok(!node.props.disabled, label); await act(async () => { await node.props.onClick(); }); };
const check = () => act(() => checkbox().props.onChange({ target: { checked: true } }));
const tree = () => <MemoryRouter><ConsultSaveReview {...props} /></MemoryRouter>;
const revise = values => act(() => { props = { ...props, ...values }; renderer.update(tree()); });
const writes = () => requests.filter(r => r.url.endsWith("/save-case"));
const normal = config => response(config, config.url.endsWith("/preview-case") ? preview : config.url.endsWith("/save-case") ? { case_id: 7, message: "saved" } : config.url === "/api/cases/7" ? saved : { session_id: "synthetic", case_id: 7 });

beforeEach(() => {
  requests = []; receipts = []; boundCalls = []; adapter = async config => normal(config);
  api.defaults.adapter = async config => { requests.push({ method: config.method, url: config.url, data: config.data }); return adapter(config); };
  props = { sessionId: "synthetic", payload: { ...input }, revision: 0, allowed: true, blocked: false, hasPendingAnswers: false, onSaved: (record, receipt) => receipts.push({ record, receipt }), onBound: id => boundCalls.push(id) };
  act(() => { renderer = TestRenderer.create(tree()); });
});
afterEach(() => { act(() => renderer.unmount()); });

test("first save requires review and reads session binding plus all case fields", async () => {
  await click("核对保存内容");
  assert.equal(writes().length, 0);
  assert.equal(button("确认并保存病例").props.disabled, true);
  assert.ok(output().includes("医生补充"));
  check(); await click("确认并保存病例");
  assert.equal(writes().length, 1);
  assert.deepEqual(JSON.parse(writes()[0].data), { ...input, expected_preview_token: preview.preview_token });
  assert.deepEqual(requests.slice(-2).map(r => r.url), ["/api/ai/consult/session/synthetic", "/api/cases/7"]);
  assert.equal(receipts.length, 1);
  assert.equal(receipts[0].receipt.inputsChanged, false);
  assert.ok(output().includes("保存内容一致"));
  assert.equal(button("确认并保存病例"), undefined);
});

test("changing payload alone invalidates checked preview and preserves edits on cancel", async () => {
  await click("核对保存内容"); check();
  revise({ payload: { ...input, history: "新的医生补记" } });
  assert.ok(output().includes("原确认失效"));
  assert.equal(button("确认并保存病例"), undefined);
  await click("重新预览保存内容");
  assert.equal(JSON.parse(requests.at(-1).data).history, "新的医生补记");
  assert.equal(checkbox().props.checked, false);
  await click("返回修改");
  assert.equal(props.payload.history, "新的医生补记");
  assert.equal(writes().length, 0);
});

test("late preview cannot authorize inputs edited while it was loading", async () => {
  const gate = deferred(); adapter = async config => { await gate.promise; return normal(config); };
  let pending;
  await act(async () => { pending = button("核对保存内容").props.onClick(); await new Promise(setImmediate); });
  revise({ payload: { ...input, weight: "新的体重" } });
  await act(async () => { gate.resolve(); await pending; });
  assert.equal(button("确认并保存病例"), undefined);
  assert.ok(output().includes("内容已修改"));
});

test("double click makes one POST and edits during saving are explicitly unsaved", async () => {
  await click("核对保存内容"); check();
  const gate = deferred(); adapter = async config => { if (config.url.endsWith("/save-case")) await gate.promise; return normal(config); };
  const submit = button("确认并保存病例").props.onClick;
  let pending;
  await act(async () => { pending = submit(); await new Promise(setImmediate); await submit(); });
  assert.equal(writes().length, 1);
  assert.ok(output().includes("正在保存"));
  revise({ payload: { ...input, history: "保存期间新写的内容" } });
  await act(async () => { gate.resolve(); await pending; });
  assert.equal(receipts[0].receipt.inputsChanged, true);
  assert.ok(output().includes("这些修改尚未保存"));
  assert.equal(props.payload.history, "保存期间新写的内容");
});

test("lost save response resolves through session binding without a duplicate POST", async () => {
  await click("核对保存内容"); check();
  adapter = async config => { if (config.url.endsWith("/save-case")) throw new Error("Lost save response"); return normal(config); };
  await click("确认并保存病例");
  assert.equal(writes().length, 1);
  assert.equal(receipts.length, 1);
  assert.equal(receipts[0].record.id, 7);
});

test("unknown binding or failed GET keeps preview and recovery performs reads only", async () => {
  await click("核对保存内容"); check();
  adapter = async config => config.url.endsWith("/session/synthetic") ? response(config, { session_id: "synthetic", case_id: null }) : normal(config);
  await click("确认并保存病例");
  assert.ok(output().includes("暂未查到已绑定病例"));
  assert.equal(receipts.length, 0);
  adapter = async config => { throw new Error("Disconnected"); };
  await click("核对保存结果");
  assert.ok(output().includes("保存结果待核对"));
  assert.ok(output().includes("医生补充"));
  adapter = async config => normal(config);
  await click("核对保存结果");
  assert.equal(writes().length, 1);
  assert.equal(receipts.length, 1);
});

test("a field mismatch cannot claim success or create another case", async () => {
  await click("核对保存内容"); check();
  adapter = async config => config.url === "/api/cases/7" ? response(config, { ...saved, owner_phone: "不同的主人电话" }) : normal(config);
  await click("确认并保存病例");
  assert.equal(receipts.length, 0);
  assert.ok(output().includes("当前病例与核对内容不一致"));
  assert.equal(button("确认并保存病例"), undefined);
  assert.equal(button("重新预览保存内容"), undefined);
  await click("进入已绑定病例更新核对");
  assert.deepEqual(boundCalls, [7]);
  assert.equal(writes().length, 1);
});

test("preview of an already saved session reads the case without any save POST", async () => {
  adapter = async config => config.url.endsWith("/preview-case") ? response(config, { ...preview, case_id: 7 }) : normal(config);
  await click("核对保存内容");
  assert.equal(writes().length, 0);
  assert.equal(receipts.length, 1);
});

test("409 expires confirmation and requires a new preview", async () => {
  await click("核对保存内容"); check();
  adapter = async () => { throw { response: { status: 409 } }; };
  await click("确认并保存病例");
  assert.ok(output().includes("原确认已失效"));
  assert.equal(button("确认并保存病例"), undefined);
  assert.equal(requests.filter(r => r.method === "get").length, 0);
});

test("review changes and unsubmitted answers block first save and reset checkbox", async () => {
  await click("核对保存内容"); check();
  revise({ hasPendingAnswers: true });
  assert.equal(button("确认并保存病例"), undefined);
  revise({ hasPendingAnswers: false });
  assert.equal(checkbox().props.checked, false);
  check(); revise({ allowed: false });
  assert.equal(button("核对保存内容"), undefined);
  assert.equal(button("重新预览保存内容").props.disabled, true);
  assert.equal(writes().length, 0);
});

test("late save response after session unmount cannot bind another session", async () => {
  await click("核对保存内容"); check();
  const gate = deferred(); adapter = async config => { await gate.promise; return normal(config); };
  let pending;
  await act(async () => { pending = button("确认并保存病例").props.onClick(); await new Promise(setImmediate); });
  act(() => renderer.unmount());
  await act(async () => { gate.resolve(); await pending; });
  assert.equal(receipts.length, 0);
  assert.equal(requests.filter(r => r.method === "get").length, 0);
});


test("navigation invalidates confirmation without claiming unchanged input is unsaved", async () => {
  revise({ contentRevision: "same-input" });
  await click("核对保存内容"); check();
  adapter = async config => { if (config.method === "get") throw new Error("Read failed"); return normal(config); };
  await click("确认并保存病例");
  revise({ revision: "returned-to-intake", contentRevision: "same-input" });
  adapter = async config => normal(config);
  await click("核对保存结果");
  assert.equal(writes().length, 1);
  assert.equal(receipts.length, 1);
  assert.equal(receipts[0].receipt.inputsChanged, false);
});
