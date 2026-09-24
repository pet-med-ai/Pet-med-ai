import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";
import { caseEditFields } from "./CaseEditReview";
import { caseEditDraftOwner } from "../caseEditDraft";

const ATTEMPT_KEY = "pmai.manual-create-attempt.v1";
const textStyle = { whiteSpace: "pre-wrap", overflowWrap: "anywhere", fontFamily: "inherit" };
export const manualCasePayload = values => Object.fromEntries(caseEditFields.map(([key]) => {
  const value = values[key] ?? "";
  return [key, key === "species" ? value || "dog" : value === "" ? null : String(value)];
}));
export function clearManualCreateAttempt() {
  try { window.sessionStorage.removeItem(ATTEMPT_KEY); return true; } catch { return false; }
}
export function hasManualCreateAttempt() {
  try { return window.sessionStorage.getItem(ATTEMPT_KEY) !== null; } catch { return true; }
}
function remember(attempt) {
  try { window.sessionStorage.setItem(ATTEMPT_KEY, JSON.stringify(attempt)); return true; } catch { return false; }
}
function recover(owner) {
  try {
    const raw = window.sessionStorage.getItem(ATTEMPT_KEY);
    if (!raw) return null;
    // Expiry is not an explicit logout: retain the private receipt until a
    // valid login can identify its owner, without displaying its contents.
    if (!owner) return { owner: null, payload: null, caseId: null };
    const item = JSON.parse(raw);
    if (item.owner !== owner) { clearManualCreateAttempt(); return null; }
    if (!item.payload || !caseEditFields.every(([key]) => Object.hasOwn(item.payload, key) && (item.payload[key] === null || typeof item.payload[key] === "string")) ||
        (item.caseId !== null && (!Number.isSafeInteger(item.caseId) || item.caseId <= 0))) throw Error("Invalid receipt");
    return item;
  } catch { return { owner, payload: null, caseId: null }; }
}

