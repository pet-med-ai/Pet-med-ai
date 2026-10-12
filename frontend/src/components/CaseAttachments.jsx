import React, { useEffect, useRef, useState } from "react";
import { attachmentClient, attachmentMessage, attachmentMetadata, newAttachmentRequest, verifyAttachmentBytes } from "../caseAttachments";

const kinds = { lab: "检验报告", dr: "DR", ultrasound: "超声", other: "其他" };
const box = { padding: 16, border: "1px solid #ccd5d1", borderRadius: 8, margin: "12px 0" };

export default function CaseAttachments(props) {
  return <AttachmentPanel key={JSON.stringify([props.caseId, props.requestToken])} {...props} />;
}

function AttachmentPanel({ caseId, requestToken, onChanged }) {
  const [list, setList] = useState(null), [busy, setBusy] = useState(false), [message, setMessage] = useState("");
  const [file, setFile] = useState(null), [stage, setStage] = useState(null), [editing, setEditing] = useState(null);
  const [meta, setMeta] = useState(attachmentMetadata), [reason, setReason] = useState("");
  const [review, setReview] = useState(null), [checked, setChecked] = useState(false), [filter, setFilter] = useState("");
  const [type, setType] = useState(""), [image, setImage] = useState(null), [unknown, setUnknown] = useState(null);
  const control = useRef(null), active = useRef(false), inFlight = useRef(false), imageUrl = useRef(null), input = useRef(null);
  const current = () => active.current && localStorage.getItem("token") === requestToken;
  const client = (method, path, data, options) => attachmentClient(caseId, requestToken, control.current?.signal)(method, path, data, options);
  function clearImage() { if (imageUrl.current) URL.revokeObjectURL(imageUrl.current); imageUrl.current = null; setImage(null); }
  function invalidate() { setReview(null); setChecked(false); }
  function reset() { setFile(null); setStage(null); setEditing(null); setMeta(attachmentMetadata()); setReason(""); setUnknown(null); invalidate(); if (input.current) input.current.value = ""; }
  async function refresh() { const result = await client("get"); if (current()) setList(result); return result; }
  async function action(fn) {
    if (!current() || inFlight.current) return;
    inFlight.current = true; setBusy(true); setMessage("");
    try { await fn(); } catch (error) { if (current()) setMessage(attachmentMessage(error)); }
    finally { inFlight.current = false; if (current()) setBusy(false); }
  }
  useEffect(() => {
    active.current = true; control.current = new AbortController();
    action(refresh);
    return () => { active.current = false; control.current.abort(); if (imageUrl.current) URL.revokeObjectURL(imageUrl.current); };
  }, [caseId, requestToken]);

  function selected(value) {
    invalidate(); setStage(null); setEditing(null); setUnknown(null); setFile(null);
    if (!value) return;
    if (!/\.(pdf|jpe?g|png)$/i.test(value.name) || !value.size || value.size > 10 * 1024 * 1024) {
      setMessage("请选择不超过 10 MiB 的 PDF、JPG 或 PNG 文件。"); return;
    }
    setFile(value); setMeta({ ...attachmentMetadata(), title: value.name }); setMessage("");
  }
  async function readUnknown(pending) {
    const result = await client("get", pending.kind === "upload" ? `/uploads/${pending.id}` : `/requests/${pending.id}`);
    if (!current()) return;
    if (pending.kind === "upload" && result.state === "pending") {
      setStage({ ...result.attachment, uploadId: pending.id }); setUnknown(null); setMessage("上传已核实，请核对后确认关联。");
    } else if (["committed", "active", "withdrawn", "already_attached"].includes(result.state)) {
      reset(); await refresh(); if (current()) { onChanged?.(); setMessage("操作结果已回读，未重复提交。"); }
    } else if (["expired", "cancelled"].includes(result.state)) {
      reset(); await refresh(); if (current()) setMessage("暂存已取消或到期，请重新选择文件。");
    } else if (result.state === "not_committed") {
      setUnknown(null); invalidate(); await refresh(); if (current()) setMessage("未找到已提交结果，请重新核对后操作。");
    }
  }
  async function upload() {
    const rid = newAttachmentRequest(), pending = { kind: "upload", id: rid };
    const mime = /\.pdf$/i.test(file.name) ? "application/pdf" : /\.png$/i.test(file.name) ? "image/png" : "image/jpeg";
    try {
      const result = await client("post", `/uploads/${rid}`, file, { headers: { "Content-Type": mime,
        "X-Attachment-Filename": encodeURIComponent(file.name), "X-Case-Token": list.case_token } });
      if (!current()) return;
      if (result.state === "pending") { setStage({ ...result.attachment, uploadId: rid }); setMessage("原件已暂存，请核对后确认关联。"); }
      else { reset(); await refresh(); if (current()) setMessage("相同原件已关联，未重复添加。"); }
    } catch (error) {
      if (!current()) return;
      setUnknown(pending); setMessage(attachmentMessage(error));
      try { await readUnknown(pending); } catch { if (current()) setMessage("上传结果未知，请点击核对结果；不要重复上传。"); }
    }
  }
  async function preview(operation, item) {
    const body = { request_id: newAttachmentRequest(), attachment_id: item.id, operation,
      expected_case_token: list.case_token, metadata: meta, reason };
    const result = await client("post", "/preview", body);
    if (current()) { setReview({ ...result, body }); setChecked(false); }
  }
  async function confirm() {
    const pending = { kind: "operation", id: review.body.request_id };
    try {
      await client("post", "/confirm", { ...review.body, preview_token: review.preview_token, reviewed: true });
      if (current()) { reset(); clearImage(); await refresh(); if (current()) { onChanged?.(); setMessage("资料操作已保存。"); } }
    } catch (error) {
      if (!current()) return;
      setUnknown(pending); setChecked(false); setMessage(attachmentMessage(error));
      try { await readUnknown(pending); } catch { if (current()) setMessage("保存结果未知，请核对结果；不要重复确认。"); }
    }
  }
  async function content(item, show) {
    const bytes = await client("get", `/${item.id}/content?request_id=${newAttachmentRequest()}&preview=${show}`, undefined, { responseType: "arraybuffer" });
    await verifyAttachmentBytes(bytes, item);
    if (!current()) return;
    const url = URL.createObjectURL(new Blob([bytes], { type: item.mime }));
    if (show) { clearImage(); imageUrl.current = url; setImage({ url, name: item.name }); }
    else { const link = document.createElement("a"); link.href = url; link.download = item.name; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
  }
  function edit(item, operation) { reset(); clearImage(); setEditing({ item, operation }); setMeta(item.metadata); }
  const locked = busy || Boolean(unknown);
  const rows = (list?.items || []).filter(a => (!type || a.metadata?.kind === type) && `${a.name} ${a.metadata?.title}`.toLowerCase().includes(filter.toLowerCase()));
  return <section aria-label="检查资料" style={box}>
    <h2>检查资料</h2>
    {list && <p>当前病例 #{list.case_id} · {list.patient_name} · {list.species}</p>}
    <p>选择报告或图片，核对后关联到本病例。每个原件最多 10 MiB。</p>
    <button type="button" disabled={busy} onClick={() => action(async () => { invalidate(); clearImage(); await refresh(); })}>刷新资料列表</button>
    <p role="status">{busy ? "正在处理…" : message}</p>
    {unknown && <button type="button" disabled={busy} onClick={() => action(() => readUnknown(unknown))}>核对操作结果</button>}
    {list && <>
      {!stage && !editing && <label>选择检查文件<input ref={input} type="file" accept=".pdf,.jpg,.jpeg,.png" disabled={locked} onChange={e => selected(e.target.files?.[0])} /></label>}
      {file && !stage && <button type="button" disabled={locked} onClick={() => action(upload)}>上传待核对原件</button>}
      {(stage || editing) && <div style={box}>
        <p>原件：{(stage || editing.item).name} · {(stage || editing.item).size} 字节</p>
        {editing?.operation !== "withdraw" && <fieldset disabled={locked}>
          <legend>资料信息</legend>
          <label>资料标题<input maxLength={150} value={meta.title} onChange={e => { setMeta({ ...meta, title: e.target.value }); invalidate(); }} /></label>
          <label>资料类型<select aria-label="资料类型" value={meta.kind} onChange={e => { setMeta({ ...meta, kind: e.target.value }); invalidate(); }}>{Object.entries(kinds).map(([k,v]) => <option key={k} value={k}>{v}</option>)}</select></label>
          {[['taken_at', '采样或检查时间'], ['reported_at', '报告时间']].map(([k,label]) => <label key={k}>{label}<input type="datetime-local" value={meta[k] ? new Date(new Date(meta[k]).getTime() - new Date(meta[k]).getTimezoneOffset()*60000).toISOString().slice(0,16) : ""} onChange={e => { setMeta({ ...meta, [k]: e.target.value ? new Date(e.target.value).toISOString() : "" }); invalidate(); }} /></label>)}
          <label>来源机构<input maxLength={150} value={meta.source} onChange={e => { setMeta({ ...meta, source: e.target.value }); invalidate(); }} /></label>
          <label>备注<textarea maxLength={1000} value={meta.note} onChange={e => { setMeta({ ...meta, note: e.target.value }); invalidate(); }} /></label>
        </fieldset>}
        {editing?.operation === "withdraw" && <label>撤销原因<textarea maxLength={500} disabled={locked} value={reason} onChange={e => { setReason(e.target.value); invalidate(); }} /></label>}
        <button type="button" disabled={locked} onClick={() => action(() => preview(editing?.operation || "confirm", stage || editing.item))}>核对资料关联</button>
        <button type="button" disabled={locked} onClick={() => action(async () => { if (stage) await client("post", `/uploads/${stage.uploadId}/cancel`); if (current()) { reset(); setMessage("本次操作已取消。"); } })}>取消本次操作</button>
      </div>}
      {review && <section aria-label="资料关联核对" style={box}>
        <h3>{review.operation === "withdraw" ? "核对撤销关联" : "核对资料关联"}</h3>
        <p>病例 #{review.case_id} · {review.patient_name} · {review.species}</p>
        <p>原件：{review.proposed.name} · {review.proposed.size} 字节</p>
        <p>标题：{review.proposed.metadata?.title}；类型：{kinds[review.proposed.metadata?.kind]}</p>
        <p>检查时间：{review.proposed.metadata?.taken_at || "未记录"}；报告时间：{review.proposed.metadata?.reported_at || "未记录"}</p>
        <p>来源：{review.proposed.metadata?.source || "未记录"}；备注：{review.proposed.metadata?.note || "未记录"}</p>
        {review.operation === "withdraw" && <p>撤销原因：{review.proposed.withdrawal_reason}</p>}
        <label><input type="checkbox" disabled={locked} checked={checked} onChange={e => setChecked(e.target.checked)} />已核对病例、原件和资料信息</label>
        <button type="button" disabled={locked || !checked} onClick={() => action(confirm)}>确认资料操作</button>
      </section>}
      <label>筛选资料<input value={filter} onChange={e => setFilter(e.target.value)} /></label>
      <label>筛选类型<select aria-label="筛选类型" value={type} onChange={e => setType(e.target.value)}><option value="">全部</option>{Object.entries(kinds).map(([k,v]) => <option key={k} value={k}>{v}</option>)}</select></label>
      {list.legacy_count > 0 && <p>另有 {list.legacy_count} 条历史附件记录，本页保留原记录。</p>}
      <ul>{rows.map(item => <li key={item.id} style={{ margin: '12px 0' }}>
        <strong>{item.metadata?.title || item.name}</strong> · {kinds[item.metadata?.kind]} · {item.state === "active" ? "已关联" : "已撤销"}
        <div>{item.name} · {item.size} 字节 · 检查时间 {item.metadata?.taken_at || "未记录"} · 来源 {item.metadata?.source || "未记录"}</div>
        {item.state === "active" ? <>
          {item.mime.startsWith("image/") && <button type="button" disabled={locked} onClick={() => action(() => content(item, true))}>查看图片</button>}
          <button type="button" disabled={locked} onClick={() => action(() => content(item, false))}>下载原件</button>
          <button type="button" disabled={locked || Boolean(stage) || Boolean(editing)} onClick={() => edit(item, "update")}>更正资料信息</button>
          <button type="button" disabled={locked || Boolean(stage) || Boolean(editing)} onClick={() => edit(item, "withdraw")}>撤销关联</button>
        </> : <span> · 原因：{item.withdrawal_reason}</span>}
      </li>)}</ul>
      {!rows.length && <p>暂无匹配的检查资料。</p>}
      {image && <div><img alt={image.name} src={image.url} style={{ maxWidth: "100%", maxHeight: 600 }} /><button onClick={clearImage}>关闭图片</button></div>}
    </>}
  </section>;
}
