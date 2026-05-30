// src/pages/KpiDashboard.jsx
import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";

function todayIsoDate() {
  return new Date().toISOString().slice(0, 10);
}

function dateDaysAgo(days) {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

function toPercent(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function formatValue(card) {
  if (!card) return "—";
  const value = card.value;
  if (value === null || value === undefined || card.status === "unavailable") return "暂不可用";
  if (String(card.label || "").includes("时长")) return `${Number(value).toFixed(1)}h`;
  return toPercent(value);
}

function metricState(card) {
  if (!card || card.value === null || card.value === undefined || card.status === "unavailable") {
    return { key: "unknown", label: "待数据模型补齐" };
  }
  const value = Number(card.value);
  const threshold = Number(card.threshold);
  const ok = card.direction === "lower_is_better" ? value <= threshold : value >= threshold;
  return ok ? { key: "ok", label: "达标" } : { key: "warn", label: "关注" };
}

function shortDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 16);
  return date.toLocaleString("zh-CN", { hour12: false });
}

export default function KpiDashboard() {
  const [start, setStart] = useState(() => dateDaysAgo(30));
  const [end, setEnd] = useState(() => todayIsoDate());
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const isAuthed = Boolean(localStorage.getItem("token"));

  const load = async () => {
    if (!isAuthed) {
      setError("请先回首页登录后查看 KPI 仪表盘。");
      setData(null);
      return;
    }

    try {
      setLoading(true);
      setError("");
      const res = await api.get("/api/kpi/dashboard", {
        params: {
          start: start || undefined,
          end: end || undefined,
        },
      });
      setData(res.data || null);
    } catch (err) {
      console.error("KPI dashboard load failed", err);
      if (err?.response?.status === 401) {
        setError("登录状态已失效，请回首页重新登录。");
      } else {
        setError("KPI 仪表盘加载失败，请检查后端日志或网络。 ");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const cards = data?.cards || {};
  const cardItems = useMemo(() => ([
    ["case_completeness", cards.case_completeness],
    ["repeat_imaging_rate", cards.repeat_imaging_rate],
    ["followup_compliance", cards.followup_compliance],
    ["average_time_to_close_hours", cards.average_time_to_close_hours],
    ["duplicate_imaging_share", cards.duplicate_imaging_share],
    ["qa_audit_coverage", cards.qa_audit_coverage],
  ]), [cards]);

  const cases = data?.sections?.cases?.metrics?.case_completeness || {};
  const imaging = data?.sections?.imaging?.metrics || {};
  const followups = data?.sections?.followups?.metrics?.followup_compliance || {};
  const qa = data?.sections?.qa?.metrics?.qa_audit_coverage || {};

  return (
    <div lang="zh-CN" translate="no" className="notranslate" style={page}>
      <header style={hero}>
        <div>
          <div style={eyebrow}>Pet Med AI · Operations</div>
          <h1 style={{ margin: "4px 0 8px", fontSize: 30 }}>运维 KPI 仪表盘</h1>
          <div style={{ opacity: 0.78, lineHeight: 1.6 }}>
            一页查看病例完整度、影像复拍、回访合规、结案时长、重复影像占比和 QA 覆盖率。
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <Link to="/" style={ghostBtn}>返回首页</Link>
          <button type="button" onClick={() => { setStart(dateDaysAgo(7)); setEnd(todayIsoDate()); }} style={ghostBtn}>近 7 天</button>
          <button type="button" onClick={() => { setStart(dateDaysAgo(30)); setEnd(todayIsoDate()); }} style={ghostBtn}>近 30 天</button>
        </div>
      </header>

      <section style={toolbar}>
        <label style={fieldInline}>
          <span>开始日期</span>
          <input type="date" value={start} onChange={(e) => setStart(e.target.value)} style={input} />
        </label>
        <label style={fieldInline}>
          <span>结束日期</span>
          <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} style={input} />
        </label>
        <button type="button" onClick={load} disabled={loading} style={primaryBtn}>
          {loading ? "刷新中…" : "刷新 KPI"}
        </button>
        <span style={{ fontSize: 12, opacity: 0.72 }}>
          {data?.period ? `统计区间：${shortDate(data.period.start)} → ${shortDate(data.period.end)}` : "统计区间待加载"}
        </span>
      </section>

      {error && <div style={errorBox}>{error}</div>}

      <section style={gridCards}>
        {cardItems.map(([key, card]) => (
          <KpiCard key={key} cardKey={key} card={card} />
        ))}
      </section>

      <section style={contentGrid}>
        <Panel title="病例字段完整度" subtitle="按当前 Case 字段近似计算；后续补齐体温、过敏史、收费字段后升级口径。">
          <div style={bigNumber}>{toPercent(cases.rate)}</div>
          <div style={muted}>完整 {cases.complete_cases ?? 0} / 总计 {cases.total_cases ?? 0}</div>
          <MiniDict title="缺失字段分布" data={cases.missing_by_field || {}} />
          <CaseSamples rows={cases.incomplete_samples || []} />
        </Panel>

        <Panel title="影像复拍 / 重复影像" subtitle="基于 imaging_studies 与 imaging_billing 的只读聚合。">
          <div style={twoCols}>
            <MiniMetric label="复拍率" value={toPercent(imaging.repeat_imaging?.rate)} threshold="阈值 < 8%" />
            <MiniMetric label="重复影像占比" value={toPercent(imaging.duplicate_imaging_share?.share)} threshold="阈值 < 5%" />
          </div>
          <ImagingAnomalies rows={imaging.repeat_imaging?.anomalies || []} />
        </Panel>

        <Panel title="回访合规" subtitle="到期日 ±1 天内完成视为合规。">
          <div style={bigNumber}>{toPercent(followups.rate)}</div>
          <div style={muted}>合规 {followups.done_within_due_plus_minus_1_day ?? 0} / 到期 {followups.due_total ?? 0}</div>
          <MiniDict title="分档" data={followups.bands || {}} />
          <FollowupSamples rows={followups.overdue_samples || []} />
        </Panel>

        <Panel title="QA 审计覆盖" subtitle="病例抽检覆盖率与严重度 / 状态分布。">
          <div style={bigNumber}>{toPercent(qa.rate)}</div>
          <div style={muted}>已审计病例 {qa.audited_cases ?? 0} / 总病例 {qa.total_cases ?? 0}</div>
          <MiniDict title="严重度" data={qa.severity_counts || {}} />
          <QaSamples rows={qa.samples || []} />
        </Panel>
      </section>

      <section style={panelWide}>
        <h2 style={panelTitle}>异常触发表 Top20</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 12 }}>
          <CompactList title="字段不完整病例" rows={(cases.incomplete_samples || []).map((row) => ({
            key: row.case_id,
            main: `#${row.case_id} · ${row.patient_name || "未命名"}`,
            sub: `缺失：${(row.missing_fields || []).join("、") || "—"}`,
            to: row.case_id ? `/cases/${row.case_id}` : "",
          }))} />
          <CompactList title="影像复拍异常" rows={(imaging.repeat_imaging?.anomalies || []).map((row) => ({
            key: `${row.case_id}-${row.modality}-${row.body_part}`,
            main: `#${row.case_id} · ${row.modality || "影像"} · ${row.body_part || "部位未记"}`,
            sub: `次数：${row.count}，最近：${shortDate(row.last_taken_at)}`,
            to: row.case_id ? `/cases/${row.case_id}` : "",
          }))} />
          <CompactList title="逾期 / 未完成回访" rows={(followups.overdue_samples || []).map((row) => ({
            key: `${row.case_id}-${row.due_date}`,
            main: `#${row.case_id} · ${row.owner || "未分配"}`,
            sub: `到期：${shortDate(row.due_date)}；完成：${shortDate(row.done_at)}`,
            to: row.case_id ? `/cases/${row.case_id}` : "",
          }))} />
        </div>
      </section>
    </div>
  );
}

