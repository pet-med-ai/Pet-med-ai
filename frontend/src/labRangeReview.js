import api from "./api";
import { draftOwner } from "./consultDraft";

export const rangeSchema = "clinical-lab-range-review-cw-b11-v1";
export const rangeRules = "saved-decimal-closed-bounds-separate-v1";
export const rangeStates = { below: "低于参考下限", between: "位于参考上下限之间", above: "高于参考上限", boundary: "等于参考边界，请核对边界含义", reference_incomplete: "参考范围不完整，无法比较", comparison: "比较符结果，无法确定实际数值", text: "文本结果，未作数值比较", not_tested: "未检", not_provided: "结果未提供" };
export const flagStates = { agrees: "与区间位置一致", conflict: "与区间位置冲突，请回看原件", not_assessed: "当前结果不作标记一致性判断", uninterpreted: "原始标记未解释", not_provided: "未提供标记" };
export const unableStates = ["reference_incomplete", "comparison", "text", "not_tested", "not_provided"];
const hex = value => typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
const object = value => value && typeof value === "object" && !Array.isArray(value);
const positive = value => Number.isSafeInteger(value) && value > 0;
function require(valid) { if (!valid) throw Error("区间核对数据无法确认，请刷新或回原入口核对。"); }

export function validateRangeReview(data, caseId) {
  require(object(data) && data.schema === rangeSchema && data.rules === rangeRules && data.case_id === caseId);
  require(data.read_only === true && data.writes_database === false && data.includes_unsaved_drafts === false);
  require(hex(data.snapshot) && typeof data.read_at === "string" && Number.isFinite(Date.parse(data.read_at)));
  require(object(data.identity) && ["patient_name", "species", "sex", "breed", "coat_color", "owner_name", "owner_phone", "age_info", "weight"].every(k => k in data.identity && (data.identity[k] === null || typeof data.identity[k] === "string")));
  require(Array.isArray(data.reports) && Array.isArray(data.excluded));
  require(Number.isSafeInteger(data.legacy_count) && data.legacy_count >= 0);
  const ids = new Set(), roots = new Set();
  for (const [rows, current] of [[data.reports, true], [data.excluded, false]]) for (const row of rows) {
    require(object(row) && positive(row.id) && positive(row.root_id) && positive(row.version) && !ids.has(row.id)); ids.add(row.id);
    require(hex(row.token) && hex(row.attachment_id) && typeof row.title === "string" && row.target === "lab");
    require(object(row.source) && hex(row.source.sha256) && row.source.id === row.attachment_id && typeof row.source.name === "string");
    require(["active", "withdrawn", "source_unavailable"].includes(row.source_state));
    require(typeof row.reviewed_at === "string" && typeof row.reviewed_by === "string" && typeof row.reason === "string");
    require(object(row.report) && ["title", "panel", "specimen", "collected_at", "reported_at", "laboratory", "device", "note"].every(k => typeof row.report[k] === "string"));
    require(row.report.title === row.title);
    if (!current) { require(["needs_review", "source_unavailable", "superseded", "withdrawn"].includes(row.state) && !("items" in row)); continue; }
    require(row.state === "confirmed" && row.source_state === "active" && !roots.has(row.root_id)); roots.add(row.root_id);
    require(Array.isArray(row.items) && row.items.length > 0);
    row.items.forEach((item, index) => {
      require(object(item) && item.index === index + 1 && item.checked === true);
      require(["name", "result_type", "value", "unit", "reference", "reference_low", "reference_high", "reference_unit", "flag", "position"].every(k => typeof item[k] === "string"));
      require(["number", "comparison", "text", "not_tested", "not_provided"].includes(item.result_type));
      require(["decimal", "reference_low_decimal", "reference_high_decimal", "comparator"].every(k => item[k] === null || typeof item[k] === "string"));
      const c = item.comparison;
      require(object(c) && Object.hasOwn(rangeStates, c.state) && Object.hasOwn(flagStates, c.flag_state));
      require(item.result_type === "number" ? ["below", "between", "above", "boundary", "reference_incomplete"].includes(c.state) : c.state === item.result_type);
      if (["below", "between", "above", "boundary"].includes(c.state)) require(item.decimal !== null && item.reference_low_decimal !== null && item.reference_high_decimal !== null && item.unit.trim() && item.unit === item.reference_unit);
      const expectedFlag = item.flag === "" ? "not_provided" : !["H", "L"].includes(item.flag) ? "uninterpreted" :
        !["below", "between", "above"].includes(c.state) ? "not_assessed" : ((item.flag === "H" && c.state === "above") || (item.flag === "L" && c.state === "below")) ? "agrees" : "conflict";
      require(c.flag_state === expectedFlag);
    });
  }
  const items = data.reports.flatMap(r => r.items);
  const expected = { reports: data.reports.length, items: items.length, out_of_range: items.filter(i => ["below", "above"].includes(i.comparison.state)).length, unable: items.filter(i => unableStates.includes(i.comparison.state)).length, boundary: items.filter(i => i.comparison.state === "boundary").length, flag_conflicts: items.filter(i => i.comparison.flag_state === "conflict").length };
  require(object(data.counts) && Object.keys(data.counts).sort().join() === Object.keys(expected).sort().join());
  for (const [key, count] of Object.entries(expected)) require(data.counts[key] === count);
  return data;
}

export async function readRangeReview(caseId, token, signal) {
  if (!positive(caseId) || !token || localStorage.getItem("token") !== token) throw Error("登录已变化，请重新打开病例。");
  const response = await api.get(`/api/cases/${caseId}/lab-range-review`, { signal, timeout: 30000, expectedAuthOwner: draftOwner(token) });
  if (localStorage.getItem("token") !== token) throw Error("登录已变化，请重新打开病例。");
  return validateRangeReview(response.data, caseId);
}
export function rangeMessage(error) {
  const status = error?.response?.status, detail = error?.response?.data?.detail;
  if (status === 401) return "登录已失效，请重新登录后读取区间核对。";
  if (status === 404) return "当前病例不存在、已删除或当前账号无权查看。";
  if (["lab_range_review_disabled", "manual_lab_disabled", "attachments_disabled"].includes(detail)) return "检验结果区间核对暂未启用，仍可使用现有入口。";
  if (status === 409) return "已保存资料结构或来源无法确认，读取失败；请回原入口核对。";
  if (status === 503) return "区间核对读取失败，请稍后主动刷新。";
  return error?.message || "区间核对读取失败，请主动刷新。";
}
