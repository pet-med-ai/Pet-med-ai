import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";

const READY_STATUS = "ready_for_import";
const PAGE_SIZE = 20;

function fmt(value) {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

function prettyJson(value) {
  try {
    return JSON.stringify(value || {}, null, 2);
  } catch {
    return String(value || "");
  }
}

function statusStyle(status) {
  const s = String(status || "").toLowerCase();
  const base = {
    display: "inline-block",
    padding: "3px 8px",
    borderRadius: 999,
    fontSize: 12,
    fontWeight: 800,
    border: "1px solid",
  };
  if (s === "ready_for_import" || s === "frozen") {
    return { ...base, color: "#166534", background: "#dcfce7", borderColor: "#86efac" };
  }
  if (s === "draft") {
    return { ...base, color: "#1d4ed8", background: "#dbeafe", borderColor: "#93c5fd" };
  }
  if (s.includes("reject") || s === "failed") {
    return { ...base, color: "#991b1b", background: "#fee2e2", borderColor: "#fca5a5" };
  }
  return { ...base, color: "#334155", background: "#f1f5f9", borderColor: "#cbd5e1" };
}

function SummaryCard({ label, value, hint }) {
  return (
    <div style={cardStyle}>
      <div style={{ fontSize: 12, opacity: 0.7 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 900, marginTop: 4 }}>{value}</div>
      {hint && <div style={{ fontSize: 12, opacity: 0.65, marginTop: 4 }}>{hint}</div>}
    </div>
  );
}

function JsonBlock({ title, value, emptyText = "暂无" }) {
  const hasContent = value && (Array.isArray(value) ? value.length > 0 : Object.keys(value || {}).length > 0);
  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ fontWeight: 800, marginBottom: 6 }}>{title}</div>
      <pre style={preStyle}>{hasContent ? prettyJson(value) : emptyText}</pre>
    </div>
  );
}

