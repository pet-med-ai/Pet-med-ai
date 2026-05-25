// src/pages/CaseDetail.jsx
import React, { useEffect, useMemo, useState } from "react";
import { useParams, Link, useNavigate, useLocation } from "react-router-dom";
import api from "../api";

export default function CaseDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const autoPrint = Boolean(location.state?.autoPrint);

  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);

  // 拉取详情
  useEffect(() => {
    let stop = false;
    (async () => {
      try {
        const res = await api.get(`/api/cases/${id}`);
        if (!stop) setData(res.data);
      } catch (e) {
        setErr(String(e));
      } finally {
        if (!stop) setLoading(false);
      }
    })();
    return () => { stop = true; };
  }, [id]);

  // 自动打印（来自列表 state 的 autoPrint）
  useEffect(() => {
    if (!loading && data && autoPrint) {
      const t = setTimeout(() => {
        window.print();
        if (history.replaceState) {
          history.replaceState(null, "", window.location.pathname + window.location.search);
        }
      }, 80);
      return () => clearTimeout(t);
    }
  }, [loading, data, autoPrint]);

  const doDelete = async () => {
    if (!confirm("确定删除该病例？此操作不可恢复。")) return;
    try {
      setDeleting(true);
      await api.delete(`/api/cases/${id}`);
      alert("已删除");
      navigate("/");
    } catch (e) {
      alert("删除失败：" + e);
    } finally {
      setDeleting(false);
    }
  };

  const doPrint = () => setTimeout(() => window.print(), 40);

  const derived = useMemo(() => {
    if (!data) return {};
    return {
      patientName: data.patient_name || data?.patient?.name || "—",
      species: data.species || data?.patient?.species || "—",
      sex: data.sex || "—",
      ageInfo: data.age_info || "—",
      breed: data.breed || "—",
      weight: data.weight || "—",
      coatColor: data.coat_color || "—",
      ownerName: data.owner_name || "—",
      ownerPhone: data.owner_phone || "—",
      riskLevel: extractRiskLevel(data),
      sourceSessionId: extractSourceSessionId(data.exam_findings),
      isDynamicConsultCase: isDynamicConsultCase(data),
    };
  }, [data]);

  if (loading) return <div style={{ padding: 24 }}>加载中…</div>;
  if (err) return <div style={{ padding: 24, color: "crimson" }}>加载失败：{err}</div>;
  if (!data) return <div style={{ padding: 24 }}>未找到病例</div>;

  return (
    <div
      lang="zh-CN"
      translate="no"
      className="notranslate case-detail-root"
      style={{ padding: 24, maxWidth: 980, margin: "0 auto", fontFamily: "system-ui,-apple-system,Arial" }}
    >
      <style>{css}</style>

      <div className="screen-toolbar" style={toolbar}>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <Link to="/" style={btn}>返回首页</Link>
          <Link to={`/cases/${data.id}/edit`} style={btnPrimary}>编辑</Link>
          <button onClick={doPrint} style={btnSecondary}>打印病例</button>
          <button onClick={doDelete} disabled={deleting} style={btnDanger}>
            {deleting ? "删除中…" : "删除"}
          </button>
        </div>
        <div style={{ opacity: .6, fontSize: 12 }}>
          后端：{import.meta.env.VITE_API_BASE}
        </div>
      </div>

      <div className="print-header">
        <div style={{ fontSize: 20, fontWeight: 700 }}>病例报告 / Case Report</div>
        <div style={{ fontSize: 12, opacity: .8 }}>
          ID: {data.id}　|　导出时间: {formatDateTime(new Date())}
        </div>
      </div>

      <header className="case-hero print-block">
        <div>
          <div className="eyebrow">Pet Med AI 病例记录</div>
          <h1 style={{ margin: "4px 0 8px" }}>病例详情 #{data.id}</h1>
          <div className="muted">
            {derived.patientName} · {derived.species}
            {derived.sex !== "—" ? ` · ${derived.sex}` : ""}
            {derived.ageInfo !== "—" ? ` · ${derived.ageInfo}` : ""}
          </div>
        </div>
        <RiskBadge value={derived.riskLevel} />
      </header>

      {derived.isDynamicConsultCase && (
        <div className="notice print-block">
          <strong>来源：</strong>动态问诊保存为病例
          {derived.sourceSessionId && (
            <>
              <span className="notice-session">会话 ID：{derived.sourceSessionId}</span>
              <Link
                className="source-consult-link screen-only"
                to={`/?restore_session_id=${encodeURIComponent(derived.sourceSessionId)}`}
              >
                恢复来源问诊
              </Link>
            </>
          )}
        </div>
      )}

      <Section title="一、基础信息">
        <InfoGrid
          items={[
            ["病例名 / 宠物名", derived.patientName],
            ["物种", derived.species],
            ["性别", derived.sex],
            ["年龄信息", derived.ageInfo],
            ["品种 / 宠物信息", derived.breed],
            ["体重", derived.weight],
            ["毛色", derived.coatColor],
            ["主人姓名", derived.ownerName],
            ["主人电话", derived.ownerPhone],
          ]}
        />
      </Section>

      <Section title="二、主诉">
        <TextCard>{data.chief_complaint}</TextCard>
      </Section>

      <Section title="三、动态问诊追问记录 / 病史">
        <DynamicHistory value={data.history} />
      </Section>

      <Section title="四、体检 / 化验 / 来源信息">
        <TextCard>{data.exam_findings}</TextCard>
      </Section>

      <Section title="五、AI 分析">
        <TextCard>{data.analysis}</TextCard>
      </Section>

      <Section title="六、治疗建议">
        <TextCard>{data.treatment}</TextCard>
      </Section>

      <Section title="七、风险提示 / 后续随访">
        <TextCard>{data.prognosis}</TextCard>
      </Section>

      {Array.isArray(data.attachments) && data.attachments.length > 0 && (
        <Section title="八、附件">
          <ul className="attach-list">
            {data.attachments.map((a) => (
              <li key={a.id}>
                <span className="attach-name">{a.name}</span>
                {a.url && (
                  <a className="no-underline" href={a.url} target="_blank" rel="noreferrer">
                    {a.url}
                  </a>
                )}
              </li>
            ))}
          </ul>
        </Section>
      )}

      <div className="disclaimer print-block">
        AI 结果仅用于辅助分诊与病例整理，不能替代兽医临床诊断。高风险、持续恶化或疑似急症时，应立即进行临床检查与处置。
      </div>

      <div className="print-footer">由 Pet Med AI 生成 · {formatDateTime(new Date())}</div>
    </div>
  );
}

