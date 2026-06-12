import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";

const STATUS_OPTIONS = [
  ["", "全部状态"],
  ["dry_run_only", "Dry-run"],
  ["manual_reviewed_dry_run", "已人工审核 Dry-run"],
  ["manual_changes_requested", "要求修改"],
  ["manual_rejected", "已拒绝"],
  ["manual_paused", "已暂停"],
  ["canceled", "已取消"],
];

const CHANNEL_OPTIONS = [
  ["", "全部渠道"],
  ["sms", "SMS"],
  ["wechat", "WeChat"],
  ["email", "Email"],
  ["in_app", "站内"],
];

export default function AutomatedReminderDeliveryManualApprovalPage() {
  const [items, setItems] = useState([]);
  const [status, setStatus] = useState("");
  const [channel, setChannel] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [busyId, setBusyId] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const totalPages = Math.max(1, Math.ceil((total || 0) / pageSize));

  const stats = useMemo(() => {
    const result = {};
    for (const item of items) {
      const key = item.status || "unknown";
      result[key] = (result[key] || 0) + 1;
    }
    return result;
  }, [items]);

  const fetchAttempts = async (nextPage = page) => {
    try {
      setLoading(true);
      const res = await api.get("/api/automated-reminder-delivery/attempts", {
        params: {
          page: nextPage,
          page_size: pageSize,
          status: status || undefined,
          channel: channel || undefined,
        },
      });
      setItems(Array.isArray(res.data?.items) ? res.data.items : []);
      setTotal(Number(res.data?.total || 0));
      setPage(Number(res.data?.page || nextPage));
      setMessage(`已加载 ${res.data?.total || 0} 条 dry-run delivery attempt · auto_send=false · sends_external_message=false`);
    } catch (err) {
      console.error("Load automated reminder delivery attempts failed:", err);
      setMessage(`加载失败：${formatError(err)}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setPage(1);
    fetchAttempts(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, channel]);

  const manualReview = async (item, decision) => {
    try {
      setBusyId(`review-${item.delivery_id}`);
      await api.post(`/api/automated-reminder-delivery/attempts/${item.delivery_id}/manual-review`, {
        decision,
        reviewed_by: "UI-OPERATOR",
        note: "Manual Approval UI V1：仅审核 dry-run attempt，不允许真实发送。",
        metadata: {
          source: "automated-reminder-delivery-manual-approval-ui-v1",
          dry_run: true,
          auto_send: false,
          sends_external_message: false,
        },
      });
      setMessage("已记录人工审核结果 · dry_run=true · auto_send=false · sends_external_message=false");
      await fetchAttempts(page);
    } catch (err) {
      console.error("Manual review failed:", err);
      alert(`人工审核失败：${formatError(err)}`);
    } finally {
      setBusyId("");
    }
  };

  const cancelAttempt = async (item) => {
    if (!confirm("确定取消这条 dry-run delivery attempt？不会发送外部消息。")) return;

    try {
      setBusyId(`cancel-${item.delivery_id}`);
      await api.post(`/api/automated-reminder-delivery/attempts/${item.delivery_id}/cancel`, {
        canceled_by: "UI-OPERATOR",
        reason: "Manual Approval UI V1 canceled dry-run attempt",
        note: "No provider was called. No external message was sent.",
      });
      setMessage("已取消 dry-run attempt");
      await fetchAttempts(page);
    } catch (err) {
      console.error("Cancel dry-run attempt failed:", err);
      alert(`取消失败：${formatError(err)}`);
    } finally {
      setBusyId("");
    }
  };

  return (
    <div style={pageWrap}>
      <div style={topbar}>
        <div>
          <div style={eyebrow}>Automated Reminder Delivery Manual Approval UI V1</div>
          <h1 style={{ margin: "4px 0" }}>自动提醒发送人工审批（Dry-run）</h1>
          <div style={muted}>
            仅用于 dry-run attempt 人工复核；不会发送短信/微信/邮件。dry_run=true · auto_send=false · sends_external_message=false
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Link to="/" style={btn}>返回首页</Link>
          <button type="button" style={btnPrimary} onClick={() => fetchAttempts(page)} disabled={loading}>
            {loading ? "刷新中…" : "刷新 attempts"}
          </button>
        </div>
      </div>

      <section style={card}>
        <h2 style={h2}>一、筛选</h2>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <select value={status} onChange={(e) => setStatus(e.target.value)} style={input}>
            {STATUS_OPTIONS.map(([value, title]) => (
              <option value={value} key={value || "all"}>{title}</option>
            ))}
          </select>
          <select value={channel} onChange={(e) => setChannel(e.target.value)} style={input}>
            {CHANNEL_OPTIONS.map(([value, title]) => (
              <option value={value} key={value || "all"}>{title}</option>
            ))}
          </select>
          <span style={muted}>本页状态：{Object.entries(stats).map(([k, v]) => `${formatStatus(k)} ${v}`).join(" / ") || "—"}</span>
        </div>
        {message && <div style={notice}>{message}</div>}
      </section>

      <section style={card}>
        <h2 style={h2}>二、Dry-run attempts</h2>
        {loading ? (
          <div style={empty}>加载中…</div>
        ) : items.length === 0 ? (
          <div style={empty}>
            暂无 dry-run attempt。请先通过 Automated Reminder Delivery API Dry-run V1 创建 dry-run attempt。
          </div>
        ) : (
          <div style={{ display: "grid", gap: 10 }}>
            {items.map((item) => {
              const safetyOk = item.dry_run === true && item.auto_send === false && item.sends_external_message === false;
              return (
                <div key={item.delivery_id} style={attemptCard}>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                      <strong>{formatStatus(item.status)}</strong>
                      <span style={badge}>{item.channel || "—"}</span>
                      <span style={safetyOk ? okBadge : dangerBadge}>
                        {safetyOk ? "safe dry-run" : "CHECK SAFETY"}
                      </span>
                    </div>
                    <div style={meta}>delivery_id：{item.delivery_id}</div>
                    <div style={meta}>reminder_id：{item.reminder_id || "—"}　notification_id：{item.notification_id || "—"}</div>
                    <div style={meta}>template：{item.template_key || "—"} / {item.template_version || "—"}</div>
                    <div style={meta}>eligibility：{item.eligibility_result || "—"}　blocked_reason：{item.blocked_reason || "—"}</div>
                    <div style={safeLine}>
                      dry_run={String(item.dry_run)} · auto_send={String(item.auto_send)} · sends_external_message={String(item.sends_external_message)} · creates_case=false · updates_case=false
                    </div>
                  </div>
                  <div style={actions}>
                    <button type="button" style={btnSmall} disabled={Boolean(busyId)} onClick={() => manualReview(item, "approve_dry_run_only")}>
                      审核通过 dry-run
                    </button>
                    <button type="button" style={btnSmall} disabled={Boolean(busyId)} onClick={() => manualReview(item, "changes_requested")}>
                      要求修改
                    </button>
                    <button type="button" style={btnDanger} disabled={Boolean(busyId)} onClick={() => manualReview(item, "reject")}>
                      拒绝
                    </button>
                    <button type="button" style={btnDanger} disabled={Boolean(busyId)} onClick={() => cancelAttempt(item)}>
                      取消
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <div style={pager}>
          <span style={muted}>共 {total} 条，{pageSize} 条/页</span>
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <button type="button" style={btnSmall} disabled={page <= 1} onClick={() => fetchAttempts(Math.max(1, page - 1))}>上一页</button>
            <span>{page} / {totalPages}</span>
            <button type="button" style={btnSmall} disabled={page >= totalPages} onClick={() => fetchAttempts(Math.min(totalPages, page + 1))}>下一页</button>
          </div>
        </div>
      </section>

      <section style={card}>
        <h2 style={h2}>三、安全说明</h2>
        <ul style={{ margin: 0, paddingLeft: 18, color: "#334155", lineHeight: 1.7 }}>
          <li>本页只审核 dry-run attempt，不会触发 provider。</li>
          <li>审核通过 dry-run 不等于批准真实短信/微信/邮件发送。</li>
          <li>真实发送仍需后续 provider sandbox、pilot runbook、feature flags 和 kill switch 阶段。</li>
          <li>当前硬边界：auto_send=false；sends_external_message=false；manual_review_required=true。</li>
        </ul>
      </section>
    </div>
  );
}

function formatError(err) {
  const detail = err?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail) return JSON.stringify(detail);
  return String(err?.message || err);
}

function formatStatus(value) {
  const map = {
    dry_run_only: "Dry-run",
    manual_reviewed_dry_run: "已人工审核 Dry-run",
    manual_changes_requested: "要求修改",
    manual_rejected: "已拒绝",
    manual_paused: "已暂停",
    canceled: "已取消",
    draft: "草稿",
    blocked: "已阻断",
    eligible: "理论可发送",
  };
  return map[value] || value || "未记录";
}

const pageWrap = { padding: 24, maxWidth: 1120, margin: "0 auto", fontFamily: "system-ui,-apple-system,Arial" };
const topbar = { display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-start", flexWrap: "wrap", marginBottom: 14 };
const eyebrow = { color: "#0f3b2e", fontWeight: 800, fontSize: 13, letterSpacing: ".03em" };
const muted = { color: "#64748b", fontSize: 13 };
const card = { border: "1px solid #e5e7eb", borderRadius: 14, padding: 16, margin: "12px 0", background: "#fff", boxShadow: "0 1px 2px rgba(15,23,42,.04)" };
const h2 = { margin: "0 0 12px", fontSize: 18 };
const input = { padding: "8px 10px", borderRadius: 8, border: "1px solid #cbd5e1", minWidth: 180 };
const btn = { padding: "8px 14px", borderRadius: 8, border: "1px solid #64748b", background: "#fff", color: "#111", textDecoration: "none", cursor: "pointer" };
const btnPrimary = { ...btn, border: "1px solid #0f3b2e", background: "#0f3b2e", color: "#fff" };
const btnSmall = { ...btn, padding: "6px 10px", fontSize: 12 };
const btnDanger = { ...btnSmall, border: "1px solid #ef4444", color: "#b91c1c", background: "#fff" };
const notice = { marginTop: 10, border: "1px solid #bbf7d0", background: "#f0fdf4", color: "#166534", borderRadius: 12, padding: "10px 12px", fontSize: 13, fontWeight: 700 };
const empty = { border: "1px dashed #cbd5e1", borderRadius: 12, padding: 12, color: "#64748b", background: "#f8fafc" };
const attemptCard = { display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start", border: "1px solid #e5e7eb", background: "#f8fafc", borderRadius: 12, padding: 12, flexWrap: "wrap" };
const badge = { border: "1px solid #bfdbfe", background: "#eff6ff", color: "#1d4ed8", borderRadius: 999, padding: "2px 8px", fontSize: 12, fontWeight: 700 };
const okBadge = { border: "1px solid #bbf7d0", background: "#f0fdf4", color: "#166534", borderRadius: 999, padding: "2px 8px", fontSize: 12, fontWeight: 700 };
const dangerBadge = { border: "1px solid #fecaca", background: "#fef2f2", color: "#991b1b", borderRadius: 999, padding: "2px 8px", fontSize: 12, fontWeight: 700 };
const meta = { color: "#64748b", fontSize: 12, marginTop: 4, wordBreak: "break-word" };
const safeLine = { marginTop: 6, color: "#166534", fontSize: 12 };
const actions = { display: "flex", gap: 6, flexWrap: "wrap", justifyContent: "flex-end" };
const pager = { display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 14, gap: 10, flexWrap: "wrap" };
