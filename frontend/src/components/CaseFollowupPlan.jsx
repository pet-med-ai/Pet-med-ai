import React,{useEffect,useRef,useState} from 'react';
import api from '../api';
import {followupClient,makeRequest,message,newPlanData,newRequestId,same,states,validData,validList,validPreview,validReceipt} from '../followupPlan';

const box={padding:16,margin:'12px 0',border:'1px solid #ccd5d1',borderRadius:8,overflowWrap:'anywhere'};
const leaveMessage='复查计划草稿或保存结果尚未核对，离开不会取消可能已提交的保存。是否继续？';
export function PlanContent({data}){return <dl style={{whiteSpace:'pre-wrap'}}>
  <dt>计划复查日期（上海）</dt><dd>{data.planned_date}</dd><dt>复查目的</dt><dd>{data.purpose}</dd>
  <dt>复查项目</dt><dd><ol>{data.items.map((item,i)=><li key={i}>{item}</li>)}</ol></dd>
  <dt>提前返回条件</dt><dd>{data.return_conditions||'未填写'}</dd><dt>备注</dt><dd>{data.note||'未填写'}</dd>
</dl>;}
export default function CaseFollowupPlan(props){return <Panel key={JSON.stringify([props.caseId,props.requestToken])} {...props}/>;}
function Panel({caseId,requestToken,onDirtyChange,caseRevision=0,inspectTarget}){
  const targets=useRef(new Map());
  const [inspectNotice,setInspectNotice]=useState('');
  const [list,setList]=useState(null),[draft,setDraft]=useState(null),[review,setReview]=useState(null),[checked,setChecked]=useState(false);
  const [busy,setBusy]=useState(false),[unknown,setUnknown]=useState(null),[notice,setNotice]=useState('');
  const active=useRef(false),epoch=useRef(0),flight=useRef(false),control=useRef(null),queued=useRef(false),dirty=useRef(false),pending=useRef(null);
  const callback=useRef(onDirtyChange);callback.current=onDirtyChange;
  const owned=()=>active.current&&Boolean(requestToken)&&localStorage.getItem('token')===requestToken;
  const current=e=>owned()&&epoch.current===e;
  const client=(method,path,data)=>followupClient(caseId,requestToken,control.current?.signal)(method,path,data);
  function invalidate(){epoch.current++;control.current?.abort();setReview(null);setChecked(false);}
  function clear(){setDraft(null);pending.current=null;setUnknown(null);invalidate();}
  async function refresh(){
    const e=epoch.current;setList(null);
    const result=await client('get');if(!current(e))return;
    if(!validList(result,caseId))throw Error('未收到完整的复查计划，暂不能确认保存。');
    setList(result);return result;
  }
  async function run(fn){
    if(!owned()||flight.current)return;
    flight.current=true;control.current=new AbortController();setBusy(true);setNotice('');
    const e=epoch.current;
    try{await fn();}catch(error){if(current(e))setNotice(message(error));}
    finally{
      flight.current=false;
      if(owned()){
        setBusy(false);
        if(queued.current){queued.current=false;void run(refresh);}
      }
    }
  }
  function reread(){if(!owned())return;invalidate();setList(null);if(flight.current)queued.current=true;else void run(refresh);}
  useEffect(()=>{
    active.current=true;void run(refresh);
    return()=>{active.current=false;epoch.current++;control.current?.abort();callback.current?.(false);};
  },[caseId,requestToken]);
  useEffect(()=>{dirty.current=Boolean(draft||unknown);callback.current?.(dirty.current);},[draft,unknown]);
  const previousRevision=useRef(caseRevision);
  useEffect(()=>{
    if(!inspectTarget||!list)return;
    const row=list.plans.find(p=>p.id===inspectTarget.id&&p.version===inspectTarget.version);
    setInspectNotice(row?`正在回看计划 #${row.id} 版本 ${row.version}，未改变编辑草稿。`:'指定计划版本当前无法读取，请刷新核对。');
    if(row){const node=targets.current.get(row.id);node?.scrollIntoView?.({block:'nearest'});node?.focus?.();}
  },[inspectTarget,list]);
  useEffect(()=>{if(previousRevision.current!==caseRevision){previousRevision.current=caseRevision;reread();}},[caseRevision]);
  useEffect(()=>{
    const focus=()=>reread(),storage=e=>{if(e.key==='token'||e.key===null){invalidate();setList(null);}};
    const affects=c=>{const method=c?.method?.toLowerCase();return (['put','patch','delete'].includes(method)&&c.url===`/api/cases/${caseId}`)||(method==='post'&&(c.url===`/api/cases/${caseId}/edit-confirm`||c.url===`/api/cases/${caseId}/confirm-edit`||c.url===`/api/cases/${caseId}/analyze`));};
    const request=api.interceptors.request.use(c=>{if(affects(c))reread();return c;});
    const response=api.interceptors.response.use(r=>{if(affects(r.config))reread();return r;},e=>{if(affects(e.config))reread();return Promise.reject(e);});
    const unload=e=>{if(dirty.current){e.preventDefault();e.returnValue='';}};
    const click=e=>{if(dirty.current&&e.target.closest?.('a[href]')&&!window.confirm(leaveMessage)){e.preventDefault();e.stopPropagation();}};
    window.addEventListener('focus',focus);window.addEventListener('storage',storage);window.addEventListener('beforeunload',unload);document.addEventListener?.('click',click,true);
    return()=>{api.interceptors.request.eject(request);api.interceptors.response.eject(response);window.removeEventListener('focus',focus);window.removeEventListener('storage',storage);window.removeEventListener('beforeunload',unload);document.removeEventListener?.('click',click,true);};
  },[caseId,requestToken]);
  function edit(row,operation){
    if(!owned()||flight.current||pending.current)return;
    if(dirty.current&&!window.confirm(leaveMessage))return;
    invalidate();setNotice('');setDraft({operation,plan_id:row?.id??null,expected_plan_token:row?.token||'',reason:'',data:row?structuredClone(row.data):newPlanData(),requestId:newRequestId()});
  }
  function change(patch){invalidate();setDraft(d=>({...d,...patch,requestId:newRequestId()}));}
  async function preview(){
    const e=epoch.current,body=makeRequest(draft,list),saved=list;
    setReview(null);setChecked(false);
    const result=await client('post','/preview',body);if(!current(e))return;
    if(!validPreview(result,saved,body))throw Error('复查计划预览与本次输入不一致，暂不能确认。');
    setReview({...result,body});
  }
  function matchesReceipt(result,request,before,readOnly=false){
    return validReceipt(result,caseId,request.request_id,readOnly)&&result.state==='committed'&&result.operation===request.operation&&
      (request.operation==='withdraw'?result.plan.id===request.plan_id:same(result.plan.data,request.data))&&
      (request.operation!=='correct'||result.plan.root_id===before.root_id&&result.plan.version===before.version+1);
  }
  async function checkResult(attempt){
    const {body:request,before}=attempt;
    const e=epoch.current;
    const result=await client('get','/requests/'+request.request_id);if(!current(e))return;
    if(!validReceipt(result,caseId,request.request_id,true)||result.state==='committed'&&!matchesReceipt(result,request,before,true))throw Error('保存结果尚不能确认，请继续核对，勿重复提交。');
    // Re-read independently before allowing another edit, including not-committed results.
    const saved=await refresh();if(!current(e)||!saved)return;
    if(result.state==='committed'){
      pending.current=null;setUnknown(null);setDraft(null);setReview(null);setChecked(false);
      setNotice('已核对服务端保存结果，未重复提交；请查看当前版本。');
    }else{
      pending.current=null;setUnknown(null);setReview(null);setChecked(false);
      setNotice('暂未查到该请求已提交。已保留请求标识与草稿，请重新预览核对；不会自动重发。');
    }
  }
  async function confirm(){
    const e=epoch.current,request={...review.body,preview_token:review.preview_token,reviewed:true};
    const attempt={body:request,before:review.before};pending.current=attempt;setUnknown(attempt);setChecked(false);
    try{
      const result=await client('post','/confirm',request);if(!current(e))return;
      if(!matchesReceipt(result,request,attempt.before))throw Error('保存回包不能确认');
      const saved=await refresh();if(!current(e)||!saved)return;
      pending.current=null;setUnknown(null);setDraft(null);setReview(null);
      setNotice('复查计划已保存并独立回读。计划不代表已完成复查。');
    }catch{
      if(!current(e))return;
      // A write may have succeeded even when its response or following GET failed.
      control.current=new AbortController();
      try{await checkResult(attempt);}catch{if(current(e))setNotice('保存结果待核对，请点击核对保存结果；不要重复提交。');}
    }
  }
  const locked=busy||Boolean(unknown),hasCurrent=list?.plans.some(p=>p.stored_state==='planned');
  return <section aria-label="人工复查计划" style={box}>
    <h2>人工复查计划</h2><p>由医生填写并核对。计划不代表已复查，不会自动预约或发送消息。门诊病历和宠主说明草稿可明确选择当前有效计划，仍需重新核对整份文书。</p>
    {inspectNotice&&<p role="status">{inspectNotice}</p>}
    <p>未保存草稿仅留在本页；刷新、离开或切换病例和账号后清除。</p>
    <p role="status">{busy?'正在处理…':notice}</p>
    <button type="button" disabled={busy} onClick={reread}>刷新复查计划</button>
    {unknown&&<section aria-label="复查保存结果待核对"><p>保存结果待核对。页面变化或取消请求不代表服务端未保存。</p><button disabled={busy} onClick={()=>run(()=>checkResult(unknown))}>核对复查保存结果</button></section>}
    {list&&<><p>病例 #{caseId} · {list.case.patient_name} · {list.case.species} · 读取日期 {list.as_of_date}（上海）</p>
      {!list.plans.length&&<p>尚未建立复查计划，不代表无需复查。</p>}
      <button disabled={locked||Boolean(draft)||hasCurrent||list.plans.length>=50} onClick={()=>edit(null,'create')}>新增复查计划</button>
      {list.plans.length>=50&&<p>已达版本上限，仍可查看或撤销。</p>}</>}
    {draft&&<section aria-label="复查计划草稿" style={box}>
      <h3>{{create:'新增复查计划',correct:'更正复查计划',withdraw:'撤销复查计划'}[draft.operation]}</h3>
      {draft.operation!=='withdraw'&&<fieldset disabled={locked}>
        <legend>医生填写</legend>
        <label>计划复查日期（上海）<input aria-label="计划复查日期" type="date" value={draft.data.planned_date} onChange={e=>change({data:{...draft.data,planned_date:e.target.value}})}/></label>
        {draft.data.planned_date&&list&&draft.data.planned_date<list.as_of_date&&<p>计划日期已过，请核对日期；此提示不代表已完成复查。</p>}
        {[['purpose','复查目的'],['return_conditions','提前返回条件'],['note','复查备注']].map(([key,label])=><label key={key} style={{display:'block'}}>{label}<textarea aria-label={label} value={draft.data[key]} onChange={e=>change({data:{...draft.data,[key]:e.target.value}})}/></label>)}
        {draft.data.items.map((item,i)=><div key={i}><label>复查项目 {i+1}<textarea aria-label={`复查项目 ${i+1}`} value={item} onChange={e=>change({data:{...draft.data,items:draft.data.items.map((v,j)=>i===j?e.target.value:v)}})}/></label><button type="button" disabled={draft.data.items.length===1} onClick={()=>change({data:{...draft.data,items:draft.data.items.filter((_,j)=>j!==i)}})}>移除复查项目 {i+1}</button></div>)}
        <button type="button" disabled={draft.data.items.length>=10} onClick={()=>change({data:{...draft.data,items:[...draft.data.items,'']}})}>添加复查项目</button>
      </fieldset>}
      {draft.operation!=='create'&&<label>更正或撤销原因<textarea disabled={locked} aria-label="复查更正或撤销原因" value={draft.reason} onChange={e=>change({reason:e.target.value})}/></label>}
      <button disabled={locked||!list||(draft.operation!=='withdraw'&&!validData(draft.data))||(draft.operation!=='create'&&!draft.reason.trim())} onClick={()=>run(preview)}>预览并核对复查计划</button>
      <button disabled={locked} onClick={()=>{if(window.confirm(leaveMessage))clear();}}>放弃复查草稿</button>
    </section>}
    {review&&<section aria-label="复查计划核对" style={box}><h3>核对本次计划与原记录</h3>
      <p>病例 #{review.case_id} · {review.case.patient_name} · {review.case.species} · 宠主 {review.case.owner_name||'未填写'} · 毛色 {review.case.coat_color||'未填写'}</p>
      <p style={{whiteSpace:'pre-wrap'}}>本次操作：{{create:'新增',correct:'更正',withdraw:'撤销'}[review.operation]}；原因：{review.reason||'首次建立'}</p>
      {review.before&&<div><h4>原版本 {review.before.version}</h4><PlanContent data={review.before.data}/></div>}
      {review.data&&<div><h4>本次计划</h4><PlanContent data={review.data}/>{review.data.planned_date<review.as_of_date&&<p>计划日期已过，请核对。</p>}</div>}
      <label><input type="checkbox" aria-label="已核对复查计划" disabled={locked} checked={checked} onChange={e=>setChecked(e.target.checked)}/>已核对病例、日期、全部原文及本次操作</label>
      <button disabled={locked||!checked} onClick={()=>run(confirm)}>确认保存复查计划</button>
    </section>}
    {list&&<section aria-label="复查计划版本历史"><h3>已保存计划与版本历史</h3>{list.plans.map(p=><article key={p.id} ref={node=>{if(node)targets.current.set(p.id,node);else targets.current.delete(p.id);}} tabIndex={-1} aria-label={`复查计划记录 ${p.id}`} style={box}>
      <strong>版本 {p.version} · {states[p.state]}</strong><p style={{whiteSpace:'pre-wrap'}}>确认账号 {p.reviewed_by} · 时间 {p.reviewed_at} · 原因 {p.reason||'首次建立'}</p>
      {p.data.planned_date<list.as_of_date&&p.stored_state==='planned'&&<p>计划日期已过；尚未登记实际复查结果。</p>}
      <details open={inspectTarget?.id===p.id&&inspectTarget?.version===p.version?true:undefined}><summary>查看复查计划 #{p.id} 版本 {p.version}</summary><PlanContent data={p.data}/><p>内容标识 {p.token}</p></details>
      {p.withdrawal&&<p style={{whiteSpace:'pre-wrap'}}>撤销原因 {p.withdrawal.reason} · 账号 {p.withdrawal.by} · 时间 {p.withdrawal.at}</p>}
      {p.stored_state==='planned'&&<><button disabled={locked||Boolean(draft)||list.plans.length>=50} onClick={()=>edit(p,'correct')}>更正复查计划</button><button disabled={locked||Boolean(draft)} onClick={()=>edit(p,'withdraw')}>撤销复查计划</button></>}
    </article>)}</section>}
  </section>;
}
