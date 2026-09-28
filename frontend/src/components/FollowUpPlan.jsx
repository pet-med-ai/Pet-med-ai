import React, { useEffect, useRef, useState } from "react";
import api from "../api";
import { draftOwner } from "../consultDraft";
import { loadPlanLocal, savePlanDraft, savePlanAttempt, clearPlanDraft, clearPlanAttempt } from "../followUpPlanState";

const textStyle = { whiteSpace: "pre-wrap", overflowWrap: "anywhere", font: "inherit" };
const hash = value => typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
const errorText = error => typeof error?.response?.data?.detail === "string" ? error.response.data.detail : error.message || "请求未完成，请核对后继续。";
function validateState(data, caseId) {
  if (data?.case_id !== caseId || !hash(data.state_token) || typeof data.account_id !== "string" ||
      !Array.isArray(data.items) || data.items.some(r => !Number.isSafeInteger(r.id) || r.case_id !== caseId || typeof r.managed !== "boolean") ||
      typeof data.can_write !== "boolean" || typeof data.conflict !== "string" || data.writes_database !== false ||
      (data.current !== null && !data.items.some(r => r.id === data.current?.id && r.status === "due" && r.managed))) {
    throw Error("未收到完整复查记录，请重新读取，暂不能保存。");
  }
  return data;
}
function validateReceipt(receipt, attempt, caseId, accountId) {
  const r = attempt.request;
  if (receipt?.case_id !== caseId || receipt.account_id !== accountId || receipt.request_id !== r.request_id ||
      receipt.action !== r.action || receipt.before_state_token !== r.expected_state_token || !hash(receipt.after_state_token) ||
      (r.action === "cancel" ? receipt.after !== null : receipt.after?.due_date !== r.due_date || receipt.after?.note !== r.note || receipt.after?.status !== "due") ||
      (r.action === "create" ? receipt.cancelled !== null : receipt.cancelled?.id !== attempt.before_id || receipt.cancelled?.status !== "cancelled")) {
    throw Error("回执与本次核对请求不一致，暂不能确认保存结果。");
  }
}

