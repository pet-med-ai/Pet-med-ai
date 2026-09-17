import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";

export const caseEditFields = [
  ["patient_name", "病例名 / 宠物名"], ["species", "物种"], ["sex", "性别"],
  ["age_info", "年龄"], ["breed", "品种"], ["weight", "体重"], ["coat_color", "毛色"],
  ["owner_name", "主人姓名"], ["owner_phone", "主人电话"], ["chief_complaint", "主诉"],
  ["history", "完整病史"], ["exam_findings", "体检 / 化验"], ["analysis", "AI 分析"],
  ["treatment", "治疗建议"], ["prognosis", "风险提示 / 随访"],
];
const sameFields = (a, b) => caseEditFields.every(([key]) => a?.[key] === b?.[key]);
const textStyle = { whiteSpace: "pre-wrap", overflowWrap: "anywhere", fontFamily: "inherit", fontSize: 14 };

export default function CaseEditReview({ caseId, baseline, changes, onVerified, onReload, onBusyChange }) {
  const [preview, setPreview] = useState(null);
  const [confirmed, setConfirmed] = useState(false);
  const [phase, setPhase] = useState("idle");
  const [message, setMessage] = useState("");
  const [readback, setReadback] = useState(null);
  const revision = JSON.stringify([baseline.case_token, changes]);
  const latest = useRef(revision); latest.current = revision;
  const callbacks = useRef(null); callbacks.current = { onVerified, onReload };
  const mounted = useRef(false), busy = useRef(false), previewRevision = useRef(null);
  const working = ["previewing", "saving", "checking", "reloading"].includes(phase);
  const unresolved = phase === "uncertain";
  const invalidated = preview && previewRevision.current !== revision;
  const dirty = Object.keys(changes).length > 0;
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => { setConfirmed(false); }, [revision]);
  useEffect(() => { onBusyChange?.(working || unresolved); return () => onBusyChange?.(false); }, [working, unresolved, onBusyChange]);

  async function requestPreview() {
    if (busy.current || !dirty || unresolved) return;
    busy.current = true;
    const requested = latest.current;
    const request = { expected_case_token: baseline.case_token, changes: { ...changes } };
    setPhase("previewing"); setMessage(""); setConfirmed(false); setPreview(null); setReadback(null);
    try {
      const { data } = await api.post(`/api/cases/${caseId}/preview-edit`, request, { timeout: 15000 });
      if (!mounted.current) return;
      if (requested !== latest.current) { setPhase("idle"); setMessage("输入已修改，请重新核对。"); return; }
      if (data.case_id !== caseId || data.case_token !== baseline.case_token || !data.preview_token ||
          !sameFields(data.before, baseline.before) || !sameFields(data.proposed, { ...baseline.before, ...request.changes })) throw new Error("Invalid edit preview");
      previewRevision.current = requested;
      setPreview({ ...data, request }); setPhase("review");
    } catch (err) {
      if (mounted.current) {
        setPhase(err.response?.status === 409 ? "stale" : "idle");
        setMessage(err.response?.status === 409 ? "病例已被修改，本次输入仍保留。请读取最新病例后重新核对。" : "无法获取修改预览，请检查输入和网络后重试。");
      }
    } finally { busy.current = false; }
  }

  async function checkSaved(snapshot) {
    setPhase("checking");
    try {
      const { data } = await api.get(`/api/cases/${caseId}/edit-state`, { timeout: 15000 });
      if (!mounted.current) return;
      if (data.case_id === caseId && data.case_token && sameFields(data.before, snapshot.proposed)) {
        setReadback(data); setPhase("verified"); setMessage("已从服务器回读，15 项病例内容与本次核对一致。");
        callbacks.current.onVerified(data);
      } else { setPhase("uncertain"); setMessage("当前病例与核对内容不一致。请查看最新内容，不要重复提交。"); }
    } catch {
      if (mounted.current) { setPhase("uncertain"); setMessage("暂时无法回读，保存结果待核对。本次输入仍保留，请先核对保存结果。"); }
    }
  }

  async function confirmSave() {
    if (busy.current || !confirmed || !preview || invalidated || phase !== "review") return;
    busy.current = true; const snapshot = preview;
    setPhase("saving"); setMessage(""); setConfirmed(false);
    try {
      await api.post(`/api/cases/${caseId}/confirm-edit`, { ...snapshot.request, expected_preview_token: snapshot.preview_token }, { timeout: 30000 });
      if (mounted.current) await checkSaved(snapshot);
    } catch (err) {
      if (!mounted.current) return;
      if (err.response?.status >= 400 && err.response?.status < 500) {
        setPhase("stale"); setMessage(err.response.status === 409 ? "病例或输入已变化，原确认失效。本次修改仍保留，请读取最新病例再核对。" : "保存未被接受，请检查登录状态和病例后重新核对。");
      } else { await checkSaved(snapshot); }
    } finally { busy.current = false; }
  }

  async function retryReadback() {
    if (busy.current || !preview) return;
    busy.current = true;
    try { await checkSaved(preview); } finally { busy.current = false; }
  }

  async function reloadLatest() {
    if (busy.current) return;
    busy.current = true; setPhase("reloading"); setConfirmed(false);
    try {
      const { data } = await api.get(`/api/cases/${caseId}/edit-state`, { timeout: 15000 });
      if (!mounted.current) return;
      if (data.case_id !== caseId || !data.case_token || !data.before) throw new Error("Invalid case state");
      callbacks.current.onReload(data); setPreview(null); setReadback(null); setPhase("idle");
      setMessage("已读取最新病例，并保留本次修改。请逐项比较，尤其是双方都修改过的内容，再重新核对保存。");
    } catch { if (mounted.current) { setPhase("uncertain"); setMessage("读取最新病例失败，本次输入仍保留。"); } }
    finally { busy.current = false; }
  }

  return <section aria-label="病例修改核对" style={{ marginTop: 20, padding: 18, border: "1px solid #93c5fd", borderRadius: 10 }}>
    <h2>核对本次修改</h2>
    <p>只保存实际修改的字段；完整病史如有删改，会按下方核对内容保存。此操作不会重新分析 AI 建议，也不代表诊断签署。</p>
    {!dirty && phase !== "verified" && <p>尚无修改。</p>}
    {invalidated && phase === "review" && <p role="status">输入已修改，原确认失效，请重新核对。</p>}
    {message && <p role="status">{message}</p>}
    {phase === "verified" && dirty && <p role="status">当前输入另有修改，尚未保存；下方仍是上次回读的病例内容。</p>}
    {working && <p role="status">{phase === "saving" ? "正在保存…" : phase === "checking" ? "正在回读…" : phase === "reloading" ? "正在读取最新病例…" : "正在生成预览…"}</p>}
    {!working && !unresolved && <button type="button" disabled={!dirty} onClick={requestPreview}>{preview ? "重新核对修改" : "核对修改内容"}</button>}
    {preview && <div>
      <p>病例 #{caseId} · {preview.before.patient_name} · 本次修改 {Object.keys(preview.changes).length} 项</p>
      {caseEditFields.filter(([key]) => Object.hasOwn(preview.changes, key)).map(([key, label]) => <section key={key} aria-label={label + "修改对照"} style={{ borderTop: "1px solid #dbeafe", marginTop: 12 }}>
        <h3>{label}</h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 280px), 1fr))", gap: 16 }}>
          <div><strong>服务器已保存内容</strong><pre style={textStyle}>{preview.before[key] ?? "未填写"}</pre></div>
          <div><strong>本次保存内容</strong><pre style={textStyle}>{preview.proposed[key] === "" || preview.proposed[key] == null ? "（清空此项）" : preview.proposed[key]}</pre></div>
        </div>
      </section>)}
      {phase === "review" && !invalidated && <div>
        <label><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} /> 已核对本次病例修改</label>
        <button type="button" disabled={!confirmed} onClick={confirmSave}>确认并保存修改</button>
      </div>}
    </div>}
    {!working && unresolved && preview && <button type="button" onClick={retryReadback}>核对保存结果</button>}
    {!working && ["stale", "uncertain"].includes(phase) && <button type="button" onClick={reloadLatest}>读取最新病例并保留本次修改</button>}
    {phase === "verified" && readback && <section aria-label="修改后服务器回读">
      <h3>已保存并回读</h3>
      {caseEditFields.filter(([key]) => Object.hasOwn(preview?.changes || {}, key)).map(([key, label]) => <div key={key}><strong>{label}</strong><pre style={textStyle}>{readback.before[key] ?? "未填写"}</pre></div>)}
      <Link to={`/cases/${caseId}`}>查看已保存病例 #{caseId}</Link>
    </section>}
  </section>;
}
