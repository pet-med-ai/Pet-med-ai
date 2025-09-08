// src/pages/CaseDetail.jsx
import React, { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import api from "../api"; // 统一使用全局 axios 实例（自动带 token）

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
      const res = await api.delete(`/api/cases/${id}`);
      if (!res.ok) throw new Error(await res.text());
      alert("已删除");
      navigate("/");
    } catch (e) {
      alert("删除失败：" + e);
    } finally {
      setDeleting(false);
    }
  };

  if (loading) return <div style={{ padding: 24 }}>加载中…</div>;
  if (err) return <div style={{ padding: 24, color: "crimson" }}>加载失败：{err}</div>;
  if (!data) return <div style={{ padding: 24 }}>未找到病例</div>;

  return (
    <div style={{ padding: 24, maxWidth: 960, margin: "0 auto", fontFamily: "system-ui,-apple-system,Arial" }}>
      <h1 style={{ marginTop: 0 }}>病例详情 #{data.id}</h1>

      <div style={row}><b>病例名</b><span>{data.patient_name || data?.patient?.name || "-"}</span></div>
      <div style={row}><b>物种</b><span>{data.species || data?.patient?.species || "-"}</span></div>
      <div style={row}><b>主诉</b><span>{data.chief_complaint || "-"}</span></div>
      <div style={row}><b>既往史</b><span style={{ whiteSpace: "pre-wrap" }}>{data.history || "-"}</span></div>
      <div style={row}><b>体检/化验摘要</b><span style={{ whiteSpace: "pre-wrap" }}>{data.exam_findings || "-"}</span></div>

      {(data.analysis || data.treatment || data.prognosis) && (
        <div style={{ marginTop: 16, background: "#f6f8fa", border: "1px solid #e5e7eb", borderRadius: 12, padding: 16 }}>
          <h3 style={{ marginTop: 0 }}>分析结果</h3>
          {data.analysis && (<div style={{ marginTop: 8 }}><b>分析：</b><div style={{ whiteSpace: "pre-wrap" }}>{data.analysis}</div></div>)}
          {data.treatment && (<div style={{ marginTop: 8 }}><b>治疗建议：</b><div style={{ whiteSpace: "pre-wrap" }}>{data.treatment}</div></div>)}
          {data.prognosis && (<div style={{ marginTop: 8 }}><b>预后：</b><div style={{ whiteSpace: "pre-wrap" }}>{data.prognosis}</div></div>)}
        </div>
      )}

      <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
        <Link to={`/cases/${data.id}/edit`} style={btnPrimary}>编辑</Link>
        <button onClick={doDelete} disabled={deleting} style={btnDanger}>
          {deleting ? "删除中…" : "删除"}
        </button>
        <Link to="/" style={btn}>返回首页</Link>
      </div>
    </div>
  );
}

const row = {
  display: "grid",
  gridTemplateColumns: "120px 1fr",
  gap: 12,
  padding: "8px 0",
  borderBottom: "1px solid #eee"
};
const btn = {
  padding: "8px 14px",
  borderRadius: 8,
  border: "1px solid #64748b",
  background: "#fff",
  color: "#111",
  textDecoration: "none",
  display: "inline-block"
};
const btnPrimary = { ...btn, border: "1px solid #0ea5e9", background: "#0ea5e9", color: "#fff" };
const btnDanger = { ...btn, border: "1px solid #ef4444", background: "#ef4444", color: "#fff" };
