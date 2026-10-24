import React, { useEffect, useRef, useState } from "react";
import api from "../api";
import { comparisonMessage, comparisonReasons, deltaStates, itemSelection, previewComparison, readComparison } from "../labComparison";
import { labStates, labTypes } from "../manualLabResults";

const box = { padding: 16, margin: "12px 0", border: "1px solid #ccd5d1", borderRadius: 8, overflowWrap: "anywhere" };
const literal = v => v === "" || v === null ? "未填写" : v;
const empty = () => ({ a: { report: "", item: "" }, b: { report: "", item: "" } });
export default function CaseLabComparison(props) { return <Comparison key={JSON.stringify([props.caseId, props.requestToken])} {...props} />; }
function Comparison({ caseId, requestToken, sourceRevision = 0, onInspect, onSelect, onInvalidated }) {
  const [saved, setSaved] = useState(null), [selected, setSelected] = useState(empty), [confirmed, setConfirmed] = useState(false);
  const [preview, setPreview] = useState(null), [message, setMessage] = useState(""), [busy, setBusy] = useState(false), [calculating, setCalculating] = useState(false);
  const active = useRef(false), epoch = useRef(0), calculation = useRef(0), reader = useRef(null), calculator = useRef(null), refresh = useRef(null);
  const callbacks = useRef({ onSelect, onInvalidated }); callbacks.current = { onSelect, onInvalidated };
  const previewRequest = useRef(null), runPending = useRef(false);
  const current = () => active.current && Boolean(requestToken) && localStorage.getItem("token") === requestToken;
  const clearPreview = () => { callbacks.current.onInvalidated?.(); previewRequest.current = null; runPending.current = false; calculation.current++; calculator.current?.abort(); setPreview(null); setCalculating(false); setConfirmed(false); };
  const clear = () => { clearPreview(); setSelected(empty()); setSaved(null); };
  refresh.current = async () => {
    const attempt = ++epoch.current; reader.current?.abort(); reader.current = new AbortController(); clear(); setMessage("");
    if (!current()) { setBusy(false); setMessage("登录已变化，请重新打开病例。"); return; }
    setBusy(true);
    try { const result = await readComparison(caseId, requestToken, reader.current.signal); if (current() && attempt === epoch.current) setSaved({ result, revision: sourceRevision }); }
    catch (error) { if (active.current && attempt === epoch.current) setMessage(current() ? comparisonMessage(error) : "登录已变化，请重新打开病例。"); }
    finally { if (active.current && attempt === epoch.current) setBusy(false); }
  };
  useEffect(() => {
    active.current = true; refresh.current();
    const focus = () => refresh.current(), storage = event => { if (event.key === "token" || event.key === null) refresh.current(); };
    window.addEventListener("focus", focus); window.addEventListener("storage", storage);
    return () => { active.current = false; epoch.current++; calculation.current++; reader.current?.abort(); calculator.current?.abort(); window.removeEventListener("focus", focus); window.removeEventListener("storage", storage); };
  }, [caseId, requestToken]);
  useEffect(() => {
    const affects = config => config?.method?.toLowerCase() === "post" && ["attachments", "manual-lab"].some(kind => config.url === `/api/cases/${caseId}/${kind}/confirm`);
    const request = api.interceptors.request.use(config => {
      if (current() && affects(config)) { epoch.current++; reader.current?.abort(); clear(); setBusy(false); setMessage("资料操作已开始，等待重新读取。"); }
      return config;
    });
    const response = api.interceptors.response.use(r => { if (current() && affects(r.config)) refresh.current(); return r; }, e => { if (current() && affects(e.config)) refresh.current(); return Promise.reject(e); });
    return () => { api.interceptors.request.eject(request); api.interceptors.response.eject(response); };
  }, [caseId, requestToken]);
  const previousRevision = useRef(sourceRevision);
  useEffect(() => { if (previousRevision.current !== sourceRevision) { previousRevision.current = sourceRevision; refresh.current(); } }, [sourceRevision]);
  const data = current() && saved?.revision === sourceRevision ? saved.result : null;
  const pair = side => { const row = data?.reports.find(r => String(r.id) === selected[side].report); return [row, row?.items.find(i => String(i.index) === selected[side].item)]; };
  const change = (side, field, value) => { clearPreview(); setMessage(""); setSelected(old => ({ ...old, [side]: { ...old[side], [field]: value, ...(field === "report" ? { item: "" } : {}) } })); };
  const inspect = row => <button type="button" onClick={() => { if (current() && data) onInspect?.({ caseId, id: row.id, version: row.version, token: row.token }); }}>回看检验记录 #{row.id} 版本 {row.version}</button>;
  const source = row => <><p>采样时间：{literal(row.report.collected_at)} · 报告时间：{literal(row.report.reported_at)}</p><p>核对账号：{row.reviewed_by} · 核对时间：{row.reviewed_at}</p><p>来源文件：{row.source.name} · SHA256：<code>{row.source.sha256}</code></p>{inspect(row)}</>;
  const run = async () => {
    const a = pair("a"), b = pair("b"); if (runPending.current || !current() || !data || !a[1] || !b[1]) return;
    const request = { snapshot: data.snapshot, a: itemSelection(...a), b: itemSelection(...b), doctor_confirmed: confirmed };
    callbacks.current.onInvalidated?.(); runPending.current = true; previewRequest.current = null;
    const attempt = ++calculation.current; calculator.current?.abort(); calculator.current = new AbortController(); setPreview(null); setMessage(""); setCalculating(true);
    try { const result = await previewComparison(data, request, requestToken, calculator.current.signal); if (current() && attempt === calculation.current) { previewRequest.current = request; setPreview(result); } }
    catch (error) { if (active.current && attempt === calculation.current) { setMessage(current() ? comparisonMessage(error) : "登录已变化，请重新打开病例。"); if ([401, 404, 409, 422].includes(error?.response?.status)) clear(); } }
    finally { if (active.current && attempt === calculation.current) { runPending.current = false; setCalculating(false); } }
  };
  return <section aria-label="同次就诊检验前后对照" style={box}>
    <h2>同次就诊检验前后对照</h2>
    <p>选择同一次就诊的两份当前有效、已核对报告。未保存草稿不参与；默认不选择或配对项目。</p>
    <p>只有名称、单位、检验组合、样本类型、实验室和设备一致，且 A 采样早于 B，才可在医生核实方法与采样条件后相减。这里只显示数值变化，不判断病情好转或恶化。</p>
    <button type="button" onClick={() => refresh.current()}>刷新检验前后对照</button>
    <p role="status" aria-live="polite">{busy ? "正在读取前后对照…" : calculating ? "正在核对保存版本与可比条件…" : message}</p>
    {data && <>
      <p>病例 #{data.case_id} · {data.identity.patient_name || "动物名未填写"} · {data.identity.species || "物种未填写"}</p>
      <p>宠主 {literal(data.identity.owner_name)} · 联系方式 {literal(data.identity.owner_phone)} · 性别 {literal(data.identity.sex)} · 品种 {literal(data.identity.breed)} · 毛色 {literal(data.identity.coat_color)} · 年龄 {literal(data.identity.age_info)} · 体重 {literal(data.identity.weight)}</p>
      <p>读取时间：<time dateTime={data.read_at}>{data.read_at}</time> · 快照 <code>{data.snapshot}</code></p>
      <p>当前报告 {data.counts.reports} · 保存项目 {data.counts.items}</p>
      {!data.reports.length && <p>没有当前可选择的已核对报告，请回原入口处理或查看下方未纳入记录。</p>}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 340px), 1fr))", gap: 16 }}>
        {["a", "b"].map(side => { const [row, item] = pair(side), label = side.toUpperCase(); return <article key={side} aria-label={`对照 ${label}`} style={box}>
          <h3>{label} · {side === "a" ? "较早采样" : "较晚采样"}</h3>
          <label>报告 {label}<select aria-label={`对照报告 ${label}`} style={{ maxWidth: "100%" }} value={selected[side].report} onChange={e => change(side, "report", e.target.value)}><option value="">请选择报告</option>{data.reports.map(r => <option key={r.id} value={String(r.id)}>#{r.id} {r.title} · 版本 {r.version}</option>)}</select></label>
          {row && <><h4>{row.title} · 版本 {row.version}</h4>{source(row)}<p>检验组合 {row.report.panel} · 样本 {literal(row.report.specimen)} · 实验室 {literal(row.report.laboratory)} · 设备 {literal(row.report.device)}</p><p style={{ whiteSpace: "pre-wrap" }}>报告备注：{literal(row.report.note)}</p>
            <label>项目 {label}<select aria-label={`对照项目 ${label}`} style={{ maxWidth: "100%" }} value={selected[side].item} onChange={e => change(side, "item", e.target.value)}><option value="">请选择项目</option>{row.items.map(i => <option key={i.index} value={String(i.index)}>{i.index}. {i.name} · {i.position}</option>)}</select></label>
            {item && <dl style={{ whiteSpace: "pre-wrap" }}>{[["项目原文", item.name], ["原文位置", item.position], ["结果类型", labTypes[item.result_type]], ["结果原文", item.value], ["单位", item.unit], ["参考范围原文", item.reference], ["下限", item.reference_low], ["上限", item.reference_high], ["参考单位", item.reference_unit], ["原始标记", item.flag]].map(([key, value]) => <React.Fragment key={key}><dt style={{ fontWeight: "bold", marginTop: 8 }}>{key}</dt><dd style={{ marginLeft: 0 }}>{literal(value)}</dd></React.Fragment>)}</dl>}
          </>}
        </article>; })}
      </div>
      <button type="button" disabled={!selected.a.report && !selected.b.report} onClick={() => { clearPreview(); setMessage(""); setSelected(old => ({ a: old.b, b: old.a })); }}>交换 A 与 B</button>
      <p>设备和实验室名称相同不能证明方法相同，请对照原件核实。此处勾选仅用于当前预览，刷新或选择变化后清除，不保存为报告核对或医生验收记录。</p>
      <label><input type="checkbox" aria-label="确认方法与采样条件可比" checked={confirmed} onChange={e => { clearPreview(); setConfirmed(e.target.checked); setMessage(""); }} />已对照原件确认同一项目、方法和采样条件可比</label>
      <button type="button" disabled={busy || calculating || !pair("a")[1] || !pair("b")[1]} onClick={run}>核对条件并预览数值差</button>
      {preview && <article aria-label="检验对照预览" style={box}>
        <p>核对时间：{preview.read_at}</p>
        {preview.reference_changed && <p>参考范围不同，请分别回看。两侧参考范围不会互相套用。</p>}
        {preview.can_calculate ? <><h3>{deltaStates[preview.delta.state]}</h3><p>差值 B−A：<strong>{preview.delta.value}</strong> {preview.delta.unit}</p><p>数值变化不等于病情变化，不自动写入诊断或文书。</p></> : <><h3>当前不能计算数值差</h3><ul>{preview.reasons.map(reason => <li key={reason}>{comparisonReasons[reason]}</li>)}</ul></>}
        {onSelect && preview.can_calculate && <button type="button" onClick={() => { if (current() && previewRequest.current) callbacks.current.onSelect?.(data, previewRequest.current, preview); }}>纳入本次文书核对</button>}
      </article>}
      <h3>未纳入当前对照的记录</h3>
      {data.excluded.map(row => <article key={row.id} style={box}><h4>{row.title} · 版本 {row.version} · {labStates[row.state]}</h4>{source(row)}<p>原因：{row.invalidated_reason || row.reason || labStates[row.state]}</p></article>)}
      {!data.excluded.length && <p>暂无本流程被排除的记录。</p>}
      {data.legacy_count > 0 && <p>另有 {data.legacy_count} 条旧式报告未参与对照，请回原入口核对。</p>}
      <p>回看保留现有未保存草稿。打开原件需在检验记录中明确点击；本页不自动下载原件或文书。</p>
    </>}
  </section>;
}
