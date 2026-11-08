import React from "react";
import TestRenderer, { act } from "react-test-renderer";
import { test, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import ClinicReadPilot from "../src/pages/ClinicReadPilot";

let renderer, requests, handler, originalFetch;
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
  act(() => renderer.root.findByProps({ type: "email" }).props.onChange({ target: { value: "test@example.invalid" } }));
  act(() => renderer.root.findByProps({ type: "password" }).props.onChange({ target: { value: "synthetic" } }));
  await act(async () => { await renderer.root.findByType("form").props.onSubmit({ preventDefault() {} }); });
}
async function select(value) {
  await act(async () => { await renderer.root.findByType("select").props.onChange({ target: { value } }); });
}
beforeEach(() => {
  originalFetch = global.fetch; requests = [];
  handler = async url => response({ items: [{ id: 1, patient_name: "犬 A", species: "dog" }], next_after: null });
  global.fetch = async (url, options) => {
    requests.push({ url, options });
    if (url.endsWith("/auth/login")) return response({ access_token: "new-session" });
    if (url.endsWith("/scopes")) return response({ items: scopes });
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
  act(() => { pending = renderer.root.findByType("select").props.onChange({ target: { value: "o1/c1" } }); });
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
  act(() => { pending = renderer.root.findByType("select").props.onChange({ target: { value: "o1/c1" } }); });
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
