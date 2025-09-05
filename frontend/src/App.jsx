// src/App.jsx
import React, { useEffect, useState } from "react";
import axios from "axios";
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import CaseEditorPage from "./pages/CaseEditorLite";

// 后端基地址：优先取环境变量，没配就用你当前后端域名
const API_BASE = import.meta.env.VITE_API_BASE || "https://pet-med-ai-backend.onrender.com";

/** ===== 把你现有的界面封装为 Home 页面，并保持原样 ===== */
function Home() {
  // ====== 登录区 ======
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const isAuthed = !!localStorage.getItem("token");

  const api = axios.create({
    baseURL: API_BASE,
    headers: isAuthed ? { Authorization: `Bearer ${localStorage.getItem("token")}` } : {},
    withCredentials: true,
  });

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const form = new FormData();
      form.append("username", email);   // OAuth2PasswordRequestForm 需要 username 字段
      form.append("password", password);
      const res = await api.post("/auth/login", form);
      localStorage.setItem("token", res.data.access_token);
      alert("登录成功");
      window.location.reload();
    } catch (err) {
      console.error(err);
      alert("登录失败，请检查账号或密码");
    }
  };

  const handleSignup = async () => {
    try {
      await api.post("/auth/signup", { email, password, full_name: "" });
      alert("注册成功，请登录");
    } catch (err) {
      console.error(err);
      alert("注册失败，邮箱可能已存在");
    }
  };

  const handleLogout = () => { localStorage.removeItem("token"); window.location.reload(); };

  // ====== 你原有的状态与逻辑（保持不变） ======
  const [chiefComplaint, setChiefComplaint] = useState("");
  const [history, setHistory] = useState("");
  const [examFindings, setExamFindings] = useState("");
  const [analysis, setAnalysis] = useState("");
  const [treatment, setTreatment] = useState("");
  const [prognosis, setPrognosis] = useState("");
  const [loadingAnalyze, setLoadingAnalyze] = useState(false);
  const [errMsg, setErrMsg] = useState("");

  const [patientName, setPatientName] = useState("");
  const [species, setSpecies] = useState("dog");
  const [sex, setSex] = useState("");
  const [ageInfo, setAgeInfo] = useState("");
  const [cases, setCases] = useState([]);
  const [loadingCases, setLoadingCases] = useState(false);
  const [loadingCreate, setLoadingCreate] = useState(false);
  const [loadingReAnalyzeId, setLoadingReAnalyzeId] = useState(null);

  useEffect(() => { fetchCases(); }, []);

  const fetchCases = async () => {
    try {
      setLoadingCases(true);
      const res = await axios.get(`${API_BASE}/cases`);
      setCases(res.data || []);
    } catch (e) {
      console.error("拉取病例失败：", e);
    } finally {
      setLoadingCases(false);
    }
  };

  const handleAnalyzeSubmit = async (e) => {
    e.preventDefault();
    setErrMsg("");
    setAnalysis(""); setTreatment(""); setPrognosis("");
    setLoadingAnalyze(true);
    try {
      const url = `${API_BASE}/analyze`;
      const res = await axios.post(url, {
        chief_complaint: chiefComplaint,
        history,
        exam_findings: examFindings,
        species,
        age_info: ageInfo,
      });
      setAnalysis(res.data.analysis || "");
      setTreatment(res.data.treatment || "");
      setPrognosis(res.data.prognosis || "");
    } catch (err) {
      console.error("Analyze error:", err);
      setErrMsg("分析请求失败，请稍后重试或检查后端日志。");
    } finally {
      setLoadingAnalyze(false);
    }
  };

  const handleCreateCase = async () => {
    if (!patientName || !chiefComplaint) {
      alert("请至少填写病例名与主诉");
      return;
    }
    try {
      setLoadingCreate(true);
      const res = await axios.post(`${API_BASE}/cases`, {
        patient_name: patientName,
        species,
        sex: sex || null,
        age_info: ageInfo || null,
        chief_complaint: chiefComplaint,
        history: history || null,
        exam_findings: examFindings || null,
      });
      await fetchCases();
      alert(`创建成功：病例ID = ${res.data.id}`);
    } catch (e) {
      console.error("创建病例失败：", e);
      alert("创建病例失败，请查看控制台或后端日志");
    } finally {
      setLoadingCreate(false);
    }
  };

  const handleReAnalyze = async (caseItem) => {
    try {
      setLoadingReAnalyzeId(caseItem.id);
      await axios.post(`${API_BASE}/cases/${caseItem.id}/analyze`, {
        chief_complaint: caseItem.chief_complaint,
        history: caseItem.history || "",
        exam_findings: caseItem.exam_findings || "",
        species: caseItem.species || "dog",
        age_info: caseItem.age_info || "",
      });
      await fetchCases();
      alert(`病例 ${caseItem.id} 已更新分析结果`);
    } catch (e) {
      console.error("病例重分析失败：", e);
      alert("病例重分析失败，请查看控制台或后端日志");
    } finally {
      setLoadingReAnalyzeId(null);
    }
  };

  return (
    <div style={{ fontFamily: "system-ui, -apple-system, Arial", padding: 24, maxWidth: 1000, margin: "0 auto" }}>
      <h1 style={{ marginTop: 0 }}>Pet Med AI — 前端联调面板</h1>

      {/* 登录区 */}
      {!isAuthed ? (
        <form onSubmit={handleLogin} style={{ display:"flex", gap:8, alignItems:"center", margin:"8px 0" }}>
          <input value={email} onChange={(e)=>setEmail(e.target.value)} placeholder="邮箱" />
          <input value={password} onChange={(e)=>setPassword(e.target.value)} placeholder="密码" type="password" />
          <button type="submit" style={btnTiny}>登录</button>
          <button type="button" onClick={handleSignup} style={btnTiny}>注册</button>
        </form>
      ) : (
        <div style={{ margin:"8px 0" }}>
          <span style={{ opacity:.7, marginRight:8 }}>已登录</span>
          <button onClick={handleLogout} style={btnTiny}>退出</button>
        </div>
      )}

      {/* ====== 病例信息（基础） ====== */}
      <section style={card}>
        <h2 style={h2}>1) 填写病例基础信息</h2>
        <div style={grid2}>
          <Field label="病例名 / 宠物名">
            <input value={patientName} onChange={(e) => setPatientName(e.target.value)} placeholder="如：乐乐 / Lucky" />
          </Field>
          <Field label="物种">
            <select value={species} onChange={(e) => setSpecies(e.target.value)}>
              <option value="dog">dog</option>
              <option value="cat">cat</option>
              <option value="other">other</option>
            </select>
          </Field>
          <Field label="性别">
            <input value={sex} onChange={(e) => setSex(e.target.value)} placeholder="M / F / 已绝育等" />
          </Field>
          <Field label="年龄信息">
            <input value={ageInfo} onChange={(e) => setAgeInfo(e.target.value)} placeholder="如 4y / 6m" />
          </Field>
        </div>
      </section>

      {/* ====== 分析表单 ====== */}
      <section style={card}>
        <h2 style={h2}>2) 主诉 / 既往史 / 体检化验 & 即时分析</h2>
        <form onSubmit={handleAnalyzeSubmit}>
          <Field label="主诉（必填）">
            <textarea value={chiefComplaint} onChange={(e) => setChiefComplaint(e.target.value)} required rows={3} />
          </Field>
          <Field label="既往史">
            <textarea value={history} onChange={(e) => setHistory(e.target.value)} rows={3} />
          </Field>
          <Field label="体检/化验摘要">
            <textarea value={examFindings} onChange={(e) => setExamFindings(e.target.value)} rows={3} />
          </Field>
          <div style={{ display: "flex", gap: 12, marginTop: 8 }}>
            <button type="submit" disabled={loadingAnalyze} style={btn}>
              {loadingAnalyze ? "分析中…" : "提交分析（不入库）"}
            </button>
            <button type="button" onClick={handleCreateCase} disabled={loadingCreate} style={btnSecondary}>
              {loadingCreate ? "保存中…" : "保存为病例（入库）"}
            </button>
            <Link to="/cases/new/edit" style={{ ...btnSecondary, textDecoration:"none", display:"inline-block" }}>
              新建病例（进入编辑器）
            </Link>
          </div>
        </form>

        {errMsg && <p style={{ color: "crimson", marginTop: 8 }}>{errMsg}</p>}

        {(analysis || treatment || prognosis) && (
          <div style={{ marginTop: 16 }}>
            <h3>即时分析结果</h3>
            {analysis && <Block title="分析">{analysis}</Block>}
            {treatment && <Block title="治疗建议">{treatment}</Block>}
            {prognosis && <Block title="预后">{prognosis}</Block>}
          </div>
        )}
      </section>

      {/* ====== 病例列表 ====== */}
      <section style={card}>
        <h2 style={h2}>3) 病例列表</h2>
        <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
          <button onClick={fetchCases} disabled={loadingCases} style={btn}>
            {loadingCases ? "刷新中…" : "刷新列表"}
          </button>
          <Link to="/cases/new/edit" style={{ ...btnSecondary, textDecoration:"none", display:"inline-block" }}>
            新建病例（进入编辑器）
          </Link>
        </div>

        {cases.length === 0 ? (
          <p style={{ opacity: 0.7 }}>暂无病例。</p>
        ) : (
          <table style={table}>
            <thead>
              <tr>
                <th>ID</th>
                <th>病例名</th>
                <th>物种</th>
                <th>主诉</th>
                <th>已存分析</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => (
                <tr key={c.id}>
                  <td>{c.id}</td>
                  <td>{c.patient_name}</td>
                  <td>{c.species}</td>
                  <td title={c.chief_complaint} style={{ maxWidth: 220, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {c.chief_complaint}
                  </td>
                  <td style={{ color: c.analysis ? "#16a34a" : "#999" }}>
                    {c.analysis ? "✓" : "—"}
                  </td>
                  <td>
                    <div style={{ display: "inline-flex", gap: 8 }}>
                      <Link
                        to={`/cases/${c.id}/edit`}
                        style={{ ...btnTiny, textDecoration: "none", display: "inline-block" }}
                      >
                        编辑
                      </Link>
                      <button
                        type="button"
                        style={{ ...btnTiny }}
                        onClick={() => handleReAnalyze(c)}
                        disabled={loadingReAnalyzeId === c.id}
                        title="用当前字段重新分析并写回病例"
                      >
                        {loadingReAnalyzeId === c.id ? "分析中…" : "重分析并写回"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <p style={{ marginTop: 24, opacity: 0.7, fontSize: 12 }}>
        后端：{API_BASE}
      </p>
    </div>
  );
}

/** ===== 路由容器 ===== */
export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/cases/new/edit" element={<CaseEditorPage />} />
        <Route path="/cases/:id/edit" element={<CaseEditorPage />} />
        <Route path="*" element={<div style={{ padding: 24 }}>页面不存在（404）。</div>} />
      </Routes>
    </Router>
  );
}

/* ----------------- 小组件 & 样式 ----------------- */
function Field({ label, children }) {
  return (
    <label style={{ display: "block", marginTop: 12 }}>
      <div style={{ fontSize: 13, opacity: 0.8, marginBottom: 4 }}>{label}</div>
      {children}
    </label>
  );
}
function Block({ title, children }) {
  return (
    <div style={{ background: "#f6f8fa", padding: 12, borderRadius: 8, whiteSpace: "pre-wrap", marginTop: 8 }}>
      <div style={{ fontWeight: 600, marginBottom: 6 }}>{title}</div>
      {children}
    </div>
  );
}
const h2 = { margin: "0 0 12px" };
const card = { background: "#fff", border: "1px solid #e5e7eb", borderRadius: 12, padding: 16, marginTop: 16 };
const grid2 = { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 };
const btn = { padding: "8px 14px", borderRadius: 8, border: "1px solid #0ea5e9", background: "#0ea5e9", color: "#fff", cursor: "pointer" };
const btnSecondary = { padding: "8px 14px", borderRadius: 8, border: "1px solid #64748b", background: "#fff", color: "#111", cursor: "pointer" };
const btnTiny = { padding: "6px 10px", borderRadius: 8, border: "1px solid #64748b", background: "#fff", color: "#111", cursor: "pointer", fontSize: 12 };
const table = { width: "100%", borderCollapse: "collapse" };