export default function EmrImportBatchPlanningPage() {
  const isAuthed = !!localStorage.getItem("token");

  const [readyReceipts, setReadyReceipts] = useState([]);
  const [receiptTotal, setReceiptTotal] = useState(0);
  const [selectedReceiptIds, setSelectedReceiptIds] = useState(new Set());

  const [batches, setBatches] = useState([]);
  const [batchTotal, setBatchTotal] = useState(0);
  const [batchPage, setBatchPage] = useState(1);
  const [selectedBatchId, setSelectedBatchId] = useState("");
  const [batchDetail, setBatchDetail] = useState(null);

  const [createdBy, setCreatedBy] = useState(localStorage.getItem("clinician_id") || "");
  const [clinicalSignoffId, setClinicalSignoffId] = useState("");
  const [rollbackSnapshotId, setRollbackSnapshotId] = useState("");
  const [note, setNote] = useState("EMR real import batch planning UI V1：候选批次冻结，不执行真实导入。");
  const [freeze, setFreeze] = useState(true);

  const [loadingReceipts, setLoadingReceipts] = useState(false);
  const [loadingBatches, setLoadingBatches] = useState(false);
  const [planning, setPlanning] = useState(false);
  const [errMsg, setErrMsg] = useState("");
  const [lastPlanResult, setLastPlanResult] = useState(null);

  const [approvalOperatorId, setApprovalOperatorId] = useState(localStorage.getItem("clinician_id") || "");
  const [approvalSignoffId, setApprovalSignoffId] = useState("");
  const [approvalRollbackSnapshotId, setApprovalRollbackSnapshotId] = useState("");
  const [approvalAction, setApprovalAction] = useState("approve");
  const [approvalNote, setApprovalNote] = useState("EMR real import clinical approval UI V1：临床 Go / No-Go 批准；仍不执行真实导入。");
  const [approving, setApproving] = useState(false);
  const [lastApprovalResult, setLastApprovalResult] = useState(null);

  const selectedCount = selectedReceiptIds.size;
  const batchTotalPages = Math.max(1, Math.ceil((batchTotal || 0) / PAGE_SIZE));

  const selectedReceipts = useMemo(
    () => readyReceipts.filter((item) => selectedReceiptIds.has(item.receipt_id)),
    [readyReceipts, selectedReceiptIds]
  );

  const fetchReadyReceipts = async () => {
    if (!localStorage.getItem("token")) return;
    try {
      setErrMsg("");
      setLoadingReceipts(true);
      const res = await api.get("/api/webhooks/emr/inbox", {
        params: {
          page: 1,
          page_size: 100,
          status: READY_STATUS,
          dry_run: true,
        },
      });
      const payload = res.data || {};
      setReadyReceipts(payload.items || []);
      setReceiptTotal(payload.total || 0);
      setSelectedReceiptIds((prev) => {
        const next = new Set();
        const available = new Set((payload.items || []).map((item) => item.receipt_id));
        for (const id of prev) {
          if (available.has(id)) next.add(id);
        }
        return next;
      });
    } catch (err) {
      console.error("Load ready receipts failed:", err);
      setErrMsg("读取 ready_for_import receipts 失败，请确认已登录且后端服务正常。");
    } finally {
      setLoadingReceipts(false);
    }
  };

  const fetchBatches = async (page = batchPage) => {
    if (!localStorage.getItem("token")) return;
    try {
      setErrMsg("");
      setLoadingBatches(true);
      const res = await api.get("/api/emr/import-batches", {
        params: {
          page,
          page_size: PAGE_SIZE,
        },
      });
      const payload = res.data || {};
      setBatches(payload.items || []);
      setBatchTotal(payload.total || 0);
      setBatchPage(payload.page || page);
    } catch (err) {
      console.error("Load EMR import batches failed:", err);
      setErrMsg("读取 EMR import batches 失败。");
    } finally {
      setLoadingBatches(false);
    }
  };

  const fetchBatchDetail = async (batchId = selectedBatchId) => {
    if (!batchId || !localStorage.getItem("token")) return;
    try {
      setErrMsg("");
      const res = await api.get(`/api/emr/import-batches/${encodeURIComponent(batchId)}`);
      setSelectedBatchId(batchId);
      setBatchDetail(res.data || null);
    } catch (err) {
      console.error("Load batch detail failed:", err);
      setErrMsg("读取 batch 详情失败。该 batch 可能不存在。");
    }
  };

  useEffect(() => {
    if (isAuthed) {
      fetchReadyReceipts();
      fetchBatches(1);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthed]);

  const toggleReceipt = (receiptId) => {
    setSelectedReceiptIds((prev) => {
      const next = new Set(prev);
      if (next.has(receiptId)) next.delete(receiptId);
      else next.add(receiptId);
      return next;
    });
  };

  const selectAllVisible = () => {
    setSelectedReceiptIds(new Set(readyReceipts.map((item) => item.receipt_id)));
  };

  const clearSelection = () => {
    setSelectedReceiptIds(new Set());
  };

  const handlePlanBatch = async () => {
    if (!localStorage.getItem("token")) {
      alert("请先登录");
      return;
    }
    const cleanCreatedBy = String(createdBy || "").trim();
    if (!cleanCreatedBy) {
      alert("请填写 created_by / 临床人员 ID");
      return;
    }
    if (selectedReceiptIds.size === 0) {
      alert("请至少选择一条 ready_for_import receipt");
      return;
    }

    try {
      setErrMsg("");
      setPlanning(true);
      localStorage.setItem("clinician_id", cleanCreatedBy);
      const body = {
        receipt_ids: Array.from(selectedReceiptIds),
        freeze,
        created_by: cleanCreatedBy,
        clinical_signoff_id: clinicalSignoffId.trim() || null,
        rollback_snapshot_id: rollbackSnapshotId.trim() || null,
        note: note.trim() || null,
        metadata: {
          ui: "emr_import_batch_planning_ui_v1",
          selected_count: selectedReceiptIds.size,
        },
      };

      const res = await api.post("/api/emr/import-batches/plan", body);
      const payload = res.data || {};
      setLastPlanResult(payload);
      const batchId = payload.batch?.batch_id;
      if (batchId) {
        setSelectedBatchId(batchId);
        await fetchBatches(1);
        await fetchBatchDetail(batchId);
      }
      await fetchReadyReceipts();
      alert(`已创建 EMR 导入候选批次：${batchId || "unknown"}`);
    } catch (err) {
      console.error("Plan EMR import batch failed:", err);
      const detail = err?.response?.data?.detail;
      setErrMsg(`创建 batch planning 失败：${typeof detail === "string" ? detail : JSON.stringify(detail || err.message)}`);
    } finally {
      setPlanning(false);
    }
  };

  const handleClinicalApproval = async () => {
    if (!localStorage.getItem("token")) {
      alert("请先登录");
      return;
    }
    const batchId = batchDetail?.batch?.batch_id || selectedBatchId;
    if (!batchId) {
      alert("请先选择一个 batch");
      return;
    }

    const cleanOperator = String(approvalOperatorId || "").trim();
    const cleanSignoff = String(approvalSignoffId || batchDetail?.batch?.clinical_signoff_id || "").trim();
    const cleanSnapshot = String(approvalRollbackSnapshotId || batchDetail?.batch?.rollback_snapshot_id || "").trim();
    if (!cleanOperator) {
      alert("请填写 operator_id / 临床人员 ID");
      return;
    }
    if (!cleanSignoff) {
      alert("请填写 clinical_signoff_id");
      return;
    }
    if (!cleanSnapshot) {
      alert("请填写 rollback_snapshot_id");
      return;
    }
    if (["needs_fix", "reject", "rejected"].includes(approvalAction) && String(approvalNote || "").trim().length < 10) {
      alert("needs_fix / reject 必须填写至少 10 字说明");
      return;
    }

    try {
      setErrMsg("");
      setApproving(true);
      localStorage.setItem("clinician_id", cleanOperator);
      const body = {
        operator_id: cleanOperator,
        clinical_signoff_id: cleanSignoff,
        rollback_snapshot_id: cleanSnapshot,
        approval_action: approvalAction,
        note: approvalNote.trim() || null,
        request_id: `emr-clinical-approval-ui-${Date.now()}`,
        metadata: {
          ui: "emr_import_clinical_approval_ui_v1",
          batch_id: batchId,
        },
      };

      const res = await api.post(`/api/emr/import-batches/${encodeURIComponent(batchId)}/clinical-approval`, body);
      const payload = res.data || {};
      setLastApprovalResult(payload);
      if (payload.batch?.clinical_signoff_id) setApprovalSignoffId(payload.batch.clinical_signoff_id);
      if (payload.batch?.rollback_snapshot_id) setApprovalRollbackSnapshotId(payload.batch.rollback_snapshot_id);
      await fetchBatches(batchPage);
      await fetchBatchDetail(batchId);
      alert(`已写入临床批准动作：${payload.status_after || payload.batch?.status || "unknown"}；audit_log_id=${payload.audit_log_id || "unknown"}`);
    } catch (err) {
      console.error("Clinical approval failed:", err);
      const detail = err?.response?.data?.detail;
      setErrMsg(`临床批准失败：${typeof detail === "string" ? detail : JSON.stringify(detail || err.message)}`);
    } finally {
      setApproving(false);
    }
  };

  if (!isAuthed) {
    return (
      <div style={pageStyle}>
        <h1>EMR Real Import Batch Planning</h1>
        <div style={noticeStyle}>
          请先回首页登录后查看 EMR 真实导入候选批次规划页。V1 只做 planning，不执行真实导入。
        </div>
        <Link to="/" style={btnStyle}>返回首页登录</Link>
      </div>
    );
  }

  return (
    <div style={pageStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap" }}>
        <div>
          <h1 style={{ marginBottom: 4 }}>EMR Real Import Batch Planning</h1>
          <div style={{ opacity: 0.72, fontSize: 13 }}>
            从人工复核为 ready_for_import 的 webhook_inbox receipts 创建真实导入候选批次。V1 只写批次规划与审计，不创建病例。
          </div>
          <div style={{ marginTop: 8, fontSize: 12, color: "#1d4ed8", fontWeight: 800 }}>
            安全边界：writes_emr_import_batches=true；writes_emr_import_batch_receipts=true；writes_audit_log=true；writes_case_database=false；creates_case=false；updates_case=false；downloads_attachments=false；executes_real_import=false；can_execute_import=false。
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Link to="/" style={secondaryBtnStyle}>首页</Link>
          <Link to="/webhooks/emr/inbox" style={secondaryBtnStyle}>Webhook Inbox</Link>
          <button type="button" onClick={() => { fetchReadyReceipts(); fetchBatches(batchPage); }} disabled={loadingReceipts || loadingBatches} style={btnStyle}>
            刷新
          </button>
        </div>
      </div>

      {errMsg && <div style={{ ...noticeStyle, borderColor: "#fecaca", background: "#fef2f2", color: "#991b1b" }}>{errMsg}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 10, marginTop: 16 }}>
        <SummaryCard label="ready_for_import receipts" value={receiptTotal} hint="可用于规划的候选收据" />
        <SummaryCard label="已选择" value={selectedCount} hint="将写入 emr_import_batch_receipts" />
        <SummaryCard label="Batch 总数" value={batchTotal} hint={`第 ${batchPage} / ${batchTotalPages} 页`} />
        <SummaryCard label="安全边界" value="Planning only" hint="executes_real_import=false" />
      </div>

      <section style={sectionStyle}>
        <h2 style={sectionTitleStyle}>创建候选批次</h2>
        <div style={formGridStyle}>
          <label style={labelStyle}>
            created_by / 临床人员 ID
            <input value={createdBy} onChange={(e) => setCreatedBy(e.target.value)} placeholder="HS-0001" style={inputStyle} />
          </label>
          <label style={labelStyle}>
            clinical_signoff_id
            <input value={clinicalSignoffId} onChange={(e) => setClinicalSignoffId(e.target.value)} placeholder="SIGNOFF-YYYYMMDD-001，可空" style={inputStyle} />
          </label>
          <label style={labelStyle}>
            rollback_snapshot_id
            <input value={rollbackSnapshotId} onChange={(e) => setRollbackSnapshotId(e.target.value)} placeholder="SNAPSHOT-YYYYMMDD-001，可空" style={inputStyle} />
          </label>
          <label style={{ ...labelStyle, display: "inline-flex", alignItems: "center", gap: 8, marginTop: 22 }}>
            <input type="checkbox" checked={freeze} onChange={(e) => setFreeze(e.target.checked)} />
            创建后冻结 batch（status=frozen）
          </label>
        </div>
        <label style={{ ...labelStyle, marginTop: 10 }}>
          note
          <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={3} style={{ ...inputStyle, resize: "vertical" }} />
        </label>
        <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
          <button type="button" onClick={handlePlanBatch} disabled={planning || selectedCount === 0} style={btnStyle}>
            {planning ? "创建中…" : `创建候选批次（${selectedCount} 条）`}
          </button>
          <button type="button" onClick={selectAllVisible} disabled={loadingReceipts || readyReceipts.length === 0} style={secondaryBtnStyle}>选择本页全部</button>
          <button type="button" onClick={clearSelection} disabled={selectedCount === 0} style={secondaryBtnStyle}>清空选择</button>
        </div>
        <div style={{ marginTop: 8, fontSize: 12, opacity: 0.72 }}>
          说明：POST /api/emr/import-batches/plan 只写 emr_import_batches、emr_import_batch_receipts 和 audit_log；不会执行真实导入。
        </div>
      </section>

      <section style={sectionStyle}>
        <h2 style={sectionTitleStyle}>ready_for_import Receipt 选择</h2>
        {loadingReceipts ? (
          <div style={emptyStyle}>Receipt 加载中…</div>
        ) : readyReceipts.length === 0 ? (
          <div style={emptyStyle}>暂无 ready_for_import receipt。请先在 Webhook Inbox 页面完成人工复核动作。</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={thStyle}>选择</th>
                  <th style={thStyle}>status</th>
                  <th style={thStyle}>receipt_id</th>
                  <th style={thStyle}>external_case_id</th>
                  <th style={thStyle}>idempotency_key</th>
                  <th style={thStyle}>received_at</th>
                </tr>
              </thead>
              <tbody>
                {readyReceipts.map((item) => (
                  <tr key={item.receipt_id} style={selectedReceiptIds.has(item.receipt_id) ? selectedRowStyle : undefined}>
                    <td style={tdStyle}>
                      <input type="checkbox" checked={selectedReceiptIds.has(item.receipt_id)} onChange={() => toggleReceipt(item.receipt_id)} />
                    </td>
                    <td style={tdStyle}><span style={statusStyle(item.status)}>{fmt(item.status)}</span></td>
                    <td style={monoTdStyle}>{item.receipt_id}</td>
                    <td style={tdStyle}>{fmt(item.external_case_id)}</td>
                    <td style={monoTdStyle}>{fmt(item.idempotency_key)}</td>
                    <td style={tdStyle}>{fmt(item.received_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {selectedReceipts.length > 0 && (
          <JsonBlock
            title="selected_receipts preview"
            value={selectedReceipts.map((item) => ({
              receipt_id: item.receipt_id,
              external_case_id: item.external_case_id,
              idempotency_key: item.idempotency_key,
            }))}
          />
        )}
      </section>

      <section style={sectionStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <h2 style={sectionTitleStyle}>已规划 Batch 列表</h2>
          <button type="button" onClick={() => fetchBatches(batchPage)} disabled={loadingBatches} style={secondaryBtnStyle}>刷新 batches</button>
        </div>
        {batches.length === 0 ? (
          <div style={emptyStyle}>暂无 batch。</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={thStyle}>status</th>
                  <th style={thStyle}>batch_id</th>
                  <th style={thStyle}>receipt_count</th>
                  <th style={thStyle}>created_by</th>
                  <th style={thStyle}>frozen_at</th>
                  <th style={thStyle}>操作</th>
                </tr>
              </thead>
              <tbody>
                {batches.map((item) => (
                  <tr key={item.batch_id} style={item.batch_id === selectedBatchId ? selectedRowStyle : undefined}>
                    <td style={tdStyle}><span style={statusStyle(item.status)}>{fmt(item.status)}</span></td>
                    <td style={monoTdStyle}>{item.batch_id}</td>
                    <td style={tdStyle}>{item.receipt_count}</td>
                    <td style={tdStyle}>{fmt(item.created_by)}</td>
                    <td style={tdStyle}>{fmt(item.frozen_at)}</td>
                    <td style={tdStyle}>
                      <button type="button" onClick={() => fetchBatchDetail(item.batch_id)} style={btnTinyStyle}>查看详情</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 12 }}>
          <div style={{ opacity: 0.7, fontSize: 12 }}>共 {batchTotal} 条，{PAGE_SIZE} 条/页</div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <button type="button" style={btnTinyStyle} disabled={batchPage <= 1 || loadingBatches} onClick={() => fetchBatches(Math.max(1, batchPage - 1))}>上一页</button>
            <span>第 {batchPage} / {batchTotalPages} 页</span>
            <button type="button" style={btnTinyStyle} disabled={batchPage >= batchTotalPages || loadingBatches} onClick={() => fetchBatches(Math.min(batchTotalPages, batchPage + 1))}>下一页</button>
          </div>
        </div>
      </section>

      <section style={sectionStyle}>
        <h2 style={sectionTitleStyle}>Batch 详情</h2>
        {!batchDetail ? (
          <div style={emptyStyle}>请选择一个 batch 查看详情。</div>
        ) : (
          <div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 10 }}>
              <SummaryCard label="batch_id" value={batchDetail.batch?.batch_id?.slice(0, 18) || "—"} hint={batchDetail.batch?.batch_id} />
              <SummaryCard label="status" value={batchDetail.batch?.status || "—"} hint={`receipt_count=${batchDetail.batch?.receipt_count ?? "-"}`} />
              <SummaryCard label="真实导入" value="未执行" hint="executes_real_import=false" />
            </div>
            <JsonBlock title="batch" value={batchDetail.batch || {}} />
            <JsonBlock title="receipts" value={batchDetail.receipts || []} />
            <JsonBlock title="safety" value={batchDetail.safety || {}} />

            <div style={{ marginTop: 16, padding: 14, border: "1px solid #bbf7d0", borderRadius: 12, background: "#f0fdf4" }}>
              <h3 style={{ marginTop: 0 }}>EMR Real Import Clinical Approval</h3>
              <div style={{ fontSize: 13, lineHeight: 1.55, color: "#166534", fontWeight: 700 }}>
                临床 Go / No-Go 批准门禁：POST /api/emr/import-batches/{"{batch_id}"}/clinical-approval。
              </div>
              <div style={{ marginTop: 6, fontSize: 12, color: "#166534" }}>
                安全边界：writes_emr_import_batches=true；writes_audit_log=true；writes_case_database=false；creates_case=false；updates_case=false；downloads_attachments=false；executes_real_import=false；can_execute_import=false。
              </div>

              <div style={formGridStyle}>
                <label style={labelStyle}>
                  operator_id / 临床人员 ID
                  <input value={approvalOperatorId} onChange={(e) => setApprovalOperatorId(e.target.value)} placeholder="HS-0001" style={inputStyle} />
                </label>
                <label style={labelStyle}>
                  clinical_signoff_id
                  <input value={approvalSignoffId || batchDetail.batch?.clinical_signoff_id || ""} onChange={(e) => setApprovalSignoffId(e.target.value)} placeholder="SIGNOFF-YYYYMMDD-001" style={inputStyle} />
                </label>
                <label style={labelStyle}>
                  rollback_snapshot_id
                  <input value={approvalRollbackSnapshotId || batchDetail.batch?.rollback_snapshot_id || ""} onChange={(e) => setApprovalRollbackSnapshotId(e.target.value)} placeholder="SNAPSHOT-YYYYMMDD-001" style={inputStyle} />
                </label>
                <label style={labelStyle}>
                  approval_action
                  <select value={approvalAction} onChange={(e) => setApprovalAction(e.target.value)} style={inputStyle}>
                    <option value="approve">approve → approved</option>
                    <option value="clinical_signed">clinical_signed</option>
                    <option value="needs_fix">needs_fix</option>
                    <option value="reject">reject → approval_rejected</option>
                    <option value="rejected">rejected → approval_rejected</option>
                  </select>
                </label>
              </div>

              <label style={{ ...labelStyle, marginTop: 10 }}>
                note / 批准或 No-Go 说明
                <textarea value={approvalNote} onChange={(e) => setApprovalNote(e.target.value)} rows={3} style={{ ...inputStyle, resize: "vertical" }} />
              </label>

              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
                <button type="button" onClick={handleClinicalApproval} disabled={approving || !batchDetail?.batch?.batch_id} style={btnStyle}>
                  {approving ? "写入中…" : "写入临床批准动作"}
                </button>
                <span style={{ fontSize: 12, opacity: 0.72, alignSelf: "center" }}>
                  返回字段：audit_log_id / status_after / approval_action / can_execute_import=false
                </span>
              </div>

              {lastApprovalResult && (
                <JsonBlock
                  title="last_clinical_approval_result"
                  value={{
                    audit_log_id: lastApprovalResult.audit_log_id,
                    status_before: lastApprovalResult.status_before,
                    status_after: lastApprovalResult.status_after,
                    approval_action: lastApprovalResult.approval_action || lastApprovalResult.action,
                    writes_emr_import_batches: lastApprovalResult.writes_emr_import_batches,
                    writes_audit_log: lastApprovalResult.writes_audit_log,
                    writes_case_database: lastApprovalResult.writes_case_database,
                    creates_case: lastApprovalResult.creates_case,
                    updates_case: lastApprovalResult.updates_case,
                    downloads_attachments: lastApprovalResult.downloads_attachments,
                    executes_real_import: lastApprovalResult.executes_real_import,
                    can_execute_import: lastApprovalResult.can_execute_import,
                  }}
                />
              )}
            </div>
          </div>
        )}
      </section>

      {lastPlanResult && (
        <section style={sectionStyle}>
          <h2 style={sectionTitleStyle}>最近创建结果</h2>
          <JsonBlock title="planning response" value={lastPlanResult} />
        </section>
      )}
    </div>
  );
}

const pageStyle = { maxWidth: 1200, margin: "0 auto", padding: 24, color: "#0f172a" };
const sectionStyle = { marginTop: 16, padding: 14, border: "1px solid #dbeafe", borderRadius: 12, background: "#ffffff" };
const sectionTitleStyle = { margin: 0, marginBottom: 10 };
const noticeStyle = { marginTop: 12, padding: 12, border: "1px solid #bfdbfe", borderRadius: 10, background: "#eff6ff" };
const cardStyle = { padding: 12, border: "1px solid #dbeafe", borderRadius: 12, background: "#f8fafc", minHeight: 74 };
const formGridStyle = { display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 10 };
const labelStyle = { display: "block", fontSize: 13, fontWeight: 800 };
const inputStyle = { width: "100%", marginTop: 4, padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: 8, boxSizing: "border-box" };
const btnStyle = { padding: "8px 12px", border: "1px solid #2563eb", borderRadius: 8, background: "#2563eb", color: "#fff", cursor: "pointer", textDecoration: "none", display: "inline-block" };
const secondaryBtnStyle = { padding: "8px 12px", border: "1px solid #cbd5e1", borderRadius: 8, background: "#fff", color: "#0f172a", cursor: "pointer", textDecoration: "none", display: "inline-block" };
const btnTinyStyle = { padding: "5px 8px", border: "1px solid #cbd5e1", borderRadius: 6, background: "#fff", cursor: "pointer" };
const tableStyle = { width: "100%", borderCollapse: "collapse", fontSize: 13 };
const thStyle = { textAlign: "left", borderBottom: "1px solid #e5e7eb", padding: 8, background: "#f8fafc" };
const tdStyle = { borderBottom: "1px solid #e5e7eb", padding: 8, verticalAlign: "top" };
const monoTdStyle = { ...tdStyle, fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace", fontSize: 12, maxWidth: 240, wordBreak: "break-all" };
const selectedRowStyle = { background: "#eff6ff" };
const emptyStyle = { padding: 14, border: "1px dashed #cbd5e1", borderRadius: 10, background: "#f8fafc", color: "#64748b" };
const preStyle = { margin: 0, padding: 12, border: "1px solid #e2e8f0", borderRadius: 10, background: "#0f172a", color: "#dbeafe", whiteSpace: "pre-wrap", overflow: "auto", maxHeight: 420, fontSize: 12, lineHeight: 1.55 };
