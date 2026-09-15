import React from "react";
import TestRenderer, { act } from "react-test-renderer";
import { MemoryRouter } from "react-router-dom";
import { test, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import api from "../src/api";
import ConsultUpdateReview from "../src/components/ConsultUpdateReview";

// Isolated component state tests: no browser, user credentials, or real API calls.
global.localStorage = { getItem: () => null };
let renderer, requests, adapter, props;
const before = { chief_complaint: "旧主诉", history: "合成病史🐾\r\n保留原文  ", exam_findings: "待补充", analysis: "原分析", treatment: "原处理", prognosis: "原风险" };
const proposed = { ...before, history: before.history + "\n\n合成问诊摘要", analysis: "本轮分析" };
const preview = { case_id: 7, session_id: "synthetic", patient_name: "合成犬", before, proposed, preview_token: "a".repeat(64) };
const saved = { id: 7, patient_name: "合成犬", ...proposed };
const response = (config, data) => ({ data, status: 200, config });
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };
const nodes = () => renderer.root.findAllByType("button");
const button = label => nodes().find(n => n.children.join("") === label);
const checkbox = () => renderer.root.findByType("input");
const output = () => JSON.stringify(renderer.toJSON());
const click = async label => { const target = button(label); assert.ok(target, label); assert.ok(!target.props.disabled, label); await act(async () => { await target.props.onClick(); }); };
const check = () => act(() => checkbox().props.onChange({ target: { checked: true } }));
const render = () => <MemoryRouter><ConsultUpdateReview {...props} /></MemoryRouter>;
const revise = change => act(() => { props = { ...props, ...change }; renderer.update(render()); });

beforeEach(() => {
  requests = [];
  adapter = async config => response(config, config.url.endsWith("/preview-update-case") ? preview : config.method === "get" ? saved : { case_id: 7, message: "updated" });
  api.defaults.adapter = async config => { requests.push({ method: config.method, url: config.url, data: config.data }); return adapter(config); };
  props = { sessionId: "synthetic", caseId: 7, revision: 0, allowed: true, blocked: false, hasPendingAnswers: false, onUpdated: () => {} };
  act(() => { renderer = TestRenderer.create(render()); });
});
afterEach(() => { act(() => renderer.unmount()); });

const writes = () => requests.filter(r => r.url.endsWith("/update-case"));

test("preview is not a save; checkbox gates POST and all fields are read back", async () => {
  await click("核对更新内容");
  assert.equal(writes().length, 0);
  assert.equal(button("确认并更新病例").props.disabled, true);
  assert.ok(output().includes("保留原文"));
  check(); await click("确认并更新病例");
  assert.equal(writes().length, 1);
  assert.deepEqual(JSON.parse(writes()[0].data), { expected_preview_token: preview.preview_token });
  assert.equal(requests.at(-1).url, "/api/cases/7");
  assert.ok(output().includes("本次核对的六项内容一致"));
  assert.equal(button("确认并更新病例"), undefined);
});

test("editing after confirmation requires a new preview and confirmation", async () => {
  await click("核对更新内容"); check(); revise({ revision: 1 });
  assert.ok(output().includes("原确认失效"));
  assert.equal(button("确认并更新病例"), undefined);
  await click("重新预览更新内容");
  assert.equal(checkbox().props.checked, false);
  assert.equal(button("确认并更新病例").props.disabled, true);
  await click("返回修改");
  assert.equal(writes().length, 0);
});

test("late preview response is discarded when editing occurs during the request", async () => {
  const gate = deferred(); adapter = async config => { await gate.promise; return response(config, preview); };
  let inflight;
  await act(async () => { inflight = button("核对更新内容").props.onClick(); await new Promise(setImmediate); });
  revise({ revision: 1 });
  await act(async () => { gate.resolve(); await inflight; });
  assert.equal(button("确认并更新病例"), undefined);
  assert.ok(output().includes("内容已修改"));
});

test("pending writes cannot be submitted twice", async () => {
  await click("核对更新内容"); check();
  const gate = deferred();
  adapter = async config => { if (config.method === "post") await gate.promise; return response(config, config.method === "get" ? saved : { case_id: 7 }); };
  const submit = button("确认并更新病例").props.onClick;
  let inflight;
  await act(async () => { inflight = submit(); await new Promise(setImmediate); await submit(); });
  assert.equal(writes().length, 1);
  assert.ok(output().includes("正在保存"));
  await act(async () => { gate.resolve(); await inflight; });
  assert.ok(output().includes("六项内容一致"));
});

test("409 invalidates confirmation and does not retry or claim saved", async () => {
  await click("核对更新内容"); check();
  adapter = async () => { throw { response: { status: 409 } }; };
  await click("确认并更新病例");
  assert.equal(writes().length, 1);
  assert.equal(requests.filter(r => r.method === "get").length, 0);
  assert.ok(output().includes("原确认已失效"));
  assert.equal(button("确认并更新病例"), undefined);
});

test("lost write response is resolved by GET without a second write", async () => {
  await click("核对更新内容"); check();
  adapter = async config => { if (config.method === "post") throw new Error("Lost response"); return response(config, saved); };
  await click("确认并更新病例");
  assert.equal(writes().length, 1);
  assert.ok(output().includes("六项内容一致"));
});

test("failed read preserves preview; recovery only reads and mismatch is not success", async () => {
  await click("核对更新内容"); check();
  adapter = async config => { if (config.method === "get") throw new Error("Read failed"); return response(config, { case_id: 7 }); };
  await click("确认并更新病例");
  assert.ok(output().includes("保存结果待核对"));
  assert.ok(output().includes("合成问诊摘要"));
  assert.equal(button("确认并更新病例"), undefined);
  adapter = async config => response(config, { ...saved, treatment: "其他更新" });
  await click("核对保存结果");
  assert.ok(output().includes("当前病例与核对内容不一致"));
  assert.ok(!output().includes("六项内容一致"));
  adapter = async config => response(config, saved);
  await click("核对保存结果");
  assert.equal(writes().length, 1);
  assert.ok(output().includes("六项内容一致"));
});

test("unsubmitted answers, in-flight changes and missing review block confirmation", async () => {
  await click("核对更新内容"); check();
  for (const flag of ["hasPendingAnswers", "blocked"]) {
    revise({ [flag]: true });
    assert.equal(button("确认并更新病例").props.disabled, true);
    revise({ [flag]: false });
    assert.equal(checkbox().props.checked, false);
  }
  check(); revise({ allowed: false });
  assert.equal(button("确认并更新病例").props.disabled, true);
  assert.equal(writes().length, 0);
});

test("a response to an unmounted session cannot refresh another session", async () => {
  await click("核对更新内容"); check();
  let refreshes = 0; props.onUpdated = () => { refreshes++; }; revise(props);
  const gate = deferred(); adapter = async config => { await gate.promise; return response(config, saved); };
  let inflight;
  await act(async () => { inflight = button("确认并更新病例").props.onClick(); await new Promise(setImmediate); });
  act(() => renderer.unmount());
  await act(async () => { gate.resolve(); await inflight; });
  assert.equal(refreshes, 0);
  assert.equal(requests.filter(r => r.method === "get").length, 0);
});
