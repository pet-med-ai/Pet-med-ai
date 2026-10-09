import React,{useEffect,useRef,useState} from 'react';
import api from '../api';
import {PlanContent} from './CaseFollowupPlan';
import {contactClient,makeRequest,message,newData,newRequestId,same,states,sourceStates,methods,outcomes,validData,validList,validPreview,validReceipt} from '../followupContacts';
const box={padding:16,margin:'12px 0',border:'1px solid #ccd5d1',borderRadius:8,overflowWrap:'anywhere'};
const leaveMessage='人工随访草稿或保存结果尚未核对，离开不会取消可能已提交的保存。是否继续？';
export function ContactContent({data}){return <dl style={{whiteSpace:'pre-wrap'}}><dt>实际联系或尝试时间（上海）</dt><dd>{data.occurred_at}</dd><dt>联系方式</dt><dd>{methods[data.method]}</dd><dt>实际结果</dt><dd>{outcomes[data.outcome]}</dd><dt>记录原文</dt><dd>{data.note}</dd><dt>后续安排</dt><dd>{data.next_action||'未填写'}</dd></dl>;}
function SourceContent({source,state}){return <div><p>来源计划 #{source.id} · 版本 {source.version} · {sourceStates[state]}</p><p>保存时病例 #{source.case_snapshot.id} · {source.case_snapshot.patient_name} · {source.case_snapshot.species}</p><PlanContent data={source.data}/></div>;}
export default function CaseFollowupContacts(props){return <Panel key={JSON.stringify([props.caseId,props.requestToken])} {...props}/>;}
function Panel({caseId,requestToken,onDirtyChange,caseRevision=0,inspectTarget}){
  const targets=useRef(new Map()),targetRef=useRef(inspectTarget),readForTarget=useRef(null);
  targetRef.current=inspectTarget;
  const [inspectNotice,setInspectNotice]=useState('');
  const [list,setList]=useState(null),[draft,setDraft]=useState(null),[review,setReview]=useState(null),[checked,setChecked]=useState(false);
  const [busy,setBusy]=useState(false),[unknown,setUnknown]=useState(null),[notice,setNotice]=useState('');
  const active=useRef(false),epoch=useRef(0),flight=useRef(false),control=useRef(null),queued=useRef(false),dirty=useRef(false),pending=useRef(null);
  const callback=useRef(onDirtyChange);callback.current=onDirtyChange;
  const owned=()=>active.current&&Boolean(requestToken)&&localStorage.getItem('token')===requestToken;
  const current=e=>owned()&&epoch.current===e;
  const client=(method,path,data)=>contactClient(caseId,requestToken,control.current?.signal)(method,path,data);
  function invalidate(){epoch.current++;control.current?.abort();setReview(null);setChecked(false);}
  function clear(){setDraft(null);pending.current=null;setUnknown(null);invalidate();}
  async function refresh(){
    const e=epoch.current,target=targetRef.current;setList(null);
    const result=await client('get');if(!current(e))return;
    if(!validList(result,caseId))throw Error('未收到完整的人工随访记录，暂不能确认保存。');
    readForTarget.current={target,list:result};setList(result);return result;
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
  function reread(){if(!owned())return;invalidate();setList(null);setInspectNotice(targetRef.current?'正在重新核对指定随访版本…':'');if(flight.current)queued.current=true;else void run(refresh);}
  useEffect(()=>{
    active.current=true;void run(refresh);
    return()=>{active.current=false;epoch.current++;control.current?.abort();callback.current?.(false);};
  },[caseId,requestToken]);
  useEffect(()=>{dirty.current=Boolean(draft||unknown);callback.current?.(dirty.current);},[draft,unknown]);
  const previousRevision=useRef(caseRevision);
  useEffect(()=>{
    setInspectNotice('');
    if(!inspectTarget)return;
    if(!Number.isSafeInteger(inspectTarget.id)||inspectTarget.id<1||!Number.isSafeInteger(inspectTarget.version)||inspectTarget.version<1||inspectTarget.version>50){
      readForTarget.current=null;setInspectNotice('指定随访定位信息无效，请返回总览核对。');return;
    }
    reread();
  },[inspectTarget]);
  useEffect(()=>{
    if(!inspectTarget||!list||readForTarget.current?.target!==inspectTarget||readForTarget.current?.list!==list)return;
    const row=list.records.find(r=>r.id===inspectTarget.id&&r.version===inspectTarget.version);
    setInspectNotice(row?`正在回看随访 #${row.id} 版本 ${row.version}，未改变编辑草稿。`:'指定随访版本当前无法读取，请刷新核对。');
    if(row){const node=targets.current.get(row.id);node?.scrollIntoView?.({block:'nearest'});node?.focus?.();}
  },[inspectTarget,list]);
  useEffect(()=>{if(previousRevision.current!==caseRevision){previousRevision.current=caseRevision;reread();}},[caseRevision]);
  useEffect(()=>{
    const focus=()=>reread(),visibility=()=>{if(!document.hidden)reread();},storage=e=>{if(e.key==='token'||e.key===null){clear();setList(null);}};
    const affects=c=>{const method=c?.method?.toLowerCase();return (['put','patch','delete'].includes(method)&&c.url===`/api/cases/${caseId}`)||(method==='post'&&(c.url===`/api/cases/${caseId}/edit-confirm`||c.url===`/api/cases/${caseId}/confirm-edit`||c.url===`/api/cases/${caseId}/analyze`||c.url===`/api/cases/${caseId}/followup-plan/confirm`));};
    const request=api.interceptors.request.use(c=>{if(affects(c))reread();return c;});
    const response=api.interceptors.response.use(r=>{if(affects(r.config))reread();return r;},e=>{if(affects(e.config))reread();return Promise.reject(e);});
    const unload=e=>{if(dirty.current){e.preventDefault();e.returnValue='';}};
    const click=e=>{if(dirty.current&&e.target.closest?.('a[href]')&&!window.confirm(leaveMessage)){e.preventDefault();e.stopPropagation();}};
    window.addEventListener('focus',focus);window.addEventListener('storage',storage);window.addEventListener('beforeunload',unload);document.addEventListener?.('click',click,true);document.addEventListener?.('visibilitychange',visibility);
    return()=>{api.interceptors.request.eject(request);api.interceptors.response.eject(response);window.removeEventListener('focus',focus);window.removeEventListener('storage',storage);window.removeEventListener('beforeunload',unload);document.removeEventListener?.('click',click,true);document.removeEventListener?.('visibilitychange',visibility);};
  },[caseId,requestToken]);
  function edit(row,operation){
    if(!owned()||flight.current||pending.current)return;
    if(dirty.current&&!window.confirm(leaveMessage))return;
    invalidate();setNotice('');setDraft({operation,contact_id:row?.id??null,expected_contact_token:row?.token||'',source_plan_id:row?.source.id??null,reason:'',data:row?structuredClone(row.data):newData(),requestId:newRequestId()});
  }
  function change(patch){invalidate();setDraft(d=>({...d,...patch,requestId:newRequestId()}));}
  async function preview(){
    const e=epoch.current,body=makeRequest(draft,list),saved=list;
    setReview(null);setChecked(false);
    const result=await client('post','/preview',body);if(!current(e))return;
    if(!validPreview(result,saved,body))throw Error('人工随访记录预览与本次输入不一致，暂不能确认。');
    setReview({...result,body});
  }
  function matchesReceipt(result,attempt,readOnly=false){
    const {body:request,before,source}=attempt;
    return validReceipt(result,caseId,request.request_id,readOnly)&&result.state==='committed'&&result.operation===request.operation&&same(result.record.source,source)&&
      (request.operation==='withdraw'?result.record.id===request.contact_id&&same(result.record.data,before.data)&&result.record.withdrawal?.reason===request.reason:same(result.record.data,request.data))&&
      (request.operation!=='correct'||result.record.root_id===before.root_id&&result.record.version===before.version+1)&&
      (request.operation!=='create'||result.record.version===1&&result.record.root_id===result.record.id);
  }
  function savedRecord(list,result){return list.records.some(r=>r.id===result.record.id&&r.version===result.record.version&&same(r.data,result.record.data)&&same(r.source,result.record.source));}
  async function checkResult(attempt){
    const {body:request,before}=attempt;
    const e=epoch.current;
    const result=await client('get','/requests/'+request.request_id);if(!current(e))return;
    if(!validReceipt(result,caseId,request.request_id,true)||result.state==='committed'&&!matchesReceipt(result,attempt,true))throw Error('保存结果尚不能确认，请继续核对，勿重复提交。');
    // Re-read independently before allowing another edit, including not-committed results.
    const saved=await refresh();if(!current(e)||!saved)return;
    if(result.state==='committed'){
      if(!savedRecord(saved,result))throw Error('独立回读未匹配保存记录，请继续核对。');
      pending.current=null;setUnknown(null);setDraft(null);setReview(null);setChecked(false);
      setNotice('已核对服务端保存结果，未重复提交；请查看当前版本。');
    }else{
      pending.current=null;setUnknown(null);setReview(null);setChecked(false);
      setNotice('暂未查到该请求已提交。已保留请求标识与草稿，请重新预览核对；不会自动重发。');
    }
  }
  async function confirm(){
    const e=epoch.current,request={...review.body,preview_token:review.preview_token,reviewed:true};
    const attempt={body:request,before:review.before,source:review.source};pending.current=attempt;setUnknown(attempt);setChecked(false);
    try{
      const result=await client('post','/confirm',request);if(!current(e))return;
      if(!matchesReceipt(result,attempt))throw Error('保存回包不能确认');
      const saved=await refresh();if(!current(e)||!saved)return;
      if(!savedRecord(saved,result))throw Error('独立回读未匹配保存记录');
      pending.current=null;setUnknown(null);setDraft(null);setReview(null);
      setNotice('人工随访记录已保存并独立回读。联系不代表已完成复查。');
    }catch{
      if(!current(e))return;
      // A write may have succeeded even when its response or following GET failed.
      control.current=new AbortController();
      try{await checkResult(attempt);}catch{if(current(e))setNotice('保存结果待核对，请点击核对保存结果；不要重复提交。');}
    }
  }
  const locked=busy||Boolean(unknown),eligible=list?.plans.filter(p=>p.state==='planned')||[];
  const selected=list?.plans.find(p=>p.id===draft?.source_plan_id);
  const validSelection=selected&&(draft?.operation!=='create'||selected.state==='planned');
  return <section aria-label="人工随访记录" style={box}>
    <h2>人工随访记录</h2><p>登记已经发生的联系或尝试。联系不代表已复诊或完成检查，不会自动关闭计划或发送消息。</p>
    {inspectNotice&&<p role="status">{inspectNotice}</p>}
    <p>未保存草稿仅留在本页；登记账号由系统记录，不代替实际联系医生或电子签名。</p>
    <p role="status">{busy?'正在处理…':notice}</p>
    <button type="button" disabled={busy} onClick={reread}>刷新人工随访记录</button>
    {unknown&&<section aria-label="随访保存结果待核对"><p>保存结果待核对。取消请求或离开页面不代表未保存。</p><button disabled={busy} onClick={()=>run(()=>checkResult(unknown))}>核对随访保存结果</button></section>}
    {list&&<><p>病例 #{caseId} · {list.case.patient_name} · {list.case.species} · 读取日期 {list.as_of_date}（上海）</p>
      {!list.records.length&&<p>尚无人工随访记录，不代表从未联系或无需复查。</p>}
      {!eligible.length&&<p>暂无当前有效且已核对的计划，请先打开复查计划处理。</p>}
      <button disabled={locked||Boolean(draft)||!eligible.length||list.records.length>=50} onClick={()=>edit(null,'create')}>新增人工随访记录</button>
      {list.records.length>=50&&<p>已达 50 条版本上限，仍可回看或撤销。</p>}</>}
    {draft&&<section aria-label="人工随访草稿" style={box}>
      <h3>{{create:'新增人工随访记录',correct:'更正人工随访记录',withdraw:'撤销人工随访记录'}[draft.operation]}</h3>
      {draft.operation==='create'?<label>来源复查计划<select style={{maxWidth:'100%'}} aria-label="随访来源计划" disabled={locked} value={draft.source_plan_id??''} onChange={e=>change({source_plan_id:e.target.value?Number(e.target.value):null})}><option value="">请选择准确计划</option>{eligible.map(p=><option key={p.id} value={p.id}>计划 #{p.id} 版本 {p.version} · {p.data.planned_date} · {p.data.purpose}</option>)}</select></label>:<p>来源计划固定为 #{draft.source_plan_id}，更正不能改绑。</p>}
      {selected&&<details><summary>核对来源计划原文</summary><SourceContent source={selected} state={selected.state}/></details>}
      {!validSelection&&<p>请选择或重新核对来源计划。</p>}
      {draft.operation!=='withdraw'&&<fieldset style={{minWidth:0}} disabled={locked}><legend>医生填写实际记录</legend>
        <label>实际联系时间（上海）<input aria-label="随访联系时间" type="datetime-local" value={draft.data.occurred_at.slice(0,16)} onChange={e=>change({data:{...draft.data,occurred_at:e.target.value?e.target.value+'+08:00':''}})}/></label>
        {[['method','随访联系方式',methods],['outcome','随访联系结果',outcomes]].map(([key,label,options])=><label key={key} style={{display:'block'}}>{label}<select aria-label={label} value={draft.data[key]} onChange={e=>change({data:{...draft.data,[key]:e.target.value}})}><option value="">请选择</option>{Object.entries(options).map(([v,n])=><option key={v} value={v}>{n}</option>)}</select></label>)}
        {[['note','随访记录原文'],['next_action','随访后续安排']].map(([key,label])=><label key={key} style={{display:'block'}}>{label}<textarea style={{maxWidth:'100%'}} aria-label={label} value={draft.data[key]} onChange={e=>change({data:{...draft.data,[key]:e.target.value}})}/></label>)}
      </fieldset>}
      {draft.operation!=='create'&&<label>更正或撤销原因<textarea aria-label="随访更正或撤销原因" disabled={locked} value={draft.reason} onChange={e=>change({reason:e.target.value})}/></label>}
      <button disabled={locked||!list||!validSelection||(draft.operation!=='withdraw'&&!validData(draft.data))||(draft.operation!=='create'&&!draft.reason.trim())} onClick={()=>run(preview)}>预览并核对人工随访</button>
      <button disabled={locked} onClick={()=>{if(window.confirm(leaveMessage))clear();}}>放弃人工随访草稿</button>
    </section>}
    {review&&<section aria-label="人工随访核对" style={box}><h3>核对来源与本次联系记录</h3>
      <p>病例 #{review.case_id} · {review.case.patient_name} · {review.case.species} · 宠主 {review.case.owner_name||'未填写'}</p>
      <SourceContent source={review.source} state={review.source_state}/>
      <p style={{whiteSpace:'pre-wrap'}}>本次操作：{{create:'新增',correct:'更正',withdraw:'撤销'}[review.operation]}；原因：{review.reason||'首次登记'}</p>
      {review.before&&<div><h4>原联系版本 {review.before.version}</h4><ContactContent data={review.before.data}/></div>}
      {review.data&&<div><h4>本次联系记录</h4><ContactContent data={review.data}/></div>}
      <label><input type="checkbox" aria-label="已核对人工随访" disabled={locked} checked={checked} onChange={e=>setChecked(e.target.checked)}/>已核对病例、来源计划版本、时间、完整原文及本次操作</label>
      <button disabled={locked||!checked} onClick={()=>run(confirm)}>确认保存人工随访</button>
    </section>}
    {list&&<section aria-label="人工随访版本历史"><h3>已保存联系与版本历史</h3>{list.records.map(r=><article key={r.id} ref={node=>{if(node)targets.current.set(r.id,node);else targets.current.delete(r.id);}} tabIndex={-1} aria-label={`人工随访记录 ${r.id}`} style={box}>
      <strong>记录 #{r.id} · 版本 {r.version} · {states[r.state]}</strong><p>登记账号 {r.recorded_by} · 确认时间 {r.recorded_at}</p>
      <p style={{whiteSpace:'pre-wrap'}}>原因 {r.reason||'首次登记'} · {sourceStates[r.source_state]}</p>
      <details open={inspectTarget?.id===r.id&&inspectTarget?.version===r.version?true:undefined}><summary>查看随访记录 #{r.id} 版本 {r.version}</summary><ContactContent data={r.data}/><SourceContent source={r.source} state={r.source_state}/></details>
      {r.withdrawal&&<p style={{whiteSpace:'pre-wrap'}}>撤销原因 {r.withdrawal.reason} · 账号 {r.withdrawal.by} · 时间 {r.withdrawal.at}</p>}
      {r.state==='recorded'&&<><button disabled={locked||Boolean(draft)||list.records.length>=50} onClick={()=>edit(r,'correct')}>更正人工随访记录</button><button disabled={locked||Boolean(draft)} onClick={()=>edit(r,'withdraw')}>撤销人工随访记录</button></>}
    </article>)}</section>}
  </section>;
}
