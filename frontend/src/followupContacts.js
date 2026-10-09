import api from './api';
import {draftOwner} from './consultDraft';
import {same,validData as validPlanData,validList as validPlanList,schema as planSchema} from './followupPlan';
export {same,newRequestId} from './followupPlan';
export const schema='clinical-followup-contacts-cw-b19-v1';
export const methods={phone:'电话',wechat:'微信',in_person:'当面',other:'其他'};
export const outcomes={reached:'已取得联系',not_reached:'未取得联系',declined:'对方拒绝沟通',other:'其他'};
export const states={recorded:'已核对保存',superseded:'旧版本',withdrawn:'已撤销'};
export const sourceStates={planned:'当前已核对计划',needs_review:'病例已变化，计划待重新核对',superseded:'来源计划已更正',withdrawn:'来源计划已撤销'};
export const newData=()=>({occurred_at:'',method:'',outcome:'',note:'',next_action:''});
const obj=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const keys=(v,n)=>obj(v)&&Object.keys(v).sort().join('|')===[...n].sort().join('|');
const id=v=>Number.isSafeInteger(v)&&v>0;
const hash=v=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
const literal=(v,n,required=false)=>typeof v==='string'&&[...v].length<=n&&(!required||Boolean(v.trim()))&&!/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f\ud800-\udfff\ufffe\uffff]/u.test(v);
const timestamp=v=>typeof v==='string'&&/(Z|[+-]\d\d:\d\d)$/.test(v)&&Number.isFinite(Date.parse(v));
const fields=['patient_name','species','sex','age_info','breed','weight','coat_color','owner_name','owner_phone','chief_complaint','history','exam_findings','analysis','treatment','prognosis'];
const validCase=(v,cid)=>keys(v,['id','owner_id',...fields])&&v.id===cid&&id(cid)&&id(v.owner_id)&&fields.every(k=>v[k]===null||typeof v[k]==='string');
export function validTime(v){
  if(typeof v!=='string'||!/^\d{4}-\d\d-\d\dT\d\d:\d\d\+08:00$/.test(v)||v<'0001-01-01T08:00+08:00')return false;
  const raw=v.slice(0,16),d=new Date(raw+'Z');return Number.isFinite(d.valueOf())&&d.toISOString().slice(0,16)===raw;
}
export function validData(v){return keys(v,Object.keys(newData()))&&validTime(v.occurred_at)&&typeof v.method==='string'&&Object.hasOwn(methods,v.method)&&typeof v.outcome==='string'&&Object.hasOwn(outcomes,v.outcome)&&literal(v.note,2000,true)&&literal(v.next_action,1000);}
export const frozenSource=p=>Object.fromEntries(['id','root_id','version','data','case_snapshot','reviewed_by','reviewed_at'].map(k=>[k,p[k]]));
function validSource(s,cid){return keys(s,['id','root_id','version','data','case_snapshot','reviewed_by','reviewed_at'])&&id(s.id)&&id(s.root_id)&&id(s.version)&&s.version<=50&&validPlanData(s.data)&&validCase(s.case_snapshot,cid)&&s.reviewed_by===String(s.case_snapshot.owner_id)&&timestamp(s.reviewed_at);}
export function validRecord(r,cid){return keys(r,['id','root_id','version','state','token','source','source_state','data','case_snapshot','recorded_by','recorded_at','reason','withdrawal'])&&id(r.id)&&id(r.root_id)&&id(r.version)&&r.version<=50&&Object.hasOwn(states,r.state)&&hash(r.token)&&validSource(r.source,cid)&&Object.hasOwn(sourceStates,r.source_state)&&validData(r.data)&&validCase(r.case_snapshot,cid)&&r.recorded_by===String(r.case_snapshot.owner_id)&&timestamp(r.recorded_at)&&literal(r.reason,500,r.version>1)&&
  (r.state==='withdrawn'?keys(r.withdrawal,['reason','by','at'])&&literal(r.withdrawal.reason,500,true)&&typeof r.withdrawal.by==='string'&&/^[1-9]\d*$/.test(r.withdrawal.by)&&timestamp(r.withdrawal.at):r.withdrawal===null);}