/* ===== UI 组件 ===== */
function Section({ title, children }) {
  return (
    <section className="print-block section-card">
      <h3 className="print-section-title">{title}</h3>
      {children}
    </section>
  );
}

function InfoGrid({ items }) {
  return (
    <div className="info-grid">
      {items.map(([label, value]) => (
        <div className="info-item" key={label}>
          <div className="info-label">{label}</div>
          <div className="info-value">{safeText(value)}</div>
        </div>
      ))}
    </div>
  );
}

function TextCard({ children }) {
  return (
    <div className="text-card">
      <div className="text-body">{children ? String(children) : "—"}</div>
    </div>
  );
}

function RiskBadge({ value }) {
  const normalized = normalizeRisk(value);
  return (
    <div className={`risk-badge risk-${normalized.key}`}>
      <div className="risk-label">风险等级</div>
      <div className="risk-value">{normalized.label}</div>
    </div>
  );
}

function DynamicHistory({ value }) {
  const text = value ? String(value) : "";
  const qaItems = parseDynamicHistory(text);

  if (qaItems.length === 0) {
    return <TextCard>{text}</TextCard>;
  }

  return (
    <div className="qa-list">
      {qaItems.map((item) => (
        <div className="qa-item" key={item.index}>
          <div className="qa-index">第 {item.index} 轮追问</div>
          <div className="qa-row">
            <span className="qa-tag">问</span>
            <span>{item.question || "未记录"}</span>
          </div>
          <div className="qa-row">
            <span className="qa-tag answer">答</span>
            <span>{item.answer || "未记录"}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ===== 工具函数 ===== */
function safeText(v) { return v ? String(v) : "—"; }

function pad(n) { return n < 10 ? `0${n}` : `${n}`; }

function formatDateTime(d) {
  const y = d.getFullYear(); const m = pad(d.getMonth() + 1); const day = pad(d.getDate());
  const hh = pad(d.getHours()); const mm = pad(d.getMinutes());
  return `${y}-${m}-${day} ${hh}:${mm}`;
}

function normalizeRisk(v) {
  const text = String(v || "").trim();
  if (/高|high/i.test(text)) return { key: "high", label: "高风险" };
  if (/中|medium/i.test(text)) return { key: "medium", label: "中风险" };
  if (/低|low/i.test(text)) return { key: "low", label: "低风险" };
  return { key: "unknown", label: text || "未记录" };
}

function extractRiskLevel(data) {
  const raw = [data?.analysis, data?.prognosis].filter(Boolean).join("\n");
  const match = raw.match(/风险(?:等级|提示)?[:：]\s*([^\n]+)/);
  if (match?.[1]) return match[1].trim();
  return data?.risk_level || "未记录";
}

function extractSourceSessionId(value) {
  const text = String(value || "");
  const match = text.match(/原始会话[:：]\s*([A-Za-z0-9_-]+)/);
  return match?.[1] || "";
}

function isDynamicConsultCase(data) {
  const combined = [data?.history, data?.exam_findings, data?.analysis, data?.prognosis]
    .filter(Boolean)
    .join("\n");
  return /动态问诊|原始会话|风险等级|后续追问/.test(combined);
}

function parseDynamicHistory(value) {
  const lines = String(value || "").split(/\r?\n/);
  const items = [];
  let current = null;

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line || line.includes("动态问诊追问记录")) continue;

    const q = line.match(/^(\d+)[.、]\s*问[:：]\s*(.*)$/);
    if (q) {
      if (current) items.push(current);
      current = {
        index: Number(q[1]) || items.length + 1,
        question: q[2] || "",
        answer: "",
      };
      continue;
    }

    const a = line.match(/^答[:：]\s*(.*)$/);
    if (a && current) {
      current.answer = a[1] || "";
      continue;
    }

    if (current) {
      if (!current.answer) {
        current.question = [current.question, line].filter(Boolean).join("\n");
      } else {
        current.answer = [current.answer, line].filter(Boolean).join("\n");
      }
    }
  }

  if (current) items.push(current);
  return items;
}

/* ===== 屏幕工具栏样式 ===== */
const toolbar = {
  display: "flex", justifyContent: "space-between", alignItems: "center",
  gap: 12, marginBottom: 12, flexWrap: "wrap",
};

const btn = {
  padding: "8px 14px",
  borderRadius: 8,
  border: "1px solid #64748b",
  background: "#fff",
  color: "#111",
  textDecoration: "none",
  display: "inline-block",
  cursor: "pointer",
};

const btnPrimary = { ...btn, border: "1px solid #0ea5e9", background: "#0ea5e9", color: "#fff" };
const btnSecondary = { ...btn, border: "1px solid #111", background: "#fff" };
const btnDanger = { ...btn, border: "1px solid #ef4444", background: "#ef4444", color: "#fff" };

/* ===== 打印友好样式 ===== */
const css = `
  @page { size: A4; margin: 14mm 14mm 16mm 14mm; }
  body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  * { box-sizing: border-box; }

  @media print {
    .screen-toolbar, .screen-only { display: none !important; }
    a { color: #000 !important; text-decoration: none !important; }
    .no-underline { text-decoration: none !important; color: #000 !important; }
    .print-header, .print-footer { position: fixed; left: 0; right: 0; }
    .print-header { top: 0; padding: 4mm 14mm; border-bottom: 1px solid #ddd; background: #fff; }
    .print-footer { bottom: 0; padding: 4mm 14mm; border-top: 1px solid #ddd; font-size: 11px; color: #555; background: #fff; }
    body { margin: 0; }
    .print-block, h1 { page-break-inside: avoid; }
    .case-detail-root { padding-top: 24mm !important; padding-bottom: 18mm !important; }
    .section-card, .text-card, .qa-item, .notice, .disclaimer { box-shadow: none !important; }
  }

  h1 { font-size: 24px; line-height: 1.25; }

  .print-header, .print-footer { display: none; }
  @media print {
    .print-header, .print-footer { display: block; }
  }

  .case-hero {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    align-items: flex-start;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 16px;
    background: linear-gradient(180deg, #f8fafc, #fff);
    margin-bottom: 12px;
  }

  .eyebrow {
    color: #0369a1;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: .03em;
  }

  .muted { color: #64748b; font-size: 14px; }

  .risk-badge {
    min-width: 112px;
    border-radius: 12px;
    padding: 10px 12px;
    border: 1px solid #e5e7eb;
    background: #f8fafc;
    text-align: center;
  }
  .risk-label { font-size: 12px; opacity: .75; margin-bottom: 3px; }
  .risk-value { font-size: 18px; font-weight: 800; }
  .risk-high { border-color: #fecaca; background: #fef2f2; color: #991b1b; }
  .risk-medium { border-color: #fed7aa; background: #fff7ed; color: #9a3412; }
  .risk-low { border-color: #bbf7d0; background: #f0fdf4; color: #166534; }
  .risk-unknown { color: #334155; }

  .notice {
    border: 1px solid #bfdbfe;
    background: #eff6ff;
    border-radius: 12px;
    padding: 10px 12px;
    margin: 12px 0;
    color: #1e3a8a;
  }
  .notice-session {
    display: inline-block;
    margin-left: 12px;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 12px;
  }
  .source-consult-link {
    display: inline-block;
    margin-left: 12px;
    padding: 4px 9px;
    border-radius: 999px;
    border: 1px solid #2563eb;
    background: #fff;
    color: #1d4ed8;
    font-size: 12px;
    font-weight: 700;
    text-decoration: none;
  }
  .source-consult-link:hover {
    background: #dbeafe;
  }

  .section-card {
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 14px;
    margin: 12px 0;
    background: #fff;
    box-shadow: 0 1px 2px rgba(15,23,42,.04);
  }

  .print-section-title {
    font-size: 16px;
    font-weight: 800;
    margin: 0 0 10px;
    color: #0f172a;
  }

  .info-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    overflow: hidden;
  }
  .info-item { padding: 10px 12px; border-right: 1px solid #e5e7eb; background: #fff; }
  .info-item:last-child { border-right: 0; }
  .info-label { font-size: 12px; color: #64748b; margin-bottom: 4px; }
  .info-value { font-weight: 700; color: #111827; word-break: break-word; }

  .text-card {
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    background: #f8fafc;
    padding: 12px;
  }
  .text-body {
    white-space: pre-wrap;
    line-height: 1.7;
    color: #111827;
  }

  .qa-list { display: grid; gap: 10px; }
  .qa-item {
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 12px;
    background: #f8fafc;
  }
  .qa-index {
    font-weight: 800;
    margin-bottom: 8px;
    color: #0f172a;
  }
  .qa-row {
    display: flex;
    gap: 8px;
    align-items: flex-start;
    line-height: 1.65;
    margin: 4px 0;
  }
  .qa-tag {
    flex: 0 0 auto;
    min-width: 26px;
    text-align: center;
    border-radius: 999px;
    background: #dbeafe;
    color: #1d4ed8;
    font-weight: 800;
    font-size: 13px;
  }
  .qa-tag.answer {
    background: #dcfce7;
    color: #15803d;
  }

  .disclaimer {
    color: #64748b;
    font-size: 12px;
    line-height: 1.6;
    margin: 16px 0;
    padding: 10px 12px;
    border: 1px dashed #cbd5e1;
    border-radius: 12px;
    background: #f8fafc;
  }

  .attach-list { padding-left: 18px; margin: 6px 0; }
  .attach-name { font-weight: 600; margin-right: 6px; }

  @media (max-width: 720px) {
    .case-hero { flex-direction: column; }
    .info-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .info-item:nth-child(2) { border-right: 0; }
  }
`;
