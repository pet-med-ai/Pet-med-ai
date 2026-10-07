import React, { useEffect, useRef, useState } from "react";
import api from "../api";
import { draftOwner } from "../consultDraft";
import { documentResult, manualLabDocumentMessage, validDocumentReports } from "../manualLabDocuments";

function Report({ row }) {
  const r = row.data.report;
  return <section aria-label={`检验报告 ${r.title}`}>
    <h3>{r.title} · 版本 {row.version}</h3>
    <p>样本：{r.specimen || "未提供"}；采样：{r.collected_at || "未提供"}；报告：{r.reported_at || "未提供"}</p>
    <p>实验室：{r.laboratory || "未提供"}；仪器：{r.device || "未提供"}；核对账号：{row.reviewed_by}；核对时间：{row.reviewed_at}</p>
    <p style={{overflowWrap:"anywhere"}}>报告编号：{row.root_id}；原件：{row.source.name}；SHA-256：{row.source.sha256}</p>
    <div style={{overflowX:"auto"}}><table style={{borderCollapse:"collapse",width:"100%"}}>
      <thead><tr>{["项目","结果原文","单位","参考区间原文","原报告标记","原报告位置"].map(s=><th key={s} scope="col">{s}</th>)}</tr></thead>
      <tbody>{row.data.items.map((i,n)=><tr key={n}>{[i.name,documentResult(i),i.unit || "未提供",i.reference || "未提供",i.flag || "未提供",i.position].map((v,k)=><td key={k} style={{whiteSpace:"pre-wrap",overflowWrap:"anywhere",border:"1px solid #aaa",padding:6}}>{v}</td>)}</tr>)}</tbody>
    </table></div>
    {r.note && <p style={{whiteSpace:"pre-wrap"}}>报告备注原文：{r.note}</p>}
  </section>;
}

export default function ClinicalDocLabSelection({ caseId, requestToken, selected = [], onChange, onInspect, reports, mode = "select" }) {
  const [rows,setRows] = useState(null), [message,setMessage] = useState("");
  const generation = useRef(0), callbacks = useRef({onChange}); callbacks.current = {onChange};
  const current = stamp => stamp === generation.current && localStorage.getItem("token") === requestToken;
  async function reload() {
    const stamp=++generation.current;
    callbacks.current.onChange?.([]); setRows(null); setMessage("正在读取当前有效检验报告…");
    try {
      const {data} = await api.get(`/api/clinical-docs/cases/${caseId}/manual-lab-options`, {timeout:15000,expectedAuthOwner:draftOwner(requestToken)});
      if (!current(stamp)) return;
      if (data.case_id !== caseId || data.writes_database !== false || !validDocumentReports(data.reports)) throw Error("Incomplete reports");
      setRows(data.reports); setMessage(data.reports.length ? "每次最多 5 份报告、合计 200 项。选择后请重新读取完整草稿。" : "当前没有可纳入的已核对检验报告。");
    } catch(error) { if(current(stamp)) setMessage(manualLabDocumentMessage(error)); }
  }
  useEffect(()=>{
    if(mode !== "select") return;
    void reload();
    const focus=()=>{void reload();}; window.addEventListener("focus",focus);
    return ()=>{generation.current++;window.removeEventListener("focus",focus);};
  },[caseId,requestToken,mode]);
  if(mode === "preview") return <section aria-label="检验结果文书附节">
    <h2>检验结果附节 · 已选择的核对原文</h2>
    <p>以下内容将随本次草稿导出。原报告标记仅为抄录，不代表系统诊断。</p>
    {(reports || []).map(row=><Report key={row.id} row={row}/>)}
  </section>;
  function toggle(id, checked) {
    const ids=checked ? [...selected,id] : selected.filter(i=>i!==id);
    if(ids.length>5 || (rows || []).filter(r=>ids.includes(r.id)).reduce((n,r)=>n+r.data.items.length,0)>200) {
      setMessage("超出 5 份报告或 200 项上限，请减少选择；未截断报告。"); return;
    }
    onChange([...ids].sort((a,b)=>a-b));
  }
  return <section aria-label="选择文书检验报告">
    <h3>纳入已核对检验报告</h3>
    <p role="status">{message}</p>
    <button type="button" onClick={reload}>刷新可选检验报告</button>{" "}
    <button type="button" onClick={onInspect}>返回检验项目与原件</button>
    {(rows || []).map(row=><label key={row.id} style={{display:"block",margin:"10px 0"}}>
      <input type="checkbox" aria-label={`纳入 ${row.data.report.title}`} checked={selected.includes(row.id)} onChange={e=>toggle(row.id,e.target.checked)}/>
      {row.data.report.title} · 版本 {row.version} · {row.data.items.length} 项 · 报告时间 {row.data.report.reported_at || "未提供"} · {row.data.report.laboratory || "实验室未提供"} · 核对账号 {row.reviewed_by}
    </label>)}
  </section>;
}
