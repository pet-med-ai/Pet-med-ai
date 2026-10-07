import React, { useEffect, useRef, useState } from "react";
import api from "../api";
import { draftOwner } from "../consultDraft";
import { validImagingReports, imagingTextSize, imagingDocumentMessage } from "../manualImagingDocuments";
import { imagingLabels, imagingModalities } from "../manualImagingRecords";
function Report({row}) {return <section aria-label={`影像报告 ${row.data.title}`}>
  <h3>{row.data.title} · 版本 {row.version}</h3>
  <p style={{overflowWrap:"anywhere"}}>报告编号 {row.root_id} · 原件 {row.source.name} · SHA-256：{row.source.sha256}</p>
  <p>核对账号 {row.reviewed_by} · 核对时间 {row.reviewed_at}</p>
  <dl>{Object.entries(imagingLabels).map(([k,label])=><React.Fragment key={k}><dt>{label}</dt><dd style={{whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}>{k==="modality"?imagingModalities[row.data[k]]:row.data[k] || "未提供"}</dd></React.Fragment>)}</dl>
</section>;}
export default function ClinicalDocImagingSelection({caseId,requestToken,selected=[],onChange,onInspect,reports,mode="select"}) {
  const [rows,setRows]=useState(null),[message,setMessage]=useState("");
  const generation=useRef(0),callbacks=useRef({onChange});callbacks.current={onChange};
  const current=stamp=>stamp===generation.current && Boolean(requestToken) && localStorage.getItem("token")===requestToken;
  async function reload() {
    const stamp=++generation.current;callbacks.current.onChange?.([]);setRows(null);setMessage("正在读取当前有效影像记录…");
    try {
      const {data}=await api.get(`/api/clinical-docs/cases/${caseId}/manual-imaging-options`,{timeout:15000,expectedAuthOwner:draftOwner(requestToken)});
      if(!current(stamp)) return;
      if(data.case_id!==caseId || data.writes_database!==false || !validImagingReports(data.reports)) throw Error("Incomplete imaging reports");
      setRows(data.reports);setMessage(data.reports.length?"最多选择 5 份影像记录、合计 20000 正文字符。选择后请重新读取完整草稿。":"当前没有可纳入的已核对影像记录。");
    }catch(error){if(current(stamp))setMessage(imagingDocumentMessage(error));}
  }
  useEffect(()=>{if(mode!=="select")return;void reload();const focus=()=>void reload();window.addEventListener("focus",focus);return()=>{generation.current++;window.removeEventListener("focus",focus);};},[caseId,requestToken,mode]);
  if(mode==="preview")return <section aria-label="影像报告文书附节"><h2>影像报告附节 · 已选择的核对原文</h2><p>以下内容将随本次草稿导出，原报告结论为原文记录。</p>{(reports || []).map(row=><Report key={row.id} row={row}/>)}</section>;
  function toggle(id,checked) {
    const ids=checked?[...selected,id]:selected.filter(i=>i!==id);
    if(ids.length>5 || imagingTextSize((rows || []).filter(row=>ids.includes(row.id)))>20000){setMessage("超出 5 份记录或 20000 字符上限，请减少选择；未截断原文。");return;}
    onChange([...ids].sort((a,b)=>a-b));
  }
  return <section aria-label="选择文书影像报告"><h3>纳入已核对影像记录</h3><p role="status">{message}</p>
    <button type="button" onClick={reload}>刷新可选影像记录</button>{" "}<button type="button" onClick={onInspect}>返回影像记录与原件</button>
    {(rows || []).map(row=><label key={row.id} style={{display:"block",margin:"10px 0"}}><input type="checkbox" aria-label={`纳入影像 ${row.data.title}`} checked={selected.includes(row.id)} onChange={e=>toggle(row.id,e.target.checked)}/>{row.data.title} · {imagingModalities[row.data.modality]} · {row.data.body_part} · {row.data.taken_at} · 版本 {row.version} · 核对账号 {row.reviewed_by}</label>)}
  </section>;
}
