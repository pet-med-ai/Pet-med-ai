import React, { useEffect, useRef, useState } from "react";
import { editableLabData, labMessage, labStates, labTypes, manualLabClient, newLabData, newLabRow } from "../manualLabResults";
import { attachmentClient, newAttachmentRequest, verifyAttachmentBytes } from "../caseAttachments";

const box = { padding: 16, margin: "12px 0", border: "1px solid #ccd5d1", borderRadius: 8 };
const panels = { cbc: "血常规", chemistry: "生化", urine: "尿检", mixed: "组合报告", other: "其他" };
const fields = { name: "项目名称", value: "结果原文", unit: "结果单位", reference: "参考范围原文", reference_low: "参考下限", reference_high: "参考上限", reference_unit: "参考单位", flag: "报告标记原文", position: "页码或原件位置" };
const prompt = "检验录入尚未保存，离开会丢失本页草稿。是否继续？";

function Results({ data }) {
  return <div style={{ overflowX: "auto" }}><table><thead><tr>{["项目", "结果类型", "结果原文", "单位", "参考范围原文", "下限", "上限", "参考单位", "报告标记", "原件位置"].map(s => <th key={s}>{s}</th>)}</tr></thead>
    <tbody>{data.items.map((r, i) => <tr key={i}>{[r.name, labTypes[r.result_type], r.value || "未填写", r.unit || "未提供", r.reference || "未提供", r.reference_low || "未提供", r.reference_high || "未提供", r.reference_unit || "未提供", r.flag || "未提供", r.position].map((v, j) => <td key={j} style={{ padding: 6, whiteSpace: "pre-wrap" }}>{v}</td>)}</tr>)}</tbody></table></div>;
}

