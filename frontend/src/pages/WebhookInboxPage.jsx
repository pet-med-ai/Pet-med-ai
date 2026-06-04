import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";
// audit_log_id marker: review-action response returns audit_log_id for the append-only audit trail.

const PAGE_SIZE = 20;

function fmt(value) {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

function boolText(value) {
  return value ? "是" : "否";
}

function statusBadgeStyle(status) {
  const s = String(status || "").toLowerCase();
  const base = {
    display: "inline-block",
    padding: "3px 8px",
    borderRadius: 999,
    fontSize: 12,
    fontWeight: 700,
    border: "1px solid",
  };
  if (s === "accepted") return { ...base, color: "#166534", background: "#dcfce7", borderColor: "#86efac" };
  if (s === "duplicate") return { ...base, color: "#92400e", background: "#fef3c7", borderColor: "#fcd34d" };
  if (s === "ready_for_import") return { ...base, color: "#075985", background: "#e0f2fe", borderColor: "#7dd3fc" };
  if (s === "needs_fix") return { ...base, color: "#92400e", background: "#fef3c7", borderColor: "#fcd34d" };
  if (s === "rejected_by_reviewer" || s === "rejected") return { ...base, color: "#991b1b", background: "#fee2e2", borderColor: "#fca5a5" };
  return { ...base, color: "#334155", background: "#f1f5f9", borderColor: "#cbd5e1" };
}

function prettyJson(value) {
  try {
    return JSON.stringify(value || {}, null, 2);
  } catch {
    return String(value || "");
  }
}

function SummaryCard({ label, value, hint }) {
  return (
    <div style={cardStyle}>
      <div style={{ fontSize: 12, opacity: 0.7 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 800, marginTop: 4 }}>{value}</div>
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

export default function WebhookInboxPage() {
  const isAuthed = !!localStorage.getItem("token");
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [dryRun, setDryRun] = useState("all");
  const [receiptFilter, setReceiptFilter] = useState("");
  const [externalCaseFilter, setExternalCaseFilter] = useState("");
  const [idempotencyFilter, setIdempotencyFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [errMsg, setErrMsg] = useState("");
  const [selectedReceiptId, setSelectedReceiptId] = useState("");
  const [detail, setDetail] = useState(null);
  const [includePayload, setIncludePayload] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [reviewAction, setReviewAction] = useState("ready_for_import");
  const [reviewClinicianId, setReviewClinicianId] = useState(() => localStorage.getItem("clinician_id") || "");
  const [reviewReason, setReviewReason] = useState("");
  const [reviewNote, setReviewNote] = useState("");
  const [savingReview, setSavingReview] = useState(false);
  const [lastReviewResult, setLastReviewResult] = useState(null);

  const totalPages = Math.max(1, Math.ceil((total || 0) / PAGE_SIZE));
  const selectedItem = useMemo(
    () => items.find((item) => item.receipt_id === selectedReceiptId),
    [items, selectedReceiptId]
  );

  const fetchList = async (nextPage = page) => {
    if (!localStorage.getItem("token")) return;
    try {
      setErrMsg("");
      setLoading(true);
      const params = {
        page: nextPage,
        page_size: PAGE_SIZE,
      };
      if (status) params.status = status;
      if (dryRun !== "all") params.dry_run = dryRun === "true";
      if (receiptFilter.trim()) params.receipt_id = receiptFilter.trim();
      if (externalCaseFilter.trim()) params.external_case_id = externalCaseFilter.trim();
      if (idempotencyFilter.trim()) params.idempotency_key = idempotencyFilter.trim();

      const res = await api.get("/api/webhooks/emr/inbox", { params });
      const payload = res.data || {};
      const nextItems = payload.items || [];
      setItems(nextItems);
      setTotal(payload.total || 0);
      setPage(payload.page || nextPage);

      if (selectedReceiptId && !nextItems.some((item) => item.receipt_id === selectedReceiptId)) {
        setSelectedReceiptId("");
        setDetail(null);
      }
    } catch (err) {
      console.error("Load webhook inbox error:", err);
      setErrMsg("读取 EMR Webhook inbox 失败，请确认已登录且后端服务正常。");
    } finally {
      setLoading(false);
    }
  };

  const fetchDetail = async (receiptId = selectedReceiptId, nextIncludePayload = includePayload) => {
    if (!receiptId || !localStorage.getItem("token")) return;
    try {
      setErrMsg("");
      setLoadingDetail(true);
      const res = await api.get(`/api/webhooks/emr/inbox/${encodeURIComponent(receiptId)}`, {
        params: { include_payload: nextIncludePayload },
      });
      setDetail(res.data?.receipt || null);
      setSelectedReceiptId(receiptId);
    } catch (err) {
      console.error("Load webhook inbox detail error:", err);
      setErrMsg("读取 receipt 详情失败。该记录可能不存在，或当前账号没有权限。 ");
    } finally {
      setLoadingDetail(false);
    }
  };

  useEffect(() => {
    if (isAuthed) fetchList(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthed]);

  const resetFilters = () => {
    setStatus("");
    setDryRun("all");
    setReceiptFilter("");
    setExternalCaseFilter("");
    setIdempotencyFilter("");
    setPage(1);
    setTimeout(() => fetchList(1), 0);
  };

  const handleSearch = () => {
    setPage(1);
    fetchList(1);
  };

  const togglePayload = (checked) => {
    setIncludePayload(checked);
    if (selectedReceiptId) fetchDetail(selectedReceiptId, checked);
  };

  const submitReviewAction = async () => {
    if (!selectedReceiptId || !detail) {
      alert("请先选择一条 receipt");
      return;
    }

    const clinicianId = reviewClinicianId.trim();
    const reason = reviewReason.trim();
    const note = reviewNote.trim();

    if (!clinicianId) {
      alert("请填写临床复核人员 ID");
      return;
    }

    if (["needs_fix", "rejected"].includes(reviewAction) && `${reason} ${note}`.trim().length < 10) {
      alert("标记为需修复或拒绝时，请填写至少 10 个字的理由或说明");
      return;
    }

    try {
      setErrMsg("");
      setSavingReview(true);
      localStorage.setItem("clinician_id", clinicianId);
      const body = {
        action: reviewAction,
        clinician_id: clinicianId,
        reason: reason || null,
        note: note || null,
        request_id: `webhook-ui-review-${selectedReceiptId}-${Date.now()}`,
        metadata: { ui: "webhook_inbox_detail", receipt_id: selectedReceiptId },
      };
      const res = await api.post(`/api/webhooks/emr/inbox/${encodeURIComponent(selectedReceiptId)}/review-action`, body);
      setLastReviewResult(res.data || null);
      await fetchDetail(selectedReceiptId, includePayload);
      await fetchList(page);
      alert(`已写入复核动作：${res.data?.status_after || reviewAction}`);
    } catch (err) {
      console.error("Webhook inbox review action error:", err);
      setErrMsg("写入人工复核动作失败，请确认已登录、receipt 存在且审计表可写。");
    } finally {
      setSavingReview(false);
    }
  };

  if (!isAuthed) {
    return (
      <div style={pageStyle}>
        <h1>EMR Webhook Inbox</h1>
        <div style={noticeStyle}>
          请先回首页登录后查看 EMR Webhook inbox。这个页面只读展示 dry-run receipt，不会创建病例。
        </div>
        <Link to="/" style={btnStyle}>返回首页登录</Link>
      </div>
    );
  }

  return (
    <div style={pageStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap" }}>
        <div>
          <h1 style={{ marginBottom: 4 }}>EMR Webhook Inbox</h1>
          <div style={{ opacity: 0.72, fontSize: 13 }}>
            只读复核页：查看 receipt、validation report、mapped_case_preview 与 import plan。V1 不创建病例、不下载附件、不写真实入库。安全边界：writes_webhook_inbox=true；writes_audit_log=true；writes_case_database=false；creates_case=false；updates_case=false；downloads_attachments=false。
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Link to="/" style={secondaryBtnStyle}>首页</Link>
          <Link to="/kpi" style={secondaryBtnStyle}>KPI Dashboard</Link>
          <button type="button" onClick={() => fetchList(page)} disabled={loading} style={btnStyle}>
            {loading ? "刷新中…" : "刷新 inbox"}
          </button>
        </div>
      </div>

      {errMsg && <div style={{ ...noticeStyle, borderColor: "#fecaca", background: "#fef2f2", color: "#991b1b" }}>{errMsg}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 10, marginTop: 16 }}>
        <SummaryCard label="Receipt 总数" value={total} hint="当前筛选条件" />
        <SummaryCard label="本页条数" value={items.length} hint={`第 ${page} / ${totalPages} 页`} />
        <SummaryCard label="选中状态" value={fmt(selectedItem?.status)} hint={selectedReceiptId ? selectedReceiptId.slice(0, 18) : "未选中"} />
        <SummaryCard label="安全边界" value="只读" hint="不创建病例 / 不写入 Case" />
      </div>

      <section style={sectionStyle}>
        <h2 style={sectionTitleStyle}>筛选</h2>
        <div style={filterGridStyle}>
          <label style={labelStyle}>
            状态
            <select value={status} onChange={(e) => setStatus(e.target.value)} style={inputStyle}>
              <option value="">全部</option>
              <option value="accepted">accepted</option>
              <option value="rejected">rejected</option>
              <option value="duplicate">duplicate</option>
              <option value="received">received</option>
            </select>
          </label>
          <label style={labelStyle}>
            dry-run
            <select value={dryRun} onChange={(e) => setDryRun(e.target.value)} style={inputStyle}>
              <option value="all">全部</option>
              <option value="true">true</option>
              <option value="false">false</option>
            </select>
          </label>
          <label style={labelStyle}>
            receipt_id
            <input value={receiptFilter} onChange={(e) => setReceiptFilter(e.target.value)} placeholder="rcpt_..." style={inputStyle} />
          </label>
          <label style={labelStyle}>
            external_case_id
            <input value={externalCaseFilter} onChange={(e) => setExternalCaseFilter(e.target.value)} placeholder="EMR case_id" style={inputStyle} />
          </label>
          <label style={labelStyle}>
            Idempotency-Key
            <input value={idempotencyFilter} onChange={(e) => setIdempotencyFilter(e.target.value)} placeholder="stable event key" style={inputStyle} />
          </label>
        </div>
        <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
          <button type="button" onClick={handleSearch} disabled={loading} style={btnStyle}>查询</button>
          <button type="button" onClick={resetFilters} disabled={loading} style={secondaryBtnStyle}>清空筛选</button>
        </div>
      </section>

      <section style={sectionStyle}>
        <h2 style={sectionTitleStyle}>Receipt 列表</h2>
        {items.length === 0 ? (
          <div style={emptyStyle}>暂无 receipt。可以先通过 smoke 或 EMR dry-run endpoint 生成一条。</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={thStyle}>状态</th>
                  <th style={thStyle}>receipt_id</th>
                  <th style={thStyle}>external_case_id</th>
                  <th style={thStyle}>idempotency_key</th>
                  <th style={thStyle}>错误/警告</th>
                  <th style={thStyle}>received_at</th>
                  <th style={thStyle}>操作</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.receipt_id} style={item.receipt_id === selectedReceiptId ? selectedRowStyle : undefined}>
                    <td style={tdStyle}><span style={statusBadgeStyle(item.status)}>{fmt(item.status)}</span></td>
                    <td style={monoTdStyle}>{item.receipt_id}</td>
                    <td style={tdStyle}>{fmt(item.external_case_id)}</td>
                    <td style={monoTdStyle}>{fmt(item.idempotency_key)}</td>
                    <td style={tdStyle}>{item.validation_error_count || 0} / {item.validation_warning_count || 0}</td>
                    <td style={tdStyle}>{fmt(item.received_at)}</td>
                    <td style={tdStyle}>
                      <button type="button" onClick={() => fetchDetail(item.receipt_id, includePayload)} style={btnTinyStyle}>
                        查看详情
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 12 }}>
          <div style={{ opacity: 0.7, fontSize: 12 }}>共 {total} 条，{PAGE_SIZE} 条/页</div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <button type="button" style={btnTinyStyle} disabled={page <= 1 || loading} onClick={() => fetchList(Math.max(1, page - 1))}>上一页</button>
            <span>第 {page} / {totalPages} 页</span>
            <button type="button" style={btnTinyStyle} disabled={page >= totalPages || loading} onClick={() => fetchList(Math.min(totalPages, page + 1))}>下一页</button>
          </div>
        </div>
      </section>

      <section style={sectionStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <h2 style={sectionTitleStyle}>Receipt 详情</h2>
          <label style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 13 }}>
            <input type="checkbox" checked={includePayload} onChange={(e) => togglePayload(e.target.checked)} disabled={!selectedReceiptId || loadingDetail} />
            include_payload=true，显示原始 payload
          </label>
        </div>

        {!selectedReceiptId ? (
          <div style={emptyStyle}>请选择一条 receipt 查看详情。</div>
        ) : loadingDetail ? (
          <div style={emptyStyle}>详情加载中…</div>
        ) : detail ? (
          <div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 10 }}>
              <SummaryCard label="receipt_id" value={detail.receipt_id?.slice(0, 18) || "—"} hint={detail.receipt_id} />
              <SummaryCard label="status" value={detail.status || "—"} hint={`dry_run=${boolText(detail.dry_run)}`} />
              <SummaryCard label="payload 默认隐藏" value={detail.payload_omitted ? "隐藏" : "已显示"} hint="减少误暴露外部 EMR 内容" />
            </div>
            <JsonBlock title="validation_errors" value={detail.validation_errors || []} emptyText="无错误" />
            <JsonBlock title="validation_warnings" value={detail.validation_warnings || []} emptyText="无警告" />
            <JsonBlock title="mapped_case_preview" value={detail.mapped_case_preview || {}} emptyText="暂无映射预览" />
            {detail.payload_omitted ? (
              <div style={noticeStyle}>原始 payload 默认隐藏。勾选 include_payload=true 后才会拉取并展示。</div>
            ) : (
              <JsonBlock title="payload" value={detail.payload || {}} emptyText="payload 为空" />
            )}
          </div>
        ) : (
          <div style={emptyStyle}>暂无详情。</div>
        )}
      </section>
    </div>
  );
}

const pageStyle = { maxWidth: 1200, margin: "0 auto", padding: 24, color: "#0f172a" };
const sectionStyle = { marginTop: 16, padding: 14, border: "1px solid #dbeafe", borderRadius: 12, background: "#ffffff" };
const sectionTitleStyle = { margin: 0, marginBottom: 10 };
const noticeStyle = { marginTop: 12, padding: 12, border: "1px solid #bfdbfe", borderRadius: 10, background: "#eff6ff" };
const cardStyle = { padding: 12, border: "1px solid #dbeafe", borderRadius: 12, background: "#f8fafc", minHeight: 74 };
const filterGridStyle = { display: "grid", gridTemplateColumns: "repeat(5, minmax(0, 1fr))", gap: 10 };
const labelStyle = { display: "block", fontSize: 13, fontWeight: 700 };
const inputStyle = { width: "100%", marginTop: 4, padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: 8 };
const btnStyle = { padding: "8px 12px", border: "1px solid #2563eb", borderRadius: 8, background: "#2563eb", color: "#fff", cursor: "pointer", textDecoration: "none", display: "inline-block" };
const secondaryBtnStyle = { padding: "8px 12px", border: "1px solid #cbd5e1", borderRadius: 8, background: "#fff", color: "#0f172a", cursor: "pointer", textDecoration: "none", display: "inline-block" };
const btnTinyStyle = { padding: "5px 8px", border: "1px solid #cbd5e1", borderRadius: 6, background: "#fff", cursor: "pointer" };
const tableStyle = { width: "100%", borderCollapse: "collapse", fontSize: 13 };
const thStyle = { textAlign: "left", borderBottom: "1px solid #e5e7eb", padding: 8, background: "#f8fafc" };
const tdStyle = { borderBottom: "1px solid #e5e7eb", padding: 8, verticalAlign: "top" };
const monoTdStyle = { ...tdStyle, fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace", fontSize: 12, maxWidth: 220, wordBreak: "break-all" };
const selectedRowStyle = { background: "#eff6ff" };
const emptyStyle = { padding: 14, border: "1px dashed #cbd5e1", borderRadius: 10, background: "#f8fafc", color: "#64748b" };
const preStyle = { margin: 0, padding: 12, border: "1px solid #e2e8f0", borderRadius: 10, background: "#0f172a", color: "#dbeafe", whiteSpace: "pre-wrap", overflow: "auto", maxHeight: 420, fontSize: 12, lineHeight: 1.55 };

const reviewBoxStyle = { marginTop: 12, padding: 12, border: "1px solid #bbf7d0", borderRadius: 10, background: "#f0fdf4" };
