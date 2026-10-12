import React, { useEffect, useRef, useState } from "react";
import "./ClinicalLabTable.css";
import api from "../api";
import { flagStates, rangeMessage, rangeStates, readRangeReview, unableStates } from "../labRangeReview";
import { labStates, labTypes } from "../manualLabResults";

const box = { padding: 16, margin: "12px 0", border: "1px solid #ccd5d1", borderRadius: 8, overflowWrap: "anywhere" };
const literal = value => value === "" ? "未提供" : value;
export default function CaseLabRangeReview(props) { return <RangeReview key={JSON.stringify([props.caseId, props.requestToken])} {...props} />; }
function RangeReview({ caseId, requestToken, sourceRevision = 0, onInspect, onCompare }) {
  const [saved, setSaved] = useState(null), [message, setMessage] = useState(""), [busy, setBusy] = useState(false), [filter, setFilter] = useState("all");
  const active = useRef(false), epoch = useRef(0), controller = useRef(null), refresh = useRef(null);
  const current = () => active.current && Boolean(requestToken) && localStorage.getItem("token") === requestToken;
  refresh.current = async () => {
    const attempt = ++epoch.current;
    controller.current?.abort(); controller.current = new AbortController();
    setSaved(null); setMessage("");
    if (!current()) { setBusy(false); setMessage("登录已变化，请重新打开病例。"); return; }
    setBusy(true);
    try { const result = await readRangeReview(caseId, requestToken, controller.current.signal); if (current() && attempt === epoch.current) setSaved({ result, revision: sourceRevision }); }
    catch (error) { if (active.current && attempt === epoch.current) setMessage(current() ? rangeMessage(error) : "登录已变化，请重新打开病例。"); }
    finally { if (active.current && attempt === epoch.current) setBusy(false); }
  };
  useEffect(() => {
    active.current = true; refresh.current();
    const focus = () => refresh.current();
    const storage = event => { if (event.key === "token" || event.key === null) refresh.current(); };
    window.addEventListener("focus", focus); window.addEventListener("storage", storage);
    return () => { active.current = false; epoch.current++; controller.current?.abort(); window.removeEventListener("focus", focus); window.removeEventListener("storage", storage); };
  }, [caseId, requestToken]);
  useEffect(() => {
    const affects = config => config?.method?.toLowerCase() === "post" && ["attachments", "manual-lab"].some(kind => config.url === `/api/cases/${caseId}/${kind}/confirm`);
    const request = api.interceptors.request.use(config => {
      if (current() && affects(config)) { epoch.current++; controller.current?.abort(); setSaved(null); setBusy(false); setMessage("资料操作已开始，等待重新读取。"); }
      return config;
    });
    const success = response => { if (current() && affects(response.config)) refresh.current(); return response; };
    const failure = error => { if (current() && affects(error.config)) refresh.current(); return Promise.reject(error); };
    const response = api.interceptors.response.use(success, failure);
    return () => { api.interceptors.request.eject(request); api.interceptors.response.eject(response); };
  }, [caseId, requestToken]);
  const previousRevision = useRef(sourceRevision);
  useEffect(() => { if (previousRevision.current !== sourceRevision) { previousRevision.current = sourceRevision; refresh.current(); } }, [sourceRevision]);
  const data = current() && saved?.revision === sourceRevision ? saved.result : null;
  const shown = item => filter === "all" || (filter === "out" ? ["below", "above"].includes(item.comparison.state) : unableStates.includes(item.comparison.state));
  const inspect = row => <button type="button" onClick={() => { if (current() && data) onInspect?.({ caseId, id: row.id, version: row.version, token: row.token }); }}>回看检验记录 #{row.id} 版本 {row.version}</button>;
  const source = row => <><p>采样时间：{literal(row.report.collected_at)} · 报告时间：{literal(row.report.reported_at)}</p><p>核对账号：{row.reviewed_by} · 核对时间：{row.reviewed_at}</p><p>来源文件：{row.source.name} · SHA256：<code>{row.source.sha256}</code></p>{inspect(row)}</>;
  return <section aria-label="检验结果区间核对" style={box}>
    <h2>检验结果区间核对</h2>
    {onCompare && <button type="button" onClick={() => { if (current()) onCompare(); }}>进入同次就诊检验前后对照</button>}
    <p>仅比较已保存、当前有效的人工检验记录；未保存草稿不参与。这里只表示数值与原报告参考区间的位置，不作诊断。</p>
    <p>位于上下限之间、没有区间外项目或已核对，都不代表健康或排除疾病。边界含义仍需医生核对。</p>
    <button type="button" onClick={() => refresh.current()}>刷新检验区间核对</button><p role="status" aria-live="polite">{busy ? "正在读取检验区间…" : message}</p>
    {data && <>
      <p>病例 #{data.case_id} · {data.identity.patient_name || "动物名未填写"} · {data.identity.species || "物种未填写"}</p>
      <p>宠主 {data.identity.owner_name || "未填写"} · 联系方式 {data.identity.owner_phone || "未填写"} · 性别 {data.identity.sex || "未填写"} · 品种 {data.identity.breed || "未填写"} · 毛色 {data.identity.coat_color || "未填写"} · 年龄 {data.identity.age_info || "未填写"} · 体重 {data.identity.weight || "未填写"}</p>
      <p>读取时间：<time dateTime={data.read_at}>{data.read_at}</time> · 快照 <code>{data.snapshot}</code>。后续变更请刷新。</p>
      <p>当前报告 {data.counts.reports} · 项目 {data.counts.items} · 区间外 {data.counts.out_of_range} · 无法比较 {data.counts.unable} · 边界值 {data.counts.boundary} · 标记冲突 {data.counts.flag_conflicts}</p>
      <label>项目筛选<select aria-label="检验区间项目筛选" value={filter} onChange={e => setFilter(e.target.value)}><option value="all">全部项目（{data.counts.items}）</option><option value="out">区间外（{data.counts.out_of_range}）</option><option value="unable">无法比较（{data.counts.unable}）</option></select></label>
      {!data.reports.length && <p>没有当前可比较的已核对报告，请查看下方未纳入记录或返回检验录入。</p>}
      {data.reports.map(row => <article key={row.id} aria-label={`区间报告 ${row.id}`} style={box}>
        <h3>{row.title} · 版本 {row.version}</h3>{source(row)}
        <p>本报告显示 {row.items.filter(shown).length} / {row.items.length} 项</p>
        <p>表格可横向滚动查看全部字段；键盘可聚焦表格后使用左右方向键。</p>
        <div className="clinical-lab-table-region" role="region" aria-label="区间核对表，可横向滚动" tabIndex={0}><table className="clinical-lab-table"><thead><tr>{["项目与位置", "类型", "结果原文", "单位", "参考范围原文", "下限", "上限", "参考单位", "原始标记", "区间位置", "标记核对"].map(label => <th key={label} scope="col">{label}</th>)}</tr></thead><tbody>
          {row.items.filter(shown).map(item => <tr key={item.index}>{[`${item.index}. ${item.name}\n${item.position}`, labTypes[item.result_type], literal(item.value), literal(item.unit), literal(item.reference), literal(item.reference_low), literal(item.reference_high), literal(item.reference_unit), literal(item.flag), rangeStates[item.comparison.state], flagStates[item.comparison.flag_state]].map((v, i) => <td key={i} className={([3,4,5,6,7].includes(i) || (i === 2 && ["number", "comparison"].includes(item.result_type))) ? "clinical-lab-table__literal" : "clinical-lab-table__text"}>{v}</td>)}</tr>)}
        </tbody></table></div>
      </article>)}
      <h3>未纳入当前比较的记录</h3><p>旧版本按原记录列出，不重复计入当前报告与项目数量。</p>
      {data.excluded.map(row => <article key={row.id} style={box}><h4>{row.title} · 版本 {row.version} · {labStates[row.state]}</h4>{source(row)}<p>原因：{row.invalidated_reason || row.reason || labStates[row.state]}</p></article>)}
      {!data.excluded.length && <p>暂无本流程被排除的记录。</p>}
      {data.legacy_count > 0 && <p>另有 {data.legacy_count} 条旧式报告未参与区间比较，请回原入口核对。</p>}
      <p>回看不会自动下载原件。请在检验记录中明确选择打开原件；更正和撤销仍需逐项与整份核对。文书内容和下载选择不随筛选自动改变。</p>
    </>}
  </section>;
}
