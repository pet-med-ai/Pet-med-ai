// src/pages/CaseDetail.jsx
import React, { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import api from "../api";

export default function CaseDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);

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

  const doPrint = () => {
    // 为了防止图片没加载完就打印，给一点延迟（有图片时可按需调大）
    setTimeout(() => window.print(), 80);
  };

  if (loading) return <div style={{ padding: 24 }}>加载中…</div>;
  if (err) return <div style={{ padding: 24, color: "crimson" }}>加载失败：{err}</div>;
  if (!data) return <div style={{ padding: 24 }}>未找到病例</div>;

  // 简单的字段兜底
  const patientName = data.patient_name || data?.patient?.name || "-";
  const species = data.species || data?.patient?.species || "-";

  return (
    <div style={{ padding: 24, maxWidth: 940, margin: "0 auto", fontFamily: "system-ui,-apple-system,Arial" }}>
      {/* 打印专用样式 */}
      <style>{css}</style>

      {/* 顶部工具栏（仅屏幕显示，打印隐藏） */}
      <div className="screen-toolbar" style={toolbar}>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <Link to="/" style={btn}>返回首页</Link>
          <Link to={`/cases/${data.id}/edit`} style={btnPrimary}>编辑</Link>
          <button onClick={doPrint} style={btnSecondary}>打印（或按 ⌘/Ctrl+P）</button>
          <button onClick={doDelete} disabled={deleting} style={btnDanger}>
            {deleting ? "删除中…" : "删除"}
          </button>
        </div>
        <div style={{ opacity: .6, fontSize: 12 }}>
          后端：{import.meta.env.VITE_API_BASE}
        </div>
      </div>

      {/* 打印页眉（仅打印显示） */}
      <div className="print-header">
        <div style={{ fontSize: 20, fontWeight: 700 }}>病例报告 / Case Report</div>
        <div style={{ fontSize: 12, opacity: .8 }}>
          ID: {data.id}　|　导出时间: {formatDateTime(new Date())}
        </div>
      </div>

      {/* 标题（屏幕/打印都显示） */}
      <h1 style={{ margin: "8px 0 12px" }}>病例详情 #{data.id}</h1>

      {/* 基本信息 */}
      <section className="print-block">
        <h3 className="print-section-title">基本信息</h3>
        <table className="kv">
          <tbody>
            <tr><th>病例名</th><td>{patientName}</td><th>物种</th><td>{species}</td></tr>
            <tr><th>主诉</th><td colSpan={3}>{safeText(data.chief_complaint)}</td></tr>
            <tr><th>既往史</th><td colSpan={3}>{safeMulti(data.history)}</td></tr>
            <tr><th>体检/化验摘要</th><td colSpan={3}>{safeMulti(data.exam_findings)}</td></tr>
          </tbody>
        </table>
      </section>

      {/* 分析结果 */}
      {(data.analysis || data.treatment || data.prognosis) && (
        <section className="print-block">
          <h3 className="print-section-title">分析结果</h3>
          {data.analysis && (
            <div className="card">
              <div className="card-title">分析</div>
              <div className="card-body">{safeMulti(data.analysis)}</div>
            </div>
          )}
          {data.treatment && (
            <div className="card">
              <div className="card-title">治疗建议</div>
              <div className="card-body">{safeMulti(data.treatment)}</div>
            </div>
          )}
          {data.prognosis && (
            <div className="card">
              <div className="card-title">预后</div>
              <div className="card-body">{safeMulti(data.prognosis)}</div>
            </div>
          )}
        </section>
      )}

      {/* 附件（如果你的后端返回 attachments，可打印为清单） */}
      {Array.isArray(data.attachments) && data.attachments.length > 0 && (
        <section className="print-block">
          <h3 className="print-section-title">附件</h3>
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
        </section>
      )}

      {/* 打印页脚（仅打印显示） */}
      <div className="print-footer">
        由 Pet Med AI 生成 · {formatDateTime(new Date())}
      </div>
    </div>
  );
}

/* ===== 帮助函数 & 样式 ===== */
function safeText(v) {
  return v ? String(v) : "—";
}
function safeMulti(v) {
  return <div style={{ whiteSpace: "pre-wrap" }}>{v || "—"}</div>;
}
function pad(n) { return n < 10 ? `0${n}` : `${n}`; }
function formatDateTime(d) {
  const y = d.getFullYear();
  const m = pad(d.getMonth() + 1);
  const day = pad(d.getDate());
  const hh = pad(d.getHours());
  const mm = pad(d.getMinutes());
  return `${y}-${m}-${day} ${hh}:${mm}`;
}

/* ---- 屏幕按钮样式 ---- */
const toolbar = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: 12,
  marginBottom: 12,
  flexWrap: "wrap",
};
const btn = { padding: "8px 14px", borderRadius: 8, border: "1px solid #64748b", background: "#fff", color: "#111", textDecoration: "none", display: "inline-block", cursor: "pointer" };
const btnPrimary = { ...btn, border: "1px solid #0ea5e9", background: "#0ea5e9", color: "#fff" };
const btnSecondary = { ...btn, border: "1px solid #111", background: "#fff" };
const btnDanger = { ...btn, border: "1px solid #ef4444", background: "#ef4444", color: "#fff" };

/* ---- 打印友好样式（屏幕也适用的基础样式 + @media print） ---- */
const css = `
  /* 全局 */
  @page { size: A4; margin: 14mm 14mm 16mm 14mm; }
  body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  * { box-sizing: border-box; }

  /* 屏幕工具栏在打印时隐藏 */
  @media print {
    .screen-toolbar { display: none !important; }
    a { color: #000 !important; text-decoration: none !important; }
    .no-underline { text-decoration: none !important; color: #000 !important; }
    .print-header, .print-footer { position: fixed; left: 0; right: 0; }
    .print-header { top: 0; padding: 4mm 14mm; border-bottom: 1px solid #ddd; }
    .print-footer { bottom: 0; padding: 4mm 14mm; border-top: 1px solid #ddd; font-size: 11px; color: #555; }
    /* 让正文避开页眉页脚 */
    body { margin: 0; }
    .print-block, h1 { page-break-inside: avoid; }
  }

  /* 标题样式 */
  h1 { font-size: 22px; margin: 6px 0 12px 0; }
  .print-section-title { font-size: 16px; font-weight: 600; margin: 12px 0 8px; }

  /* 关键值表 */
  table.kv { width: 100%; border-collapse: collapse; border: 1px solid #e5e7eb; }
  table.kv th, table.kv td { border: 1px solid #e5e7eb; padding: 8px 10px; vertical-align: top; }
  table.kv th { width: 120px; background: #f8fafc; text-align: left; font-weight: 600; }

  /* 卡片 */
  .card { border: 1px solid #e5e7eb; border-radius: 10px; margin: 10px 0; }
  .card-title { font-weight: 600; padding: 8px 12px; background: #f8fafc; border-bottom: 1px solid #e5e7eb; }
  .card-body { padding: 10px 12px; white-space: pre-wrap; }

  /* 附件列表 */
  .attach-list { padding-left: 18px; margin: 6px 0; }
  .attach-name { font-weight: 600; margin-right: 6px; }
`;
