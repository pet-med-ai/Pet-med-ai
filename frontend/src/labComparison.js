import api from "./api";
import { draftOwner } from "./consultDraft";
import { validateRangeReview, rangeSchema, rangeRules } from "./labRangeReview";

export const comparisonSchema = "clinical-lab-comparison-cw-b12-v1";
export const comparisonRules = "explicit-same-case-exact-difference-v1";
export const comparisonReasons = {
  same_report_root: "两侧属于同一份报告，不能作为两次采样。",
  same_source: "两侧来源文件相同，不能作为两次采样。",
  item_name_mismatch: "项目名称不一致，请回看原件。",
  non_numeric: "两侧并非都是数值结果；比较符、文本、未检和未提供不参与相减。",
  unit_missing: "结果单位未填写。", unit_mismatch: "结果单位不一致，本页不作换算。",
  panel_missing: "检验组合未填写。", panel_mismatch: "检验组合不一致。",
  specimen_missing: "样本类型未填写。", specimen_mismatch: "样本类型不一致。",
  laboratory_missing: "实验室未填写。", laboratory_mismatch: "实验室不一致。",
  device_missing: "设备未填写。", device_mismatch: "设备不一致。",
  collected_at_missing: "采样时间未填写，不能用其他时间代替。",
  collected_at_equal: "两侧采样时间为同一时刻。",
  collected_at_reversed: "A 的采样时间晚于 B，请核对后明确交换两侧。",
  doctor_confirmation_required: "尚未确认项目、方法和采样条件可比。",
};
export const deltaStates = { increase: "数值增加", decrease: "数值减少", same: "数值相同" };
const require = valid => { if (!valid) throw Error("前后对照数据无法确认，请刷新后重新选择。"); };
const object = value => value && typeof value === "object" && !Array.isArray(value);
export const itemSelection = (row, item) => ({ id: row.id, version: row.version, token: row.token, index: item.index, position: item.position });
const equalSelection = (a, b) => object(a) && object(b) && Object.keys(a).sort().join() === "id,index,position,token,version" && ["id", "version", "token", "index", "position"].every(k => a[k] === b[k]);
export function validateComparison(data, caseId) {
  require(object(data) && data.schema === comparisonSchema && data.rules === comparisonRules);
  validateRangeReview({ ...data, schema: rangeSchema, rules: rangeRules }, caseId);
  return data;
}
export function validatePreview(data, saved, request) {
  require(object(data) && data.schema === comparisonSchema && data.rules === comparisonRules && data.case_id === saved.case_id);
  require(data.read_only === true && data.writes_database === false && data.includes_unsaved_drafts === false);
  require(data.snapshot === saved.snapshot && data.snapshot === request.snapshot && Number.isFinite(Date.parse(data.read_at)));
  require(equalSelection(data.a, request.a) && equalSelection(data.b, request.b) && data.doctor_confirmed === request.doctor_confirmed);
  const selected = target => { const row = saved.reports.find(r => r.id === target.id); const item = row?.items.find(i => equalSelection(itemSelection(row, i), target)); require(row && item); return [row, item]; };
  const [ar, ai] = selected(request.a), [br, bi] = selected(request.b);
  const reasons = [];
  if (ar.root_id === br.root_id) reasons.push("same_report_root");
  if (ar.source.sha256 === br.source.sha256) reasons.push("same_source");
  if (ai.name !== bi.name) reasons.push("item_name_mismatch");
  if (ai.result_type !== "number" || bi.result_type !== "number") reasons.push("non_numeric");
  if (!ai.unit.trim() || !bi.unit.trim()) reasons.push("unit_missing"); else if (ai.unit !== bi.unit) reasons.push("unit_mismatch");
  for (const field of ["panel", "specimen", "laboratory", "device"]) {
    if (!ar.report[field].trim() || !br.report[field].trim()) reasons.push(field + "_missing");
    else if (ar.report[field] !== br.report[field]) reasons.push(field + "_mismatch");
  }
  require(Array.isArray(data.reasons) && data.reasons.every(r => Object.hasOwn(comparisonReasons, r)));
  if (!ar.report.collected_at || !br.report.collected_at) reasons.push("collected_at_missing");
  else {
    // Python compares saved timezone-aware datetimes. JS Date truncates microseconds;
    // preserve the server's time-order decision instead of recalculating it here.
    const timeReasons = data.reasons.filter(r => ["collected_at_equal", "collected_at_reversed"].includes(r));
    require(timeReasons.length <= 1); reasons.push(...timeReasons);
  }
  if (!request.doctor_confirmed) reasons.push("doctor_confirmation_required");
  require(Array.isArray(data.reasons) && JSON.stringify(data.reasons) === JSON.stringify(reasons));
  require(data.can_calculate === (reasons.length === 0));
  require(data.reference_changed === ["reference", "reference_low", "reference_high", "reference_unit"].some(k => ai[k] !== bi[k]));
  if (!data.can_calculate) require(data.delta === null);
  else {
    require(object(data.delta) && typeof data.delta.value === "string" && data.delta.value.length <= 1200 && /^-?\d+(?:\.\d+)?$/.test(data.delta.value));
    require(data.delta.unit === ai.unit && Object.hasOwn(deltaStates, data.delta.state));
    const zero = /^-?0+(?:\.0+)?$/.test(data.delta.value);
    require(data.delta.state === (zero ? "same" : data.delta.value.startsWith("-") ? "decrease" : "increase"));
  }
  return data;
}
function auth(caseId, token) {
  if (!Number.isSafeInteger(caseId) || caseId < 1 || !token || localStorage.getItem("token") !== token) throw Error("登录已变化，请重新打开病例。");
}
export async function readComparison(caseId, token, signal) {
  auth(caseId, token);
  const r = await api.get(`/api/cases/${caseId}/lab-comparison`, { signal, timeout: 30000, expectedAuthOwner: draftOwner(token) });
  auth(caseId, token); return validateComparison(r.data, caseId);
}
export async function previewComparison(saved, request, token, signal) {
  auth(saved.case_id, token);
  const r = await api.post(`/api/cases/${saved.case_id}/lab-comparison/preview`, request, { signal, timeout: 30000, expectedAuthOwner: draftOwner(token) });
  auth(saved.case_id, token); return validatePreview(r.data, saved, request);
}
export function comparisonMessage(error) {
  const status = error?.response?.status, detail = error?.response?.data?.detail;
  if (status === 401) return "登录已失效，请重新登录后读取前后对照。";
  if (status === 404) return "当前病例不存在、已删除或当前账号无权查看。";
  if (["lab_comparison_disabled", "manual_lab_disabled", "attachments_disabled"].includes(detail)) return "检验前后对照暂未启用，仍可使用现有入口。";
  if (status === 409) return "保存版本、来源或病例资料已变化或无法确认；请刷新并重新选择。";
  if (status === 422) return "所选项目无法确认，请刷新后重新选择。";
  if (status === 503) return "前后对照读取失败，请稍后主动刷新。";
  return error?.message || "前后对照读取失败，请主动刷新。";
}