function KpiCard({ card, cardKey }) {
  const state = metricState(card);
  return (
    <div style={{ ...cardStyle, borderColor: state.key === "warn" ? "#f59e0b" : state.key === "ok" ? "#22c55e" : "#334155" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
        <div style={{ color: "#cbd5e1", fontSize: 13 }}>{card?.label || cardKey}</div>
        <span style={{ ...badge, background: state.key === "warn" ? "#451a03" : state.key === "ok" ? "#052e16" : "#1e293b" }}>{state.label}</span>
      </div>
      <div style={cardValue}>{formatValue(card)}</div>
      <div style={{ color: "#94a3b8", fontSize: 12 }}>
        阈值：{card?.threshold === null || card?.threshold === undefined ? "—" : (String(card?.label || "").includes("时长") ? `${card.threshold}h` : toPercent(card.threshold))}
      </div>
    </div>
  );
}

function Panel({ title, subtitle, children }) {
  return (
    <section style={panel}>
      <h2 style={panelTitle}>{title}</h2>
      {subtitle && <div style={panelSubtitle}>{subtitle}</div>}
      {children}
    </section>
  );
}

function MiniMetric({ label, value, threshold }) {
  return (
    <div style={miniMetric}>
      <div style={muted}>{label}</div>
      <div style={{ fontSize: 26, fontWeight: 900 }}>{value}</div>
      <div style={{ fontSize: 12, opacity: 0.7 }}>{threshold}</div>
    </div>
  );
}

function MiniDict({ title, data }) {
  const entries = Object.entries(data || {});
  if (!entries.length) return <div style={muted}>{title}：暂无数据</div>;
  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ fontWeight: 700, marginBottom: 6 }}>{title}</div>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        {entries.map(([key, value]) => <span key={key} style={pill}>{key}: {value}</span>)}
      </div>
    </div>
  );
}