// A local preview freezes exactly the fifteen fields sent to the existing create
// API. The API remains compatible; this is not a server-side preview requirement
// or a cross-tab idempotency guarantee. A persisted attempt prevents an automatic
// second POST after an ambiguous response or a reload in this tab.
export default function ManualCaseCreateReview({ values, onLockChange, onNew, onVerified, blocked = false }) {
  const owner = caseEditDraftOwner();
  const [attempt, setAttempt] = useState(() => recover(owner));
  const [preview, setPreview] = useState(null);
  const [confirmed, setConfirmed] = useState(false);
  const [phase, setPhase] = useState(attempt ? "uncertain" : "idle");
  const [message, setMessage] = useState(attempt ? "发现上次新建记录，先核对保存结果；不会再次提交创建。" : "");
  const [record, setRecord] = useState(null);
  const [, refreshIdentity] = useState(0);
  const revision = JSON.stringify(values);
  const attemptRef = useRef(attempt); attemptRef.current = attempt;
  const busy = useRef(false), mounted = useRef(false);
  const callbacks = useRef(null); callbacks.current = { onVerified, onNew };
  const working = phase === "saving" || phase === "checking";
  const invalidated = preview && (preview.revision !== revision || preview.owner !== owner);
  const sameOwner = expected => expected && expected === caseEditDraftOwner();
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => { setConfirmed(false); }, [revision, owner]);
  useEffect(() => { onLockChange?.(working || !!attempt); return () => onLockChange?.(false); }, [working, !!attempt, onLockChange]);
  useEffect(() => {
    const changed = event => { if (event.key === "token" || event.key === null) refreshIdentity(n => n + 1); };
    window.addEventListener("storage", changed);
    return () => window.removeEventListener("storage", changed);
  }, []);

  function prepare() {
    if (blocked || busy.current || attemptRef.current || !sameOwner(owner)) return;
    const payload = manualCasePayload(values);
    if (!payload.patient_name?.trim() || !payload.chief_complaint?.trim()) {
      setMessage("请填写病例名 / 宠物名和主诉，再核对保存内容。"); return;
    }
    setPreview({ payload, owner, revision }); setConfirmed(false); setMessage(""); setPhase("review");
  }
  async function readback(snapshot) {
    setPhase("checking");
    try {
      const { data } = await api.get(`/api/cases/${snapshot.caseId}`, { timeout: 15000, expectedAuthOwner: snapshot.owner });
      if (!mounted.current || !sameOwner(snapshot.owner)) return;
      if (data.id !== snapshot.caseId) throw Error("Wrong case");
      setRecord(data);
      if (!snapshot.payload || !caseEditFields.every(([key]) => data[key] === snapshot.payload[key])) {
        setPhase("uncertain"); setMessage("病例已创建，但回读内容与预览不一致。请查看已保存病例，不要重复创建。"); return;
      }
      setPhase("verified"); setMessage(`已回读病例 #${data.id}，本次核对的十五项内容一致。`);
      callbacks.current.onVerified?.();
    } catch {
      if (mounted.current && sameOwner(snapshot.owner)) { setPhase("uncertain"); setMessage("病例已创建，暂时无法回读。请核对保存结果，不要重复创建。"); }
    }
  }
  async function save() {
    if (blocked || busy.current || attemptRef.current || !preview || !confirmed || invalidated || !sameOwner(preview.owner)) return;
    busy.current = true;
    const snapshot = { owner: preview.owner, payload: preview.payload, caseId: null };
    // Persist before dispatch: a reload cannot turn an unknown result into a new POST.
    if (!remember(snapshot)) { busy.current = false; setMessage("浏览器无法保留本次保存状态，尚未提交。请检查浏览器存储设置后重试。"); return; }
    attemptRef.current = snapshot; setAttempt(snapshot); setPhase("saving"); setMessage("");
    try {
      const { data } = await api.post("/api/cases", snapshot.payload, { timeout: 15000, expectedAuthOwner: snapshot.owner });
      if (!Number.isSafeInteger(data?.id) || data.id <= 0) throw Error("Missing case id");
      snapshot.caseId = data.id;
      if (!sameOwner(snapshot.owner)) return;
      remember(snapshot);
      if (!mounted.current) return;
      setAttempt({ ...snapshot });
      await readback(snapshot);
    } catch (error) {
      if (!mounted.current || !sameOwner(snapshot.owner)) return;
      if ([400, 401, 403, 422].includes(error?.response?.status) && clearManualCreateAttempt()) {
        attemptRef.current = null; setAttempt(null); setConfirmed(false); setPhase("review");
        setMessage("创建请求被拒绝，未保存。请检查登录状态和输入，重新核对后提交。");
      } else {
        setPhase("uncertain"); setMessage("创建结果待核实，请先到病例列表检查。本页不会重复提交；不要重新新建同一病例。");
      }
    } finally { busy.current = false; }
  }
  async function checkResult() {
    const snapshot = attemptRef.current;
    if (busy.current || !snapshot?.caseId || !sameOwner(snapshot.owner)) return;
    busy.current = true;
    try { await readback(snapshot); } finally { busy.current = false; }
  }
  function startAnother() {
    if (phase !== "verified" || busy.current || !sameOwner(attempt?.owner)) return;
    if (callbacks.current.onNew?.() === false) { setMessage("浏览器未能清除旧输入，仍保留本次保存记录；请稍后重试。"); return; }
    if (!clearManualCreateAttempt()) { setMessage("浏览器未能清除上次保存状态，请稍后重试。"); return; }
    attemptRef.current = null; setAttempt(null); setPreview(null); setConfirmed(false); setRecord(null); setPhase("idle"); setMessage("");
  }
  const visibleRecord = sameOwner(attempt?.owner) ? record : null;
  return <section aria-label="手工新建病例核对" style={{ border: "1px solid #bfdbfe", borderRadius: 12, padding: 16, marginTop: 16 }}>
    <h2>手工新建病例 · 核对后保存</h2>
    <p>核对本次手工录入的内容后再创建病例；确认保存不代表诊断签署。</p>
    <p>本次保存状态仅保留在当前标签页，退出登录会清除。保存结果待核实时，请先检查病例列表。</p>
    {!owner && <p role="status">请先返回首页登录，再核对保存。</p>}
    {attempt && !sameOwner(attempt.owner) && <p role="alert">登录账号已变化或登录已过期，请返回首页登录后重新打开；不会提交或回读原账号的记录。</p>}
    {message && <p role="status">{message}</p>}
    {!attempt && <button type="button" disabled={blocked || !owner || working} onClick={prepare}>{preview ? "重新核对新建内容" : "核对新建内容"}</button>}
    {invalidated && !attempt && <p role="status">输入已修改，原确认失效，请重新核对。</p>}
    {preview && !attempt && <div>
      <FieldList data={preview.payload} />
      <label><input type="checkbox" checked={confirmed} disabled={blocked || !!invalidated || !owner} onChange={e => setConfirmed(e.target.checked)} />已核对本次新建内容</label>
      <div><button type="button" onClick={save} disabled={blocked || !confirmed || !!invalidated || !owner || working}>确认并创建病例</button></div>
    </div>}
    {working && <p role="status">{phase === "saving" ? "正在创建病例，请稍候…" : "正在回读核对…"}</p>}
    {attempt?.caseId && sameOwner(attempt.owner) && <div>
      <p>本次病例编号：#{attempt.caseId}</p>
      {phase === "uncertain" && <button type="button" disabled={working} onClick={checkResult}>核对保存结果</button>}
      <Link to={`/cases/${attempt.caseId}`}>查看已保存病例 #{attempt.caseId}</Link>{" "}
      <Link to={`/cases/${attempt.caseId}/edit`}>编辑此病例</Link>
    </div>}
    {visibleRecord && <section aria-label="手工新建实际回读"><h3>服务器实际回读内容</h3><FieldList data={visibleRecord} /></section>}
    {phase === "verified" && <button type="button" onClick={startAnother}>新建另一个病例</button>}
    {attempt && !attempt.caseId && <p><Link to="/">返回首页核对病例列表</Link></p>}
  </section>;
}
function FieldList({ data }) {
  return <dl style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 260px), 1fr))", gap: 12 }}>
    {caseEditFields.map(([key, label]) => <div key={key}><dt>{label}</dt><dd style={{ margin: 0 }}><pre style={textStyle}>{data[key] ?? "未填写"}</pre></dd></div>)}
  </dl>;
}
