import React, { useEffect, useRef, useState } from "react";
import api from "../api";
import { caseEditDraftOwner } from "../caseEditDraft";
import { cleanIntakeDraft, intakeContextMatches, intakeRequest, intakeSignature, intakeReviewed, INTAKE_LABELS, intakeKey as draftKey } from "../chiefComplaintIntakeState";

const states = { unfilled: "未填写", not_asked: "未询问", observed: "已记录", absent: "明确否定", uncertain: "不确定", unobservable: "无法观察" };
export default function ChiefComplaintIntake({ intakeKey = "diarrhea", draft, review, context, disabled, onChange, onReview, onArchive, onAppend }) {
  const title = INTAKE_LABELS[intakeKey];
  const boundContext = { ...context, intakeKey };
  context = boundContext;
  const [busy, setBusy] = useState(false), [error, setError] = useState(""), [preview, setPreview] = useState(null);
  const [identity, setIdentity] = useState(caseEditDraftOwner);
  const live = useRef(), request = useRef(0), mounted = useRef(false);
  live.current = { draft, context, disabled };
  useEffect(() => {
    mounted.current = true;
    const check = () => { setIdentity(caseEditDraftOwner()); request.current++; setPreview(null); onReview(null); setBusy(false); };
    window.addEventListener("storage", check); window.addEventListener("focus", check);
    const timer = setInterval(() => { if (caseEditDraftOwner() !== live.current.context.owner) check(); }, 1000);
    return () => { mounted.current = false; request.current++; clearInterval(timer); window.removeEventListener("storage", check); window.removeEventListener("focus", check); };
  }, []);
  const contextKey = JSON.stringify(context), signature = draft ? intakeSignature(draft) : "";
  useEffect(() => { request.current++; setPreview(null); setError(""); setBusy(false); onReview(null); }, [contextKey, signature]);
  const owned = identity && identity === context.owner && caseEditDraftOwner() === context.owner && (!draft || draft.binding.owner === context.owner);
  const matches = intakeContextMatches(draft, context);
  const usable = owned && (!draft || matches) && !disabled && !busy;
  const current = (id, key, raw) => mounted.current && request.current === id && caseEditDraftOwner() === live.current.context.owner &&
    JSON.stringify(live.current.context) === key && (!raw || intakeSignature(live.current.draft) === raw);
  const start = async () => {
    if (!owned || disabled || busy || !["dog", "cat"].includes(context.species)) return;
    const id = ++request.current, key = contextKey;
    setBusy(true); setError(""); setPreview(null); onReview(null);
    try {
      const r = await api.get(`/api/ai/consult/intake/${intakeKey}`, { params: { species: context.species }, expectedAuthOwner: context.owner });
      if (!current(id, key)) return;
      const next = cleanIntakeDraft({ template: r.data, binding: context, answers: {} });
      if (draft) {
        if (matches && draft.template.fingerprint === next.template.fingerprint) next.answers = draft.answers;
        else onArchive(`原${INTAKE_LABELS[draftKey(draft)]}问卷（未自动套入新表）：\n` + JSON.stringify(draft, null, 2));
      }
      onChange(next);
    } catch (e) { if (current(id, key)) setError(typeof e.response?.data?.detail === "string" ? e.response.data.detail : `${title}问卷读取失败，原输入仍保留。请重试读取。`); }
    finally { if (mounted.current && request.current === id) setBusy(false); }
  };
  const summarize = async () => {
    if (!usable || !draft || !matches) return;
    const id = ++request.current, key = contextKey, raw = signature;
    setBusy(true); setError(""); setPreview(null); onReview(null);
    try {
      const r = await api.post(`/api/ai/consult/intake/${intakeKey}/preview`, intakeRequest(draft), { expectedAuthOwner: context.owner });
      if (current(id, key, raw)) setPreview({ signature: raw, snapshot: r.data.snapshot, historyBlock: r.data.history_block });
    } catch (e) { if (current(id, key, raw)) setError(typeof e.response?.data?.detail === "string" ? e.response.data.detail : "汇总暂不可读取，原输入仍保留；请重新核对。"); }
    finally { if (mounted.current && request.current === id) setBusy(false); }
  };
  const change = (q, patch) => {
    if (!usable || !matches || caseEditDraftOwner() !== context.owner) return;
    onReview(null); setPreview(null);
    const next = { ...draft, answers: { ...draft.answers, [q.key]: { ...draft.answers[q.key], ...patch } } };
    try { onChange(cleanIntakeDraft(next)); setError(""); }
    catch { setError("本次输入超过问卷长度限制，尚未应用；先前原文仍保留，请整理后重新输入。"); }
  };
  return <section aria-label={`犬猫${title}问诊`} className="workbench-secondary">
    <h2>犬猫{title}问诊</h2>
    <p>医生采集 · 临床草稿，问题与条件需医生审阅。未填写不代表正常；问卷核对后仍需核对病例保存内容。</p>
    <p>无需填完问卷；可随时收起问卷处理当前诊疗，已输入原文会保留。</p>
    {!owned ? <p role="status">请使用当前登录账号重新进入；旧账号问卷不会显示或提交。</p> : <>
      <button type="button" disabled={disabled || busy || !["dog", "cat"].includes(context.species)} onClick={start}>{draft ? (matches ? `重新读取${title}模板` : `为当前病例开始${title}问卷`) : `开始${title}问诊`}</button>
      {!["dog", "cat"].includes(context.species) && <p>请明确选择犬或猫后使用专用问卷。</p>}
      {draft && <>
        <p>模板：{draft.template.version} · {draft.template.fingerprint}。绑定病例：{draft.binding.patientName || "未命名"} / {draft.binding.species}。</p>
        {!matches && <p role="alert">病例、物种、主诉或问诊已切换。原输入保留供回看，旧确认已失效；开始当前病例问卷会保留这份原文供重新整理。</p>}
        {draft.template.questions.map(q => {
          const a = draft.answers[q.key], active = !q.when || draft.answers[q.when].state === "observed";
          return <fieldset key={q.key} data-diarrhea-question={intakeKey === "diarrhea" ? q.key : undefined} data-intake-question={q.key} disabled={!usable || !active} style={{ marginTop: 12 }}>
            <legend>{q.label}</legend>
            {!active && <p>当前不适用，原分支输入只读保留；上游回答变化后需要重新核对。</p>}
            <label>回答状态<select aria-label={q.label + "：回答状态"} value={a.state} onChange={e => change(q, { state: e.target.value })}>
              {Object.entries(states).filter(([s]) => s !== "absent" || q.kind === "presence").map(([s, label]) => <option key={s} value={s}>{label}</option>)}
            </select></label>
            <label style={{ display: "block" }}>医生原文<textarea aria-label={q.label + "：医生原文"} rows={2} maxLength={6000} readOnly={!usable || !active} value={a.text} onChange={e => change(q, { text: e.target.value })} /></label>
          </fieldset>;
        })}
        <button type="button" disabled={!usable || !matches} onClick={summarize}>{busy ? "正在读取汇总…" : `核对${title}问卷汇总`}</button>
        {preview && <section aria-label={`${title}问卷汇总`}>
          <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{preview.historyBlock}</pre>
          <button type="button" disabled={!usable || !matches} onClick={() => {
            if (usable && matches && preview.signature === intakeSignature(live.current.draft) && caseEditDraftOwner() === context.owner) onReview(preview);
          }}>确认当前{title}问卷</button>
        </section>}
        {intakeReviewed(draft, review, context) && <p role="status">当前{title}问卷已核对。修改输入或切换病例后需重新核对。</p>}
        {onAppend && <button type="button" disabled={!usable || !intakeReviewed(draft, review, context)} onClick={() => {
          if (caseEditDraftOwner() === context.owner && intakeReviewed(live.current.draft, review, live.current.context)) onAppend(review.historyBlock);
        }}>将{title}原文加入病史补记</button>}
      </>}
    </>}
    {error && <p role="alert">{error}</p>}
  </section>;
}