function CaseSamples({ rows }) {
  if (!rows.length) return <div style={empty}>暂无字段不完整样本。</div>;
  return <CompactList title="样本" rows={rows.map((row) => ({ key: row.case_id, main: `#${row.case_id} · ${row.patient_name}`, sub: (row.missing_fields || []).join("、"), to: `/cases/${row.case_id}` }))} />;
}

function ImagingAnomalies({ rows }) {
  if (!rows.length) return <div style={empty}>暂无影像复拍异常。</div>;
  return <CompactList title="复拍明细" rows={rows.map((row) => ({ key: `${row.case_id}-${row.modality}-${row.body_part}`, main: `#${row.case_id} · ${row.modality} · ${row.body_part}`, sub: `次数 ${row.count}；${shortDate(row.first_taken_at)} → ${shortDate(row.last_taken_at)}`, to: `/cases/${row.case_id}` }))} />;
}

function FollowupSamples({ rows }) {
  if (!rows.length) return <div style={empty}>暂无逾期 / 未完成样本。</div>;
  return <CompactList title="回访样本" rows={rows.map((row) => ({ key: `${row.case_id}-${row.due_date}`, main: `#${row.case_id} · ${row.owner || "未分配"}`, sub: `到期：${shortDate(row.due_date)}；状态：${row.status || "—"}`, to: `/cases/${row.case_id}` }))} />;
}

function QaSamples({ rows }) {
  if (!rows.length) return <div style={empty}>暂无 QA 抽检样本。</div>;
  return <CompactList title="QA 样本" rows={rows.map((row) => ({ key: `${row.case_id}-${row.created_at}`, main: `#${row.case_id} · ${row.audit_type || "QA"}`, sub: `${row.severity || "未分级"} · ${row.status || "未记录"}`, to: `/cases/${row.case_id}` }))} />;
}

