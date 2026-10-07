export const imagingTextSize = rows => rows.reduce((n,r)=>n+["findings","impression","limitations","note"].reduce((v,k)=>v+Array.from(r.data[k]).length,0),0);
export function validImagingReports(rows,ids=null) {
  if(!Array.isArray(rows) || new Set(rows.map(r=>r?.id)).size!==rows.length) return false;
  if(ids && (rows.length>5 || rows.length!==ids.length || JSON.stringify(rows.map(r=>r.id).sort((a,b)=>a-b))!==JSON.stringify([...ids].sort((a,b)=>a-b)))) return false;
  const valid=rows.every(r=>Number.isSafeInteger(r.id) && r.id>0 && r.state==="confirmed" && Number.isSafeInteger(r.root_id) && r.root_id>0 && Number.isSafeInteger(r.version) && r.version>0 &&
    typeof r.reviewed_by==="string" && typeof r.reviewed_at==="string" && typeof r.source?.name==="string" && /^[a-f0-9]{64}$/.test(r.source?.sha256 || "") &&
    ["title","modality","body_part","taken_at","institution","findings","impression","limitations","note","position"].every(k=>typeof r.data?.[k]==="string") &&
    ["dr","ultrasound"].includes(r.data.modality) && r.data.checked_findings===true && r.data.checked_impression===true);
  return valid && (!ids || imagingTextSize(rows)<=20000);
}
export const imagingDocumentMessage = error => ({
  manual_imaging_disabled:"影像记录暂未启用。可继续导出原有草稿。",
  manual_imaging_document_stale:"影像记录或原件已变化，请重新选择并核对。",
  manual_imaging_document_text_limit:"所选影像正文超过 20000 字符，请减少选择。",
  attachments_disabled:"检查资料暂未启用。可继续导出原有草稿。",
}[error?.response?.data?.detail] || "读取影像记录失败，请重新读取；旧确认已失效。");