export default function CaseLabResults(props) { return <LabPanel key={JSON.stringify([props.caseId, props.requestToken])} {...props} />; }
function LabPanel({ caseId, requestToken, sourceRevision = 0, onDirtyChange }) {
  const [list, setList] = useState(null), [draft, setDraft] = useState(null), [review, setReview] = useState(null);
  const [checked, setChecked] = useState(false), [busy, setBusy] = useState(false), [unknown, setUnknown] = useState(null), [message, setMessage] = useState("");
  const active = useRef(false), control = useRef(null), inFlight = useRef(false), dirty = useRef(false), reviewEpoch = useRef(0), pendingRefresh = useRef(false), readEpoch = useRef(0);
  const current = () => active.current && localStorage.getItem("token") === requestToken;
  const client = (method, path, data) => manualLabClient(caseId, requestToken, control.current?.signal)(method, path, data);
  const invalidate = () => { reviewEpoch.current++; setReview(null); setChecked(false); };
  const reset = () => { setDraft(null); setUnknown(null); invalidate(); };
  async function refresh() { const epoch = ++readEpoch.current; setList(null); const result = await client("get"); if (current() && epoch === readEpoch.current) setList(result); return result; }
  async function action(fn) {
    if (!current() || inFlight.current) return;
    inFlight.current = true; setBusy(true); setMessage("");
    try { await fn(); } catch (e) { if (current()) setMessage(labMessage(e)); }
    finally {
      if (current() && pendingRefresh.current) {
        pendingRefresh.current = false;
        try { await refresh(); } catch (e) { if (current()) setMessage(labMessage(e)); }
      }
      inFlight.current = false; if (current()) setBusy(false);
    }
  }
  useEffect(() => {
    active.current = true; control.current = new AbortController(); action(refresh);
    return () => { active.current = false; control.current.abort(); onDirtyChange?.(false); };
  }, [caseId, requestToken]);
  useEffect(() => { dirty.current = Boolean(draft || unknown); onDirtyChange?.(dirty.current); }, [draft, unknown, onDirtyChange]);
  function sourceRefresh() {
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
    if (dirty.current && !window.confirm(prompt)) return;
    invalidate(); setUnknown(null);
    setDraft({ operation, report_id: row?.id || null, expected_report_token: row?.token || "", attachment_id: row?.attachment_id || "", reason: "", data: row ? editableLabData(row.data) : newLabData() });
  }
  function change(patch) { setDraft(d => ({ ...d, ...patch })); invalidate(); }
  function reportChange(key, value) { change({ data: { ...draft.data, report: { ...draft.data.report, [key]: value }, items: draft.data.items.map(r => ({ ...r, checked: false })) } }); }
  function rowChange(index, key, value) { change({ data: { ...draft.data, items: draft.data.items.map((r, i) => i === index ? { ...r, [key]: value, checked: key === "checked" ? value : false } : r) } }); }
  async function preview() {
    const body = { ...draft, data: draft.operation === "withdraw" ? null : draft.data, request_id: newAttachmentRequest(), expected_case_token: list.case_token };
    const epoch = reviewEpoch.current;
    const result = await client("post", "/preview", body);
    if (current() && epoch === reviewEpoch.current) { setReview({ ...result, body }); setChecked(false); }
  }
  async function readUnknown(id) {
    const result = await client("get", `/requests/${id}`); if (!current()) return;
    if (result.state === "committed") { reset(); await refresh(); if (current()) setMessage("已回读保存结果，未重复提交。"); }
    else if (result.state === "not_committed") { setUnknown(null); invalidate(); await refresh(); if (current()) setMessage("未找到已提交记录，请重新核对后保存。"); }
  }
  async function confirm() {
    const id = review.body.request_id;
    try { await client("post", "/confirm", { ...review.body, preview_token: review.preview_token, reviewed: true }); if (current()) { reset(); await refresh(); if (current()) setMessage("检验记录已保存。"); } }
    catch (error) {
      if (!current()) return;
      setUnknown(id); setChecked(false);
      try { await readUnknown(id); } catch { if (current()) setMessage("保存结果未知，请核对保存结果；不要重复提交。"); }
    }
  }
  async function sourceFile(source) {
    const bytes = await attachmentClient(caseId, requestToken, control.current?.signal)("get", `/${source.id}/content?request_id=${newAttachmentRequest()}&preview=false`, undefined, { responseType: "arraybuffer" });
    await verifyAttachmentBytes(bytes, source); if (!current()) return;
    const url = URL.createObjectURL(new Blob([bytes], { type: source.mime })), link = document.createElement("a");
    link.href = url; link.download = source.name; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  const locked = busy || Boolean(unknown);
  return <section aria-label="检验项目人工录入" style={box}>
    <h2>检验项目人工录入</h2><p>按原报告逐项填写并核对。保留原始数值、单位、范围和标记；未提供的内容请留空。</p>
    <p>未保存草稿仅留在本页，刷新或切换病例、账号后清除。</p>
    <p role="status">{busy ? "正在处理…" : message}</p>
    <button disabled={locked} onClick={() => action(async () => { invalidate(); await refresh(); })}>刷新检验记录</button>
    {unknown && <button disabled={busy} onClick={() => action(() => readUnknown(unknown))}>核对检验保存结果</button>}
    {list && <>
      <p>病例 #{list.case_id} · {list.patient_name} · {list.species}</p>
      <button disabled={locked || Boolean(draft)} onClick={() => edit(null, "create")}>录入检验报告</button>
      {draft && <section style={box} aria-label="检验录入草稿">
        <h3>{draft.operation === "create" ? "新增检验录入" : draft.operation === "correct" ? "更正检验录入" : "撤销检验录入"}</h3>
        {draft.operation !== "withdraw" && <fieldset disabled={locked}>
          <legend>原件与报告</legend>
          <label>检验原件<select aria-label="检验原件" value={draft.attachment_id} disabled={draft.operation !== "create"} onChange={e => change({ attachment_id: e.target.value, data: editableLabData(draft.data) })}><option value="">请选择已关联的检验原件</option>{list.sources.map(s => <option key={s.id} value={s.id}>{s.metadata.title} · {s.name}</option>)}</select></label>
          {list.sources.find(s => s.id === draft.attachment_id) && <button type="button" onClick={() => action(() => sourceFile(list.sources.find(s => s.id === draft.attachment_id)))}>打开核对原件</button>}
          {!list.sources.length && <p>请先在“检查资料”关联一份检验报告。</p>}
          <label>报告类型<select aria-label="报告类型" value={draft.data.report.panel} onChange={e => reportChange("panel", e.target.value)}>{Object.entries(panels).map(([k,v]) => <option key={k} value={k}>{v}</option>)}</select></label>
          {Object.entries({ title: "报告标题", specimen: "样本类型", collected_at: "采样时间（含时区）", reported_at: "报告时间（含时区）", laboratory: "实验室", device: "仪器", note: "报告备注" }).map(([key,label]) => <label key={key}>{label}<input aria-label={label} maxLength={key === "note" ? 1000 : 150} value={draft.data.report[key]} placeholder={key.endsWith("_at") ? "2026-10-06T10:00:00+08:00，可留空" : ""} onChange={e => reportChange(key,e.target.value)} /></label>)}
          {draft.data.items.map((row,index) => <fieldset key={index} aria-label={`检验项目 ${index+1}`} style={box}>
            <legend>项目 {index+1}</legend>
            <label>结果类型<select aria-label={`项目 ${index+1} 结果类型`} value={row.result_type} onChange={e => rowChange(index,"result_type",e.target.value)}>{Object.entries(labTypes).map(([k,v]) => <option key={k} value={k}>{v}</option>)}</select></label>
            {Object.entries(fields).map(([key,label]) => <label key={key}>{label}<input aria-label={`项目 ${index+1} ${label}`} maxLength={key.includes("unit") ? 50 : 255} value={row[key]} onChange={e => rowChange(index,key,e.target.value)} /></label>)}
            <label><input type="checkbox" aria-label={`已核对项目 ${index+1}`} checked={row.checked} onChange={e => rowChange(index,"checked",e.target.checked)} />已对照原件核对本项目</label>
            <button type="button" disabled={draft.data.items.length === 1} onClick={() => change({ data: { ...draft.data, items: draft.data.items.filter((_,i) => i !== index) } })}>删除项目 {index+1}</button>
          </fieldset>)}
          <button type="button" disabled={draft.data.items.length >= 100} onClick={() => change({ data: { ...draft.data, items: [...draft.data.items,newLabRow()] } })}>添加检验项目</button>
        </fieldset>}
        {draft.operation !== "create" && <label>更正或撤销原因<textarea aria-label="更正或撤销原因" disabled={locked} maxLength={500} value={draft.reason} onChange={e => change({ reason:e.target.value })} /></label>}
        <button disabled={locked || (draft.operation !== "withdraw" && (!draft.attachment_id || !draft.data.items.every(r => r.checked)))} onClick={() => action(preview)}>核对整份检验记录</button>
        <button disabled={locked} onClick={() => { if (window.confirm(prompt)) reset(); }}>放弃本页检验草稿</button>
      </section>}
      {review && <section aria-label="整份检验核对" style={box}>
        <h3>核对整份检验记录</h3><p>病例 #{review.case.case_id} · {review.case.patient_name} · {review.case.species}</p>
        <p>宠主 {review.identity.owner_name || "未填写"} · 毛色 {review.identity.coat_color || "未填写"} · 性别 {review.identity.sex || "未填写"} · 品种 {review.identity.breed || "未填写"}</p>
        <p>原件：{review.source.name} · {review.source.metadata.title} · 版本 {review.before ? review.before.version + (review.operation === "correct" ? 1 : 0) : 1}</p>
        {review.data && <><dl>{Object.entries(review.data.report).map(([k,v]) => <React.Fragment key={k}><dt>{{title:"报告标题",panel:"报告类型",specimen:"样本类型",collected_at:"采样时间",reported_at:"报告时间",laboratory:"实验室",device:"仪器",note:"备注"}[k]}</dt><dd>{k === "panel" ? panels[v] : v || "未提供"}</dd></React.Fragment>)}</dl><Results data={review.data}/></>}
        {review.before && <details><summary>更正前的检验记录</summary><Results data={review.before.data}/></details>}
        <p>原因：{review.reason || "首次录入"}</p>
        <label><input type="checkbox" aria-label="已核对整份检验记录" disabled={locked} checked={checked} onChange={e => setChecked(e.target.checked)} />已核对病例、原件及整份检验内容</label>
        <button disabled={locked || !checked} onClick={() => action(confirm)}>确认保存检验记录</button>
      </section>}
      <h3>检验记录与版本历史</h3>
      {list.reports.map(row => <article key={row.id} style={box} aria-label={`检验记录 ${row.id}`}>
        <strong>{row.data.report.title}</strong> · 版本 {row.version} · {labStates[row.state] || "需核对状态"}
        <p>原件 {row.source.name} · 核对账号 {row.reviewed_by} · 核对时间 {row.reviewed_at} · 原因 {row.reason || "首次录入"}</p>
        <details><summary>查看该版本内容</summary><p>类型 {panels[row.data.report.panel]} · 样本 {row.data.report.specimen || "未提供"} · 采样 {row.data.report.collected_at || "未提供"} · 报告 {row.data.report.reported_at || "未提供"}</p><p>实验室 {row.data.report.laboratory || "未提供"} · 仪器 {row.data.report.device || "未提供"} · 备注 {row.data.report.note || "未提供"}</p><Results data={row.data}/></details>
        {!['withdrawn','superseded'].includes(row.state) && <><button disabled={locked || Boolean(draft)} onClick={() => edit(row,"correct")}>更正检验记录</button><button disabled={locked || Boolean(draft)} onClick={() => edit(row,"withdraw")}>撤销检验记录</button></>}
      </article>)}
      {!list.reports.length && <p>暂无已保存的检验项目。</p>}
    </>}
  </section>;
}