export function validList(v,cid){
  if(!keys(v,['schema','case_id','case','as_of_date','timezone','plans','records','limits','writes_database','case_token','state_token'])||v.schema!==schema||!same(v.limits,{versions:50}))return false;
  const {records,...p}=v;
  if(!validPlanList({...p,schema:planSchema,limits:{items:10,versions:50}},cid)||!Array.isArray(records)||records.length>50||!records.every(r=>validRecord(r,cid))||new Set(records.map(r=>r.id)).size!==records.length)return false;
  const roots=new Map();
  for(const r of records){const source=v.plans.find(p=>p.id===r.source.id);if(!source||!same(r.source,frozenSource(source))||r.source_state!==source.state)return false;roots.set(r.root_id,[...(roots.get(r.root_id)||[]),r]);}
  return [...roots.entries()].every(([root,rs])=>rs[0].id===root&&rs.every((r,i)=>r.version===i+1&&same(r.source,rs[0].source)&&(i===rs.length-1?r.state!=='superseded':r.state==='superseded')));
}
export function makeRequest(draft,list){
  const source=list.plans.find(p=>p.id===draft.source_plan_id);
  return {request_id:draft.requestId,operation:draft.operation,contact_id:draft.contact_id,expected_contact_token:draft.expected_contact_token,
    source_plan_id:draft.source_plan_id,source_plan_version:source?.version,expected_source_token:source?.token,
    expected_case_token:list.case_token,expected_state_token:list.state_token,data:draft.operation==='withdraw'?null:structuredClone(draft.data),reason:draft.reason};
}
export function validPreview(v,list,body){
  const before=body.contact_id===null?null:list.records.find(r=>r.id===body.contact_id),source=list.plans.find(p=>p.id===body.source_plan_id);
  return Boolean(source)&&keys(v,['schema','case_id','case','as_of_date','timezone','before','source','source_state','data','operation','reason','request_id','writes_database','case_token','state_token','preview_token'])&&v.schema===schema&&v.case_id===list.case_id&&same(v.case,list.case)&&v.as_of_date===list.as_of_date&&v.timezone==='Asia/Shanghai'&&same(v.before,before)&&same(v.source,frozenSource(source))&&v.source_state===source.state&&same(v.data,body.data)&&v.operation===body.operation&&v.reason===body.reason&&v.request_id===body.request_id&&!v.writes_database&&v.writes_database===false&&v.case_token===body.expected_case_token&&v.state_token===body.expected_state_token&&hash(v.preview_token);
}
export function validReceipt(v,cid,rid,readOnly=false){
  if(!obj(v)||v.schema!==schema||v.case_id!==cid||v.request_id!==rid||typeof v.writes_database!=='boolean'||readOnly&&v.writes_database)return false;
  if(v.state==='not_committed')return readOnly&&keys(v,['schema','case_id','request_id','state','writes_database'])&&!v.writes_database;
  return v.state==='committed'&&keys(v,['schema','case_id','request_id','state','operation','record','writes_database'])&&['create','correct','withdraw'].includes(v.operation)&&validRecord(v.record,cid);
}
export function contactClient(cid,token,signal){return async(method,path='',data)=>{
  if(!token||localStorage.getItem('token')!==token)throw Error('账号已变化，请重新打开病例。');
  const response=await api.request({method,url:`/api/cases/${cid}/followup-contacts${path}`,data,signal,timeout:30000,expectedAuthOwner:draftOwner(token)});
  if(localStorage.getItem('token')!==token)throw Error('账号已变化，请重新打开病例。');return response.data;
};}
export function message(error){const code=error?.response?.data?.detail;return ({
  followup_contacts_disabled:'人工随访记录暂未启用。',followup_plans_disabled:'复查计划暂未启用。',case_not_found:'病例不可访问，请重新打开。',
  contact_invalid_time:'请填写有效的实际联系时间（上海）。',contact_future_time:'实际联系时间不能晚于当前时间。',contact_invalid_choice:'请选择联系方式及实际结果。',
  contact_version_limit:'已达 50 条版本上限，仍可回看或撤销。',contact_source_not_current:'来源计划需重新核对，请通过复查计划面板处理。',
  contact_changed_review_again:'病例、计划或随访记录已变化，请刷新并重新核对。',contact_source_changed:'来源计划已变化，请重新核对。',
  contact_version_changed:'随访版本已变化，请刷新并重新核对。',contact_invalid_saved_data:'保存记录或审计结构异常，暂不能继续。',
  contact_request_payload_changed:'同一请求内容发生变化，请先核对保存结果。',contact_database_unavailable:'随访记录服务暂不可用；已点击保存时请先核对结果。'
})[code]||(error?.response?.status===422?'请核对联系时间、必填项、原因和文字长度。':error?.response?.status===401?'登录已失效，请重新登录。':error.message||'读取或保存未完成，请重试核对。');}
