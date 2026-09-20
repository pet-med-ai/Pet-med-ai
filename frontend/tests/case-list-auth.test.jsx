import React from "react";
import TestRenderer, { act } from "react-test-renderer";
import { MemoryRouter } from "react-router-dom";
import { test, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import api from "../src/api";
import { Home } from "../src/App";

const memory = () => {
  const data = new Map();
  return { getItem: k => data.get(k) ?? null, setItem: (k, v) => data.set(k, String(v)), removeItem: k => data.delete(k), get length() { return data.size; }, key: i => [...data.keys()][i] ?? null };
};
const token = "synthetic." + Buffer.from(JSON.stringify({ sub: "case-list-test", exp: 4102444800 })).toString("base64url") + ".signature";
const row = { id: 7, patient_name: "合成病例", species: "dog", chief_complaint: "虚构验收", history: "虚构病史" };
let renderer, requests, listAdapter, mutationAdapter, confirmations, alerts, errors, warnings, originalError, originalWarn;
const caseRequests = () => requests.filter(c => c.url === "/api/cases");
const output = () => JSON.stringify(renderer.toJSON());
const button = name => renderer.root.findAllByType("button").find(n => n.children.join("") === name);
const listSection = () => renderer.root.findAllByType("section").find(n => n.findAllByType("h2").some(h => h.children.join("") === "病例列表"));
const listButton = name => listSection().findAllByType("button").find(n => n.children.join("") === name);
const search = () => renderer.root.findByProps({ placeholder: "搜索：病例名 / 物种 / 主诉" });
const change = (field, value) => act(() => field.props.onChange({ target: { value } }));
const settle = () => act(async () => { await new Promise(resolve => setTimeout(resolve, 360)); });
const mount = async (authed = true) => {
  if (authed) localStorage.setItem("token", token);
  await act(async () => { renderer = TestRenderer.create(<MemoryRouter><Home /></MemoryRouter>); });
};
const click = async node => {
  assert(node); assert(!node.props.disabled);
  await act(async () => { await node.props.onClick(); });
};

beforeEach(() => {
  global.localStorage = memory();
  global.window = { sessionStorage: memory(), addEventListener() {}, removeEventListener() {}, location: { reload() {} } };
  confirmations = []; alerts = [];
  global.confirm = message => { confirmations.push(message); return true; };
  global.alert = message => alerts.push(message);
  requests = []; errors = []; warnings = []; renderer = null;
  originalError = console.error; originalWarn = console.warn;
  console.error = (...args) => errors.push(args);
  console.warn = (...args) => warnings.push(args);
  listAdapter = async config => ({ config, status: 200, data: { items: [row], total: 21 } });
  mutationAdapter = () => assert.fail("Unexpected synthetic mutation");
  // No real HTTP: every request is intercepted, and every unexpected route fails.
  api.defaults.adapter = async config => {
    requests.push(config);
    if (config.method !== "get") return mutationAdapter(config);
    assert.equal(config.method, "get");
    if (config.url === "/api/cases") return listAdapter(config);
    assert.equal(config.url, "/api/ai/consult/sessions");
    return { config, status: 200, data: { items: [], total: 0 } };
  };
});
afterEach(() => {
  if (renderer) act(() => renderer.unmount());
  console.error = originalError; console.warn = originalWarn;
});

test("anonymous home makes no protected requests and explains the login requirement", async () => {
  await mount(false); await settle();
  assert.equal(requests.length, 0);
  assert.match(output(), /请先登录后查看病例列表/);
  assert.equal(button("刷新列表"), undefined);
  assert.equal(button("导出全量 CSV"), undefined);
  assert.equal(errors.length, 0);
});

test("authenticated mount loads cases once with the current Authorization header", async () => {
  await mount(); await settle();
  assert.equal(caseRequests().length, 1);
  assert.equal(caseRequests()[0].headers.Authorization, `Bearer ${token}`);
  assert.equal(caseRequests()[0].params.page, 1);
  assert.match(output(), /合成病例/);
});

test("rapid search uses only the final query", async () => {
  await mount(); await settle(); requests = [];
  change(search(), "合"); change(search(), "合成"); change(search(), "合成病例");
  await settle();
  assert.equal(caseRequests().length, 1);
  assert.equal(caseRequests()[0].params.q, "合成病例");
});

test("pagination loads once and search plus filters reset to page one without stale requests", async () => {
  await mount(); await settle(); requests = [];
  await click(listButton("下一页")); await settle();
  assert.equal(caseRequests().length, 1);
  assert.equal(caseRequests()[0].params.page, 2);
  requests = [];
  change(search(), "最终查询");
  change(renderer.root.findByProps({ title: "按风险等级筛选" }), "high");
  change(renderer.root.findByProps({ title: "按病例来源筛选" }), "dynamic");
  await settle();
  assert.equal(caseRequests().length, 1);
  assert.deepEqual(caseRequests()[0].params, { q: "最终查询", page: 1, page_size: 10, risk: "high", source: "dynamic" });
});

test("refresh from a later page resets and fetches page one only once", async () => {
  await mount(); await settle(); await click(listButton("下一页")); await settle(); requests = [];
  await click(button("刷新列表")); await settle();
  assert.equal(caseRequests().length, 1);
  assert.equal(caseRequests()[0].params.page, 1);
});

test("manual refresh cancels the pending search instead of fetching the same query twice", async () => {
  await mount(); await settle(); requests = [];
  change(search(), "立即刷新");
  await click(button("刷新列表")); await settle();
  assert.equal(caseRequests().length, 1);
  assert.equal(caseRequests()[0].params.q, "立即刷新");
});

test("unmount cancels pending search rather than sending a request from the old page", async () => {
  await mount(); await settle(); requests = [];
  change(search(), "不应发送");
  act(() => renderer.unmount()); renderer = null;
  await settle();
  assert.equal(caseRequests().length, 0);
});

test("removing the token before the pending request prevents dispatch", async () => {
  await mount(); await settle(); requests = [];
  change(search(), "登录已退出"); localStorage.removeItem("token");
  await settle();
  assert.equal(caseRequests().length, 0);
  assert.match(output(), /请先登录后查看病例列表/);
  assert.doesNotMatch(output(), /合成病例/);
});

test("a real 401 is still handled by the existing interceptor and never retried automatically", async () => {
  listAdapter = async config => { throw { config, response: { status: 401 } }; };
  await mount(); await settle(); await settle();
  assert.equal(caseRequests().length, 1);
  assert.equal(localStorage.getItem("token"), null);
  assert.match(output(), /请先登录后查看病例列表/);
  assert(errors.some(args => args[0] === "拉取病例失败："));
});

test("server failures remain visible in logs and keep the current login", async () => {
  listAdapter = async config => { throw { config, response: { status: 500 } }; };
  await mount(); await settle();
  assert.equal(caseRequests().length, 1);
  assert.equal(localStorage.getItem("token"), token);
  assert(errors.some(args => args[0] === "拉取病例失败："));
});

// Resolve synthetic requests explicitly to exercise out-of-order network responses.
const deferCaseResponses = () => {
  const pending = [];
  listAdapter = config => new Promise((resolve, reject) => {
    pending.push({
      config,
      succeed: (name, total = 1) => resolve({ config, status: 200, data: {
        items: [{ ...row, patient_name: name, analysis: "高风险" }], total,
      } }),
      fail: () => reject({ config, response: { status: 500 } }),
    });
  });
  return pending;
};
const complete = callback => act(async () => { callback(); });

test("a late search response cannot replace newer rows, totals or selection", async () => {
  const pending = deferCaseResponses();
  await mount(); await settle();
  change(search(), "新查询"); await settle();
  assert.equal(pending.length, 2);
  await complete(() => pending[1].succeed("新查询结果"));
  await click(button("本页全选"));
  await complete(() => pending[0].succeed("过期查询结果", 31));
  assert.match(output(), /新查询结果/);
  assert.doesNotMatch(output(), /过期查询结果/);
  assert.equal(listButton("下一页").props.disabled, true);
  assert(button("批量删除(1)"));
});

test("changing search invalidates the old response during the debounce gap", async () => {
  await mount(); await settle();
  const pending = deferCaseResponses();
  change(search(), "旧查询"); await settle();
  change(search(), "新查询");
  await complete(() => pending[0].succeed("过期查询结果"));
  assert.doesNotMatch(output(), /过期查询结果/);
  await settle();
  await complete(() => pending[1].succeed("新查询结果"));
  assert.match(output(), /新查询结果/);
});

test("an old request finishing cannot clear the newer request's loading state", async () => {
  const pending = deferCaseResponses();
  await mount(); await settle();
  change(search(), "新查询"); await settle();
  await complete(() => pending[0].succeed("过期查询结果"));
  assert.equal(button("刷新中…")?.props.disabled, true);
  await complete(() => pending[1].succeed("新查询结果"));
  assert.equal(button("刷新列表").props.disabled, false);
});

test("a superseded request failure does not report failure for the current results", async () => {
  const pending = deferCaseResponses();
  await mount(); await settle();
  change(search(), "新查询"); await settle();
  await complete(() => pending[1].succeed("新查询结果"));
  await complete(() => pending[0].fail());
  assert.match(output(), /新查询结果/);
  assert.equal(errors.length, 0);
});

for (const [title, value] of [["按风险等级筛选", "high"], ["按病例来源筛选", "manual"]]) {
  test(`${title} invalidates an in-flight response`, async () => {
    const pending = deferCaseResponses();
    await mount(); await settle();
    change(renderer.root.findByProps({ title }), value); await settle();
    await complete(() => pending[1].succeed("筛选后结果"));
    await complete(() => pending[0].succeed("筛选前结果"));
    assert.match(output(), /筛选后结果/);
    assert.doesNotMatch(output(), /筛选前结果/);
  });
}

test("late pagination responses cannot replace the current page or total", async () => {
  await mount(); await settle();
  const pending = deferCaseResponses();
  await click(listButton("下一页")); await settle();
  await click(listButton("下一页")); await settle();
  assert.deepEqual(pending.map(p => p.config.params.page), [2, 3]);
  await complete(() => pending[1].succeed("第三页病例", 31));
  await complete(() => pending[0].succeed("第二页病例", 11));
  assert.match(output(), /第三页病例/);
  assert.doesNotMatch(output(), /第二页病例/);
  assert.equal(listButton("下一页").props.disabled, false);
});

test("manual refresh after a query change supersedes the old in-flight request", async () => {
  const pending = deferCaseResponses();
  await mount(); await settle();
  change(search(), "手动刷新查询");
  await click(button("刷新列表"));
  assert.equal(pending.length, 2);
  await complete(() => pending[1].succeed("刷新后结果"));
  await complete(() => pending[0].succeed("刷新前结果"));
  await settle();
  assert.equal(pending.length, 2);
  assert.match(output(), /刷新后结果/);
  assert.doesNotMatch(output(), /刷新前结果/);
});

test("a response received after logout is discarded rather than cached for the next render", async () => {
  const pending = deferCaseResponses();
  await mount(); await settle();
  localStorage.removeItem("token");
  await complete(() => pending[0].succeed("退出前病例"));
  assert.match(output(), /请先登录后查看病例列表/);
  localStorage.setItem("token", token);
  act(() => renderer.update(<MemoryRouter><Home /></MemoryRouter>));
  assert.doesNotMatch(output(), /退出前病例/);
});

test("a response for a replaced token cannot populate the case list", async () => {
  const pending = deferCaseResponses();
  await mount(); await settle();
  localStorage.setItem("token", token + "-changed");
  await complete(() => pending[0].succeed("旧登录病例"));
  assert.doesNotMatch(output(), /旧登录病例/);
  assert.equal(localStorage.getItem("token"), token + "-changed");
  assert.equal(button("刷新列表").props.disabled, false);
});

test("an in-flight failure after unmount does not report an error on the abandoned page", async () => {
  const pending = deferCaseResponses();
  await mount(); await settle();
  act(() => renderer.unmount()); renderer = null;
  await complete(() => pending[0].fail());
  assert.equal(errors.length, 0);
});

const caseAlerts = () => listSection().findAllByProps({ role: "alert" });
const caseErrorText = /病例列表加载失败，请稍后重试。/;

for (const failure of ["server", "network"]) {
  test(`${failure} failure is shown as an error, not an empty list, without automatic retry`, async () => {
    listAdapter = async config => { throw failure === "server"
      ? { config, response: { status: 500, data: { detail: "internal-sensitive-detail" } } }
      : Object.assign(new Error("internal-sensitive-detail"), { config }); };
    await mount(); await settle(); await settle();
    assert.equal(caseRequests().length, 1);
    assert.equal(localStorage.getItem("token"), token);
    assert.equal(caseAlerts().length, 1);
    assert.match(output(), caseErrorText);
    assert.doesNotMatch(output(), /暂无病例|internal-sensitive-detail/);
    assert.equal(button("重试").props.disabled, false);
  });
}

test("an unfinished first load does not claim there are no cases", async () => {
  const pending = deferCaseResponses();
  await mount();
  assert.doesNotMatch(output(), /暂无病例/);
  await settle();
  assert.match(output(), /正在加载病例列表/);
  assert.doesNotMatch(output(), /暂无病例/);
  await complete(() => pending[0].succeed("已加载病例"));
  assert.match(output(), /已加载病例/);
  assert.doesNotMatch(output(), /正在加载病例列表/);
});

test("a current refresh failure removes stale rows, totals and selection", async () => {
  await mount(); await settle(); await click(button("本页全选"));
  assert(button("批量删除(1)"));
  listAdapter = async config => { throw { config, response: { status: 500 } }; };
  await click(button("刷新列表"));
  assert.match(output(), caseErrorText);
  assert.doesNotMatch(output(), /合成病例|暂无病例|共 21 条/);
  assert.equal(button("批量删除(0)").props.disabled, true);
});

test("retry keeps the failed query, filters and page, sends once and recovers", async () => {
  listAdapter = async config => ({ config, status: 200, data: { items: [{ ...row, analysis: "高风险" }], total: 21 } });
  await mount(); await settle();
  change(search(), "待重试查询");
  change(renderer.root.findByProps({ title: "按风险等级筛选" }), "high");
  change(renderer.root.findByProps({ title: "按病例来源筛选" }), "manual");
  await settle();
  listAdapter = async config => { throw { config, response: { status: 500 } }; };
  await click(listButton("下一页")); await settle();
  assert.match(output(), caseErrorText);
  const failedParams = { ...caseRequests().at(-1).params };
  assert.deepEqual(failedParams, { q: "待重试查询", page: 2, page_size: 10, risk: "high", source: "manual" });
  requests = [];
  const pending = deferCaseResponses();
  await act(async () => { button("重试").props.onClick(); });
  assert.equal(caseAlerts().length, 0);
  assert.equal(button("重试"), undefined);
  assert.equal(button("刷新中…").props.disabled, true);
  await settle();
  assert.equal(caseRequests().length, 1);
  assert.deepEqual(caseRequests()[0].params, failedParams);
  await complete(() => pending[0].succeed("重试成功病例", 21));
  assert.match(output(), /重试成功病例/);
  assert.equal(caseAlerts().length, 0);
  assert.equal(button("刷新列表").props.disabled, false);
});

test("a late successful old request cannot dismiss the current failure", async () => {
  const pending = deferCaseResponses();
  await mount(); await settle();
  change(search(), "当前查询"); await settle();
  await complete(() => pending[1].fail());
  assert.match(output(), caseErrorText);
  await complete(() => pending[0].succeed("过期病例"));
  assert.match(output(), caseErrorText);
  assert.doesNotMatch(output(), /过期病例|暂无病例/);
});

test("a superseded failure during the debounce gap cannot show an error", async () => {
  const pending = deferCaseResponses();
  await mount(); await settle();
  change(search(), "新查询");
  await complete(() => pending[0].fail());
  assert.equal(caseAlerts().length, 0);
  assert.equal(errors.length, 0);
  await settle();
  await complete(() => pending[1].succeed("新结果"));
  assert.equal(caseAlerts().length, 0);
});

test("a failure for replaced credentials cannot show a retry error for the new login", async () => {
  const pending = deferCaseResponses();
  await mount(); await settle();
  localStorage.setItem("token", token + "-changed");
  await complete(() => pending[0].fail());
  assert.equal(caseAlerts().length, 0);
  assert.equal(button("重试"), undefined);
  assert.equal(localStorage.getItem("token"), token + "-changed");
});

test("logout after a failure removes the protected retry control", async () => {
  listAdapter = async config => { throw { config, response: { status: 500 } }; };
  await mount(); await settle();
  assert.match(output(), caseErrorText);
  localStorage.removeItem("token");
  act(() => renderer.update(<MemoryRouter><Home /></MemoryRouter>));
  assert.match(output(), /请先登录后查看病例列表/);
  assert.equal(caseAlerts().length, 0);
  assert.equal(button("重试"), undefined);
});

// Deletion receipts must describe completed server operations, never pending ones.
// All writes below are intercepted synthetic requests; no server or database is used.
const secondRow = { ...row, id: 8, patient_name: "第二条合成病例" };
const deleteButtons = () => listSection().findAllByProps({ title: "删除该病例" });
const mutations = () => requests.filter(c => c.method !== "get");
const deferMutations = () => {
  const pending = [];
  mutationAdapter = config => {
    assert(["/api/cases/7", "/api/cases/8", "/api/cases/7/restore", "/api/cases/8/restore"].includes(config.url));
    assert.equal(config.method, config.url.endsWith("/restore") ? "post" : "delete");
    return new Promise((resolve, reject) => pending.push({
      config,
      succeed: () => resolve({ config, status: config.method === "delete" ? 204 : 200, data: {} }),
      fail: () => reject({ config, response: { status: 500 } }),
    }));
  };
  return pending;
};
const begin = callback => act(async () => { callback(); });
const showTwoRows = () => {
  listAdapter = async config => ({ config, status: 200, data: { items: [row, secondRow], total: 2 } });
};
const receipt = () => button("撤销") || button("撤销中…");

test("cancelling a single deletion sends no mutation and shows no deletion receipt", async () => {
  await mount(); await settle();
  global.confirm = message => { confirmations.push(message); return false; };
  await click(deleteButtons()[0]);
  assert.equal(confirmations.length, 1);
  assert.equal(mutations().length, 0);
  assert.equal(Boolean(receipt()), false);
});

test("a pending deletion cannot claim success or offer undo before server confirmation", async () => {
  const pending = deferMutations();
  await mount(); await settle();
  await begin(() => deleteButtons()[0].props.onClick());
  assert.equal(pending.length, 1);
  assert.equal(deleteButtons()[0].props.disabled, true);
  assert.match(output(), /删除中/);
  assert.equal(Boolean(receipt()), false);
  assert.doesNotMatch(output(), /已删除/);
  await complete(() => pending[0].succeed());
  assert(button("撤销"));
  assert.match(output(), /已删除/);
  assert.equal(caseRequests().length, 2);
});

test("a failed deletion has no success receipt and makes no automatic retry", async () => {
  const pending = deferMutations();
  await mount(); await settle();
  await begin(() => deleteButtons()[0].props.onClick());
  await complete(() => pending[0].fail());
  assert.equal(Boolean(receipt()), false);
  assert.equal(mutations().length, 1);
  assert.equal(caseRequests().length, 1);
  assert.equal(Boolean(deleteButtons()[0].props.disabled), false);
  assert.equal(alerts.length, 1);
});

test("duplicate single-delete callbacks and a different row cannot dispatch concurrent deletions", async () => {
  showTwoRows(); const pending = deferMutations();
  await mount(); await settle();
  const first = deleteButtons()[0].props.onClick;
  const second = deleteButtons()[1].props.onClick;
  await begin(() => { first(); first(); second(); });
  assert.equal(pending.length, 1);
  assert.equal(confirmations.length, 1);
  assert(deleteButtons().every(node => node.props.disabled));
  await complete(() => pending[0].succeed());
  assert(deleteButtons().every(node => !node.props.disabled));
});

test("a later pending or failed deletion preserves the previous confirmed undo target", async () => {
  showTwoRows(); const pending = deferMutations();
  await mount(); await settle();
  await begin(() => deleteButtons()[0].props.onClick());
  await complete(() => pending[0].succeed());
  const undoPrevious = button("撤销").props.onClick;
  await begin(() => deleteButtons()[1].props.onClick());
  assert.equal(button("撤销").props.disabled, true);
  await begin(undoPrevious);
  assert.equal(pending.length, 2);
  await complete(() => pending[1].fail());
  assert.equal(Boolean(button("撤销").props.disabled), false);
  await begin(() => button("撤销").props.onClick());
  assert.equal(pending[2].config.url, "/api/cases/7/restore");
  await complete(() => pending[2].succeed());
  assert.equal(Boolean(receipt()), false);
});

test("a later successful deletion replaces the undo target only after confirmation", async () => {
  showTwoRows(); const pending = deferMutations();
  await mount(); await settle();
  await begin(() => deleteButtons()[0].props.onClick());
  await complete(() => pending[0].succeed());
  await begin(() => deleteButtons()[1].props.onClick());
  await complete(() => pending[1].succeed());
  await begin(() => button("撤销").props.onClick());
  assert.equal(pending[2].config.url, "/api/cases/8/restore");
  await complete(() => pending[2].succeed());
});

test("pending undo blocks duplicate restore and delete callbacks until completion", async () => {
  const pending = deferMutations();
  await mount(); await settle();
  await begin(() => deleteButtons()[0].props.onClick());
  await complete(() => pending[0].succeed());
  const undo = button("撤销").props.onClick;
  const remove = deleteButtons()[0].props.onClick;
  await begin(() => { undo(); undo(); remove(); });
  assert.equal(pending.length, 2);
  assert.equal(pending[1].config.url, "/api/cases/7/restore");
  assert.equal(button("撤销中…").props.disabled, true);
  assert.equal(deleteButtons()[0].props.disabled, true);
  assert.equal(button("关闭").props.disabled, true);
  await complete(() => pending[1].succeed());
  assert.equal(Boolean(receipt()), false);
  assert.equal(caseRequests().length, 3);
  assert.equal(Boolean(deleteButtons()[0].props.disabled), false);
});

test("failed undo keeps the confirmed receipt and allows an explicit retry", async () => {
  const pending = deferMutations();
  await mount(); await settle();
  await begin(() => deleteButtons()[0].props.onClick());
  await complete(() => pending[0].succeed());
  await begin(() => button("撤销").props.onClick());
  await complete(() => pending[1].fail());
  assert.equal(Boolean(button("撤销").props.disabled), false);
  assert.equal(mutations().length, 2);
  await begin(() => button("撤销").props.onClick());
  assert.equal(pending[2].config.url, "/api/cases/7/restore");
  await complete(() => pending[2].succeed());
  assert.equal(Boolean(receipt()), false);
});

test("confirmed deletion keeps undo even when the following list refresh fails", async () => {
  const pending = deferMutations();
  await mount(); await settle();
  await begin(() => deleteButtons()[0].props.onClick());
  listAdapter = async config => { throw { config, response: { status: 500 } }; };
  await complete(() => pending[0].succeed());
  assert.match(output(), caseErrorText);
  assert.equal(Boolean(button("撤销").props.disabled), false);
  assert.equal(mutations().length, 1);
});

test("confirmed restore clears undo even when the following list refresh fails", async () => {
  const pending = deferMutations();
  await mount(); await settle();
  await begin(() => deleteButtons()[0].props.onClick());
  await complete(() => pending[0].succeed());
  await begin(() => button("撤销").props.onClick());
  listAdapter = async config => { throw { config, response: { status: 500 } }; };
  await complete(() => pending[1].succeed());
  assert.match(output(), caseErrorText);
  assert.equal(Boolean(receipt()), false);
  assert.equal(mutations().length, 2);
});

test("single deletion blocks a previously selected bulk-delete callback", async () => {
  showTwoRows(); const pending = deferMutations();
  await mount(); await settle(); await click(button("本页全选"));
  const bulk = button("批量删除(2)").props.onClick;
  await begin(() => { deleteButtons()[0].props.onClick(); bulk(); });
  assert.equal(pending.length, 1);
  assert.equal(button("批量删除(2)").props.disabled, true);
  await complete(() => pending[0].succeed());
});

test("bulk deletion blocks single delete and undo while preserving existing receipt on failure", async () => {
  showTwoRows(); const pending = deferMutations();
  await mount(); await settle();
  await begin(() => deleteButtons()[0].props.onClick());
  await complete(() => pending[0].succeed());
  await click(button("本页全选"));
  const undo = button("撤销").props.onClick;
  const remove = deleteButtons()[1].props.onClick;
  const bulk = button("批量删除(2)").props.onClick;
  await begin(() => { bulk(); bulk(); undo(); remove(); });
  assert.equal(pending.length, 3);
  assert.equal(button("撤销").props.disabled, true);
  assert(deleteButtons().every(node => node.props.disabled));
  await complete(() => pending[1].fail());
  assert.equal(button("撤销").props.disabled, true);
  await begin(undo);
  assert.equal(pending.length, 3);
  assert.equal(alerts.length, 0);
  await complete(() => pending[2].succeed());
  assert.equal(Boolean(button("撤销").props.disabled), false);
  assert.equal(alerts.length, 1);
});


test("a new query clears the previous error before dispatch and can fail independently", async () => {
  listAdapter = async config => { throw { config, response: { status: 500 } }; };
  await mount(); await settle();
  assert.match(output(), caseErrorText);
  change(search(), "新的失败查询");
  assert.equal(caseAlerts().length, 0);
  assert.doesNotMatch(output(), /暂无病例/);
  await settle();
  assert.match(output(), caseErrorText);
  assert.equal(caseRequests().at(-1).params.q, "新的失败查询");
});

test("a successful empty retry shows the empty state instead of a lingering error", async () => {
  listAdapter = async config => { throw { config, response: { status: 500 } }; };
  await mount(); await settle();
  assert.match(output(), caseErrorText);
  listAdapter = async config => ({ config, status: 200, data: { items: [], total: 0 } });
  await click(button("重试"));
  assert.match(output(), /暂无病例。/);
  assert.equal(caseAlerts().length, 0);
  assert.equal(button("重试"), undefined);
});
