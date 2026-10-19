import api from './api';

// A receipt locator, never a saved clinical draft or an authorization credential.
// Kept in this tab until independently resolved; no expiry can turn UNKNOWN into failure.
const schema='followup-recovery-v1';
const positive=v=>Number.isSafeInteger(v)&&v>0;
const canonical=v=>JSON.stringify(v,(_key,value)=>value&&typeof value==='object'&&!Array.isArray(value)
  ?Object.fromEntries(Object.keys(value).sort().map(k=>[k,value[k]])):value);
const equal=(a,b)=>canonical(a)===canonical(b);
async function digest(value){
  const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(canonical(value)));
  return [...new Uint8Array(bytes)].map(v=>v.toString(16).padStart(2,'0')).join('');
}
function key(kind,caseId,ownerId){
  if(!['plan','contact'].includes(kind)||!positive(caseId)||!positive(ownerId))throw Error('恢复标识归属无效，未提交保存。');
  return 'pmai.followup-recovery.'+JSON.stringify([import.meta.env?.VITE_DOCTOR_TRIAL_SESSION||'app',api.defaults.baseURL||'',kind,ownerId,caseId]);
}
function validate(ref,kind,caseId,ownerId){
  const names=['schema','kind','caseId','ownerId','requestId','operation','targetId','rootId','recordVersion','contentHash'];
  if(!ref||typeof ref!=='object'||Array.isArray(ref)||!equal(Object.keys(ref).sort(),names.sort())
    ||ref.schema!==schema||ref.kind!==kind||ref.caseId!==caseId||ref.ownerId!==ownerId
    ||typeof ref.requestId!=='string'||!/^[a-f0-9]{32}$/.test(ref.requestId)
    ||typeof ref.contentHash!=='string'||!/^[a-f0-9]{64}$/.test(ref.contentHash)
    ||!['create','correct','withdraw'].includes(ref.operation)||!positive(ref.recordVersion)||ref.recordVersion>50
    ||(ref.operation==='create'?(ref.targetId!==null||ref.rootId!==null||ref.recordVersion!==1):(!positive(ref.targetId)||!positive(ref.rootId))))
    throw Error('恢复标识无法核对，请保留本页并核查保存记录；暂不能新增保存。');
  return ref;
}
export function readRecovery(kind,caseId,ownerId,storage=window.sessionStorage){
  try{
    const raw=storage.getItem(key(kind,caseId,ownerId));
    if(raw===null)return null;
    if(typeof raw!=='string'||raw.length>2048)throw Error();
    return validate(JSON.parse(raw),kind,caseId,ownerId);
  }catch{throw Error('恢复标识无法读取，请保留本页并检查浏览器存储；暂不能新增保存。');}
}
export async function recoveryReference(kind,caseId,ownerId,attempt){
  const {body,before,source,caseSnapshot}=attempt,op=body.operation;
  const data={data:op==='withdraw'?before.data:body.data,reason:body.reason,
    case_snapshot:op==='withdraw'?before.case_snapshot:caseSnapshot,source:kind==='contact'?source:null};
  return validate({schema,kind,caseId,ownerId,requestId:body.request_id,operation:op,
    targetId:op==='create'?null:before.id,rootId:op==='create'?null:before.root_id,
    recordVersion:op==='create'?1:before.version+(op==='correct'?1:0),contentHash:await digest(data)},kind,caseId,ownerId);
}
export function rememberRecovery(ref,storage=window.sessionStorage){
  try{
    const prior=readRecovery(ref.kind,ref.caseId,ref.ownerId,storage);
    if(prior&&!equal(prior,ref))throw Error();
    storage.setItem(key(ref.kind,ref.caseId,ref.ownerId),JSON.stringify(ref));
    if(!equal(readRecovery(ref.kind,ref.caseId,ref.ownerId,storage),ref))throw Error();
  }catch{throw Error('恢复标识未能可靠保存，本次未发送保存请求。请检查浏览器存储后重试。');}
}
export function resolveRecovery(ref,storage=window.sessionStorage){
  const prior=readRecovery(ref.kind,ref.caseId,ref.ownerId,storage);
  if(prior&&!equal(prior,ref))throw Error('恢复标识已变化，请重新核对保存结果。');
  storage.removeItem(key(ref.kind,ref.caseId,ref.ownerId));
  if(readRecovery(ref.kind,ref.caseId,ref.ownerId,storage))throw Error('恢复标识尚未清除，请继续核对。');
}
export async function matchesRecovery(ref,result){
  const row=ref.kind==='plan'?result.plan:result.record;
  if(!row||result.operation!==ref.operation||row.version!==ref.recordVersion
    ||(ref.operation==='create'?row.root_id!==row.id:row.root_id!==ref.rootId)
    ||(ref.operation==='withdraw'&&row.id!==ref.targetId))return false;
  return ref.contentHash===await digest({data:row.data,reason:ref.operation==='withdraw'?row.withdrawal?.reason:row.reason,
    case_snapshot:row.case_snapshot,source:ref.kind==='contact'?row.source:null});
}
export function savedRecoveryRecord(kind,list,result){
  const field=kind==='plan'?'plan':'record',row=result[field],rows=list[kind==='plan'?'plans':'records'];
  const keys=['id','root_id','version','data','reason','case_snapshot',...(kind==='plan'?['reviewed_by','reviewed_at']:['source','recorded_by','recorded_at'])];
  if(result.operation==='withdraw')keys.push('withdrawal');
  return rows.some(saved=>keys.every(key=>equal(saved[key],row[key])));
}
