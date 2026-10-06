import React, { useEffect, useRef, useState } from "react";
import api from "../api";
import { startCapture, toBase64 } from "../audioCapture";
import { appendVoice, sha256, voiceIdentity, voiceRevision } from "../voiceDraftState";

const messages = { provider_quota_exhausted: "服务额度不足", batch_budget_exhausted: "本批测试预算已用完", provider_rate_limit: "服务限流", request_already_reserved: "此请求已占额，不能再次提交", context_changed: "病例或问诊已改变" };

export default function VoiceDraft({ context, text, draft, onChange, onDraft, disabled = false }) {
  const [enabled, setEnabled] = useState(false), [phase, setPhase] = useState("idle"), [notice, setNotice] = useState("");
  const [result, setResult] = useState(null), [edited, setEdited] = useState(""), [reviewed, setReviewed] = useState(false);
  const [synthetic, setSynthetic] = useState(false);
  const audio = useRef(null), capture = useRef(null), controller = useRef(null), timer = useRef(null), busy = useRef(false), epoch = useRef(0), requestId = useRef(null);
  const revision = voiceRevision(context, text), latest = useRef(revision); latest.current = revision;
  const identity = voiceIdentity(context);
  const clear = () => { epoch.current++; controller.current?.abort(); capture.current?.cancel(); capture.current = null; audio.current = null; clearTimeout(timer.current); busy.current = false; };
  useEffect(() => {
    let active = true;
    api.get("/api/speech/availability", { timeout: 10000 }).then(({ data }) => { if (active) setEnabled(!!data.enabled); }).catch(() => {});
    return () => { active = false; clear(); };
  }, [identity]);
  useEffect(() => { clear(); setPhase("idle"); setResult(null); setEdited(""); setReviewed(false); setNotice(""); }, [revision, disabled]);
  useEffect(() => {
    const leave = () => clear(); window.addEventListener("pagehide", leave);
    return () => window.removeEventListener("pagehide", leave);
  }, []);
  function stop() {
    if (!capture.current) return;
    try {
      audio.current = capture.current.stop(); capture.current = null; setPhase("recorded");
      timer.current = setTimeout(() => { clear(); setPhase("idle"); setNotice("录音超过 10 分钟未提交，已释放，请重新录音。"); }, 600000);
    } catch { clear(); setPhase("idle"); setNotice("录音无效，请重录或手工输入。"); }
  }
  async function start() {
    if (busy.current || disabled || !enabled || !synthetic || !context.sessionId || !context.owner) return;
    clear(); busy.current = true; const ticket = epoch.current;
    controller.current = new AbortController(); setNotice(""); setResult(null); setReviewed(false); setPhase("permission");
    try {
      const recorder = await startCapture({ signal: controller.current.signal, onLimit: stop });
      if (ticket !== epoch.current) { recorder.cancel(); return; }
      capture.current = recorder; setPhase("recording");
    } catch { if (ticket === epoch.current) { setPhase("idle"); setNotice("麦克风未获许可或不可用，可以继续手工输入。"); } }
    finally { if (ticket === epoch.current) busy.current = false; }
  }
  async function submit() {
    if (busy.current || !audio.current || disabled || !synthetic) return;
    busy.current = true; clearTimeout(timer.current); const ticket = epoch.current, requested = latest.current;
    controller.current = new AbortController(); requestId.current = crypto.randomUUID().replaceAll("-", "");
    setPhase("submitting"); setNotice("");
    const timeout = setTimeout(() => controller.current?.abort(), 60000);
    try {
      const { data: server } = await api.get(`/api/speech/context/${encodeURIComponent(context.sessionId)}`, { signal: controller.current.signal, timeout: 10000 });
      if (ticket !== epoch.current || latest.current !== requested) return;
      const binding = { session_id: context.sessionId, case_id: context.caseId || null, patient_name: context.patientName.trim() || "未命名病例", species: context.species, session_version: server.session_version, draft_version: await sha256(requested) };
      if (server.case_id !== binding.case_id || (server.case_id && (server.patient_name !== binding.patient_name || server.species !== binding.species))) throw Error("context_changed");
      const { data } = await api.post("/api/speech/transcribe", { request_id: requestId.current, binding, synthetic_only: true, audio_base64: toBase64(audio.current) }, { signal: controller.current.signal, timeout: 50000 });
      if (ticket !== epoch.current || latest.current !== requested) return;
      if (data.request_id !== requestId.current || JSON.stringify(data.binding) !== JSON.stringify(binding) || typeof data.text !== "string" || !data.receipt) throw Error("invalid_response");
      setResult(data); setEdited(data.text); setReviewed(false); setPhase("review");
    } catch (error) {
      if (ticket === epoch.current) { setPhase("unknown"); setNotice((messages[error.response?.data?.detail] || "转写未完成或结果未知") + "。不会自动重发，请核对状态；手工输入仍可使用。"); }
    } finally { clearTimeout(timeout); audio.current = null; if (ticket === epoch.current) busy.current = false; }
  }
  async function checkStatus() {
    if (busy.current || !requestId.current) return;
    busy.current = true; const ticket = epoch.current;
    try { const { data } = await api.get(`/api/speech/requests/${requestId.current}`, { timeout: 10000 }); if (ticket === epoch.current) setNotice(`请求状态：${data.state}；已占用 ${data.reserved_fen} 分预算。原请求不会重发，未收到的文字需手工补充或主动另录一段。`); }
    catch { if (ticket === epoch.current) setNotice("暂不能确认请求状态；原请求不会重发。"); }
    finally { if (ticket === epoch.current) busy.current = false; }
  }
  async function reviewSources() {
    if (busy.current || disabled || draft.identity !== identity || draft.entries.some(e => !e.edited_text.trim() || !text.includes(e.edited_text))) return;
    busy.current = true; const ticket = epoch.current, requested = latest.current;
    try {
      const { data: server } = await api.get(`/api/speech/context/${encodeURIComponent(context.sessionId)}`, { timeout: 10000 });
      const binding = { session_id: context.sessionId, case_id: context.caseId || null, patient_name: context.patientName.trim() || "未命名病例", species: context.species, session_version: server.session_version, draft_version: await sha256(requested) };
      const entries = [];
      for (const entry of draft.entries) {
        if (ticket !== epoch.current || latest.current !== requested) return;
        const { data } = await api.post("/api/speech/review", { confirmation: { ...entry, reviewed: true }, binding }, { timeout: 10000 });
        entries.push({ ...entry, receipt: data.receipt });
      }
      if (ticket === epoch.current && latest.current === requested) onDraft({ ...draft, entries, reviewedRevision: requested });
    } catch { if (ticket === epoch.current) setNotice("语音来源无法重新核对，请检查原问诊和登录状态；不会重新发送音频。"); }
    finally { if (ticket === epoch.current) busy.current = false; }
  }
  function confirm() {
    if (!result || !reviewed || !edited.trim() || disabled || busy.current || (draft?.entries?.length || 0) >= 20) return;
    const next = appendVoice(text, edited);
    if (next.length > 20000) { setNotice("病史超过 20000 字，请先整理。"); return; }
    const entries = [...(draft?.entries || []), { receipt: result.receipt, original_text: result.text, edited_text: edited }];
    onChange(next); onDraft({ identity, entries, reviewedRevision: voiceRevision(context, next) });
    clear(); setResult(null); setEdited(""); setPhase("idle"); setReviewed(false);
  }
  return <section aria-label="语音病史草稿" style={{ padding: 12, border: "1px solid #94a3b8", borderRadius: 8 }}>
    <h3>语音病史草稿</h3>
    <p>开发验收入口 · 每段最多 30 秒。仅使用虚构病例合成音频。腾讯云识别文字可能保留 7 天；核对后加入病史，再确认保存。</p>
    {!enabled && <p role="status">外部语音服务尚未启用或额度不可用，请继续手工输入。</p>}
    {!context.sessionId && <p>请先建立问诊，再补充语音病史。</p>}
    <label><input type="checkbox" checked={synthetic} onChange={e => setSynthetic(e.target.checked)} disabled={phase === "recording" || phase === "submitting"} /> 本次仅为虚构病例合成音频</label>
    <div>
      <button type="button" onClick={start} disabled={disabled || !enabled || !synthetic || !context.sessionId || !context.owner || !["idle", "unknown"].includes(phase)}>开始录音</button>
      {phase === "permission" && <span role="status">等待麦克风许可…</span>}
      {phase === "recording" && <button type="button" onClick={stop}>停止录音</button>}
      {phase === "recorded" && <button type="button" onClick={submit} disabled={disabled}>提交转写</button>}
      {phase !== "idle" && <button type="button" onClick={() => { clear(); setPhase("idle"); setResult(null); setEdited(""); setNotice("已放弃本段；已发送请求的占额仍保留。"); }}>放弃本段</button>}
      {phase === "submitting" && <span role="status">正在转写，请勿重复提交…</span>}
      {phase === "unknown" && <button type="button" onClick={checkStatus}>核对转写状态</button>}
    </div>
    {notice && <p role="status">{notice}</p>}
    {result && <div>
      <strong>原始转写</strong><pre style={{ whiteSpace: "pre-wrap" }}>{result.text}</pre>
      <label>医生修订稿<textarea aria-label="医生修订稿" value={edited} maxLength={4000} onChange={e => { setEdited(e.target.value); setReviewed(false); }} /></label>
      <p>请逐项核对药名、数字、小数点、单位、频率及“未见／否认”等否定词。转写不代表诊断。</p>
      <label><input type="checkbox" checked={reviewed} onChange={e => setReviewed(e.target.checked)} /> 已对照原文并核对关键内容</label>
      <button type="button" disabled={!reviewed || !edited.trim() || disabled} onClick={confirm}>确认加入病史草稿</button>
    </div>}
    {!!draft?.entries?.length && <details open={draft.reviewedRevision !== revision}>
      <summary>已加入的语音来源（{draft.entries.length} 段）</summary>
      {draft.entries.map((item, i) => <div key={item.receipt}><pre style={{ whiteSpace: "pre-wrap" }}>原始：{item.original_text}</pre><label>已加入病史的语音段<textarea aria-label="已加入病史的语音段" value={item.edited_text} maxLength={4000} onChange={e => { const entries = draft.entries.map((v, j) => i === j ? { ...v, edited_text: e.target.value } : v); onDraft({ ...draft, entries, reviewedRevision: null }); }} /></label></div>)}
      {draft.identity !== identity && <p role="alert">语音来源属于另一份问诊或动物。请恢复原信息后保存；如放弃本次输入，请清空病史。</p>}
      {draft.reviewedRevision !== revision && <><p role="status">内容修改或草稿恢复后，语音确认已失效。请核对上述原文、修订段和当前病史；修订段必须与病史中的文字一致。</p><button type="button" disabled={disabled || draft.identity !== identity || draft.entries.some(e => !e.edited_text.trim() || !text.includes(e.edited_text))} onClick={reviewSources}>已重新核对语音来源和病史</button></>}
    </details>}
  </section>;
}
