import React, {useEffect, useRef, useState} from 'react';
import {ContactContent} from './CaseFollowupContacts';
import {PlanContent} from './CaseFollowupPlan';
import {states, sourceStates, message} from '../followupContacts';
import {documentContactSelection, readDocumentContacts} from '../followupContactDocuments';

function Identity({label, value}) { return <p style={{whiteSpace:'pre-wrap'}}>{label}：病例 #{value.id} · 动物 {value.patient_name||'未填写'} · 物种 {value.species||'未填写'} · 宠主 {value.owner_name||'未填写'}</p>; }
function Facts({record:r, currentCase}) {return <>
  {currentCase&&<Identity label="当前病例身份" value={currentCase}/>}
  <Identity label="联系登记时身份" value={r.case_snapshot}/><ContactContent data={r.data}/>
  <p style={{whiteSpace:'pre-wrap'}}>更正原因：{r.reason||'首次保存'}</p>
  <p>联系 #{r.id} · 根 #{r.root_id} · 版本 {r.version} · {states[r.state]}</p>
  <p>登记账号 {r.recorded_by} · 确认时间 {r.recorded_at} · 内容标识 {r.token}</p>
  <h4>联系发生时的来源计划 · 历史原文</h4>
  <p>此来源不自动作为本次文书的当前复查安排。来源当前状态：{sourceStates[r.source_state]}</p>
  <Identity label="来源计划保存时身份" value={r.source.case_snapshot}/>
  <p>来源计划 #{r.source.id} · 根 #{r.source.root_id} · 版本 {r.source.version}</p>
  <PlanContent data={r.source.data}/><p>来源核对账号 {r.source.reviewed_by} · 核对时间 {r.source.reviewed_at}</p>
</>;}
function Preview({payload, onReady}) {
  useEffect(()=>{onReady?.();},[payload]);
  return <section aria-label="文书人工随访附节" style={{overflowWrap:'anywhere'}}>
    <h3>人工随访记录附节 · {payload.template_id==='owner_visit_summary_zh'?'宠主说明 · ':''}医生本次明确选择</h3>
    <p>草稿 · 待医生核对 · 尚未签署。联系或尝试不代表已复诊、完成检查、改善或关闭计划。</p>
    {payload.template_id==='owner_visit_summary_zh'&&<p>本附节保留历史沟通及来源原文，请医生核对是否适合出示给宠主。</p>}
    <Facts record={payload.record} currentCase={payload.case}/>
    <p>来源当前内容标识 {payload.selection.source_token} · 审计校验标识 {payload.audit_token}</p>
    <p>附节版本 {payload.schema}</p>
  </section>;
}
export default function ClinicalDocFollowupContactSelection(props) {
  return props.mode === 'preview' ? <Preview {...props}/> : <Selector key={JSON.stringify([props.caseId,props.requestToken,props.templateId])} {...props}/>;
}
function Selector({caseId, requestToken, templateId='outpatient_record_zh', onSelect, onInspect, onInspectPlan, readRevision=0}) {
  const [list,setList]=useState(null),[notice,setNotice]=useState(''),[busy,setBusy]=useState(false),[revision,setRevision]=useState(0);
  const epoch=useRef(0), callbacks=useRef({onSelect,onInspect,onInspectPlan}); callbacks.current={onSelect,onInspect,onInspectPlan};
  useEffect(()=>{
    const stamp=++epoch.current, abort=new AbortController(); setList(null);setBusy(true);setNotice('正在读取已保存的人工随访…');
    readDocumentContacts(caseId,requestToken,abort.signal).then(value=>{
      if(epoch.current===stamp&&!abort.signal.aborted&&localStorage.getItem('token')===requestToken){setList(value);setNotice('');}
    }).catch(error=>{if(epoch.current===stamp&&!abort.signal.aborted)setNotice(message(error));})
      .finally(()=>{if(epoch.current===stamp&&!abort.signal.aborted)setBusy(false);});
    return()=>{epoch.current++;abort.abort();};
  },[caseId,requestToken,readRevision,revision]);
  function select(row){
    if(busy||localStorage.getItem('token')!==requestToken)return;
    try{callbacks.current.onSelect(documentContactSelection(list,row,templateId));setNotice('已明确选择，请重新读取完整草稿并核对。');}
    catch(error){callbacks.current.onSelect(null);setNotice(message(error));}
  }
  return <section aria-label="选择文书人工随访" style={{padding:12,border:'1px solid #ccd5d1',overflowWrap:'anywhere'}}>
    <h3>选择已保存的人工随访记录</h3><p>默认不纳入，最多一条当前有效联系记录。历史来源可能已经更正或撤销；请核对原文与当前状态。</p>
    {templateId==='owner_visit_summary_zh'&&<p>联系原文和历史来源可能含内部备注或旧身份，请核对是否适合出示给宠主。可取消纳入；需要更正时请回到原记录处理。下载不会自动发送。</p>}
    <button type="button" disabled={busy} onClick={()=>{callbacks.current.onSelect(null);setRevision(v=>v+1);}}>刷新可选人工随访</button>
    <p role="status">{notice}</p>
    {list&&!list.records.length&&<p>尚无保存记录，不代表从未联系或无需复查。</p>}
    {list?.records.map(row=><article key={row.id} aria-label={`文书可选随访记录 ${row.id}`}>
      <Facts record={row} currentCase={list.case}/>
      <button type="button" disabled={busy||row.state!=='recorded'} onClick={()=>select(row)}>将此随访纳入本次文书</button>{' '}
      <button type="button" disabled={busy} onClick={()=>callbacks.current.onInspect?.({id:row.id,version:row.version})}>回看此随访版本</button>{' '}
      <button type="button" disabled={busy} onClick={()=>callbacks.current.onInspectPlan?.({id:row.source.id,version:row.source.version})}>回看此随访来源计划</button>
      {row.state!=='recorded'&&<p>此联系版本不能作为本次文书选择。</p>}
    </article>)}
  </section>;
}
