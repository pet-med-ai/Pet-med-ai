export const manualLabDocumentMessage = error => ({
  manual_lab_documents_disabled: "检验报告文书附节暂未启用。可继续导出原有草稿。",
  attachments_disabled: "检查资料暂未启用。可继续导出原有草稿。",
  manual_lab_disabled: "检验项目暂未启用。可继续导出原有草稿。",
  manual_lab_document_stale: "所选检验报告或原件已变化，请重新选择并核对。",
  manual_lab_document_unavailable: "检验报告暂不可读取，请重新核对。",
  manual_lab_document_item_limit: "单次最多纳入 200 个检验项目，请减少报告选择。",
  invalid_manual_lab_document_selection: "单次请选择不重复的 1 至 5 份报告。",
  manual_lab_document_review_required: "请先预览并核对包含检验结果的文书。",
}[error?.response?.data?.detail] || "读取检验报告失败，请重新读取；旧确认已失效。");

export function validDocumentReports(rows, ids = null) {
  if (!Array.isArray(rows) || (ids && (rows.length !== ids.length || rows.length > 5))) return false;
  if (new Set(rows.map(r => r?.id)).size !== rows.length) return false;
  if (ids && JSON.stringify(rows.map(r => r.id).sort((a,b)=>a-b)) !== JSON.stringify([...ids].sort((a,b)=>a-b))) return false;
  if (ids && rows.reduce((n,r)=>n+(r?.data?.items?.length || 0),0) > 200) return false;
  return rows.every(r => Number.isSafeInteger(r.id) && r.id > 0 && r.state === "confirmed" &&
    Number.isSafeInteger(r.root_id) && Number.isSafeInteger(r.version) && r.version > 0 &&
    typeof r.reviewed_by === "string" && typeof r.reviewed_at === "string" &&
    typeof r.source?.name === "string" && /^[a-f0-9]{64}$/.test(r.source?.sha256 || "") &&
    ["title","specimen","collected_at","reported_at","laboratory","device","note"].every(k=>typeof r.data?.report?.[k] === "string") &&
    Array.isArray(r.data?.items) && r.data.items.length > 0 && r.data.items.length <= 100 &&
    r.data.items.every(i=>i.checked === true && ["number","comparison","text","not_tested","not_provided"].includes(i.result_type) &&
      ["name","value","unit","reference","flag","position"].every(k=>typeof i[k] === "string")));
}

export const documentResult = row => ({ not_tested: "未测", not_provided: "未提供" }[row.result_type] || row.value);
