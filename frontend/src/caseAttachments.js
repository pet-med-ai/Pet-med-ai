import api from "./api";
import { draftOwner } from "./consultDraft";

export const newAttachmentRequest = () => crypto.randomUUID().replaceAll("-", "");
export const attachmentMetadata = () => ({ title: "", kind: "lab", taken_at: "", reported_at: "", source: "", note: "" });
export const attachmentMessage = error => ({
  attachments_disabled: "检查资料暂未启用。原有病历仍可正常使用。",
  case_changed_review_again: "病例或资料已变化，请刷新列表并重新核对。",
  case_changed_upload_again: "病例已变化，请取消暂存后在当前病例重新上传。",
  upload_expired: "暂存已失效，请重新选择文件。",
  case_not_found: "病例不可访问，可能已删除或账号已变化。",
  attachment_not_found: "资料不可访问，可能已撤销。",
  attachment_integrity_failed: "原件完整性校验失败，请核对存储记录。",
  attachment_file_unavailable: "原件暂不可读取，请核对存储记录。",
  duplicate_attachment: "相同原件已经关联，请刷新列表。",
  attachment_storage_full: "资料存储空间已达上限。",
  case_attachment_limit: "本病例的资料数量或大小已达上限。",
  invalid_file_structure: "文件结构不完整或格式不受支持，请检查原件。",
  invalid_file_type_or_size: "请选择不超过 10 MiB 的 PDF、JPG 或 PNG 文件。",
  attachment_too_large: "单个文件不能超过 10 MiB。",
  invalid_filename: "文件名无效，请去掉路径或特殊控制字符。",
  invalid_attachment_metadata: "请填写资料标题并核对资料信息。",
  invalid_attachment_date: "检查时间或报告时间无效，请重新选择。",
  request_payload_changed: "本次请求内容已变化，请重新核对。",
  review_changed: "核对内容已变化，请重新预览。",
  attachment_storage_or_database_unavailable: "存储或数据库暂不可用，请先核对操作结果。",
}[error?.response?.data?.detail] || "操作未确认，请核对结果后再处理；原病历不受影响。");

export function attachmentClient(caseId, token, signal) {
  const root = `/api/cases/${caseId}/attachments`;
  return async (method, path = "", data, options = {}) => {
    if (!token || localStorage.getItem("token") !== token) throw new Error("Account changed");
    const result = await api.request({ method, url: root + path, data, signal, timeout: 30000,
      expectedAuthOwner: draftOwner(token), ...options });
    if (localStorage.getItem("token") !== token) throw new Error("Account changed");
    return result.data;
  };
}

export async function verifyAttachmentBytes(bytes, expected) {
  if (bytes.byteLength !== expected.size) throw new Error("Unexpected file size");
  const hash = [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))].map(x => x.toString(16).padStart(2, "0")).join("");
  if (hash !== expected.sha256) throw new Error("Unexpected file integrity");
}