export default function FollowUpPlan({ caseId, requestToken, onChanged, onClose }) {
  const owner = draftOwner(requestToken), base = `/api/cases/${caseId}/follow-up`;
  const mounted = useRef(false), pendingCall = useRef(false), epoch = useRef(0);
  const callbacks = useRef({ onChanged, onClose }); callbacks.current = { onChanged, onClose };
  const [server, setServer] = useState(null), [values, setValues] = useState({ due_date: "", note: "" });
  const [recovered, setRecovered] = useState(null), [attempt, setAttempt] = useState(null);
  const [blocked, setBlocked] = useState(false), [preview, setPreview] = useState(null);
  const [checked, setChecked] = useState(false), [busy, setBusy] = useState(false), [canRetry, setCanRetry] = useState(false);
  const [message, setMessage] = useState(""), [draftMessage, setDraftMessage] = useState("");
  const heading = useRef(null), revision = useRef("");
  revision.current = JSON.stringify(values);
  const current = stamp => mounted.current && epoch.current === stamp && owner && localStorage.getItem("token") === requestToken;
  const config = () => ({ timeout: 15000, expectedAuthOwner: owner });
  const editable = !busy && !blocked && !attempt && server?.can_write;

  async function readState() {
    const response = await api.get(base, config());
    return validateState(response.data, caseId);
  }
  async function load() {
    if (pendingCall.current || !current(epoch.current)) return;
    pendingCall.current = true; setBusy(true); setPreview(null); setChecked(false);
    const stamp = epoch.current;
    try { const data = await readState(); if (current(stamp)) { setServer(data); setMessage(data.conflict); } }
    catch (error) { if (current(stamp)) { setServer(null); setMessage(errorText(error)); } }
    finally { if (current(stamp)) { pendingCall.current = false; setBusy(false); } }
  }
  useEffect(() => {
    mounted.current = true; epoch.current++; pendingCall.current = false;
    heading.current?.focus();
    if (!owner) { setBlocked(true); setMessage("请重新登录后打开复查计划。"); return () => { mounted.current = false; epoch.current++; }; }
    const local = loadPlanLocal(owner, caseId);
    setRecovered(local.draft); setAttempt(local.attempt); setBlocked(local.blocked); setDraftMessage(local.message);
    void load();
    return () => { mounted.current = false; epoch.current++; };
  }, [caseId, requestToken]);
  useEffect(() => {
    if (!values.due_date && !values.note && !attempt) return;
    const warn = event => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [values, attempt]);

  function change(next) {
    if (!editable || pendingCall.current || !current(epoch.current)) return;
    setValues(next); setPreview(null); setChecked(false); setRecovered(null);
    setDraftMessage(savePlanDraft(owner, caseId, next) ? "输入已暂存于当前标签页，尚未保存为复查计划。" : "本地暂存失败，请保留输入；关闭页面可能丢失未提交内容。");
  }
  async function requestPreview(action) {
    if (!editable || pendingCall.current || !current(epoch.current)) return;
    pendingCall.current = true; setBusy(true); setChecked(false); setPreview(null); setMessage("");
    const stamp = epoch.current, version = revision.current;
    const request = { action, expected_state_token: server.state_token,
      due_date: action === "cancel" ? null : values.due_date, note: action === "cancel" ? null : values.note };
    try {
      const { data } = await api.post(base + "/preview", request, config());
      if (!current(stamp) || version !== revision.current) return;
      if (data.case_id !== caseId || data.state_token !== server.state_token || data.action !== action || !hash(data.preview_token) ||
          data.writes_database !== false || (data.before?.id ?? null) !== (server.current?.id ?? null) ||
          (action === "cancel" ? data.proposed !== null : data.proposed?.due_date !== values.due_date || data.proposed?.note !== values.note)) {
        throw Error("预览与输入不一致，请重新读取后核对。");
      }
      setPreview({ ...data, request, revision: version });
    } catch (error) { if (current(stamp)) setMessage(errorText(error)); }
    finally { if (current(stamp)) { pendingCall.current = false; setBusy(false); } }
  }
  async function verify(saved, stamp) {
    const { data } = await api.get(base + "/receipts/" + saved.request.request_id, config());
    if (!current(stamp)) return;
    if (data.case_id !== caseId || data.request_id !== saved.request.request_id || data.writes_database !== false ||
        !["committed", "not_found"].includes(data.status)) throw Error("未收到有效操作回执，请继续核对结果。");
    if (data.status === "not_found") {
      if (data.receipt !== null) throw Error("回执格式不一致，请继续核对。");
      if (saved.rejected) {
        const fresh = await readState(); if (!current(stamp)) return;
        if (!clearPlanAttempt(owner, caseId)) throw Error("本次请求被拒绝，但待核对记录未能清除，暂不能重新提交。");
        setAttempt(null); setServer(fresh); setPreview(null); setChecked(false);
        setMessage("本次请求已被服务拒绝，未查到成功回执。已读取当前计划，请保留输入并重新核对。");
      } else {
        setCanRetry(true); setChecked(false);
        setMessage("尚未查到本次回执，结果仍待核对。可继续查询，或核对原内容后使用同一请求重试。");
      }
      return;
    }
    validateReceipt(data.receipt, saved, caseId, server.account_id);
    const fresh = await readState(); if (!current(stamp)) return;
    if (!clearPlanAttempt(owner, caseId)) throw Error("保存回执已确认，但本地待核对记录未能清除，请继续核对结果。");
    const clean = clearPlanDraft(owner, caseId);
    setAttempt(null); setRecovered(null); setValues({ due_date: "", note: "" }); setPreview(null); setChecked(false); setCanRetry(false);
    setServer(fresh); setDraftMessage(clean ? "" : "已核实保存，但旧输入暂存未能清除。再次打开时请勿误恢复旧输入。");
    setMessage("本次操作已保存并核实；当前计划以服务器回读为准。"); callbacks.current.onChanged?.();
  }
  async function checkResult() {
    if (!attempt || pendingCall.current || !server || !current(epoch.current)) return;
    pendingCall.current = true; setBusy(true); setCanRetry(false); setChecked(false);
    const stamp = epoch.current;
    try { await verify(attempt, stamp); }
    catch (error) { if (current(stamp)) setMessage(errorText(error)); }
    finally { if (current(stamp)) { pendingCall.current = false; setBusy(false); } }
  }
  async function submit(retry = false) {
    if (pendingCall.current || blocked || !server?.can_write || !current(epoch.current) || !checked) return;
    if (retry ? !attempt || !canRetry : attempt || !preview || preview.revision !== revision.current) return;
    let saved = attempt;
    if (!retry) {
      try {
        saved = { request: { ...preview.request, expected_preview_token: preview.preview_token,
          request_id: crypto.randomUUID().replaceAll("-", "") }, before_id: preview.before?.id ?? null, rejected: false };
      } catch { setMessage("当前浏览器无法建立安全操作标识，暂不能提交。"); return; }
      if (!savePlanAttempt(owner, caseId, saved)) { setBlocked(true); setMessage("待核对请求未能可靠暂存，尚未发出保存请求。请保留输入并检查浏览器存储。"); return; }
      setAttempt(saved);
    }
    pendingCall.current = true; setBusy(true); setChecked(false); setCanRetry(false); setMessage("正在提交并核对保存结果…");
    const stamp = epoch.current;
    try {
      try { await api.post(base + "/confirm", saved.request, config()); }
      catch (error) {
        if (!current(stamp)) return;
        if ([400, 409, 422].includes(error?.response?.status)) {
          saved = { ...saved, rejected: true }; savePlanAttempt(owner, caseId, saved); setAttempt(saved);
        }
        setMessage(errorText(error) + " 正在核对服务器回执。");
      }
      if (current(stamp)) await verify(saved, stamp);
    } catch (error) { if (current(stamp)) setMessage(errorText(error) + " 保存结果仍待核对，请勿另建请求。"); }
    finally { if (current(stamp)) { pendingCall.current = false; setBusy(false); } }
  }
  function close() { mounted.current = false; epoch.current++; callbacks.current.onClose?.(); }
  if (localStorage.getItem("token") !== requestToken) return <p role="status">登录已变化，请重新打开复查计划。</p>;
  return <section aria-label="医生复查计划" className="screen-only" style={{ border: "1px solid #a3b8aa", borderRadius: 12, padding: 18, margin: "18px 0" }}>
    <h2 ref={heading} tabIndex={-1}>医生复查计划</h2>
    <p>医生手工填写日期与说明。日期按北京时间，不代表预约时段。</p>
    <button type="button" onClick={close}>关闭复查计划</button>{" "}
    <button type="button" disabled={busy} onClick={load}>重新读取复查计划</button>
    {message && <p role="status">{message}</p>}{draftMessage && <p role="status">{draftMessage}</p>}
    {server && <section aria-label="服务器复查记录"><h3>当前已保存计划</h3>
      {server.conflict ? <p>{server.conflict}</p> : server.current ? <>
        <p>复查日期：{server.current.due_date}</p><pre style={textStyle}>{server.current.note}</pre>
        <button type="button" disabled={!editable} onClick={() => change({ due_date: server.current.due_date, note: server.current.note })}>填入当前计划进行更正</button>{" "}
        <button type="button" disabled={!editable} onClick={() => requestPreview("cancel")}>核对撤销当前计划</button>
      </> : <p>{server.items.length ? "当前无有效复查计划，历史记录保留。" : "尚未记录复查计划。"}</p>}
      {server.items.length > 0 && <details><summary>查看复查历史（{server.items.length} 条）</summary>
        {server.items.map(item => <article key={item.id}><p>#{item.id} · {item.managed ? item.due_date : item.due_at_stored} · {item.status === "cancelled" ? "已撤销" : item.status === "due" ? "计划中" : item.status}{!item.managed && " · 历史记录，需单独核对"}</p><pre style={textStyle}>{item.note}</pre></article>)}
      </details>}
    </section>}
    {recovered && !attempt && <section aria-label="复查输入恢复"><p>发现本标签页暂存输入，恢复后需要重新核对。</p>
      <button type="button" disabled={!editable} onClick={() => change(recovered)}>恢复复查输入</button>{" "}
      <button type="button" disabled={!editable} onClick={() => { if (clearPlanDraft(owner, caseId)) { setRecovered(null); setDraftMessage("已丢弃未提交输入。"); } else setDraftMessage("未能清除暂存输入。"); }}>丢弃复查输入</button>
    </section>}
    {!attempt && <div>
      <label>复查日期<input type="date" aria-label="复查日期" disabled={!editable} value={values.due_date} onChange={e => change({ ...values, due_date: e.target.value })} /></label>
      <label style={{ display: "block", marginTop: 12 }}>医生复查说明<textarea aria-label="医生复查说明" rows={5} maxLength={8000} disabled={!editable} value={values.note} onChange={e => change({ ...values, note: e.target.value })} style={{ display: "block", width: "100%", boxSizing: "border-box" }} /></label>
      <button type="button" disabled={!editable || !values.due_date || !values.note.trim()} onClick={() => requestPreview(server.current ? "replace" : "create")}>核对复查计划</button>
    </div>}
    {preview && !attempt && <section aria-label="复查保存核对"><h3>{preview.action === "cancel" ? "核对撤销：旧计划保留，下方未提交输入不会保存" : "核对本次复查计划"}</h3>
      <p>病例 #{caseId} · {preview.patient_name}</p>
      {preview.before && <><h4>原计划</h4><p>{preview.before.due_date}</p><pre style={textStyle}>{preview.before.note}</pre></>}
      {preview.proposed && <><h4>本次计划</h4><p>{preview.proposed.due_date}</p><pre style={textStyle}>{preview.proposed.note}</pre></>}
      <label><input type="checkbox" checked={checked} disabled={busy} onChange={e => setChecked(e.target.checked)} /> 已核对本次复查操作</label>{" "}
      <button type="button" disabled={busy || !checked || preview.revision !== revision.current} onClick={() => submit()}>确认并保存复查操作</button>
    </section>}
    {attempt && <section aria-label="复查保存结果待核对"><h3>保存结果待核对</h3>
      <p>{attempt.request.action === "cancel" ? "撤销原计划" : attempt.request.action === "replace" ? "更正原计划" : "新增计划"} · {attempt.request.due_date}</p><pre style={textStyle}>{attempt.request.note}</pre>
      <button type="button" disabled={busy || !server} onClick={checkResult}>核对复查保存结果</button>
      {canRetry && <><label><input type="checkbox" disabled={busy} checked={checked} onChange={e => setChecked(e.target.checked)} /> 已重新核对原请求内容</label>
        <button type="button" disabled={busy || !checked || !server?.can_write} onClick={() => submit(true)}>使用同一请求重试</button></>}
    </section>}
  </section>;
}
