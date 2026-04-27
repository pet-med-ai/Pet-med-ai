import React, { useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

function normalizePath(path) {
  if (!Array.isArray(path)) return [];
  return path.map((x) => String(x || "").trim()).filter(Boolean);
}

export default function AIPetConsultBox({ onResult, onTreePathLocate }) {
  const [text, setText] = useState("狗狗两天不吃东西，呕吐，精神差");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const treePathText = useMemo(
    () => (result?.tree_best_path || []).join(" → "),
    [result]
  );

  const submit = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/ai/consult`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const normalizedPath = normalizePath(data?.tree_best_path);
      setResult(data);
      onResult?.(data);
      onTreePathLocate?.(normalizedPath);
    } catch (e) {
      setError(`调用失败：${String(e)}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section style={{ border: "1px solid #e5e7eb", borderRadius: 12, padding: 12 }}>
      <h3 style={{ marginTop: 0 }}>AI 半自动问诊</h3>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={3}
        style={{ width: "100%" }}
      />
      <div style={{ marginTop: 8 }}>
        <button onClick={submit} disabled={loading}>
          {loading ? "分析中…" : "调用 /ai/consult"}
        </button>
      </div>
      {error && <p style={{ color: "crimson" }}>{error}</p>}
      {result && (
        <div style={{ marginTop: 10, fontSize: 14 }}>
          <div><b>risk_level:</b> {result.risk_level}</div>
          <div><b>route_to:</b> {result.route_to}</div>
          <div><b>tree_best_path:</b> {treePathText}</div>
        </div>
      )}
    </section>
  );
}
