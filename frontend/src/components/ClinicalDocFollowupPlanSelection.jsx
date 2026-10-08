import React, { useEffect, useRef, useState } from 'react';
import { PlanContent } from './CaseFollowupPlan';
import { message, states } from '../followupPlan';
import { documentPlanSelection, readDocumentPlans } from '../followupPlanDocuments';

export function DocumentPlanContent({payload,onReady}) {
  useEffect(()=>{onReady?.();},[payload]);
  const plan = payload.plan;
  return <section aria-label="文书复查计划附节" style={{overflowWrap:'anywhere'}}>
    <h3>复查计划附节 · 医生本次明确选择</h3>
    <p>草稿 · 尚未签署。计划不代表已复查、已预约或已联系宠主。</p>
    <PlanContent data={plan.data}/>
    <p>病例 #{payload.case_id} · 计划记录 #{plan.id} · 根记录 #{plan.root_id} · 版本 {plan.version}</p>
    <p>确认账号 {plan.reviewed_by} · 确认时间 {plan.reviewed_at}</p>
    <p>保存版本内容标识 {plan.token}</p>
  </section>;
}
export default function ClinicalDocFollowupPlanSelection(props) {
  return props.mode === 'preview' ? <DocumentPlanContent payload={props.payload} onReady={props.onReady}/> :
    <Selector key={JSON.stringify([props.caseId,props.requestToken,props.templateId])} {...props}/>;
}
function Selector({caseId,requestToken,templateId='outpatient_record_zh',onSelect,onInspect,readRevision=0}) {
  const [list,setList]=useState(null),[notice,setNotice]=useState(''),[busy,setBusy]=useState(false),[refresh,setRefresh]=useState(0);
  const active=useRef(false),epoch=useRef(0),control=useRef(null),callbacks=useRef({onSelect,onInspect});
  callbacks.current={onSelect,onInspect};
  useEffect(()=>{
    active.current=true;const e=++epoch.current;control.current=new AbortController();
    setList(null);setBusy(true);setNotice('正在读取已保存的复查计划…');
    readDocumentPlans(caseId,requestToken,control.current.signal).then(value=>{
      if(active.current&&epoch.current===e&&localStorage.getItem('token')===requestToken){setList(value);setNotice('');}
    }).catch(error=>{if(active.current&&epoch.current===e)setNotice(message(error));})
      .finally(()=>{if(active.current&&epoch.current===e)setBusy(false);});
    return()=>{active.current=false;epoch.current++;control.current?.abort();};
  },[caseId,requestToken,readRevision,refresh]);
  function select(row){
    if(busy||!active.current||localStorage.getItem('token')!==requestToken)return;
    try{callbacks.current.onSelect(documentPlanSelection(list,row));setNotice('已明确选择；请重新读取完整草稿并核对。');}
    catch(error){callbacks.current.onSelect(null);setNotice(message(error));}
  }
  return <section aria-label="选择文书复查计划" style={{padding:12,border:'1px solid #ccd5d1',overflowWrap:'anywhere'}}>
    <h3>选择已保存的复查计划</h3><p>当前文书：{templateId==='owner_visit_summary_zh'?'宠主说明草稿':'门诊病历草稿'}。默认不纳入，最多一份当前有效计划；保存计划时的核对不代替本次全篇核对。</p>
    <button type="button" disabled={busy} onClick={()=>{callbacks.current.onSelect(null);setRefresh(v=>v+1);}}>刷新可选复查计划</button>
    <p role="status">{notice}</p>
    {list&&!list.plans.length&&<p>尚无已保存计划，不代表无需复查。</p>}
    {list?.plans.map(row=><article key={row.id} aria-label={`文书可选复查记录 ${row.id}`}>
      <h4>计划 #{row.id} · 版本 {row.version} · {states[row.state]}</h4>
      <PlanContent data={row.data}/><p>确认账号 {row.reviewed_by} · 时间 {row.reviewed_at}</p>
      <p>内容标识 {row.token}</p>
      {row.state==='planned'&&row.data.planned_date<list.as_of_date&&<p>计划日期已过，请核对；不代表已完成复查。</p>}
      <button type="button" disabled={busy||row.state!=='planned'} onClick={()=>select(row)}>将此计划纳入本次文书</button>{' '}
      <button type="button" disabled={busy} onClick={()=>callbacks.current.onInspect?.({id:row.id,version:row.version})}>回看此复查计划版本</button>
      {row.state!=='planned'&&<p>此状态不能作为本次文书的当前复查安排。</p>}
    </article>)}
  </section>;
}
