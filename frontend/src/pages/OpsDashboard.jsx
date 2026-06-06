import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";

function fmt(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "true" : "false";
  return String(value);
}

function statusLabel(ok) {
  return ok ? "OK" : "CHECK";
}

function badgeStyle(ok) {
  return {
    display: "inline-block",
    padding: "4px 9px",
    borderRadius: 999,
    fontSize: 12,
    fontWeight: 900,
    color: ok ? "#166534" : "#991b1b",
    background: ok ? "#dcfce7" : "#fee2e2",
    border: `1px solid ${ok ? "#86efac" : "#fca5a5"}`,
  };
}

function prettyJson(value) {
  try {
    return JSON.stringify(value || {}, null, 2);
  } catch {
    return String(value || "");
  }
}

function Card({ title, value, ok, hint }) {
  return (
    <div style={cardStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
        <div style={{ fontSize: 13, opacity: 0.72 }}>{title}</div>
        {typeof ok === "boolean" && <span style={badgeStyle(ok)}>{statusLabel(ok)}</span>}
      </div>
      <div style={{ fontSize: 24, fontWeight: 900, marginTop: 6 }}>{value}</div>
      {hint && <div style={{ fontSize: 12, opacity: 0.68, marginTop: 6, wordBreak: "break-word" }}>{hint}</div>}
    </div>
  );
}

function JsonBlock({ title, value }) {
  return (
    <section style={sectionStyle}>
      <h2 style={sectionTitleStyle}>{title}</h2>
      <pre style={preStyle}>{prettyJson(value)}</pre>
    </section>
  );
}

export default function OpsDashboard() {
  const [healthz, setHealthz] = useState(null);
  const [version, setVersion] = useState(null);
  const [flags, setFlags] = useState(null);
  const [loading, setLoading] = useState(false);
  const [lastLoadedAt, setLastLoadedAt] = useState("");
  const [errMsg, setErrMsg] = useState("");

  const loadOpsStatus = async () => {
    try {
      setLoading(true);
      setErrMsg("");
      const [healthRes, versionRes, flagsRes] = await Promise.all([
        api.get("/healthz"),
        api.get("/api/system/version"),
        api.get("/api/system/feature-flags"),
      ]);
      setHealthz(healthRes.data || {});
      setVersion(versionRes.data || {});
      setFlags(flagsRes.data || {});
      setLastLoadedAt(new Date().toLocaleString());
    } catch (err) {
      console.error("Load ops dashboard failed:", err);
      const detail = err?.response?.data?.detail;
      setErrMsg(`读取运维状态失败：${typeof detail === "string" ? detail : JSON.stringify(detail || err.message)}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOpsStatus();
  }, []);

  const schemaOk = !!version?.schema_ok;
  const healthOk = !!healthz?.ok;
  const dangerousOff = !!flags?.all_dangerous_features_disabled;
  const upgradeReady = !!version?.upgrade_ready;
  const dbAligned = !!version?.database_revision && !!version?.alembic_head && version.database_revision === version.alembic_head;

  const dangerousFlags = flags?.dangerous_features_enabled || [];
  const flagRows = useMemo(() => {
    const flagMap = flags?.flags || {};
    return Object.keys(flagMap).sort().map((name) => ({ name, ...(flagMap[name] || {}) }));
  }, [flags]);

  const overallOk = healthOk && schemaOk && dbAligned && dangerousOff && upgradeReady;

  return (
    <div style={pageStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap" }}>
        <div>
          <h1 style={{ marginBottom: 4 }}>Pet-Med-AI Ops Dashboard</h1>
          <div style={{ opacity: 0.72, fontSize: 13 }}>
            Release Status / Admin Ops Dashboard V1：只读查看 healthz、system version、feature flags，用于发版、升级和商业部署后排查。
          </div>
          <div style={{ marginTop: 8, fontSize: 12, color: "#1d4ed8", fontWeight: 800 }}>
            安全边界：read_only=true；writes_database=false；creates_case=false；updates_case=false；executes_real_import=false。
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Link to="/" style={secondaryBtnStyle}>首页</Link>
          <Link to="/kpi" style={secondaryBtnStyle}>KPI</Link>
          <Link to="/webhooks/emr/inbox" style={secondaryBtnStyle}>Webhook Inbox</Link>
          <Link to="/emr/import-batches" style={secondaryBtnStyle}>EMR Batch</Link>
          <button type="button" onClick={loadOpsStatus} disabled={loading} style={btnStyle}>
            {loading ? "刷新中…" : "刷新状态"}
          </button>
        </div>
      </div>

      {errMsg && <div style={{ ...noticeStyle, borderColor: "#fecaca", background: "#fef2f2", color: "#991b1b" }}>{errMsg}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 10, marginTop: 16 }}>
        <Card title="整体状态" value={overallOk ? "可发布" : "需检查"} ok={overallOk} hint={lastLoadedAt ? `最近刷新：${lastLoadedAt}` : "尚未刷新"} />
        <Card title="Backend healthz" value={healthOk ? "healthy" : "unhealthy"} ok={healthOk} hint="/healthz" />
        <Card title="Schema alignment" value={dbAligned ? "aligned" : "mismatch"} ok={dbAligned} hint={`db=${fmt(version?.database_revision)} / head=${fmt(version?.alembic_head)}`} />
        <Card title="Dangerous flags" value={dangerousOff ? "all off" : `${dangerousFlags.length} on`} ok={dangerousOff} hint={dangerousOff ? "高风险功能默认关闭" : dangerousFlags.join(", ")} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 10, marginTop: 10 }}>
        <Card title="App version" value={fmt(version?.app_version)} hint={`env=${fmt(version?.environment)} / service=${fmt(version?.service_name)}`} />
        <Card title="Git commit" value={fmt(version?.git_commit_short)} hint={fmt(version?.git_commit)} />
        <Card title="Upgrade ready" value={fmt(upgradeReady)} ok={upgradeReady} hint="来自 /api/system/version" />
      </div>

      <section style={sectionStyle}>
        <h2 style={sectionTitleStyle}>Release Gate Summary</h2>
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>检查项</th>
              <th style={thStyle}>状态</th>
              <th style={thStyle}>说明</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style={tdStyle}>healthz</td>
              <td style={tdStyle}><span style={badgeStyle(healthOk)}>{statusLabel(healthOk)}</span></td>
              <td style={tdStyle}>后端基础健康检查。</td>
            </tr>
            <tr>
              <td style={tdStyle}>schema_ok</td>
              <td style={tdStyle}><span style={badgeStyle(schemaOk)}>{statusLabel(schemaOk)}</span></td>
              <td style={tdStyle}>数据库 revision 与代码迁移 head 是否一致。</td>
            </tr>
            <tr>
              <td style={tdStyle}>database_revision == alembic_head</td>
              <td style={tdStyle}><span style={badgeStyle(dbAligned)}>{statusLabel(dbAligned)}</span></td>
              <td style={tdStyle}>{fmt(version?.database_revision)} / {fmt(version?.alembic_head)}</td>
            </tr>
            <tr>
              <td style={tdStyle}>all_dangerous_features_disabled</td>
              <td style={tdStyle}><span style={badgeStyle(dangerousOff)}>{statusLabel(dangerousOff)}</span></td>
              <td style={tdStyle}>真实导入、附件下载、处方结构化写入等高风险能力默认关闭。</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section style={sectionStyle}>
        <h2 style={sectionTitleStyle}>Feature Flags</h2>
        {flagRows.length === 0 ? (
          <div style={emptyStyle}>暂无 feature flag 数据。</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={thStyle}>Flag</th>
                  <th style={thStyle}>Enabled</th>
                  <th style={thStyle}>Risk</th>
                  <th style={thStyle}>Category</th>
                  <th style={thStyle}>Reason</th>
                </tr>
              </thead>
              <tbody>
                {flagRows.map((item) => (
                  <tr key={item.name}>
                    <td style={monoTdStyle}>{item.name}</td>
                    <td style={tdStyle}><span style={badgeStyle(!item.enabled)}>{fmt(item.enabled)}</span></td>
                    <td style={tdStyle}>{fmt(item.risk)}</td>
                    <td style={tdStyle}>{fmt(item.category)}</td>
                    <td style={tdStyle}>{fmt(item.reason)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <JsonBlock title="system_version raw" value={version || {}} />
      <JsonBlock title="feature_flags raw" value={flags || {}} />
      <JsonBlock title="healthz raw" value={healthz || {}} />
    </div>
  );
}

const pageStyle = { maxWidth: 1240, margin: "0 auto", padding: 24, color: "#0f172a" };
const sectionStyle = { marginTop: 16, padding: 14, border: "1px solid #dbeafe", borderRadius: 12, background: "#ffffff" };
const sectionTitleStyle = { margin: 0, marginBottom: 10 };
const noticeStyle = { marginTop: 12, padding: 12, border: "1px solid #bfdbfe", borderRadius: 10, background: "#eff6ff" };
const cardStyle = { padding: 12, border: "1px solid #dbeafe", borderRadius: 12, background: "#f8fafc", minHeight: 82 };
const btnStyle = { padding: "8px 12px", border: "1px solid #2563eb", borderRadius: 8, background: "#2563eb", color: "#fff", cursor: "pointer", textDecoration: "none", display: "inline-block" };
const secondaryBtnStyle = { padding: "8px 12px", border: "1px solid #cbd5e1", borderRadius: 8, background: "#fff", color: "#0f172a", cursor: "pointer", textDecoration: "none", display: "inline-block" };
const tableStyle = { width: "100%", borderCollapse: "collapse", fontSize: 13 };
const thStyle = { textAlign: "left", borderBottom: "1px solid #e5e7eb", padding: 8, background: "#f8fafc" };
const tdStyle = { borderBottom: "1px solid #e5e7eb", padding: 8, verticalAlign: "top" };
const monoTdStyle = { ...tdStyle, fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace", fontSize: 12, wordBreak: "break-all" };
const emptyStyle = { padding: 14, border: "1px dashed #cbd5e1", borderRadius: 10, background: "#f8fafc", color: "#64748b" };
const preStyle = { margin: 0, padding: 12, border: "1px solid #e2e8f0", borderRadius: 10, background: "#0f172a", color: "#dbeafe", whiteSpace: "pre-wrap", overflow: "auto", maxHeight: 460, fontSize: 12, lineHeight: 1.55 };
