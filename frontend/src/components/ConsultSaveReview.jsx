import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";

const metadata = [["patient_name", "病例名"], ["species", "物种"], ["sex", "性别"], ["age_info", "年龄"], ["breed", "品种"], ["weight", "体重"], ["coat_color", "毛色"], ["owner_name", "主人姓名"], ["owner_phone", "主人电话"]];
const clinical = [["chief_complaint", "主诉 · 医生输入"], ["history", "病史 · 医生补充与问诊记录"], ["exam_findings", "体检 / 化验"], ["analysis", "AI 分析"], ["treatment", "建议处理"], ["prognosis", "风险提示"]];
const fields = [...metadata, ...clinical];
const button = { padding: "8px 12px", border: "1px solid #94a3b8", borderRadius: 6, cursor: "pointer" };
const caseMatches = (record, snapshot) => fields.every(([key]) => record[key] === snapshot[key]);

export default function ConsultSaveReview({ sessionId, payload, revision, allowed, blocked, hasPendingAnswers, onSaved, onBound }) {
  const [preview, setPreview] = useState(null);
  const [confirmed, setConfirmed] = useState(false);
  const [phase, setPhase] = useState("idle");
  const [message, setMessage] = useState("");
  const [boundId, setBoundId] = useState(null);
  const busy = useRef(false);
  const mounted = useRef(false);
  const context = JSON.stringify([sessionId, payload, revision, allowed, blocked, hasPendingAnswers]);
  const latest = useRef(context);
  latest.current = context;
  const snapshotContext = useRef(null);
  const reviewedPayload = useRef(null);
  const invalidated = preview && snapshotContext.current !== context;
  const working = ["previewing", "saving", "checking"].includes(phase);

  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => { setConfirmed(false); }, [context]);

  async function readSaved(snapshot) {
    setPhase("checking");
    try {
      // Resolve the binding even when the save response (and its case ID) was lost.
      const { data: session } = await api.get(`/api/ai/consult/session/${encodeURIComponent(sessionId)}`, { timeout: 15000 });
      if (!mounted.current) return;
      if (session.session_id !== sessionId) throw new Error("Unexpected session");
      if (!Number.isInteger(session.case_id) || session.case_id <= 0) {
        setPhase("uncertain"); setMessage("暂未查到已绑定病例，保存结果仍待核对。请先核对保存结果，或重新预览后再确认。"); return;
      }
      setBoundId(session.case_id);
      const { data } = await api.get(`/api/cases/${session.case_id}`, { timeout: 15000 });
      if (!mounted.current) return;
      if (data.id === session.case_id && caseMatches(data, snapshot)) {
        const inputsChanged = snapshotContext.current !== latest.current;
        setPhase("verified"); setMessage("已回读病例，基本信息与本次核对的保存内容一致。" + (inputsChanged ? "保存期间另有输入修改，这些修改尚未保存。" : ""));
        Promise.resolve().then(() => { if (mounted.current) return onSaved?.(data, { inputsChanged }); }).catch(() => {});
      } else {
        setPhase("uncertain"); setMessage("问诊已绑定病例，但当前病例与核对内容不一致。请查看病例，再进入更新核对；不会另建病例或覆盖现有内容。");
      }
    } catch {
      if (mounted.current) { setPhase("uncertain"); setMessage("暂时无法回读，保存结果待核对。已保留输入和核对内容，请先核对保存结果。"); }
    }
  }

  async function requestPreview() {
    if (busy.current || !allowed || blocked || hasPendingAnswers || !sessionId) return;
    busy.current = true;
    const requestedContext = latest.current;
    const body = JSON.parse(JSON.stringify(payload));
    setPhase("previewing"); setMessage(""); setConfirmed(false); setPreview(null);
    try {
      const { data } = await api.post(`/api/ai/consult/session/${encodeURIComponent(sessionId)}/preview-case`, body, { timeout: 15000 });
      if (!mounted.current) return;
      if (latest.current !== requestedContext) {
        setPhase("idle"); setMessage("内容已修改，请重新核对保存内容。"); return;
      }
      if (data.session_id !== sessionId || !data.preview_token) throw new Error("Invalid preview");
      snapshotContext.current = requestedContext;
      reviewedPayload.current = body;
      setPreview(data);
      if (data.case_id) { setBoundId(data.case_id); await readSaved(data); }
      else { setBoundId(null); setPhase("review"); }
    } catch {
      if (mounted.current) { setPhase("idle"); setMessage("无法生成保存预览，请检查登录状态与网络后重试。"); }
    } finally { busy.current = false; }
  }

  async function confirmSave() {
    if (busy.current || !confirmed || !preview || invalidated || phase !== "review" || !allowed || blocked || hasPendingAnswers || boundId) return;
    busy.current = true;
    const snapshot = preview;
    setPhase("saving"); setMessage(""); setConfirmed(false);
    try {
      await api.post(`/api/ai/consult/session/${encodeURIComponent(sessionId)}/save-case`, {
        ...reviewedPayload.current, expected_preview_token: snapshot.preview_token,
      }, { timeout: 30000 });
      if (mounted.current) await readSaved(snapshot);
    } catch (err) {
      if (!mounted.current) return;
      if (err.response?.status === 409) {
        setPhase("stale"); setMessage("问诊或保存内容已改变，原确认已失效。请重新预览并核对。");
      } else if (err.response?.status >= 400 && err.response?.status < 500) {
        setPhase("stale"); setMessage("保存未被接受。请检查登录状态和输入，再重新预览。");
      } else {
        await readSaved(snapshot);
      }
    } finally { busy.current = false; }
  }

  async function retryReadback() {
    if (busy.current || !preview) return;
    busy.current = true;
    try { await readSaved(preview); } finally { busy.current = false; }
  }

  return <section aria-label="首次保存病例核对" style={{ marginTop: 14, padding: 16, border: "1px solid #93c5fd", borderRadius: 8, background: "white", color: "#172554" }}>
    <h3 style={{ margin: "0 0 8px", fontSize: 18 }}>首次保存病例 · 核对后保存</h3>
    <ol aria-label="首次保存步骤" style={{ display: "flex", flexWrap: "wrap", gap: 24, paddingLeft: 20, fontSize: 13 }}>
      <li aria-current={phase === "idle" ? "step" : undefined}>问诊整理</li>
      <li aria-current={preview && phase !== "verified" ? "step" : undefined}>保存前核对</li>
      <li aria-current={phase === "verified" ? "step" : undefined}>病例回看</li>
    </ol>
    <p style={{ fontSize: 13 }}>核对当前宠物信息、医生输入和问诊记录。AI 建议来自最近一次问诊分析，补记不会自动重新分析。此确认不代表诊断签署。</p>
    {!allowed && <p role="status">请先登录并完成本轮 AI 建议人工覆核。</p>}
    {hasPendingAnswers && <p role="status">有尚未提交的追问回答，请先提交回答，再核对保存内容。</p>}
    {invalidated && phase !== "verified" && <p role="status">内容已修改，原确认失效，请重新核对。</p>}
    {message && <p role="status">{message}</p>}
    {working && <p role="status">{phase === "saving" ? "正在保存，请稍候…" : phase === "checking" ? "正在回读核对…" : "正在生成保存预览…"}</p>}
    {!working && !boundId && <button type="button" style={button} disabled={!allowed || blocked || hasPendingAnswers} onClick={requestPreview}>{preview ? "重新预览保存内容" : "核对保存内容"}</button>}
    {preview && <div style={{ marginTop: 12 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 10 }}>
        {metadata.map(([key, label]) => <div key={key}><span style={{ fontSize: 12 }}>{label}</span><div style={{ fontWeight: 600, overflowWrap: "anywhere" }}>{preview[key] || "未填写"}</div></div>)}
      </div>
      {clinical.map(([key, label]) => <details key={key} open={["chief_complaint", "history", "exam_findings"].includes(key)} style={{ padding: "10px 0", borderBottom: "1px solid #dbeafe" }}>
        <summary style={{ cursor: "pointer", fontWeight: 600 }}>{label}</summary>
        <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere", fontFamily: "inherit", fontSize: 13 }}>{preview[key] || "未填写"}</pre>
      </details>)}
      {phase === "review" && !invalidated && <>
        <label style={{ display: "block", padding: "12px 0" }}><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} disabled={!allowed || blocked || hasPendingAnswers} /> 已核对本次保存内容</label>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          <button type="button" style={button} disabled={!confirmed || !allowed || blocked || hasPendingAnswers} onClick={confirmSave}>确认并保存病例</button>
          <button type="button" style={button} onClick={() => { setPreview(null); setConfirmed(false); setPhase("idle"); setMessage(""); }}>返回修改</button>
        </div>
      </>}
      {phase === "uncertain" && <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 12 }}>
        <button type="button" style={button} onClick={retryReadback}>核对保存结果</button>
        {boundId && <button type="button" style={button} onClick={() => onBound?.(boundId)}>进入已绑定病例更新核对</button>}
      </div>}
    </div>}
    {boundId && <Link to={`/cases/${boundId}`} style={{ display: "inline-block", marginTop: 12 }}>查看已保存病例 #{boundId}</Link>}
  </section>;
}
