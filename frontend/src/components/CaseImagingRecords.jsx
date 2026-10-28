import React, { useEffect, useRef, useState } from "react";
import { editableImagingData, imagingMessage, imagingStates, imagingLabels, imagingModalities, manualImagingClient, newImagingData } from "../manualImagingRecords";
import { attachmentClient, newAttachmentRequest, verifyAttachmentBytes } from "../caseAttachments";
const box={padding:16,margin:"12px 0",border:"1px solid #ccd5d1",borderRadius:8};
const prompt="影像录入尚未保存，离开会丢失本页草稿。是否继续？";
function Content({data}) {return <dl>{Object.entries(imagingLabels).map(([k,label])=><React.Fragment key={k}><dt>{label}</dt><dd style={{whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}>{k==="modality" ? imagingModalities[data[k]] : data[k] || "未提供"}</dd></React.Fragment>)}</dl>;}
export default function CaseImagingRecords(props) { return <ImagingPanel key={JSON.stringify([props.caseId, props.requestToken])} {...props} />; }
function ImagingPanel({ caseId, requestToken, sourceRevision = 0, onDirtyChange, onChanged, sessionExpired = false, isSessionCurrent }) {
  const [list, setList] = useState(null), [draft, setDraft] = useState(null), [review, setReview] = useState(null);
  const [checked, setChecked] = useState(false), [busy, setBusy] = useState(false), [unknown, setUnknown] = useState(null), [message, setMessage] = useState("");
  const active = useRef(false), control = useRef(null), inFlight = useRef(false), dirty = useRef(false), reviewEpoch = useRef(0), pendingRefresh = useRef(false), readEpoch = useRef(0);
  const retired = useRef(false), session = useRef(null);
  session.current = { sessionExpired, isSessionCurrent };
  const current = () => {
    if (!active.current) return false;
    if (retired.current || session.current.sessionExpired || session.current.isSessionCurrent?.() === false || localStorage.getItem("token") !== requestToken) {
      retired.current = true;
      return false;
    }
    return true;
  };
  const client = (method, path, data) => manualImagingClient(caseId, requestToken, control.current?.signal, current)(method, path, data);
  const invalidate = () => { reviewEpoch.current++; setReview(null); setChecked(false); };
  const reset = () => { if (!current()) return; setDraft(null); setUnknown(null); invalidate(); };
  async function refresh() { if (!current()) return; const epoch = ++readEpoch.current; setList(null); const result = await client("get"); if (current() && epoch === readEpoch.current) setList(result); return result; }
  async function action(fn) {
    if (!current() || inFlight.current) return;
    inFlight.current = true; setBusy(true); setMessage("");
    try { await fn(); } catch (e) { if (current()) setMessage(imagingMessage(e)); }
    finally {
      if (current() && pendingRefresh.current) {
        pendingRefresh.current = false;
        try { await refresh(); } catch (e) { if (current()) setMessage(imagingMessage(e)); }
      }
      inFlight.current = false; if (active.current) { setBusy(false); if (!current()) expireSession(); }
    }
  }
  useEffect(() => {
    active.current = true; control.current = new AbortController(); action(refresh);
    return () => { active.current = false; control.current.abort(); onDirtyChange?.(false); };
  }, [caseId, requestToken]);
  function expireSession() {
    if (!active.current || current()) return;
    // Keep drafts and the pre-dispatch request locator; cancellation is not rollback.
    pendingRefresh.current = false;
    invalidate(); setBusy(false); setMessage(""); control.current?.abort();
  }
  useEffect(() => { if (sessionExpired || isSessionCurrent?.() === false) expireSession(); }, [sessionExpired, isSessionCurrent]);
  useEffect(() => { dirty.current = Boolean(draft || unknown); onDirtyChange?.(dirty.current); }, [draft, unknown, onDirtyChange]);
  function sourceRefresh() {
    if (!current()) { expireSession(); return; }
    invalidate(); readEpoch.current++; setList(null);
    if (inFlight.current) pendingRefresh.current = true; else action(refresh);
  }
  useEffect(() => { if (sourceRevision) sourceRefresh(); }, [sourceRevision]);
  useEffect(() => {
    window.addEventListener("focus", sourceRefresh);
    return () => window.removeEventListener("focus", sourceRefresh);
  }, []);
  useEffect(() => {
    const unload = e => { if (dirty.current) { e.preventDefault(); e.returnValue = ""; } };
    const click = e => { if (dirty.current && e.target.closest?.("a[href]") && !window.confirm(prompt)) { e.preventDefault(); e.stopPropagation(); } };
    window.addEventListener("beforeunload", unload); document.addEventListener?.("click", click, true);
    return () => { window.removeEventListener("beforeunload", unload); document.removeEventListener?.("click", click, true); };
  }, []);
  function edit(row, operation) {
    if (!current() || inFlight.current || unknown) return;
    if (dirty.current && !window.confirm(prompt)) return;
    invalidate(); setUnknown(null);
    setDraft({ operation, report_id: row?.id || null, expected_report_token: row?.token || "", attachment_id: row?.attachment_id || "", reason: "", data: row ? editableImagingData(row.data) : newImagingData() });
  }
  function change(patch) { if (!current() || inFlight.current || unknown) return; setDraft(d => ({ ...d, ...patch })); invalidate(); }
  function dataChange(key, value) { change({data:{...editableImagingData(draft.data),[key]:value}}); }
  function checkSection(key, value) { change({data:{...draft.data,[key]:value}}); }
  async function preview() {
    if (!current()) return;
    const body = { ...draft, data: draft.operation === "withdraw" ? null : draft.data, request_id: newAttachmentRequest(), expected_case_token: list.case_token };
    const epoch = reviewEpoch.current;
    const result = await client("post", "/preview", body);
    if (current() && epoch === reviewEpoch.current) { setReview({ ...result, body }); setChecked(false); }
  }
  async function readUnknown(id) {
    if (!current()) return;
    const result = await client("get", `/requests/${id}`); if (!current()) return;
    if (result.state === "committed") { reset(); await refresh(); if (current()) { setMessage("已回读保存结果，未重复提交。"); onChanged?.(); } }
    else if (result.state === "not_committed") { setUnknown(null); invalidate(); await refresh(); if (current()) setMessage("未找到已提交记录，请重新核对后保存。"); }
  }
  async function confirm() {
    if (!current() || !review || !checked) return;
    const id = review.body.request_id;
    setUnknown(id); setChecked(false);
    try { await client("post", "/confirm", { ...review.body, preview_token: review.preview_token, reviewed: true }); if (current()) { reset(); await refresh(); if (current()) { setMessage("影像记录已保存。"); onChanged?.(); } } }
    catch (error) {
      if (!current()) return;
      setUnknown(id); setChecked(false);
      try { await readUnknown(id); } catch { if (current()) setMessage("保存结果未知，请核对保存结果；不要重复提交。"); }
    }
  }
  async function sourceFile(source) {
    if (!current()) return;
    const bytes = await attachmentClient(caseId, requestToken, control.current?.signal, current)("get", `/${source.id}/content?request_id=${newAttachmentRequest()}&preview=false`, undefined, { responseType: "arraybuffer" });
    await verifyAttachmentBytes(bytes, source); if (!current()) return;
    const url = URL.createObjectURL(new Blob([bytes], { type: source.mime })), link = document.createElement("a");
    link.href = url; link.download = source.name; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  const expired = retired.current || sessionExpired || isSessionCurrent?.() === false;
  const locked=expired || busy || Boolean(unknown);
  return <section aria-label="影像报告人工录入" style={box}>
    <h2>影像报告人工录入</h2><p>对照 DR 或超声原件填写所见和结论原文，未提供的部分请留空。</p>
    <p>未保存草稿仅留在本页，刷新或切换病例、账号后清除。</p>
    <p role="status">{busy ? "正在处理…" : message}</p>
    {expired && <section aria-label="影像登录失效保留内容">
      <p role="alert">登录状态已失效，本页操作已停止。请先复制未保存原文及待核对请求标识；刷新或离开页面后不保证保留，不要重复提交。</p>
      {draft && <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{[`原件标识：${draft.attachment_id || ""}`, `记录标识：${draft.report_id || ""}`, ...Object.entries(imagingLabels).map(([key, label]) => `${label}：${draft.data?.[key] || ""}`), `更正或撤销原因：${draft.reason || ""}`].join("\n")}</pre>}
    </section>}
    {unknown && <p>本页待核对请求标识：<code>{unknown}</code>。取消请求不代表未保存。</p>}

    <button disabled={locked} onClick={()=>action(async()=>{invalidate();await refresh();})}>刷新影像记录</button>
    {unknown && <button disabled={expired || busy} onClick={()=>action(()=>readUnknown(unknown))}>核对影像保存结果</button>}
    {list && <>
      <p>病例 #{list.case_id} · {list.patient_name} · {list.species}</p>
      <button disabled={locked || Boolean(draft)} onClick={()=>edit(null,"create")}>录入影像报告</button>
      {draft && <section style={box} aria-label="影像录入草稿">
        <h3>{draft.operation==="create" ? "新增影像录入" : draft.operation==="correct" ? "更正影像录入" : "撤销影像录入"}</h3>
        {draft.operation!=="withdraw" && <fieldset disabled={locked}>
          <legend>原件与报告</legend>
          <label>影像原件<select aria-label="影像原件" value={draft.attachment_id} disabled={draft.operation!=="create"} onChange={e=>change({attachment_id:e.target.value,data:editableImagingData(draft.data)})}>
            <option value="">请选择已关联的影像原件</option>{list.sources.map(row=><option key={row.id} value={row.id}>{row.metadata.title} · {row.name}</option>)}</select></label>
          {list.sources.find(row=>row.id===draft.attachment_id) && <button type="button" onClick={()=>action(()=>sourceFile(list.sources.find(row=>row.id===draft.attachment_id)))}>打开核对原件</button>}
          {!list.sources.length && <p>请先在“检查资料”关联 DR 或超声原件。</p>}
          <label>检查类型<select aria-label="检查类型" value={draft.data.modality} onChange={e=>dataChange("modality",e.target.value)}>{Object.entries(imagingModalities).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label>
          {Object.entries(imagingLabels).filter(([k])=>k!=="modality").map(([key,label])=>{
            const long=["findings","impression","limitations","note"].includes(key), limit=["findings","impression"].includes(key)?5000:long?1000:key==="position"?255:key==="taken_at"?40:key==="body_part"?100:150;
            const attrs={"aria-label":label,maxLength:limit,value:draft.data[key],onChange:e=>dataChange(key,e.target.value)};
            return <label key={key} style={{display:"block",margin:"8px 0"}}>{label}{long ? <textarea {...attrs} rows={6} style={{display:"block",width:"100%"}}/> : <input {...attrs} placeholder={key==="taken_at"?"2026-10-07T10:00:00+08:00":""}/>}</label>;
          })}
          {[["checked_findings","所见"],["checked_impression","结论"]].map(([key,label])=><label key={key} style={{display:"block"}}><input type="checkbox" aria-label={`已核对${label}原文`} checked={draft.data[key]} onChange={e=>checkSection(key,e.target.checked)}/>已对照原件核对{label}原文及未提供状态</label>)}
        </fieldset>}
        {draft.operation!=="create" && <label>更正或撤销原因<textarea aria-label="更正或撤销原因" disabled={locked} maxLength={500} value={draft.reason} onChange={e=>change({reason:e.target.value})}/></label>}
        <button disabled={locked || (draft.operation!=="withdraw" && (!draft.attachment_id || !draft.data.checked_findings || !draft.data.checked_impression))} onClick={()=>action(preview)}>核对整份影像记录</button>
        <button disabled={locked} onClick={()=>{if(current()&&!inFlight.current&&!unknown&&window.confirm(prompt))reset();}}>放弃本页影像草稿</button>
      </section>}
      {review && <section aria-label="整份影像核对" style={box}>
        <h3>核对整份影像记录</h3><p>病例 #{review.case.case_id} · {review.case.patient_name} · {review.case.species}</p>
        <p>宠主 {review.identity.owner_name || "未填写"} · 毛色 {review.identity.coat_color || "未填写"} · 性别 {review.identity.sex || "未填写"} · 品种 {review.identity.breed || "未填写"}</p>
        <p style={{overflowWrap:"anywhere"}}>原件：{review.source.name} · SHA-256：{review.source.sha256} · 版本 {review.before ? review.before.version+(review.operation==="correct"?1:0) : 1}</p>
        {review.data && <Content data={review.data}/>}
        {review.before && <details><summary>更正前的影像记录</summary><Content data={review.before.data}/></details>}
        <p>原因：{review.reason || "首次录入"}</p>
        <label><input type="checkbox" aria-label="已核对整份影像记录" disabled={locked} checked={checked} onChange={e=>{if(current()&&!busy&&!unknown)setChecked(e.target.checked);}}/>已核对病例、原件和完整影像记录</label>
        <button disabled={locked || !checked} onClick={()=>action(confirm)}>确认保存影像记录</button>
      </section>}
      <h3>影像记录与版本历史</h3>
      {list.reports.map(row=><article key={row.id} style={box} aria-label={`影像记录 ${row.id}`}>
        <strong>{row.data.title}</strong> · 版本 {row.version} · {imagingStates[row.state] || "需核对状态"}
        <p>原件 {row.source.name} · 核对账号 {row.reviewed_by} · 核对时间 {row.reviewed_at} · 原因 {row.reason || "首次录入"}</p>
        <details><summary>查看该版本内容</summary><Content data={row.data}/><p style={{overflowWrap:"anywhere"}}>SHA-256：{row.source.sha256}</p></details>
        {!['withdrawn','superseded'].includes(row.state) && <><button disabled={locked || Boolean(draft)} onClick={()=>edit(row,"correct")}>更正影像记录</button><button disabled={locked || Boolean(draft)} onClick={()=>edit(row,"withdraw")}>撤销影像记录</button></>}
      </article>)}
      {!list.reports.length && <p>暂无已保存的影像记录。</p>}
    </>}
  </section>;
}
