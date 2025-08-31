import React, { useState } from "react";
import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE || "https://pet-med-ai-backend.onrender.com";

export default function App() {
  const [chiefComplaint, setChiefComplaint] = useState("");
  const [history, setHistory] = useState("");
  const [examFindings, setExamFindings] = useState("");
  const [analysis, setAnalysis] = useState("");
  const [treatment, setTreatment] = useState("");
  const [prognosis, setPrognosis] = useState("");
  const [loading, setLoading] = useState(false);
  const [errMsg, setErrMsg] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrMsg("");
    setLoading(true);
    try {
      const url = `${API_BASE}/analyze`;
      const res = await axios.post(url, {
        chief_complaint: chiefComplaint,
        history,
        exam_findings: examFindings,
      });
      setAnalysis(res.data.analysis || "");
      setTreatment(res.data.treatment || "");
      setPrognosis(res.data.prognosis || "");
    } catch (err) {
      console.error("Analyze error:", err);
      setErrMsg("分析请求失败，请稍后重试或检查后端日志。");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ fontFamily: "system-ui, -apple-system, Arial", padding: 24 }}>
      <h1 style={{ marginTop: 0 }}>Pet Med AI — Frontend</h1>
      <p>Vite + React scaffold is working.</p>

      <form onSubmit={handleSubmit} style={{ maxWidth: 720 }}>
        <label style={{ display: "block", marginTop: 12 }}>主诉</label>
        <textarea
          value={chiefComplaint}
          onChange={(e) => setChiefComplaint(e.target.value)}
          required
          style={{ width: "100%", height: 80 }}
        />

        <label style={{ display: "block", marginTop: 12 }}>既往史</label>
        <textarea
          value={history}
          onChange={(e) => setHistory(e.target.value)}
          style={{ width: "100%", height: 80 }}
        />

        <label style={{ display: "block", marginTop: 12 }}>体检/化验摘要</label>
        <textarea
          value={examFindings}
          onChange={(e) => setExamFindings(e.target.value)}
          style={{ width: "100%", height: 80 }}
        />

        <div style={{ marginTop: 16 }}>
          <button type="submit" disabled={loading} style={{ padding: "8px 16px" }}>
            {loading ? "分析中…" : "提交分析"}
          </button>
          <span style={{ marginLeft: 12, opacity: 0.7, fontSize: 12 }}>
            后端：{API_BASE}/analyze
          </span>
        </div>
      </form>

      {errMsg && (
        <p style={{ color: "crimson", marginTop: 12 }}>
          {errMsg}
        </p>
      )}

      {analysis && (
        <div style={{ marginTop: 24 }}>
          <h2>分析结果</h2>
          <pre style={{ whiteSpace: "pre-wrap" }}>{analysis}</pre>

          <h3>治疗建议</h3>
          <pre style={{ whiteSpace: "pre-wrap" }}>{treatment}</pre>

          <h3>预后</h3>
          <pre style={{ whiteSpace: "pre-wrap" }}>{prognosis}</pre>
        </div>
      )}
    </div>
  );
}
