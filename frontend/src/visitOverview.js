import api from "./api";
import { draftOwner } from "./consultDraft";

export const overviewSchema = "clinical-case-overview-cw-b10-v1";
export const overviewTargets = ["edit", "attachments", "lab", "imaging", "outpatient", "owner_summary"];
export const overviewStates = { recorded: "已有记录", missing: "未填写", unknown: "结构无法确认", active: "原件可用", confirmed: "当前已核对", needs_review: "需重新核对", source_unavailable: "来源不可用", superseded: "旧版本", withdrawn: "已撤销" };
export const overviewDestinations = { edit: "编辑已保存病例（新标签页）", attachments: "前往检查资料", lab: "前往检验项目", imaging: "前往影像记录", outpatient: "核对门诊病历草稿", owner_summary: "核对宠主说明草稿" };
const hex = value => typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
const object = value => value && typeof value === "object" && !Array.isArray(value);
const positive = value => Number.isSafeInteger(value) && value > 0;
function require(valid) { if (!valid) throw Error("总览返回的数据无法确认，请刷新或回原入口核对。"); }

export function validateOverview(data, caseId) {
  require(object(data) && data.schema === overviewSchema && data.case_id === caseId);
  require(data.read_only === true && data.writes_database === false && data.includes_unsaved_drafts === false);
  require(hex(data.snapshot) && typeof data.read_at === "string" && Number.isFinite(Date.parse(data.read_at)));
  require(Array.isArray(data.navigation_targets) && JSON.stringify(data.navigation_targets) === JSON.stringify(overviewTargets));
  require(object(data.identity) && ["patient_name", "species", "sex", "breed", "coat_color", "owner_name", "owner_phone", "age_info", "weight"].every(k => k in data.identity && (data.identity[k] === null || typeof data.identity[k] === "string")));
  const keys = ["chief_complaint", "history", "exam_findings", "analysis", "treatment", "prognosis"];
  require(Array.isArray(data.fields) && data.fields.length === keys.length);
  data.fields.forEach((field, i) => {
    require(object(field) && field.key === keys[i] && typeof field.label === "string" && field.target === "edit");
    require(["recorded", "missing", "unknown"].includes(field.state) && (field.value === null || typeof field.value === "string"));
    require(field.state !== "recorded" || Boolean(field.value?.trim()));
    require(field.state !== "missing" || !field.value?.trim());
  });
  require(object(data.groups) && Object.keys(data.groups).sort().join() === "attachments,imaging,lab");
  for (const [key, group] of Object.entries(data.groups)) {
    require(object(group) && ["available", "disabled"].includes(group.status));
    if (group.status === "disabled") {
      require(key !== "attachments" && group.records === null && group.counts === null && group.legacy_count === null);
      continue;
    }
    require(Array.isArray(group.records) && object(group.counts) && Number.isSafeInteger(group.legacy_count) && group.legacy_count >= 0);
    const states = key === "attachments" ? ["active", "source_unavailable", "withdrawn"] : ["confirmed", "needs_review", "source_unavailable", "superseded", "withdrawn"];
    require(Object.keys(group.counts).sort().join() === [...states].sort().join());
    const ids = new Set();
    for (const row of group.records) {
      require(object(row) && states.includes(row.state) && row.target === key && !ids.has(row.id)); ids.add(row.id);
      if (key === "attachments") {
        require(hex(row.id) && hex(row.sha256) && typeof row.name === "string" && object(row.metadata) && typeof row.metadata.title === "string");
      } else {
        require(positive(row.id) && positive(row.root_id) && positive(row.version) && typeof row.title === "string" && hex(row.attachment_id));
        require(object(row.source) && typeof row.source.name === "string" && hex(row.source.sha256));
        require(typeof row.reviewed_by === "string" && typeof row.reviewed_at === "string" && typeof row.reason === "string");
        require(["active", "withdrawn", "source_unavailable"].includes(row.source_state));
      }
    }
    for (const state of states) require(group.counts[state] === group.records.filter(row => row.state === state).length);
    if (key !== "attachments") {
      const latest = group.records.filter(row => row.state !== "superseded");
      require(new Set(latest.map(row => row.root_id)).size === latest.length);
    }
  }
  require(Array.isArray(data.notices));
  for (const notice of data.notices) require(object(notice) && typeof notice.label === "string" && ["field_missing", "field_unknown", "module_disabled", "legacy_records", "needs_review", "source_unavailable", "source_without_record"].includes(notice.code) && overviewTargets.includes(notice.target));
  return data;
}

export async function readOverview(caseId, token, signal) {
  if (!positive(caseId) || !token || localStorage.getItem("token") !== token) throw Error("登录已变化，请重新打开病例。");
  const response = await api.get(`/api/cases/${caseId}/visit-overview`, { signal, timeout: 30000, expectedAuthOwner: draftOwner(token) });
  if (localStorage.getItem("token") !== token) throw Error("登录已变化，请重新打开病例。");
  return validateOverview(response.data, caseId);
}

export function overviewMessage(error) {
  const status = error?.response?.status, detail = error?.response?.data?.detail;
  if (status === 401) return "登录已失效，请重新登录后读取总览。";
  if (status === 404) return "当前病例不存在、已删除或当前账号无权查看。";
  if (["visit_overview_disabled", "attachments_disabled"].includes(detail)) return "就诊资料总览暂未启用，仍可使用现有入口。";
  if (status === 409) return "资料结构或来源无法确认，请回原入口核对；未将其当作空记录。";
  if (status === 503) return "总览读取失败，请稍后主动刷新；当前未显示旧快照。";
  return error?.message || "总览读取失败，请主动刷新。";
}
