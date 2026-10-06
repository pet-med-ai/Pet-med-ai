import React from "react";
import TestRenderer, { act } from "react-test-renderer";
import { test, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import { webcrypto } from "node:crypto";
import VoiceDraft from "../src/components/VoiceDraft";
import { cleanVoiceDraft, voiceReady, voicePayload, voiceRevision, voiceIdentity } from "../src/voiceDraftState";
import api from "../src/api";

let renderer, props, requests, adapter, port, stopped, closed, changed, drafted;
const context = { owner: "doctor@example.com", sessionId: "synthetic", caseId: null, patientName: "合成犬", species: "dog" };
const button = label => renderer.root.findAllByType("button").find(n => n.children.join("") === label);
const output = () => JSON.stringify(renderer.toJSON());
const click = async label => { const n = button(label); assert(n && !n.props.disabled, label); await act(async () => { await n.props.onClick(); }); };
const checkbox = n => renderer.root.findAllByType("input")[n];
const check = n => act(() => checkbox(n).props.onChange({ target: { checked: true } }));
const render = () => renderer.update(<VoiceDraft {...props} />);
const response = (config, data) => ({ config, data, status: 200 });
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };

beforeEach(async () => {
  stopped = closed = 0; changed = drafted = null; requests = [];
  Object.defineProperty(globalThis, "crypto", { configurable: true, value: webcrypto });
  global.localStorage = { getItem: () => null };
  global.window = { addEventListener() {}, removeEventListener() {}, AudioContext: class {
    sampleRate = 16000; destination = {}; audioWorklet = { addModule: async () => {} };
    createMediaStreamSource() { return { connect() {}, disconnect() {} }; }
    resume() { return Promise.resolve(); } close() { closed++; return Promise.resolve(); }
  }, AudioWorkletNode: class { constructor() { this.port = {}; port = this.port; } connect() {} disconnect() {} } };
  Object.defineProperty(globalThis, "navigator", { configurable: true, value: { mediaDevices: { getUserMedia: async () => ({ getTracks: () => [{ stop() { stopped++; } }] }) } } });
  adapter = async config => {
    if (config.url.endsWith("availability")) return response(config, { enabled: true });
    if (config.url.includes("/context/")) return response(config, { session_id: context.sessionId, case_id: null, session_version: "a".repeat(64) });
    if (config.url.endsWith("/review")) return response(config, { receipt: "synthetic-reviewed-receipt" });
    if (config.url.endsWith("/transcribe")) { const body = JSON.parse(config.data); return response(config, { request_id: body.request_id, binding: body.binding, text: "未见呕吐，零点五毫升", receipt: "synthetic-receipt-verified" }); }
    return response(config, { state: "result_unknown", reserved_fen: 1 });
  };
  api.defaults.adapter = async config => { requests.push(config); return adapter(config); };
  props = { context, text: "原始病史", draft: null, onChange: value => { changed = value; }, onDraft: value => { drafted = value; } };
  await act(async () => { renderer = TestRenderer.create(<VoiceDraft {...props} />); });
});
afterEach(() => { act(() => renderer.unmount()); });

async function record() { check(0); await click("开始录音"); act(() => port.onmessage({ data: new Float32Array(16000) })); await click("停止录音"); }
test("record then confirm is explicit and never overwrites original history", async () => {
  await record(); assert(stopped >= 1 && closed >= 1); await click("提交转写");
  assert.equal(changed, null); assert.equal(button("确认加入病史草稿").props.disabled, true);
  check(1); await click("确认加入病史草稿");
  assert.equal(changed, "原始病史\n\n未见呕吐，零点五毫升"); assert.equal(drafted.entries.length, 1);
  assert(voiceReady(drafted, context, changed)); assert.equal(voicePayload(drafted)[0].reviewed, true);
  assert.equal(requests.filter(r => r.url.endsWith("/transcribe")).length, 1);
});
test("editing transcript invalidates its checkbox", async () => {
  await record(); await click("提交转写"); check(1);
  act(() => renderer.root.findByType("textarea").props.onChange({ target: { value: "未见呕吐，0.5 毫升" } }));
  assert.equal(button("确认加入病史草稿").props.disabled, true); assert.equal(changed, null);
});
test("late transcription after changing animal cannot enter new history", async () => {
  await record(); const d = deferred(), normal = adapter;
  adapter = config => config.url.endsWith("/transcribe") ? d.promise.then(() => normal(config)) : normal(config);
  let submitted; await act(async () => { submitted = button("提交转写").props.onClick(); await new Promise(r => setTimeout(r, 10)); });
  await act(async () => { props = { ...props, context: { ...context, patientName: "另一只猫", species: "cat" } }; render(); });
  await act(async () => { d.resolve(); await submitted; });
  assert.equal(changed, null); assert.equal(button("确认加入病史草稿"), undefined);
});
test("unknown service result offers status only and never auto resends", async () => {
  await record(); const normal = adapter;
  adapter = config => config.url.endsWith("/transcribe") ? Promise.reject(Error("network")) : normal(config);
  await click("提交转写"); await click("核对转写状态");
  assert(output().includes("不会重发")); assert.equal(requests.filter(r => r.url.endsWith("/transcribe")).length, 1);
});
test("cancel and context edits release microphone", async () => {
  check(0); await click("开始录音"); await click("放弃本段"); assert(stopped >= 1); assert.equal(changed, null);
  await click("开始录音"); act(() => { props = { ...props, text: "手工更正" }; render(); }); assert(stopped >= 2);
});
test("recovered provenance is unapproved, has no audio, and requires exact history", () => {
  const original = { identity: voiceIdentity(context), entries: [{ receipt: "valid-receipt", original_text: "原文", edited_text: "修订" }], reviewedRevision: voiceRevision(context, "修订"), audio: "must-not-survive" };
  const clean = cleanVoiceDraft(original); assert.equal(clean.reviewedRevision, null); assert.equal(clean.audio, undefined);
  assert(!voiceReady(clean, context, "修订")); assert(!voiceReady(original, context, "又修改"));
});
test("manual changes cannot pass source review unless repaired segment matches history", async () => {
  const draft = { identity: voiceIdentity(context), entries: [{ receipt: "valid-receipt", original_text: "原文", edited_text: "未见呕吐" }], reviewedRevision: null };
  act(() => { props = { ...props, text: "别的内容", draft }; render(); });
  assert.equal(button("已重新核对语音来源和病史").props.disabled, true);
  act(() => { props = { ...props, text: "未见呕吐" }; render(); });
  await click("已重新核对语音来源和病史"); assert(voiceReady(drafted, context, "未见呕吐"));
});
