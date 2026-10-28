import React from "react";
import TestRenderer, { act } from "react-test-renderer";
import { MemoryRouter, Routes, Route, useNavigate } from "react-router-dom";
import { test, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import CaseDetail from "../src/pages/CaseDetail";
import api from "../src/api";
import { rememberRecovery } from "../src/followupRecovery";
import { schema as planSchema, validList as validPlanList } from "../src/followupPlan";
import { schema as contactSchema, validList as validContactList } from "../src/followupContacts";
import followupFixture from "../../tests/fixtures/clinical_followup_plan_overview_cw_b17_cases.json";

const memory = () => {
  const entries = new Map();
  return {
    getItem: key => entries.get(key) ?? null,
    setItem: (key, value) => entries.set(key, String(value)),
    removeItem: key => entries.delete(key),
    get length() { return entries.size; },
    key: index => [...entries.keys()][index] ?? null,
  };
};
const events = () => {
  const listeners = new Map();
  return {
    addEventListener: (name, fn) => {
      if (!listeners.has(name)) listeners.set(name, new Set());
      listeners.get(name).add(fn);
    },
    removeEventListener: (name, fn) => listeners.get(name)?.delete(fn),
    dispatchEvent: event => {
      for (const fn of [...(listeners.get(event.type) || [])]) fn(event);
      return true;
    },
  };
};
const tokenFor = owner => "synthetic." + Buffer.from(JSON.stringify({
  sub: owner, exp: 4102444800,
})).toString("base64url") + ".signature";
const firstToken = tokenFor("detail-expiry-first");
const nextToken = tokenFor("detail-expiry-next");
const summaryUrl = id => `/api/diagnostic-data/cases/${id}/summary`;
const record = id => ({
  id, patient_name: `401 合成病例 ${id}`, species: "dog",
  history: `病例 ${id} 的合成原文 café 🐾`, treatment: "仅用于界面验收",
});
const summary = id => ({
  counts: { reports: 1, observations: 0, imaging_studies: 0 },
  reports: [{ report_id: id, title: `病例 ${id} 的已加载诊断摘要`, status: "final", source_type: "synthetic" }],
  observations: [], imaging_studies: [],
});
const response = (config, data) => ({ config, status: 200, headers: {}, data });
const unauthorized = config => ({
  config, response: { status: 401, headers: {}, data: { detail: "Synthetic expired credential" } },
});
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};
const snapshot = "a".repeat(64);
const previewOriginal = "401 前已核对文书原文 café 🐾";
const documentPreview = config => {
  const body = JSON.parse(config.data), context = {};
  for (const key of ["case_id", "pet_name", "species", "age", "sex", "weight", "complaint", "history", "exam", "assessment", "plan", "notes", "follow_up", "owner_name", "coat_color"]) context["visit." + key] = "未填写";
  context["visit.case_id"] = String(body.case_id);
  context["visit.pet_name"] = record(body.case_id).patient_name;
  context["visit.history"] = previewOriginal;
  context["export.account_id"] = "1";
  return response(config, { ...body, context, content_snapshot: snapshot, missing_required_keys: [], writes_database: false });
};
const documentResponse = config => ({
  ...response(config, new Blob(["PK-synthetic"], { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" })),
  headers: { "content-disposition": 'attachment; filename="synthetic.docx"', "x-pmai-content-snapshot": JSON.parse(config.data).expected_content_snapshot },
});
const storedLocators = () => Array.from({ length: window.sessionStorage.length }, (_, index) => {
  const key = window.sessionStorage.key(index);
  return [key, window.sessionStorage.getItem(key)];
});

let renderer, navigate, requests, alerts, downloads, unexpected, summaryAdapter, documentAdapter, followupAdapter, extraRequestInterceptors;
let originalAdapter, originalError, originalCreate, originalRevoke, originalGlobals;
const output = () => JSON.stringify(renderer.toJSON());
const content = node => typeof node === "string" ? node : (node.children || []).map(content).join("");
const button = label => renderer.root.findAllByType("button").find(node => content(node) === label);
const blocked = node => {
  for (let item = node; item; item = item.parent) {
    if (item.props.disabled || (item.props.inert !== undefined && item.props.inert !== false)) return true;
  }
  return false;
};
const click = async label => {
  const target = button(label);
  assert(target, `Missing button: ${label}`);
  assert(!blocked(target), `Button unavailable: ${label}`);
  await act(async () => { await target.props.onClick(); });
};
function Pages() {
  navigate = useNavigate();
  return <Routes>
    <Route path="/cases/:id" element={<CaseDetail />} />
    <Route path="/" element={<p>合成登录入口</p>} />
  </Routes>;
}
const mount = () => act(async () => {
  renderer = TestRenderer.create(<MemoryRouter initialEntries={["/cases/1"]}><Pages /></MemoryRouter>);
});

beforeEach(() => {
  renderer = null; requests = []; alerts = []; downloads = []; unexpected = [];
  extraRequestInterceptors = [];
  originalAdapter = api.defaults.adapter; originalError = console.error;
  originalCreate = URL.createObjectURL; originalRevoke = URL.revokeObjectURL;
  originalGlobals = Object.fromEntries(["window", "document", "localStorage", "alert", "confirm"].map(key => [key, globalThis[key]]));
  globalThis.localStorage = memory();
  localStorage.setItem("token", firstToken);
  // Like a browser, storage writes in this window do not emit a storage event.
  globalThis.window = { ...events(), Event, sessionStorage: memory(), print() {}, location: {}, confirm: () => true };
  globalThis.document = {
    ...events(), hidden: false, body: { appendChild() {} },
    createElement: () => ({ click() { downloads.push(this.download); }, remove() {} }),
  };
  globalThis.alert = message => alerts.push(message);
  globalThis.confirm = () => true;
  URL.createObjectURL = () => "blob:synthetic-auth-expiry";
  URL.revokeObjectURL = () => {};
  console.error = (...args) => {
    if (args[0] !== "Diagnostic data summary load failed:") originalError(...args);
  };
  summaryAdapter = async config => response(config, summary(Number(config.url.split("/").at(-2))));
  documentAdapter = config => Promise.resolve(config.url.endsWith("render-preview") ? documentPreview(config) : documentResponse(config));
  followupAdapter = null;
  // Every HTTP request stays in this adapter. Unexpected reads or writes fail.
  api.defaults.adapter = async config => {
    requests.push(config);
    if (config.method === "get") {
      if (/^\/api\/cases\/[12]$/.test(config.url)) return response(config, record(Number(config.url.split("/").at(-1))));
      if (/^\/api\/diagnostic-data\/cases\/[12]\/summary$/.test(config.url)) return summaryAdapter(config);
      if (config.url === "/api/preventive-care/reminders") return response(config, { items: [] });
      if (config.url === "/api/cases/1/manual-lab") return response(config, {
        case_id: 1, case_token: "a".repeat(64), sources: [], reports: [],
      });
      if (followupAdapter && /^\/api\/cases\/1\/followup-(plan|contacts)(\/requests\/[a-f0-9]{32})?$/.test(config.url)) return followupAdapter(config);
    }
    if (config.method === "post" && ["/api/clinical-docs/render-preview", "/api/clinical-docs/render"].includes(config.url)) return documentAdapter(config);
    unexpected.push(`${config.method} ${config.url}`);
    throw new Error("Unexpected synthetic request");
  };
});
afterEach(() => {
  if (renderer) act(() => renderer.unmount());
  for (const interceptor of extraRequestInterceptors) api.interceptors.request.eject(interceptor);
  renderer = null;
  api.defaults.adapter = originalAdapter; console.error = originalError;
  URL.createObjectURL = originalCreate; URL.revokeObjectURL = originalRevoke;
  for (const [key, value] of Object.entries(originalGlobals)) {
    if (value === undefined) delete globalThis[key]; else globalThis[key] = value;
  }
  assert.deepEqual(unexpected, []);
});

test("a current summary 401 retires the loaded detail, preserves unsaved originals and blocks business actions", async () => {
  await mount();
  assert(output().includes(record(1).history), "Initial case must really be loaded");
  assert(output().includes(summary(1).reports[0].title), "Initial diagnostic summary must really be loaded");
  await click("打开检验项目");
  await click("录入检验报告");
  const rawDraft = "401 前未保存的检验原文 café 🐾";
  await act(async () => renderer.root.findByProps({ "aria-label": "报告标题" }).props.onChange({ target: { value: rawDraft } }));

  summaryAdapter = async config => { throw unauthorized(config); };
  await click("刷新诊断数据");
  const failed = requests.filter(config => config.url === summaryUrl(1));
  assert.equal(failed.length, 2, "401 must not automatically retry the read");
  assert.equal(failed[1].headers.Authorization, `Bearer ${firstToken}`);
  assert.equal(localStorage.getItem("token"), null);
  assert.deepEqual(alerts, ["登录状态已失效，请重新登录"]);

  const expiryNotice = renderer.root.findAllByProps({ role: "alert" }).find(node => /登录状态已失效/.test(content(node)));
  assert(expiryNotice, "A loaded case must visibly retire when its summary read expires the current login");
  assert.match(content(expiryNotice), /保留.*原文|原文.*保留/, "Retained text must be identified as unsaved originals to preserve");
  assert(renderer.root.findAllByType("a").some(node => node.props.href === "/" && /重新登录/.test(content(node))), "The expired page needs a deliberate login route");
  assert.equal(renderer.root.findByProps({ "aria-label": "报告标题" }).props.value, rawDraft, "401 must not silently discard another panel's unsaved original");
  assert(!output().includes(summary(1).reports[0].title), "The old diagnostic summary must not remain displayed as current");
  assert(!output().includes("已加载诊断数据："), "The old summary success status must be invalidated");
  for (const label of ["刷新诊断数据", "导出入院/住院记录 DOCX", "导出出院小结 DOCX", "导出门诊病历草稿 DOCX", "导出宠主说明草稿 DOCX", "核对整份检验记录"]) {
    const target = button(label);
    assert(!target || blocked(target), `Expired detail must not leave this action available: ${label}`);
  }
  assert.equal(downloads.length, 0);
  assert(requests.every(config => config.method === "get"), "Expiry must not issue a business write");
});

test("a late summary 401 from the old token cannot log out or retire a newly loaded case", async () => {
  await mount();
  const gate = deferred();
  let oldRequest, pending;
  summaryAdapter = config => {
    if (config.url === summaryUrl(1)) { oldRequest = config; return gate.promise; }
    return Promise.resolve(response(config, summary(2)));
  };
  await act(async () => { pending = button("刷新诊断数据").props.onClick(); });
  assert(oldRequest, "The request with the old credential must be in flight");
  assert.equal(oldRequest.headers.Authorization, `Bearer ${firstToken}`);

  localStorage.setItem("token", nextToken);
  await act(async () => navigate("/cases/2"));
  assert(output().includes(record(2).history));
  assert(output().includes(summary(2).reports[0].title));
  const requestCount = requests.length;
  await act(async () => { gate.reject(unauthorized(oldRequest)); await pending; });

  assert.equal(localStorage.getItem("token"), nextToken);
  assert.deepEqual(alerts, [], "An old 401 must not report that the new login expired");
  assert(output().includes(record(2).history));
  assert(output().includes(summary(2).reports[0].title));
  assert(!output().includes(record(1).history));
  assert(!output().includes("登录状态已失效"));
  assert(button("刷新诊断数据") && !blocked(button("刷新诊断数据")));
  assert.equal(requests.length, requestCount, "The old failure must not cause a new read or retry");
  assert.equal(downloads.length, 0);
});

test("restoring the expired token cannot revive a confirmed document or download its late response", async () => {
  await mount();
  await click("导出门诊病历草稿 DOCX");
  assert(output().includes(previewOriginal), "The document preview must have been independently loaded");
  await act(async () => renderer.root.findByProps({ "aria-label": "文书草稿内容核对" }).findByType("input").props.onChange({ target: { checked: true } }));
  const oldConfirm = button("确认并下载草稿 DOCX").props.onClick;
  const oldReload = button("重新读取草稿").props.onClick;
  const gate = deferred();
  let renderRequest, pending;
  documentAdapter = config => {
    if (config.url === "/api/clinical-docs/render") { renderRequest = config; return gate.promise; }
    return Promise.resolve(documentPreview(config));
  };
  await act(async () => { pending = oldConfirm(); });
  assert(renderRequest, "The confirmed document request must really be in flight");
  assert.equal(renderRequest.headers.Authorization, `Bearer ${firstToken}`);

  summaryAdapter = async config => { throw unauthorized(config); };
  await click("刷新诊断数据");
  assert.equal(localStorage.getItem("token"), null);
  assert(output().includes("登录状态已失效"));
  const count = requests.length;
  localStorage.setItem("token", firstToken);
  await act(async () => { gate.resolve(documentResponse(renderRequest)); await pending; });
  await act(async () => { await oldConfirm(); await oldReload(); });

  assert.equal(requests.length, count, "Retired handlers must not dispatch again even if the same token reappears");
  assert.equal(downloads.length, 0, "The response from the expired session must never create a browser download");
  assert(!output().includes(previewOriginal), "The old document must no longer be offered for confirmation");
  assert(!output().includes("已生成本次核对的草稿"));
  assert(!button("确认并下载草稿 DOCX"));
  assert(renderer.root.findByProps({ "aria-label": "文书草稿内容核对" }).findAllByProps({ role: "alert" }).some(node => /登录状态已失效/.test(content(node))), "The retired review must visibly explain why its confirmation is unavailable");
  assert.deepEqual(alerts, ["登录状态已失效，请重新登录"]);
});

for (const kind of ["plan", "contact"]) test(`${kind} unknown-save locator survives detail expiry and a late result without another write`, async () => {
  const listing = structuredClone(followupFixture.listing);
  const schema = kind === "plan" ? planSchema : contactSchema;
  if (kind === "contact") Object.assign(listing, { schema, records: [], limits: { versions: 50 } });
  assert((kind === "plan" ? validPlanList : validContactList)(listing, 1), "The recovery panel must receive a valid independently checked list");
  const reference = {
    schema: "followup-recovery-v1", kind, caseId: 1, ownerId: 1,
    requestId: (kind === "plan" ? "d" : "e").repeat(32), operation: "create",
    targetId: null, rootId: null, recordVersion: 1, contentHash: "f".repeat(64),
  };
  rememberRecovery(reference);
  const before = storedLocators();
  const gate = deferred();
  let resultRequest, pending;
  followupAdapter = config => {
    if (config.url.includes("/requests/")) { resultRequest = config; return gate.promise; }
    return Promise.resolve(response(config, listing));
  };
  await mount();
  await click(kind === "plan" ? "打开复查计划" : "打开人工随访记录");
  assert(output().includes(reference.requestId), "The stored request ID must actually be recovered into the panel");
  const oldCheck = button(kind === "plan" ? "核对复查保存结果" : "核对随访保存结果").props.onClick;
  await act(async () => { pending = oldCheck(); });
  assert(resultRequest, "A read-only result lookup must be in flight");
  assert.equal(resultRequest.method, "get");

  summaryAdapter = async config => { throw unauthorized(config); };
  await click("刷新诊断数据");
  assert.equal(localStorage.getItem("token"), null);
  assert.deepEqual(storedLocators(), before, "Expiry must preserve the exact persisted locator bytes");
  const count = requests.length;
  localStorage.setItem("token", firstToken);
  await act(async () => {
    gate.resolve(response(resultRequest, { schema, case_id: 1, request_id: reference.requestId, state: "not_committed", writes_database: false }));
    await pending;
  });
  await act(async () => { await oldCheck(); });

  assert.deepEqual(storedLocators(), before, "An expired late reply cannot resolve the unknown-save marker");
  assert.equal(requests.length, count, "No independent read or retry is allowed from the retired panel");
  assert(requests.every(config => config.method === "get"), "An existing unknown save must never be re-posted");
  assert(!output().includes("已核对服务端保存结果"));
  assert(!output().includes("未查到该请求已提交"));
  assert(output().includes("登录状态已失效"));
});

for (const [label, url] of [
  ["选择已核对检验报告", "/api/clinical-docs/cases/1/manual-lab-options"],
  ["选择已核对影像报告", "/api/clinical-docs/cases/1/manual-imaging-options"],
  ["选择复查计划附节", "/api/cases/1/followup-plan"],
  ["选择人工随访记录附节", "/api/cases/1/followup-contacts"],
]) test(`${label}: a queued selector read cannot dispatch after detail expiry and same-token restoration`, async () => {
  await mount();
  await click("导出门诊病历草稿 DOCX");
  const gate = deferred();
  let queued;
  // Hold the request before the shared API's final authorization check.
  extraRequestInterceptors.push(api.interceptors.request.use(async config => {
    if (config.url === url) { queued = config; await gate.promise; }
    return config;
  }));
  await click(label);
  assert(queued, "The selector must have enqueued its own read");
  assert(!requests.some(config => config.url === url), "The held read must not have reached the HTTP adapter");
  summaryAdapter = async config => { throw unauthorized(config); };
  await click("刷新诊断数据");
  assert.equal(localStorage.getItem("token"), null);
  const count = requests.length;
  localStorage.setItem("token", firstToken);
  await act(async () => { gate.resolve(); await new Promise(resolve => setImmediate(resolve)); });

  assert.equal(requests.length, count, "The retired selection must not cross the HTTP dispatch boundary");
  assert(!requests.some(config => config.url === url));
  assert(!button("确认并下载草稿 DOCX"));
  assert(output().includes("登录状态已失效"));
  assert.equal(downloads.length, 0);
});
