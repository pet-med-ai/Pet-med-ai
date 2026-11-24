import React, { useEffect, useRef, useState } from "react";

import TreatmentWorkspace from "./TreatmentWorkspace";
const treatmentEnabled = import.meta.env.VITE_TREATMENT_PILOT === "1";

const base = (import.meta.env.VITE_API_BASE || "").replace(/\/$/, "");
const basicFields = [
  ["patient_name", "宠物名称"], ["species", "物种"], ["sex", "性别"], ["age_info", "年龄"],
  ["owner_name", "宠主"], ["owner_phone", "联系电话"],
];
const clinicalFields = [
  ...basicFields, ["chief_complaint", "主诉"],
  ["history", "病史"], ["exam_findings", "检查"], ["analysis", "分析原文"],
  ["treatment", "治疗原文（未经本系统签署）"], ["prognosis", "预后原文"],
];

const projections = [
  { value: "clinical", label: "诊疗资料", permission: "clinical.read" },
  { value: "demographics", label: "基本资料", permission: "patient.demographics.read" },
];
function availableProjections(scope) {
  return projections.filter(item => scope?.permissions.includes(item.permission));
}

export default function ClinicReadPilot() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState("");
  const [scopes, setScopes] = useState([]);
  const [scopeKey, setScopeKey] = useState("");
  const [activeProjection, setActiveProjection] = useState("");
  const [caseNumber, setCaseNumber] = useState("");
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
  function clearSession() { setToken(""); setScopes([]); setScopeKey(""); setActiveProjection(""); setCaseNumber(""); clearContent(); }
  async function request(path, auth, signal, body) {
    const response = await fetch(base + "/api/v2" + path, {
      method: body === undefined ? "GET" : "POST", signal, cache: "no-store", credentials: "omit",
      headers: { ...(auth ? { Authorization: `Bearer ${auth}` } : {}), ...(body === undefined ? {} : { "Content-Type": "application/json" }) },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });
    if (!response.ok) throw Object.assign(new Error("request failed"), { status: response.status });
    return response.status === 204 ? null : response.json();
  }
  function failed(error, task, keepCurrent = false) {
    if (!task.current() || error.name === "AbortError") return;
    if (error.status === 401) { clearSession(); setMessage("登录已失效，请重新登录。旧页面内容已清除。"); return; }
    if (!keepCurrent) clearContent();
    const reason = error.status === 404 ? "病例不存在或当前账号无权查看。" : "读取失败。请核对服务和院区权限后重试。";
    setMessage(keepCurrent && detail ? `${reason} 当前仍显示病例 #${detail.id}。` : reason);
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
  async function loadScope(key, after = 0, preferred = key === scopeKey ? activeProjection : "") {
    const scope = selected(key);
    const allowed = availableProjections(scope);
    const view = preferred ? allowed.find(item => item.value === preferred) : allowed[0];
    const nextProjection = view?.value || "";
    if (key !== scopeKey || nextProjection !== activeProjection) setCaseNumber("");
    const task = resetWork();
    setScopeKey(key); setActiveProjection(nextProjection); clearContent(); setMessage("");
    if (!view) { setBusy(false); return; }
    setBusy(true);
    try {
      const data = await request(`${pathFor(scope)}?projection=${nextProjection}&after=${after}`, token, task.signal);
      if (!task.current()) return;
      setRows(data.items); setNextAfter(data.next_after);
      if (!data.items.length) setMessage("当前资料范围内没有可查看的病例。");
    } catch (error) { failed(error, task); }
    finally { if (task.current()) setBusy(false); }
  }
  async function openCase(id, { keepCurrent = false } = {}) {
    const task = resetWork();
    if (!keepCurrent) setDetail(null);
    setMessage(""); setBusy(true);
    const scope = selected();
    try {
      const data = await request(`${pathFor(scope)}/${id}?projection=${activeProjection}`, token, task.signal);
      if (task.current()) setDetail(data);
    } catch (error) { failed(error, task, keepCurrent); }
    finally { if (task.current()) setBusy(false); }
  }
  function lookupCase(event) {
    event.preventDefault();
    if (!activeProjection || busy) return;
    const id = caseNumber.trim().replace(/^0+/, "");
    // Case.id is a PostgreSQL INTEGER. Preserve the entered digits until validated.
    if (!/^[1-9][0-9]{0,9}$/.test(id) || (id.length === 10 && id > "2147483647")) {
      setMessage("请输入 1 到 2147483647 之间的整数病例号。");
      return;
    }
    if (String(detail?.id) === id) {
      setMessage("当前已打开该病例。");
      return;
    }
    return openCase(id, { keepCurrent: true });
  }
  async function logout() {
    const task = resetWork(); const oldToken = token; clearSession(); setBusy(false); setMessage("已退出本页。");
    try { await request("/auth/logout", oldToken, task.signal, {}); }
    catch { if (task.current()) setMessage("本页已退出；服务端会话撤销未确认，该会话最多 15 分钟后到期。"); }
  }
  const scope = selected();
  const views = availableProjections(scope);
  const fields = activeProjection === "clinical" ? clinicalFields : basicFields;
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
      {views.length > 1 && <label> 资料范围 <select aria-label="资料范围" value={activeProjection}
        onChange={event => loadScope(scopeKey, 0, event.target.value)}>
        {views.map(view => <option key={view.value} value={view.value}>{view.label}</option>)}
      </select></label>}
      <p><button onClick={() => loadScope(scopeKey)} disabled={!activeProjection || busy}>重新读取病例</button></p>
      {activeProjection && <form onSubmit={lookupCase} aria-label="按病例号查阅">
        <label>病例号 <input type="text" inputMode="numeric" autoComplete="off"
          value={caseNumber} onChange={event => setCaseNumber(event.target.value)} disabled={busy} /></label>{" "}
        <button type="submit" disabled={busy}>按号查看</button>
      </form>}
      {rows.length > 0 && <table style={{ width: "100%", textAlign: "left" }}><thead><tr><th>病例</th><th>名称</th><th>物种</th><th>操作</th></tr></thead>
        <tbody>{rows.map(row => <tr key={row.id}><td>#{row.id}</td><td>{row.patient_name}</td><td>{row.species}</td><td><button disabled={busy} onClick={() => openCase(row.id)}>查看</button></td></tr>)}</tbody></table>}
      {nextAfter !== null && <button disabled={busy} onClick={() => loadScope(scopeKey, nextAfter)}>下一页</button>}
    </>}
    {busy && <p role="status">正在读取……</p>}
    {message && <p role="status">{message}</p>}
    {detail && <section aria-label="病例详情"><h2>病例 #{detail.id} · {detail.patient_name}</h2>
      <p>{scope?.org_name}／{scope?.clinic_name} · {detail.visibility === "owner_private" ? "原账号私人病例" : "院区病例"}</p>
      <dl>{fields.filter(([key]) => Object.hasOwn(detail, key)).map(([key, label]) => <React.Fragment key={key}>
        <dt style={{ fontWeight: 700, marginTop: 16 }}>{label}</dt><dd style={{ marginLeft: 0, whiteSpace: "pre-wrap" }}>{detail[key] || "未记录"}</dd>
      </React.Fragment>)}</dl>
      {treatmentEnabled && activeProjection === "clinical" && <TreatmentWorkspace key={`${scopeKey}/${detail.id}/${token}`} token={token} scope={scope} caseId={detail.id} />}
      </section>}
  </main>;
}
