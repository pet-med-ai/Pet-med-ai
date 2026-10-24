import api from "./api";
import { draftOwner } from "./consultDraft";
import { attachmentMessage } from "./caseAttachments";

export const newLabRow = () => ({ name: "", result_type: "number", value: "", unit: "", reference: "", reference_low: "", reference_high: "", reference_unit: "", flag: "", position: "", checked: false });
export const newLabData = () => ({ report: { title: "", panel: "cbc", specimen: "", collected_at: "", reported_at: "", laboratory: "", device: "", note: "" }, items: [newLabRow()] });
export const editableLabData = data => ({ report: { ...data.report }, items: data.items.map(row => Object.fromEntries(Object.keys(newLabRow()).map(k => [k, k === "checked" ? false : row[k]]))) });
export const labStates = { confirmed: "已核对保存", needs_review: "需重新核对", source_unavailable: "原件不可用", superseded: "已被更正", withdrawn: "已撤销" };
export const labTypes = { number: "数值", comparison: "比较值（如 <5）", text: "文本结果", not_tested: "未测", not_provided: "未提供" };
export function labMessage(error) {
  const detail = error?.response?.data?.detail;
  const messages = {
    manual_lab_disabled: "检验项目录入暂未启用。",
    manual_lab_version_changed: "检验记录已有新版本，请刷新并重新核对。",
    manual_lab_report_exists: "此原件已有检验记录，请在原记录上更正。",
    manual_lab_source_changed: "检验原件已变化，请重新核对。",
    manual_lab_source_not_lab: "请选择已关联的检验报告。",
    manual_lab_check_every_item: "请逐项核对后勾选，再核对整份报告。",
    manual_lab_item_limit: "每份报告需要 1 至 100 个项目。",
    manual_lab_report_limit: "本病例已达 20 份有效报告上限。",
    manual_lab_version_limit: "该报告已达 20 个版本上限，仍可查看或撤销。",
    invalid_manual_lab_number: "数值格式无效，请保留原值；比较值需选择比较值类型。",
    manual_lab_reference_unit_conflict: "参考范围单位必须与结果单位完全一致；不确定时只保留范围原文。",
    manual_lab_reference_order: "参考范围下限不能大于上限。",
    manual_lab_reference_original_required: "填写参考范围数值时，请同时保留报告上的范围原文。",
    manual_lab_missing_value_conflict: "未测或未提供的项目应保留空值。",
    manual_lab_required_field: "请填写报告标题、项目名称及原件位置。",
    manual_lab_storage_or_database_unavailable: "保存结果暂不确定，请核对结果。",
  };
  return messages[detail] || (typeof detail === "string" && (detail.startsWith("invalid_manual_lab") || detail.startsWith("manual_lab_")) ? "检验内容不完整或格式无效，请检查各项原文。" : attachmentMessage(error));
}
export function manualLabClient(caseId, token, signal) {
  return async (method, path = "", data) => {
    if (!token || localStorage.getItem("token") !== token) throw Error("Account changed");
    const response = await api.request({ method, url: `/api/cases/${caseId}/manual-lab${path}`, data, signal, timeout: 30000, expectedAuthOwner: draftOwner(token) });
    if (localStorage.getItem("token") !== token) throw Error("Account changed");
    return response.data;
  };
}