function CompactList({ title, rows }) {
  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ fontWeight: 800, marginBottom: 6 }}>{title}</div>
      {rows.length ? (
        <div style={{ display: "grid", gap: 7 }}>
          {rows.slice(0, 20).map((row) => (
            <div key={row.key} style={listItem}>
              <div style={{ fontWeight: 700 }}>{row.to ? <Link to={row.to} style={link}>{row.main}</Link> : row.main}</div>
              <div style={{ fontSize: 12, opacity: 0.72 }}>{row.sub}</div>
            </div>
          ))}
        </div>
      ) : (
        <div style={empty}>暂无数据。</div>
      )}
    </div>
  );
}

const page = {
  minHeight: "100vh",
  padding: 24,
  color: "#e5e7eb",
  background: "radial-gradient(circle at 20% 0%, #172554 0, #020617 36%, #020617 100%)",
  fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
};
const hero = { display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-start", marginBottom: 18 };
const eyebrow = { color: "#38bdf8", fontWeight: 800, letterSpacing: ".08em", textTransform: "uppercase", fontSize: 12 };
const toolbar = { display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", padding: 12, border: "1px solid #1e3a8a", borderRadius: 14, background: "rgba(15,23,42,.82)", marginBottom: 14 };
const fieldInline = { display: "flex", gap: 6, alignItems: "center", fontSize: 13, color: "#cbd5e1" };
const input = { padding: "7px 9px", borderRadius: 8, border: "1px solid #334155", background: "#020617", color: "#e5e7eb" };
const primaryBtn = { padding: "8px 13px", borderRadius: 9, border: "1px solid #0ea5e9", background: "#0284c7", color: "#fff", cursor: "pointer", fontWeight: 800 };
const ghostBtn = { padding: "8px 13px", borderRadius: 9, border: "1px solid #38bdf8", background: "rgba(2,132,199,.12)", color: "#e0f2fe", textDecoration: "none", cursor: "pointer" };
const errorBox = { marginBottom: 14, padding: 12, borderRadius: 10, background: "#7f1d1d", border: "1px solid #ef4444" };
const gridCards = { display: "grid", gridTemplateColumns: "repeat(6, minmax(0, 1fr))", gap: 10, marginBottom: 14 };
const cardStyle = { padding: 13, border: "1px solid #334155", borderRadius: 14, background: "rgba(15,23,42,.92)", minHeight: 110 };
const cardValue = { marginTop: 10, marginBottom: 8, fontSize: 28, lineHeight: 1, fontWeight: 950 };
const badge = { color: "#e5e7eb", borderRadius: 999, padding: "2px 7px", fontSize: 11, whiteSpace: "nowrap" };
const contentGrid = { display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 14, marginBottom: 14 };
const panel = { padding: 15, border: "1px solid #1e3a8a", borderRadius: 16, background: "rgba(15,23,42,.86)", boxShadow: "0 12px 40px rgba(0,0,0,.22)" };
const panelWide = { ...panel, marginBottom: 24 };
const panelTitle = { margin: 0, fontSize: 18 };
const panelSubtitle = { marginTop: 5, marginBottom: 10, color: "#94a3b8", fontSize: 13, lineHeight: 1.6 };
const bigNumber = { fontSize: 38, fontWeight: 950, margin: "8px 0 2px" };
const muted = { color: "#94a3b8", fontSize: 13 };
const twoCols = { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 };
const miniMetric = { padding: 12, border: "1px solid #334155", borderRadius: 12, background: "rgba(2,6,23,.55)" };
const pill = { padding: "4px 8px", borderRadius: 999, border: "1px solid #334155", background: "rgba(30,41,59,.72)", fontSize: 12 };
const listItem = { padding: 9, borderRadius: 10, border: "1px solid #334155", background: "rgba(2,6,23,.45)" };
const link = { color: "#7dd3fc", textDecoration: "none" };
const empty = { marginTop: 10, color: "#94a3b8", fontSize: 13 };
