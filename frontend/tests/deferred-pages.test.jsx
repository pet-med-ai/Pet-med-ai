import React, { lazy } from "react";
import TestRenderer, { act } from "react-test-renderer";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";
import { test, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import api from "../src/api";
import { AppRoutes, DeferredPage } from "../src/App";

const memory = () => {
  const data = new Map();
  return { getItem: k => data.get(k) ?? null, setItem: (k, v) => data.set(k, String(v)), removeItem: k => data.delete(k), get length() { return data.size; }, key: i => [...data.keys()][i] ?? null };
};
const routeReads = {
  "/ops": ["/healthz", "/api/system/version", "/api/system/feature-flags", "/api/preventive-care/ops/summary", "/api/diagnostic-data/clinical-qa-dashboard/v2/summary"],
  "/preventive-care/notification-queue": ["/api/preventive-care/notification-queue"],
  "/automated-reminder-delivery/manual-approval": ["/api/automated-reminder-delivery/attempts"],
};
let renderer, requests, reloads, errors, originalError, originalAdapter, navigate, allowedReads;
const output = () => JSON.stringify(renderer.toJSON());
function Navigation() { navigate = useNavigate(); return null; }
const mount = async (children, path = "/") => {
  allowedReads = new Set(routeReads[path] || []);
  await act(async () => {
    renderer = TestRenderer.create(<MemoryRouter initialEntries={[path]}><Navigation />{children}</MemoryRouter>);
  });
};

beforeEach(() => {
  global.localStorage = memory();
  global.window = { sessionStorage: memory(), addEventListener() {}, removeEventListener() {}, location: { reload() { reloads++; } } };
  global.alert = () => assert.fail("Unexpected alert");
  requests = []; errors = []; reloads = 0; renderer = null;
  originalError = console.error; console.error = (...args) => errors.push(args);
  originalAdapter = api.defaults.adapter;
  // All requests stay in memory; allow only the mounted page's existing reads.
  allowedReads = new Set();
  api.defaults.adapter = async config => {
    requests.push(config);
    assert.equal(config.method, "get");
    assert(allowedReads.has(config.url), `Unexpected request: ${config.url}`);
    return { config, status: 200, data: {} };
  };
});
afterEach(() => {
  if (renderer) act(() => renderer.unmount());
  console.error = originalError;
  api.defaults.adapter = originalAdapter;
});

test("anonymous home remains immediately available without loading a secondary page or sending protected requests", async () => {
  await mount(<AppRoutes />);
  assert.match(output(), /请先登录后查看病例列表/);
  assert.doesNotMatch(output(), /页面加载中/);
  assert.equal(requests.length, 0);
  assert.equal(errors.length, 0);
});

for (const [path, title] of [
  ["/kpi", "运维 KPI 仪表盘"],
  ["/ops", "Pet-Med-AI Ops Dashboard"],
  ["/webhooks/emr/inbox", "EMR Webhook Inbox"],
  ["/emr/import-batches", "EMR Real Import Batch Planning"],
  ["/preventive-care/notification-queue", "预防保健前台待联系队列"],
  ["/automated-reminder-delivery/manual-approval", "自动提醒发送人工审批（Dry-run）"],
]) {
  test(`direct navigation still renders ${path}`, async () => {
    await mount(<AppRoutes />, path);
    assert(output().includes(title));
    assert.equal(renderer.root.findAllByProps({ role: "status" }).length, 0);
    assert.equal(renderer.root.findAllByProps({ role: "alert" }).length, 0);
    assert(requests.every(config => config.method === "get"));
    assert.deepEqual(requests.map(config => config.url).sort(), [...(routeReads[path] || [])].sort());
    assert.equal(errors.length, 0);
  });
}

test("a slow page shows a loading message and then renders without refreshing or clearing stored drafts", async () => {
  let resolve;
  const Slow = lazy(() => new Promise(done => { resolve = done; }));
  localStorage.setItem("token", "synthetic-token");
  window.sessionStorage.setItem("synthetic-draft", "unsaved history");
  await mount(<DeferredPage><Slow /></DeferredPage>);
  assert.match(output(), /页面加载中/);
  assert.equal(renderer.root.findByType("a").props.href, "/");
  await act(async () => { resolve({ default: () => <p>合成页面已就绪</p> }); });
  assert.match(output(), /合成页面已就绪/);
  assert.equal(reloads, 0);
  assert.equal(localStorage.getItem("token"), "synthetic-token");
  assert.equal(window.sessionStorage.getItem("synthetic-draft"), "unsaved history");
  assert.equal(requests.length, 0);
  assert.equal(errors.length, 0);
});

test("a failed chunk gives a recovery screen and refresh only occurs on an explicit click", async () => {
  const Broken = lazy(() => Promise.reject(new Error("synthetic chunk download failed")));
  window.sessionStorage.setItem("synthetic-draft", "unsaved history");
  await mount(<DeferredPage><Broken /></DeferredPage>);
  assert.match(output(), /页面加载失败/);
  assert.equal(renderer.root.findByType("a").props.href, "/");
  assert.equal(reloads, 0);
  assert.equal(window.sessionStorage.getItem("synthetic-draft"), "unsaved history");
  assert.equal(requests.length, 0);
  act(() => renderer.root.findByType("button").props.onClick());
  assert.equal(reloads, 1);
});

test("navigating away during a slow download keeps the destination after the old download finishes", async () => {
  let resolve;
  const Slow = lazy(() => new Promise(done => { resolve = done; }));
  await mount(<Routes>
    <Route path="/slow" element={<DeferredPage key="slow"><Slow /></DeferredPage>} />
    <Route path="/" element={<p>首页可继续使用</p>} />
  </Routes>, "/slow");
  assert.match(output(), /页面加载中/);
  await act(async () => navigate("/"));
  await act(async () => resolve({ default: () => <p>过期页面</p> }));
  assert.match(output(), /首页可继续使用/);
  assert.doesNotMatch(output(), /过期页面/);
  assert.equal(reloads, 0);
  assert.equal(errors.length, 0);
});

test("a failed secondary route does not poison a different secondary route or browser back navigation", async () => {
  const Broken = lazy(() => Promise.reject(new Error("synthetic chunk download failed")));
  const Healthy = lazy(async () => ({ default: () => <p>另一个页面正常</p> }));
  await mount(<Routes>
    <Route path="/broken" element={<DeferredPage key="broken"><Broken /></DeferredPage>} />
    <Route path="/healthy" element={<DeferredPage key="healthy"><Healthy /></DeferredPage>} />
    <Route path="/" element={<p>首页正常</p>} />
  </Routes>, "/broken");
  assert.match(output(), /页面加载失败/);
  await act(async () => navigate("/healthy"));
  assert.match(output(), /另一个页面正常/);
  await act(async () => navigate(-1));
  assert.match(output(), /页面加载失败/);
  await act(async () => navigate("/"));
  assert.match(output(), /首页正常/);
  assert.equal(reloads, 0);
  assert.equal(requests.length, 0);
});

test("unknown routes retain the existing 404", async () => {
  await mount(<AppRoutes />, "/missing-synthetic-route");
  assert.match(output(), /页面不存在（404）/);
  assert.equal(requests.length, 0);
  assert.equal(errors.length, 0);
});
