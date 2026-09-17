import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";

const fields = [
  ["chief_complaint", "主诉"], ["history", "病史"], ["exam_findings", "体格检查"],
  ["analysis", "AI 分析"], ["treatment", "建议处理"], ["prognosis", "风险提示"],
];
const button = { padding: "8px 12px", borderRadius: 6, border: "1px solid #94a3b8", cursor: "pointer" };
const textBlock = { whiteSpace: "pre-wrap", overflowWrap: "anywhere", margin: "8px 0", fontSize: 13, fontFamily: "inherit" };
const matches = (record, preview) => record?.id === preview.case_id &&
  fields.every(([name]) => record[name] === preview.proposed[name]);

// Mounted per bound session/case. Late responses cannot replace a newer preview.
export default function ConsultUpdateReview({ sessionId, caseId, revision, allowed, blocked, hasPendingAnswers, onUpdated, onReturnToEdit, onWorkingChange, contentRevision, historyAddendum = "" }) {
  const [syncNote, setSyncNote] = useState(null);
  const updateMode = historyAddendum.trim() && syncNote !== historyAddendum ? "history_only" : "consult_sync";
  const inputRevision = JSON.stringify([revision, historyAddendum, updateMode]);
  const [preview, setPreview] = useState(null);
  const [confirmed, setConfirmed] = useState(false);
  const [phase, setPhase] = useState("idle");
  const [message, setMessage] = useState("");
  const [readback, setReadback] = useState(null);
  const busy = useRef(false);
  const mounted = useRef(false);
  const latest = useRef(inputRevision);
  latest.current = inputRevision;
  const updatedCallback = useRef(onUpdated);
  updatedCallback.current = onUpdated;
  const previewRevision = useRef(null);
  const latestContent = useRef(null);
  latestContent.current = JSON.stringify([contentRevision ?? revision, historyAddendum, updateMode]);
  const previewContent = useRef(null);
  const invalidated = preview && previewRevision.current !== inputRevision;
  const working = ["previewing", "saving", "checking"].includes(phase);
  const unresolved = phase === "uncertain";

  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => { setSyncNote(null); }, [historyAddendum]);
  useEffect(() => { onWorkingChange?.(working); return () => onWorkingChange?.(false); }, [working, onWorkingChange]);
  useEffect(() => { setConfirmed(false); }, [inputRevision, allowed, blocked, hasPendingAnswers]);

  async function requestPreview() {
    if (busy.current || blocked || !allowed || hasPendingAnswers) return;
    busy.current = true;
    const requestedRevision = latest.current;
    setPhase("previewing"); setMessage(""); setConfirmed(false); setPreview(null); setReadback(null);
    try {
      const { data } = await api.post(`/api/ai/consult/session/${encodeURIComponent(sessionId)}/preview-update-case`, { history_addendum: historyAddendum, update_mode: updateMode }, { timeout: 15000 });
      if (!mounted.current) return;
      if (requestedRevision !== latest.current) {
        setPhase("idle"); setMessage("内容已修改，请重新核对保存内容。"); return;
      }
      if (data.case_id !== caseId || data.session_id !== sessionId || !data.preview_token) throw new Error("Invalid preview");
      if (data.update_mode !== updateMode || data.history_addendum !== historyAddendum) throw new Error("Preview scope mismatch");
      previewRevision.current = requestedRevision;
      previewContent.current = latestContent.current;
      setPreview(data); setPhase("review");
    } catch {
      if (mounted.current) { setPhase("idle"); setMessage("无法获取更新预览。请检查登录状态和网络后重试。"); }
    } finally { busy.current = false; }
  }

  async function checkSaved(snapshot) {
    setPhase("checking");
    try {
      const { data } = await api.get(`/api/cases/${snapshot.case_id}`, { timeout: 15000 });
      if (!mounted.current) return;
      setReadback(data);
      if (matches(data, snapshot)) {
        setPhase("verified"); setMessage("已回读病例，本次核对的六项内容一致。");
        // Refreshing the list must not turn successful readback into a failed save.
        Promise.resolve(updatedCallback.current?.(data, { inputsChanged: previewContent.current !== latestContent.current, historyAddendum: snapshot.history_addendum })).catch(() => {});
      } else {
        setPhase("uncertain"); setMessage("当前病例与核对内容不一致。请查看已保存病例，再重新预览；请勿直接重复提交。");
      }
    } catch {
      if (mounted.current) { setPhase("uncertain"); setMessage("暂时无法回读病例，保存结果待核对。已保留本次核对内容，请先核对保存结果。"); }
    }
  }

  async function confirmUpdate() {
    if (busy.current || !confirmed || !preview || invalidated || phase !== "review" || blocked || !allowed || hasPendingAnswers) return;
    busy.current = true;
    const snapshot = preview;
    setPhase("saving"); setMessage(""); setConfirmed(false);
    try {
      await api.post(`/api/ai/consult/session/${encodeURIComponent(sessionId)}/update-case`, {
        expected_preview_token: snapshot.preview_token,
        update_mode: snapshot.update_mode,
        ...(snapshot.history_addendum ? { history_addendum: snapshot.history_addendum } : {}),
      }, { timeout: 30000 });
      if (mounted.current) await checkSaved(snapshot);
    } catch (err) {
      if (!mounted.current) return;
      if (err.response?.status === 409) {
        setPhase("stale"); setMessage("病例或问诊内容已改变，原确认已失效。请重新预览并核对。");
      } else if (err.response?.status >= 400 && err.response?.status < 500) {
        setPhase("stale"); setMessage("更新未被接受。请检查登录状态和病例，再重新预览。");
      } else {
        // A timeout or server error can occur after the write committed.
        setMessage("保存结果待核对，正在读取已保存病例。");
        await checkSaved(snapshot);
      }
    } finally { busy.current = false; }
  }

  async function retryReadback() {
    if (busy.current || !preview) return;
    busy.current = true;
    try { await checkSaved(preview); } finally { busy.current = false; }
  }

  return (
    <section aria-label="更新已绑定病例核对" style={{ marginTop: 14, padding: 16, border: "1px solid #93c5fd", borderRadius: 8, background: "white", color: "#172554" }}>
      <h3 style={{ margin: "0 0 8px", fontSize: 18 }}>更新病例 #{caseId} · 核对后保存</h3>
      <ol aria-label="病例更新步骤" style={{ display: "flex", flexWrap: "wrap", gap: 24, paddingLeft: 20, fontSize: 13 }}>
        <li aria-current={phase === "idle" ? "step" : undefined}>问诊整理</li>
        <li aria-current={preview && phase !== "verified" ? "step" : undefined}>保存前核对</li>
        <li aria-current={phase === "verified" ? "step" : undefined}>病例回看</li>
      </ol>
      <p style={{ fontSize: 13 }}>已保存的主诉与体检原文保持不变。填写医生补记时，默认只追加病史；如需同步已提交问诊的 AI 分析、建议处理和风险提示，请明确选择并重新核对。首页其他输入不会自动写回，补记不会自动重新分析，此确认不代表诊断签署。</p>
      {!!historyAddendum.trim() && <label style={{ display: "block", margin: "12px 0" }}>本次更新范围
        <select aria-label="本次更新范围" value={updateMode} disabled={working || unresolved || blocked} onChange={e => setSyncNote(e.target.value === "consult_sync" ? historyAddendum : null)}>
          <option value="history_only">仅追加医生病史补记</option>
          <option value="consult_sync">同时同步已提交问诊结果</option>
        </select>
      </label>}
      {!allowed && <p role="status">请先登录并完成本轮 AI 建议人工覆核。</p>}
      {hasPendingAnswers && <p role="status">有尚未提交的追问或补充病史，请先提交本轮回答，再核对保存内容。</p>}
      {invalidated && phase !== "verified" && <p role="status">内容已修改，原确认失效，请重新核对。</p>}
      {message && <p role="status">{message}</p>}
      {!working && !unresolved && <button type="button" style={button} disabled={!allowed || blocked || hasPendingAnswers} onClick={requestPreview}>
        {preview ? "重新预览更新内容" : "核对更新内容"}
      </button>}
      {working && <p role="status">{phase === "saving" ? "正在保存，请稍候…" : phase === "checking" ? "正在回读核对…" : "正在生成更新预览…"}</p>}
      {preview && (
        <div style={{ marginTop: 14 }}>
          <p><strong>{preview.patient_name || "未命名病例"}</strong> · 病例 #{preview.case_id}</p>
          <p role="status">{preview.update_mode === "history_only" ? "本次只追加医生病史补记，其他五项内容保持不变。" : "本次同步已提交问诊的摘要、AI 分析、建议处理及风险提示；已保存主诉和体检保持不变。"}</p>
          {preview.history_addendum?.trim() && <section aria-label="本次医生病史补记"><strong>本次医生病史补记</strong><pre style={textBlock}>{preview.history_addendum}</pre></section>}
          {fields.map(([name, label]) => (
            <details key={name} open={name === "history"} style={{ borderTop: "1px solid #dbeafe", padding: "10px 0" }}>
              <summary style={{ cursor: "pointer", fontWeight: 600 }}>{label} · {preview.before[name] === preview.proposed[name] ? "无变化" : "有更新"}</summary>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 260px), 1fr))", gap: 12 }}>
                <div><strong>已保存内容</strong><pre style={textBlock}>{preview.before[name] || "未填写"}</pre></div>
                <div><strong>本次保存内容</strong><pre style={textBlock}>{preview.proposed[name] || "未填写"}</pre></div>
              </div>
            </details>
          ))}
          {phase === "review" && !invalidated && <>
            <label style={{ display: "block", padding: "12px 0" }}>
              <input type="checkbox" checked={confirmed} disabled={blocked || !allowed || hasPendingAnswers} onChange={e => setConfirmed(e.target.checked)} /> 已核对本次更新内容
            </label>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button type="button" style={button} disabled={!confirmed || blocked || !allowed || hasPendingAnswers} onClick={confirmUpdate}>确认并更新病例</button>
              <button type="button" style={button} onClick={() => { setPreview(null); setConfirmed(false); setPhase("idle"); setMessage(""); onReturnToEdit?.(); }}>返回修改</button>
            </div>
          </>}
          {unresolved && <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button type="button" style={button} onClick={retryReadback}>核对保存结果</button>
            <button type="button" style={button} disabled={!allowed || blocked || hasPendingAnswers} onClick={requestPreview}>重新预览更新内容</button>
          </div>}
          {phase === "verified" && readback && <p>已读取病例 #{readback.id} · {readback.patient_name || "未命名病例"}</p>}
        </div>
      )}
      <Link to={`/cases/${caseId}`} style={{ display: "inline-block", marginTop: 12 }}>查看已保存病例 #{caseId}</Link>
    </section>
  );
}
