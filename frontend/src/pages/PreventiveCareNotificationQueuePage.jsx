import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";

const STATUS_OPTIONS = [
  ["", "全部状态"],
  ["draft", "草稿"],
  ["reviewed", "已人工审核"],
  ["contacted_manually", "已人工联系"],
  ["canceled", "已取消"],
  ["blocked_opt_out", "客户已退订/阻断"],
];

const CHANNEL_OPTIONS = [
  ["", "全部渠道"],
  ["phone_call", "电话人工联系"],
  ["in_app", "站内提醒"],
  ["wechat_manual", "微信人工联系"],
  ["sms_manual", "短信人工联系"],
];

export default function PreventiveCareNotificationQueuePage() {
  const [items, setItems] = useState([]);
  const [status, setStatus] = useState("");
  const [channel, setChannel] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState("");
  const [message, setMessage] = useState("");

  const [draftReminderId, setDraftReminderId] = useState("");
  const [draftChannel, setDraftChannel] = useState("phone_call");
  const [draftMessage, setDraftMessage] = useState("");

  const totalPages = Math.max(1, Math.ceil((total || 0) / pageSize));
  const stats = useMemo(() => {
    const byStatus = {};
    for (const item of items) {
      byStatus[item.status || "unknown"] = (byStatus[item.status || "unknown"] || 0) + 1;
    }
    return byStatus;
  }, [items]);

  const fetchQueue = async (nextPage = page) => {
    try {
      setLoading(true);
      const res = await api.get("/api/preventive-care/notification-queue", {
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
      setMessage(`已加载 ${res.data?.total || 0} 条人工联系队列 · sends_external_message=false`);
    } catch (err) {
      console.error("Preventive care notification queue load failed:", err);
      setMessage(`加载失败：${formatError(err)}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setPage(1);
    fetchQueue(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, channel]);

  const createDraft = async () => {
    const reminderId = draftReminderId.trim();
    if (!reminderId) {
      alert("请填写 reminder_id");
      return;
    }

    try {
      setBusyId("create-draft");
      await api.post("/api/preventive-care/notification-queue/draft", {
        reminder_id: reminderId,
        channel: draftChannel,
        message_preview: draftMessage || undefined,
        reviewed_by: "UI-OPERATOR",
        note: "前台人工联系队列 UI V1 创建；不自动发送消息。",
        metadata: {
          source: "preventive-care-notification-queue-ui-v1",
          auto_send: false,
          sends_external_message: false,
        },
      });
      setDraftReminderId("");
      setDraftMessage("");
      setMessage("已创建人工联系草稿 · auto_send=false · sends_external_message=false");
      await fetchQueue(1);
    } catch (err) {
      console.error("Preventive care notification draft failed:", err);
      alert(`创建草稿失败：${formatError(err)}`);
    } finally {
      setBusyId("");
    }
  };

  const reviewItem = async (item) => {
    try {
      setBusyId(`review-${item.notification_id}`);
      await api.post(`/api/preventive-care/notification-queue/${item.notification_id}/review`, {
        action: "approve_for_manual_contact",
        reviewed_by: "UI-OPERATOR",
        note: "前台人工审核通过；仍需人工联系，不自动发送。",
        metadata: {
          source: "preventive-care-notification-queue-ui-v1",
          auto_send: false,
          sends_external_message: false,
        },
      });
      setMessage("已标记人工审核通过 · manual_review_required=true");
      await fetchQueue(page);
    } catch (err) {
      console.error("Preventive care notification review failed:", err);
      alert(`审核失败：${formatError(err)}`);
    } finally {
      setBusyId("");
    }
  };

  const markContacted = async (item) => {
    try {
      setBusyId(`contacted-${item.notification_id}`);
      await api.post(`/api/preventive-care/notification-queue/${item.notification_id}/mark-contacted`, {
        contacted_by: "UI-OPERATOR",
        contact_result: "manual_contact_completed",
        note: "前台已人工联系；系统没有外发消息。",
        metadata: {
          source: "preventive-care-notification-queue-ui-v1",
          manual_contact_only: true,
          sends_external_message: false,
        },
      });
      setMessage("已标记人工联系完成 · sends_external_message=false");
      await fetchQueue(page);
    } catch (err) {
      console.error("Preventive care notification contacted failed:", err);
      alert(`标记已联系失败：${formatError(err)}`);
    } finally {
      setBusyId("");
    }
  };

  const cancelItem = async (item) => {
    if (!confirm("确定取消这条人工联系队列项？")) return;

    try {
      setBusyId(`cancel-${item.notification_id}`);
      await api.post(`/api/preventive-care/notification-queue/${item.notification_id}/cancel`, {
        canceled_by: "UI-OPERATOR",
        reason: "前台人工取消",
        note: "取消队列项；没有外发消息。",
      });
      setMessage("已取消队列项");
      await fetchQueue(page);
    } catch (err) {
      console.error("Preventive care notification cancel failed:", err);
      alert(`取消失败：${formatError(err)}`);
    } finally {
      setBusyId("");
    }
  };

  return (
    <div style={pageWrap}>
      <div style={topbar}>
        <div>
          <div style={eyebrow}>Preventive Care Reminder Notification Queue UI V1</div>
          <h1 style={{ margin: "4px 0" }}>预防保健前台待联系队列</h1>
          <div style={muted}>人工审核、人工联系、人工取消；auto_send=false · sends_external_message=false</div>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Link to="/" style={btn}>返回首页</Link>
          <button type="button" style={btnPrimary} onClick={() => fetchQueue(page)} disabled={loading}>
            {loading ? "刷新中…" : "刷新队列"}
          </button>
        </div>
      </div>

      <section style={card}>
        <h2 style={h2}>一、创建人工联系草稿</h2>
        <div style={grid}>
          <label>
            <div style={label}>Reminder ID</div>
            <input value={draftReminderId} onChange={(e) => setDraftReminderId(e.target.value)} placeholder="例如 pcr_xxx" style={input} />
          </label>
          <label>
            <div style={label}>渠道 / Channel</div>
            <select value={draftChannel} onChange={(e) => setDraftChannel(e.target.value)} style={input}>
              {CHANNEL_OPTIONS.filter(([value]) => value).map(([value, title]) => (
                <option value={value} key={value}>{title}</option>
              ))}
            </select>
          </label>
        </div>
        <label style={{ display: "block", marginTop: 10 }}>
          <div style={label}>消息草稿 / Message preview</div>
          <textarea value={draftMessage} onChange={(e) => setDraftMessage(e.target.value)} rows={3} style={{ ...input, width: "100%" }} placeholder="留空则由后端按提醒自动生成。此处只是草稿，不会自动发送。" />
        </label>
        <button type="button" style={btnPrimary} onClick={createDraft} disabled={Boolean(busyId)}>
          {busyId === "create-draft" ? "创建中…" : "创建人工联系草稿"}
        </button>
      </section>

      <section style={card}>
        <h2 style={h2}>二、队列筛选</h2>
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
        <h2 style={h2}>三、前台待联系列表</h2>
        {loading ? (
          <div style={empty}>加载中…</div>
        ) : items.length === 0 ? (
          <div style={empty}>暂无队列项。</div>
        ) : (
          <div style={{ display: "grid", gap: 10 }}>
            {items.map((item) => (
              <div key={item.notification_id} style={queueItem}>
                <div style={{ minWidth: 0 }}>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                    <strong>{formatStatus(item.status)}</strong>
                    <span style={badge}>{formatChannel(item.channel)}</span>
                    {item.client_opt_out_snapshot ? <span style={dangerBadge}>client_opt_out_snapshot=true</span> : null}
                  </div>
                  <div style={meta}>ID：{item.notification_id}</div>
                  <div style={meta}>reminder_id：{item.reminder_id || "—"}　case_id：{item.case_id || "—"}</div>
                  <div style={previewText}>{item.message_preview || "—"}</div>
                  <div style={safeLine}>manual_review_required={String(item.manual_review_required)} · auto_send=false · sends_external_message=false</div>
                </div>
                <div style={actions}>
                  <button type="button" style={btnSmall} onClick={() => reviewItem(item)} disabled={Boolean(busyId) || item.client_opt_out_snapshot}>人工审核</button>
                  <button type="button" style={btnSmall} onClick={() => markContacted(item)} disabled={Boolean(busyId) || item.client_opt_out_snapshot}>标记已人工联系</button>
                  <button type="button" style={btnDanger} onClick={() => cancelItem(item)} disabled={Boolean(busyId)}>取消</button>
                </div>
              </div>
            ))}
          </div>
        )}

        <div style={pager}>
          <span style={muted}>共 {total} 条，{pageSize} 条/页</span>
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <button style={btnSmall} disabled={page <= 1} onClick={() => fetchQueue(Math.max(1, page - 1))}>上一页</button>
            <span>{page} / {totalPages}</span>
            <button style={btnSmall} disabled={page >= totalPages} onClick={() => fetchQueue(Math.min(totalPages, page + 1))}>下一页</button>
          </div>
        </div>
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
    draft: "草稿",
    reviewed: "已人工审核",
    contacted_manually: "已人工联系",
    canceled: "已取消",
    blocked_opt_out: "客户已退订/阻断",
    review_required: "需要复核",
  };
  return map[value] || value || "未记录";
}

function formatChannel(value) {
  const map = {
    phone_call: "电话人工联系",
    in_app: "站内提醒",
    wechat_manual: "微信人工联系",
    sms_manual: "短信人工联系",
  };
  return map[value] || value || "未记录";
}

const pageWrap = { padding: 24, maxWidth: 1120, margin: "0 auto", fontFamily: "system-ui,-apple-system,Arial" };
const topbar = { display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-start", flexWrap: "wrap", marginBottom: 14 };
const eyebrow = { color: "#0f3b2e", fontWeight: 800, fontSize: 13, letterSpacing: ".03em" };
const muted = { color: "#64748b", fontSize: 13 };
const card = { border: "1px solid #e5e7eb", borderRadius: 14, padding: 16, margin: "12px 0", background: "#fff", boxShadow: "0 1px 2px rgba(15,23,42,.04)" };
const h2 = { margin: "0 0 12px", fontSize: 18 };
const grid = { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 10 };
const label = { fontSize: 13, color: "#475569", marginBottom: 4 };
const input = { padding: "8px 10px", borderRadius: 8, border: "1px solid #cbd5e1", minWidth: 180 };
const btn = { padding: "8px 14px", borderRadius: 8, border: "1px solid #64748b", background: "#fff", color: "#111", textDecoration: "none", cursor: "pointer" };
const btnPrimary = { ...btn, border: "1px solid #0f3b2e", background: "#0f3b2e", color: "#fff" };
const btnSmall = { ...btn, padding: "6px 10px", fontSize: 12 };
const btnDanger = { ...btnSmall, border: "1px solid #ef4444", color: "#b91c1c", background: "#fff" };
const notice = { marginTop: 10, border: "1px solid #bbf7d0", background: "#f0fdf4", color: "#166534", borderRadius: 12, padding: "10px 12px", fontSize: 13, fontWeight: 700 };
const empty = { border: "1px dashed #cbd5e1", borderRadius: 12, padding: 12, color: "#64748b", background: "#f8fafc" };
const queueItem = { display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start", border: "1px solid #e5e7eb", background: "#f8fafc", borderRadius: 12, padding: 12, flexWrap: "wrap" };
const badge = { border: "1px solid #bfdbfe", background: "#eff6ff", color: "#1d4ed8", borderRadius: 999, padding: "2px 8px", fontSize: 12, fontWeight: 700 };
const dangerBadge = { border: "1px solid #fecaca", background: "#fef2f2", color: "#991b1b", borderRadius: 999, padding: "2px 8px", fontSize: 12, fontWeight: 700 };
const meta = { color: "#64748b", fontSize: 12, marginTop: 4, wordBreak: "break-word" };
const previewText = { marginTop: 8, whiteSpace: "pre-wrap", lineHeight: 1.55, color: "#111827" };
const safeLine = { marginTop: 6, color: "#166534", fontSize: 12 };
const actions = { display: "flex", gap: 6, flexWrap: "wrap", justifyContent: "flex-end" };
const pager = { display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 14, gap: 10, flexWrap: "wrap" };
