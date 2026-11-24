import React from "react";
import TestRenderer, { act } from "react-test-renderer";
import { test, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import ClinicReadPilot from "../src/pages/ClinicReadPilot";

let renderer, requests, handler, originalFetch, availableScopes;
const response = (body, status = 200) => ({ ok: status < 400, status, json: async () => body });
const scopes = [
  { org_id: "o1", org_name: "院方 A", clinic_id: "c1", clinic_name: "院区 A", permissions: ["clinical.read"] },
  { org_id: "o1", org_name: "院方 A", clinic_id: "c2", clinic_name: "院区 B", permissions: ["patient.demographics.read"] },
];
const output = () => JSON.stringify(renderer.toJSON());
const button = name => renderer.root.findAllByType("button").find(node => node.children.join("") === name);
async function login() {
  if (renderer) act(() => renderer.unmount());
  await act(async () => { renderer = TestRenderer.create(<ClinicReadPilot />); });
  await submitLogin("test@example.invalid");
}
async function submitLogin(email) {
  act(() => renderer.root.findByProps({ type: "email" }).props.onChange({ target: { value: email } }));
  act(() => renderer.root.findByProps({ type: "password" }).props.onChange({ target: { value: "synthetic" } }));
  await act(async () => { await renderer.root.findByType("form").props.onSubmit({ preventDefault() {} }); });
}
async function select(value) {
  await act(async () => { await renderer.root.findByProps({ "aria-label": "机构／院区" }).props.onChange({ target: { value } }); });
}
function typeCaseNumber(value) {
  act(() => renderer.root.findByProps({ inputMode: "numeric" }).props.onChange({ target: { value } }));
}
function submitLookup() {
  return renderer.root.findByProps({ "aria-label": "按病例号查阅" }).props.onSubmit({ preventDefault() {} });
}
beforeEach(() => {
  originalFetch = global.fetch; requests = []; availableScopes = scopes;
  handler = async url => response({ items: [{ id: 1, patient_name: "犬 A", species: "dog" }], next_after: null });
  global.fetch = async (url, options) => {
    requests.push({ url, options });
    if (url.endsWith("/auth/login")) return response({ access_token: "new-session" });
    if (url.endsWith("/scopes")) return response({ items: availableScopes });
    if (url.endsWith("/auth/logout")) return response(null, 204);
    return handler(url, options);
  };
});
afterEach(() => { if (renderer) act(() => renderer.unmount()); renderer = null; global.fetch = originalFetch; });

test("requires explicit clinic selection and uses projection without the legacy credential store", async () => {
  await login();
  assert.equal(requests.length, 2);
  await select("o1/c2");
  assert.match(requests.at(-1).url, /organizations\/o1\/clinics\/c2\/cases\?projection=demographics/);
  assert.equal(requests.at(-1).options.headers.Authorization, "Bearer new-session");
  assert.equal(requests.at(-1).options.credentials, "omit");
  assert.equal(requests.at(-1).options.cache, "no-store");
  assert.doesNotMatch(output(), /确认签署|确认保存|导出/);
});

test("late clinic A result cannot replace clinic B after a switch, even if abort is ignored", async () => {
  await login(); let release;
  handler = url => url.includes("/c1/") ? new Promise(resolve => { release = resolve; }) : response({ items: [{ id: 2, patient_name: "猫 B", species: "cat" }], next_after: null });
  let pending;
  act(() => { pending = renderer.root.findByProps({ "aria-label": "机构／院区" }).props.onChange({ target: { value: "o1/c1" } }); });
  await select("o1/c2");
  await act(async () => { release(response({ items: [{ id: 1, patient_name: "旧犬敏感信息" }], next_after: null })); await pending; });
  assert.match(output(), /猫 B/); assert.doesNotMatch(output(), /旧犬敏感信息/);
});

test("401 removes case data and credentials; a late old 401 cannot clear a newer scope", async () => {
  await login(); await select("o1/c1");
  handler = async () => response({}, 401);
  await act(async () => { await button("查看").props.onClick(); });
  assert.match(output(), /登录已失效/); assert.doesNotMatch(output(), /犬 A/);
  assert.equal(renderer.root.findAllByType("select").length, 0);
  await login(); let release; let pending;
  handler = url => url.includes("/c1/") ? new Promise(resolve => { release = resolve; }) : response({ items: [{ id: 2, patient_name: "猫 B" }], next_after: null });
  act(() => { pending = renderer.root.findByProps({ "aria-label": "机构／院区" }).props.onChange({ target: { value: "o1/c1" } }); });
  await select("o1/c2");
  await act(async () => { release(response({}, 401)); await pending; });
  assert.match(output(), /猫 B/); assert.equal(renderer.root.findAllByType("select").length, 1);
});

test("switching clinic clears open clinical content immediately and logout revokes the session", async () => {
  await login(); await select("o1/c1");
  handler = async () => response({ id: 1, patient_name: "犬 A", treatment: "保留原文 café 🐾\n{{literal}}" });
  await act(async () => { await button("查看").props.onClick(); });
  assert.match(output(), /保留原文/); assert.match(output(), /未经本系统签署/);
  await select(""); assert.doesNotMatch(output(), /保留原文/);
  await act(async () => { await button("退出登录").props.onClick(); });
  assert.equal(requests.at(-1).url, "/api/v2/auth/logout");
  assert.equal(requests.at(-1).options.method, "POST");
  assert.doesNotMatch(output(), /犬 A/);
});

test("case number lookup opens an off-page record only after an explicit scoped submit", async () => {
  await login();
  assert.equal(renderer.root.findAllByProps({ inputMode: "numeric" }).length, 0);
  await select("o1/c1");
  const before = requests.length;
  typeCaseNumber(" 000207 ");
  assert.equal(requests.length, before);
  handler = async () => response({ id: 207, patient_name: "已定位病例", history: "合成临床记录" });
  await act(async () => { await submitLookup(); });
  assert.equal(requests.length, before + 1);
  const { url, options } = requests.at(-1);
  assert.equal(url, "/api/v2/organizations/o1/clinics/c1/cases/207?projection=clinical");
  assert.equal(options.method, "GET");
  assert.equal(options.headers.Authorization, "Bearer new-session");
  assert.equal(options.cache, "no-store");
  assert.match(output(), /合成临床记录/);

  typeCaseNumber("207");
  await act(async () => { await submitLookup(); });
  assert.equal(requests.length, before + 1);
  assert.match(output(), /合成临床记录/);
});

test("invalid case numbers send no request and preserve the current detail", async () => {
  await login(); await select("o1/c1");
  handler = async () => response({ id: 1, patient_name: "详情中的原文" });
  await act(async () => { await button("查看").props.onClick(); });
  const before = requests.length;
  for (const value of ["", "  ", "0", "-2", "+2", "1.5", "1e2", "3/4", "2147483648", "9007199254740993"]) {
    typeCaseNumber(value);
    await act(async () => { await submitLookup(); });
    assert.equal(requests.length, before, value);
    assert.match(output(), /整数病例号/);
    assert.match(output(), /详情中的原文/);
  }
});

test("an unsuccessful lookup keeps the open workspace mounted until another case is found", async () => {
  await login(); await select("o1/c1");
  handler = async () => response({ id: 1, patient_name: "原病例详情" });
  await act(async () => { await button("查看").props.onClick(); });
  const detail = () => renderer.root.findByProps({ "aria-label": "病例详情" });
  const original = detail();
  for (const status of [404, 503]) {
    let finish, pending;
    handler = () => new Promise(resolve => { finish = resolve; });
    typeCaseNumber("207");
    act(() => { pending = submitLookup(); });
    assert.equal(detail(), original);
    await act(async () => { finish(response({}, status)); await pending; });
    assert.equal(detail(), original);
    assert.match(output(), /原病例详情/);
    assert.match(output(), /当前仍显示病例 #1/);
  }
  handler = async () => response({ id: 207, patient_name: "新病例详情" });
  await act(async () => { await submitLookup(); });
  assert.doesNotMatch(output(), /原病例详情/);
  assert.match(output(), /新病例详情/);
});

test("frontdesk lookup retains the demographic projection, including the maximum case ID", async () => {
  await login(); await select("o1/c2");
  handler = async () => response({ id: 2147483647, patient_name: "合成前台病例" });
  typeCaseNumber("2147483647");
  await act(async () => { await submitLookup(); });
  assert.equal(requests.at(-1).url, "/api/v2/organizations/o1/clinics/c2/cases/2147483647?projection=demographics");
  assert.match(output(), /合成前台病例/);
  assert.doesNotMatch(output(), /治疗评估|治疗原文（未经本系统签署）/);
});

test("lookup uses one denial message and clears the session on a current 401", async () => {
  await login(); await select("o1/c1");
  for (const reason of ["synthetic missing", "synthetic unauthorized"]) {
    handler = async () => response({ detail: reason }, 404);
    typeCaseNumber("987");
    await act(async () => { await submitLookup(); });
    assert.match(output(), /病例不存在或当前账号无权查看/);
    assert.doesNotMatch(output(), /synthetic missing|synthetic unauthorized/);
  }
  handler = async () => response({}, 401);
  await act(async () => { await submitLookup(); });
  assert.match(output(), /登录已失效/);
  assert.equal(renderer.root.findAllByProps({ inputMode: "numeric" }).length, 0);
  assert.doesNotMatch(output(), /987/);
});

test("late case lookup cannot display data or expire a different clinic, even when abort is ignored", async () => {
  await login();
  for (const status of [200, 401]) {
    await select("o1/c1");
    let finish, pending;
    handler = url => url.includes("/cases/1234?")
      ? new Promise(resolve => { finish = resolve; })
      : response({ items: [{ id: 2, patient_name: "当前院区合成猫" }], next_after: null });
    typeCaseNumber("1234");
    act(() => { pending = submitLookup(); });
    const firstSignal = requests.at(-1).options.signal;
    await select("o1/c2");
    assert.equal(firstSignal.aborted, true);
    assert.equal(renderer.root.findByProps({ inputMode: "numeric" }).props.value, "");
    await act(async () => { finish(response({ id: 1234, patient_name: "上个院区私有病例" }, status)); await pending; });
    assert.doesNotMatch(output(), /1234|上个院区私有病例|登录已失效/);
    assert.match(output(), /当前院区合成猫/);
  }
});

test("logout and signing in as a different user clear the entered case number and ignore a late lookup", async () => {
  await login(); await select("o1/c1");
  let finish, pending;
  handler = url => url.includes("/cases/7654?")
    ? new Promise(resolve => { finish = resolve; })
    : response({ items: [{ id: 3, patient_name: "新账号病例" }], next_after: null });
  typeCaseNumber("7654");
  act(() => { pending = submitLookup(); });
  await act(async () => { await button("退出登录").props.onClick(); });
  assert.doesNotMatch(output(), /7654/);
  await submitLogin("other@example.invalid");
  await select("o1/c2");
  await act(async () => { finish(response({ id: 7654, patient_name: "已退出账号私有记录" })); await pending; });
  assert.equal(renderer.root.findByProps({ inputMode: "numeric" }).props.value, "");
  assert.doesNotMatch(output(), /7654|已退出账号私有记录/);
  assert.match(output(), /新账号病例/);
});

const mixedScope = { ...scopes[0], permissions: ["clinical.read", "patient.demographics.read"] };
const viewPicker = () => renderer.root.findByProps({ "aria-label": "资料范围" });
async function chooseView(value) {
  await act(async () => { await viewPicker().props.onChange({ target: { value } }); });
}

test("mixed permissions require an explicit projection change to open a basic-only case", async () => {
  availableScopes = [mixedScope, scopes[1]];
  await login();
  const root = "/api/v2/organizations/o1/clinics/c1/cases";
  handler = async url => {
    if (url.endsWith("/treatment")) return response({ detail: "合成只读验收" }, 503);
    if (url === root + "/1?projection=clinical") return response({ id: 1, history: "单例授权的诊疗内容" });
    if (url === root + "/207?projection=clinical") return response({}, 404);
    if (url === root + "/207?projection=demographics") return response({ id: 207, patient_name: "基本资料病例", history: "多余的临床字段" });
    const { searchParams } = new URL(url, "http://example.invalid");
    const basic = searchParams.get("projection") === "demographics";
    return response({ items: [{ id: basic ? 207 : 1, patient_name: basic ? "基本资料病例" : "单例授权病例" }],
      next_after: searchParams.get("after") === "0" ? (basic ? 207 : 1) : null });
  };
  await select("o1/c1");
  assert.equal(viewPicker().props.value, "clinical");
  await act(async () => { await button("查看").props.onClick(); });
  assert.match(output(), /单例授权的诊疗内容/);
  const treatmentMounted = renderer.root.findAllByProps({ "aria-label": "治疗签署" }).length > 0;
  assert.equal(treatmentMounted, import.meta.env.VITE_TREATMENT_PILOT === "1");

  typeCaseNumber("207");
  const beforeDenied = requests.length;
  await act(async () => { await submitLookup(); });
  assert.deepEqual(requests.slice(beforeDenied).map(r => r.url), [root + "/207?projection=clinical"]);
  assert.match(output(), /病例不存在或当前账号无权查看/);

  await chooseView("demographics");
  assert.equal(viewPicker().props.value, "demographics");
  assert.equal(requests.at(-1).url, root + "?projection=demographics&after=0");
  assert.equal(renderer.root.findByProps({ inputMode: "numeric" }).props.value, "");
  assert.doesNotMatch(output(), /单例授权的诊疗内容/);
  await act(async () => { await button("下一页").props.onClick(); });
  assert.equal(requests.at(-1).url, root + "?projection=demographics&after=207");
  assert.equal(button("下一页"), undefined);
  await act(async () => { await button("查看").props.onClick(); });
  assert.equal(requests.at(-1).url, root + "/207?projection=demographics");
  assert.doesNotMatch(output(), /多余的临床字段|治疗记录与院内账号确认/);
  await act(async () => { await button("重新读取病例").props.onClick(); });
  assert.equal(requests.at(-1).url, root + "?projection=demographics&after=0");
  typeCaseNumber("207");
  const beforeDirect = requests.length;
  await act(async () => { await submitLookup(); });
  assert.deepEqual(requests.slice(beforeDirect).map(r => r.url), [root + "/207?projection=demographics"]);
  assert.match(output(), /基本资料病例/);
  assert.doesNotMatch(output(), /多余的临床字段|治疗记录与院内账号确认/);
  await select("o1/c2");
  assert.equal(renderer.root.findAllByProps({ "aria-label": "资料范围" }).length, 0);
  await select("o1/c1");
  assert.equal(viewPicker().props.value, "clinical");
  assert.equal(requests.at(-1).url, root + "?projection=clinical&after=0");
});

test("a change of projection clears the previous page and ignores delayed lookup success and 401", async () => {
  availableScopes = [mixedScope];
  await login();
  for (const staleStatus of [200, 401]) {
    handler = async () => response({ items: [{ id: 1, patient_name: "以前的临床列表" }], next_after: 1 });
    await select("");
    await select("o1/c1");
    let finishLookup, finishList, pendingLookup, pendingList;
    handler = url => url.includes("/cases/992?")
      ? new Promise(resolve => { finishLookup = resolve; })
      : new Promise(resolve => { finishList = resolve; });
    typeCaseNumber("992");
    act(() => { pendingLookup = submitLookup(); });
    const firstSignal = requests.at(-1).options.signal;
    act(() => { pendingList = viewPicker().props.onChange({ target: { value: "demographics" } }); });
    assert.equal(firstSignal.aborted, true);
    assert.equal(renderer.root.findByProps({ inputMode: "numeric" }).props.value, "");
    assert.equal(button("下一页"), undefined);
    assert.doesNotMatch(output(), /以前的临床列表/);
    await act(async () => { finishList(response({ items: [{ id: 2, patient_name: "新基本资料" }], next_after: null })); await pendingList; });
    await act(async () => { finishLookup(response({ id: 992, history: "旧视图私有原文" }, staleStatus)); await pendingLookup; });
    assert.doesNotMatch(output(), /992|旧视图私有原文|登录已失效/);
    assert.match(output(), /新基本资料/);
    assert.equal(viewPicker().props.value, "demographics");
  }
});
