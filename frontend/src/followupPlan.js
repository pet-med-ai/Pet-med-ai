import api from './api';
import { draftOwner } from './consultDraft';

export const schema = 'clinical-followup-plans-cw-b14-v1';
export const states = {planned:'已核对保存 · 计划待执行', needs_review:'病例资料已变化 · 待重新核对', superseded:'旧版本', withdrawn:'已撤销'};
export const newPlanData = () => ({planned_date:'',purpose:'',items:[''],return_conditions:'',note:''});
export const newRequestId = () => crypto.randomUUID().replaceAll('-', '');
const hash = v => typeof v === 'string' && /^[a-f0-9]{64}$/.test(v);
const id = v => Number.isSafeInteger(v) && v > 0;
const object = v => v !== null && typeof v === 'object' && !Array.isArray(v);
const keys = (v, names) => object(v) && Object.keys(v).sort().join('|') === [...names].sort().join('|');
export const same = (a,b) => a === b || (Array.isArray(a) && Array.isArray(b) && a.length===b.length && a.every((v,i)=>same(v,b[i]))) ||
  (object(a) && object(b) && keys(a,Object.keys(b)) && Object.keys(a).every(k=>same(a[k],b[k])));
export function validDate(v) {
  if(typeof v!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(v)||v<'0001-01-02')return false;
  const d=new Date(v+'T00:00:00Z');return !Number.isNaN(d.valueOf())&&d.toISOString().slice(0,10)===v;
}
function literal(v,max,required=false){return typeof v==='string'&&[...v].length<=max&&(!required||Boolean(v.trim()))&&!/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f\ud800-\udfff\ufffe\uffff]/u.test(v);}
export function validData(v){return keys(v,Object.keys(newPlanData()))&&validDate(v.planned_date)&&literal(v.purpose,1000,true)&&literal(v.return_conditions,1000)&&literal(v.note,1000)&&Array.isArray(v.items)&&v.items.length>=1&&v.items.length<=10&&v.items.every(s=>literal(s,300,true));}
const caseFields=['patient_name','species','sex','age_info','breed','weight','coat_color','owner_name','owner_phone','chief_complaint','history','exam_findings','analysis','treatment','prognosis'];
function validCase(v,cid){return keys(v,['id','owner_id',...caseFields])&&v.id===cid&&id(v.id)&&id(v.owner_id)&&caseFields.every(k=>v[k]===null||typeof v[k]==='string');}
const timestamp=v=>typeof v==='string'&&/(Z|[+-]\d\d:\d\d)$/.test(v)&&Number.isFinite(Date.parse(v));
export function validPlan(p,cid){
  return keys(p,['id','root_id','version','state','stored_state','token','data','reviewed_by','reviewed_at','reason','withdrawal','case_snapshot'])&&id(p.id)&&id(p.root_id)&&id(p.version)&&p.version<=50&&hash(p.token)&&validData(p.data)&&validCase(p.case_snapshot,cid)&&
    typeof p.reviewed_by==='string'&&p.reviewed_by===String(p.case_snapshot.owner_id)&&timestamp(p.reviewed_at)&&literal(p.reason,500,p.version>1)&&
    ['planned','superseded','withdrawn'].includes(p.stored_state)&&((p.state===p.stored_state)||(p.state==='needs_review'&&p.stored_state==='planned'))&&
    (p.stored_state==='withdrawn'?keys(p.withdrawal,['reason','by','at'])&&literal(p.withdrawal.reason,500,true)&&typeof p.withdrawal.by==='string'&&/^[1-9]\d*$/.test(p.withdrawal.by)&&timestamp(p.withdrawal.at):p.withdrawal===null);
}
export function validList(v,cid){
  if(!(keys(v,['schema','case_id','case','as_of_date','timezone','plans','limits','writes_database','case_token','state_token'])&&v.schema===schema&&v.case_id===cid&&validCase(v.case,cid)&&validDate(v.as_of_date)&&v.timezone==='Asia/Shanghai'&&same(v.limits,{items:10,versions:50})&&v.writes_database===false&&hash(v.case_token)&&hash(v.state_token)&&Array.isArray(v.plans)&&v.plans.length<=50&&v.plans.every(p=>validPlan(p,cid))))return false;
  if(new Set(v.plans.map(p=>p.id)).size!==v.plans.length||v.plans.filter(p=>p.stored_state==='planned').length>1)return false;
  const roots=new Map();for(const p of v.plans){if((p.state==='planned')!== (p.stored_state==='planned'&&same(p.case_snapshot,v.case)))return false;roots.set(p.root_id,[...(roots.get(p.root_id)||[]),p]);}
  return [...roots.entries()].every(([root,rows])=>rows[0].id===root&&rows.every((p,i)=>p.version===i+1&&(i===rows.length-1?p.stored_state!=='superseded':p.stored_state==='superseded')));
}
export function makeRequest(draft,list){return {request_id:draft.requestId,operation:draft.operation,plan_id:draft.plan_id,expected_plan_token:draft.expected_plan_token,expected_case_token:list.case_token,expected_state_token:list.state_token,data:draft.operation==='withdraw'?null:structuredClone(draft.data),reason:draft.reason};}
export function validPreview(v,list,body){
  const before=body.plan_id===null?null:list.plans.find(p=>p.id===body.plan_id);
  return keys(v,['schema','case_id','case','as_of_date','timezone','before','data','operation','reason','request_id','writes_database','case_token','state_token','preview_token'])&&v.schema===schema&&v.case_id===list.case_id&&same(v.case,list.case)&&v.as_of_date===list.as_of_date&&v.timezone==='Asia/Shanghai'&&same(v.before,before)&&same(v.data,body.data)&&v.operation===body.operation&&v.reason===body.reason&&v.request_id===body.request_id&&v.writes_database===false&&v.case_token===body.expected_case_token&&v.state_token===body.expected_state_token&&hash(v.preview_token);
}
export function validReceipt(v,cid,rid,readOnly=false){
  if(!object(v)||v.schema!==schema||v.case_id!==cid||v.request_id!==rid||typeof v.writes_database!=='boolean'||(readOnly&&v.writes_database))return false;
  if(v.state==='not_committed')return readOnly&&keys(v,['schema','case_id','request_id','state','writes_database'])&&!v.writes_database;
  return v.state==='committed'&&keys(v,['schema','case_id','request_id','state','operation','plan','writes_database'])&&['create','correct','withdraw'].includes(v.operation)&&validPlan(v.plan,cid);
}
export function followupClient(cid,token,signal){return async(method,path='',data)=>{
  if(!token||localStorage.getItem('token')!==token)throw Error('账号已变化，请重新打开病例。');
  const response=await api.request({method,url:`/api/cases/${cid}/followup-plan${path}`,data,signal,timeout:30000,expectedAuthOwner:draftOwner(token)});
  if(localStorage.getItem('token')!==token)throw Error('账号已变化，请重新打开病例。');
  return response.data;
};}
export function message(error){
  const code=error?.response?.data?.detail;
  return ({followup_plans_disabled:'复查计划暂未启用。',case_not_found:'病例不可访问，请重新打开。',followup_invalid_date:'请填写有效的计划复查日期。',followup_invalid_text:'请核对必填项、文字长度和不支持的字符。',followup_invalid_fields:'复查计划字段不完整或不受支持。',followup_item_limit:'请填写 1 至 10 项复查项目。',followup_version_limit:'已达 50 条版本上限，仍可查看或撤销。',followup_current_plan_exists:'已有当前计划，请在原计划上更正。',followup_version_changed:'计划版本已变化，请刷新并重新核对。',followup_changed_review_again:'病例或计划已变化，原核对失效，请重新读取。',followup_request_payload_changed:'同一请求的内容发生变化，请核对保存结果。',followup_invalid_saved_data:'保存记录结构异常，暂不能继续，请核对记录。',followup_database_unavailable:'复查计划服务暂不可用；如已点击保存，请核对保存结果。'})[code]||
  (error?.response?.status===422?'请核对计划的日期、必填内容、原因和长度。':error?.response?.status===401?'登录已失效，请重新登录。':error.message||'读取或保存未完成，请重试核对。');
}
