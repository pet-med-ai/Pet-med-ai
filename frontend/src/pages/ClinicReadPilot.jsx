import React, { useEffect, useRef, useState } from "react";

import TreatmentWorkspace from "./TreatmentWorkspace";
const treatmentEnabled = import.meta.env.VITE_TREATMENT_PILOT === "1";

const base = (import.meta.env.VITE_API_BASE || "").replace(/\/$/, "");
const fields = [
  ["patient_name", "宠物名称"], ["species", "物种"], ["sex", "性别"], ["age_info", "年龄"],
  ["owner_name", "宠主"], ["owner_phone", "联系电话"], ["chief_complaint", "主诉"],
  ["history", "病史"], ["exam_findings", "检查"], ["analysis", "分析原文"],
  ["treatment", "治疗原文（未经本系统签署）"], ["prognosis", "预后原文"],
];

export default function ClinicReadPilot() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState("");
  const [scopes, setScopes] = useState([]);
  const [scopeKey, setScopeKey] = useState("");
  const [rows, setRows] = useState([]);
  const [detail, setDetail] = useState(null);
  const [nextAfter, setNextAfter] = useState(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const work = useRef({ epoch: 0, abort: null });

  useEffect(() => () => { work.current.epoch++; work.current.abort?.abort(); }, []);
  function resetWork() {
    work.current.abort?.abort();
    const abort = new AbortController();
    const epoch = ++work.current.epoch;
    work.current.abort = abort;
    return { signal: abort.signal, current: () => work.current.epoch === epoch };
  }
  function clearContent() { setRows([]); setDetail(null); setNextAfter(null); }
  function clearSession() { setToken(""); setScopes([]); setScopeKey(""); clearContent(); }
  async function request(path, auth, signal, body) {
    const response = await fetch(base + "/api/v2" + path, {
      method: body === undefined ? "GET" : "POST", signal, cache: "no-store", credentials: "omit",
      headers: { ...(auth ? { Authorization: `Bearer ${auth}` } : {}), ...(body === undefined ? {} : { "Content-Type": "application/json" }) },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });
    if (!response.ok) throw Object.assign(new Error("request failed"), { status: response.status });
    return response.status === 204 ? null : response.json();
  }
  function failed(error, task) {
    if (!task.current() || error.name === "AbortError") return;
    clearContent();
    if (error.status === 401) { clearSession(); setMessage("登录已失效，请重新登录。旧页面内容已清除。"); }
    else if (error.status === 404) setMessage("病例不存在或当前账号无权查看。");
    else setMessage("读取失败。请核对服务和院区权限后重试。");
  }
  async function login(event) {
    event.preventDefault();
    const task = resetWork(); clearSession(); setMessage(""); setBusy(true);
    try {
      const session = await request("/auth/login", "", task.signal, { email, password });
      if (!task.current()) return;
      const available = await request("/scopes", session.access_token, task.signal);
      if (!task.current()) return;
      setToken(session.access_token); setScopes(available.items);
      setMessage(available.items.length ? "请选择院区。" : "当前账号尚无病例读取权限，请联系院内权限管理员。");
    } catch (error) { failed(error, task); }
    finally { if (task.current()) { setPassword(""); setBusy(false); } }
  }
  function selected(key = scopeKey) {
    return scopes.find(item => `${item.org_id}/${item.clinic_id}` === key);
  }
  function pathFor(scope) {
    return `/organizations/${scope.org_id}/clinics/${scope.clinic_id}/cases`;
  }
  function projection(scope) { return scope.permissions.includes("clinical.read") ? "clinical" : "demographics"; }
  async function loadScope(key, after = 0) {
    const task = resetWork(); setScopeKey(key); clearContent(); setMessage("");
    const scope = selected(key);
    if (!scope) { setBusy(false); return; }
    setBusy(true);
    try {
      const data = await request(`${pathFor(scope)}?projection=${projection(scope)}&after=${after}`, token, task.signal);
      if (!task.current()) return;
      setRows(data.items); setNextAfter(data.next_after);
      if (!data.items.length) setMessage("该院区没有当前账号可查看的病例。");
    } catch (error) { failed(error, task); }
    finally { if (task.current()) setBusy(false); }
  }
  async function openCase(id) {
    const task = resetWork(); setDetail(null); setMessage(""); setBusy(true);
    const scope = selected();
    try {
      const data = await request(`${pathFor(scope)}/${id}?projection=${projection(scope)}`, token, task.signal);
      if (task.current()) setDetail(data);
    } catch (error) { failed(error, task); }
    finally { if (task.current()) setBusy(false); }
  }
  async function logout() {
    const task = resetWork(); const oldToken = token; clearSession(); setBusy(false); setMessage("已退出本页。");
    try { await request("/auth/logout", oldToken, task.signal, {}); }
    catch { if (task.current()) setMessage("本页已退出；服务端会话撤销未确认，该会话最多 15 分钟后到期。"); }
  }
  return <main style={{ maxWidth: 960, margin: "32px auto", padding: 20, fontFamily: "system-ui, sans-serif" }}>
    <h1>{treatmentEnabled ? "院区病例与治疗记录" : "院区病例查阅"}</h1>
    <p>{treatmentEnabled ? "病例资料按院区授权读取；治疗记录在下方独立审核、冻结和签署。" : "当前开放病例查阅。治疗原文保留原始记录状态，本入口尚未开放编辑、处方或签署。"}</p>
    {!token ? <form onSubmit={login}>
      <p><label>邮箱 <input type="email" required autoComplete="username" value={email} onChange={e => setEmail(e.target.value)} disabled={busy} /></label></p>
      <p><label>密码 <input type="password" required autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} disabled={busy} /></label></p>
      <button disabled={busy}>登录</button>
    </form> : <>
      <label>机构／院区 <select aria-label="机构／院区" value={scopeKey} onChange={e => loadScope(e.target.value)}>
        <option value="">请选择</option>
        {scopes.map(item => <option key={`${item.org_id}/${item.clinic_id}`} value={`${item.org_id}/${item.clinic_id}`}>{item.org_name}／{item.clinic_name}</option>)}
      </select></label>{" "}<button onClick={logout}>退出登录</button>
      <p><button onClick={() => loadScope(scopeKey)} disabled={!scopeKey || busy}>重新读取病例</button></p>
      {rows.length > 0 && <table style={{ width: "100%", textAlign: "left" }}><thead><tr><th>病例</th><th>名称</th><th>物种</th><th>操作</th></tr></thead>
        <tbody>{rows.map(row => <tr key={row.id}><td>#{row.id}</td><td>{row.patient_name}</td><td>{row.species}</td><td><button disabled={busy} onClick={() => openCase(row.id)}>查看</button></td></tr>)}</tbody></table>}
      {nextAfter !== null && <button disabled={busy} onClick={() => loadScope(scopeKey, nextAfter)}>下一页</button>}
    </>}
    {busy && <p role="status">正在读取……</p>}
    {message && <p role="status">{message}</p>}
    {detail && <section aria-label="病例详情"><h2>病例 #{detail.id} · {detail.patient_name}</h2>
      <p>{selected()?.org_name}／{selected()?.clinic_name} · {detail.visibility === "owner_private" ? "原账号私人病例" : "院区病例"}</p>
      <dl>{fields.filter(([key]) => Object.hasOwn(detail, key)).map(([key, label]) => <React.Fragment key={key}>
        <dt style={{ fontWeight: 700, marginTop: 16 }}>{label}</dt><dd style={{ marginLeft: 0, whiteSpace: "pre-wrap" }}>{detail[key] || "未记录"}</dd>
      </React.Fragment>)}</dl>
      {treatmentEnabled && projection(selected()) === "clinical" && <TreatmentWorkspace key={`${scopeKey}/${detail.id}/${token}`} token={token} scope={selected()} caseId={detail.id} />}
      </section>}
  </main>;
}
