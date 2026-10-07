import api from "./api";
import { draftOwner } from "./consultDraft";
import { attachmentMessage } from "./caseAttachments";

export const imagingLabels = { title:"报告标题",modality:"检查类型",body_part:"检查部位",taken_at:"检查时间（含时区）",institution:"出具机构",findings:"所见原文",impression:"结论原文",limitations:"局限性原文",note:"备注原文",position:"页码或原件位置" };
export const imagingModalities = { dr:"DR",ultrasound:"超声" };
export const imagingStates = { confirmed:"已核对保存",needs_review:"需重新核对",source_unavailable:"原件不可用",superseded:"已被更正",withdrawn:"已撤销" };
export const newImagingData = () => ({title:"",modality:"dr",body_part:"",taken_at:"",institution:"",findings:"",impression:"",limitations:"",note:"",position:"",checked_findings:false,checked_impression:false});
export const editableImagingData = data => ({...data,checked_findings:false,checked_impression:false});
export function imagingMessage(error) {
  const detail=error?.response?.data?.detail;
  return ({ manual_imaging_disabled:"影像记录暂未启用。",manual_imaging_required_field:"请填写标题、部位、检查时间及原件位置。",
    manual_imaging_report_empty:"请填写原报告所见或结论；未提供的部分可以留空。",manual_imaging_check_sections:"请对照原件核对所见和结论两部分。",
    manual_imaging_source_not_imaging:"请选择已关联的 DR 或超声原件。",manual_imaging_modality_mismatch:"检查类型必须与所选原件一致。",
    invalid_manual_imaging_date:"请填写明确的检查时间及其时区，不以当前时间代填。",manual_imaging_report_exists:"此原件已有影像记录，请在原记录上更正。",
    manual_imaging_version_changed:"影像记录已有新版本，请刷新后重新核对。",manual_imaging_source_changed:"原件已变化，请重新核对。",
    manual_imaging_report_limit:"本病例已达 20 份有效影像记录上限。",manual_imaging_version_limit:"此记录已达 20 版本上限，仍可查看或撤销。",
    manual_imaging_storage_or_database_unavailable:"保存结果暂不确定，请核对保存结果。" }[detail]) ||
    (typeof detail === "string" && (detail.startsWith("manual_imaging") || detail.startsWith("invalid_manual_imaging")) ? "影像内容不完整或超出长度限制，请检查原文。" : attachmentMessage(error));
}
export function manualImagingClient(caseId, token, signal) {
  return async (method,path="",data) => {
    if(!token || localStorage.getItem("token")!==token) throw Error("Account changed");
    const response=await api.request({method,url:`/api/cases/${caseId}/manual-imaging${path}`,data,signal,timeout:30000,expectedAuthOwner:draftOwner(token)});
    if(localStorage.getItem("token")!==token) throw Error("Account changed");
    return response.data;
  };
}
