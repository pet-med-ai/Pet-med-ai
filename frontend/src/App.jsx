// src/App.jsx
import React, { useEffect, useState } from "react";
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import api from "./api";
import CaseDetail from "./pages/CaseDetail";
import CaseEditorPage from "./pages/CaseEditorLite";

/** ===== 首页 Home 组件 ===== */
function Home() {
  // ===== 登录区 =====
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const isAuthed = !!localStorage.getItem("token");

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const form = new FormData();
      form.append("username", email);
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

  // ===== 分析区状态 =====
  const [chiefComplaint, setChiefComplaint] = useState("");
  const [history, setHistory] = useState("");
  const [examFindings, setExamFindings] = useState("");
  const [analysis, setAnalysis] = useState("");
  const [treatment, setTreatment] = useState("");
  const [prognosis, setPrognosis] = useState("");
  
  const [result, setResult] = useState(null);
  const [consultSessionId, setConsultSessionId] = useState(null);
  const [sessionInput, setSessionInput] = useState("");
  const [savedSessionId, setSavedSessionId] = useState(() => localStorage.getItem("consult_session_id") || "");
  const [loadingSession, setLoadingSession] = useState(false);
  const [sessionHistory, setSessionHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [consultAnswers, setConsultAnswers] = useState([]);
  const [followupAnswer, setFollowupAnswer] = useState("");
  const [loadingAnalyze, setLoadingAnalyze] = useState(false);
  const [loadingFollowup, setLoadingFollowup] = useState(false);
  const [errMsg, setErrMsg] = useState("");

  const [patientName, setPatientName] = useState("");
  const [species, setSpecies] = useState("dog");
  const [sex, setSex] = useState("");
  const [ageInfo, setAgeInfo] = useState("");

  // ===== 列表 搜索 + 分页 =====
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [cases, setCases] = useState([]);
  const [total, setTotal] = useState(0);
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const [loadingCases, setLoadingCases] = useState(false);
  const [loadingCreate, setLoadingCreate] = useState(false);
  const [loadingReAnalyzeId, setLoadingReAnalyzeId] = useState(null);

  // ===== 批量选择 / 导出 / 批量删除 =====
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [bulkDeleting, setBulkDeleting] = useState(false);

  // ===== 单条删除 / 撤销 =====
  const [deletingId, setDeletingId] = useState(null);     // 正在删除的行
  const [lastDeleted, setLastDeleted] = useState(null);   // { id, data } 最近删除的完整对象（用于撤销）

  const toggleOne = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };
  const selectAllCurrentPage = () => setSelectedIds(new Set(cases.map((c) => c.id)));
  const clearSelection = () => setSelectedIds(new Set());

  const wrap = (v) => {
    const s = (v ?? "").toString();
    if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
    return s;
  };

  // 导出当前页 CSV
  const exportCSV = () => {
    if (!cases.length) { alert("当前没有可导出的数据"); return; }
    const headers = ["id","patient_name","species","chief_complaint","has_analysis"];
    const rows = cases.map(c => [
      c.id,
      wrap(c.patient_name),
      wrap(c.species),
      wrap(c.chief_complaint),
      c.analysis ? "1" : "0",
    ]);
    const bom = "\ufeff";
    const csv = [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    const blob = new Blob([bom + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const dt = new Date().toISOString().slice(0,19).replace(/[:T]/g,"-");
    a.download = `cases_page${page}_${dt}.csv`;
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url);
  };

  // 导出“本次搜索”的全量结果（自动分页抓取）
  const [exportingAll, setExportingAll] = useState(false);
  const MAX_PAGES = 1000; // 防御上限

  const exportCSVAll = async () => {
    try {
      setExportingAll(true);

      const headers = ["id","patient_name","species","chief_complaint","has_analysis"];
      const allRows = [];
      const pageSizeAll = 200; // 建议 100~500
      let cur = 1;
      let totalCount = null;

      while (cur <= MAX_PAGES) {
        const res = await api.get("/api/cases", { params: { q, page: cur, page_size: pageSizeAll } });
        const items = Array.isArray(res.data) ? res.data : (res.data.items || []);
        if (totalCount == null) totalCount = Array.isArray(res.data) ? items.length : (res.data.total ?? items.length);
        for (const c of items) {
          allRows.push([ c.id, wrap(c.patient_name), wrap(c.species), wrap(c.chief_complaint), c.analysis ? "1" : "0" ]);
        }
        if (items.length < pageSizeAll || (totalCount != null && allRows.length >= totalCount)) break;
        cur += 1;
        await new Promise(r => setTimeout(r, 80)); // 轻微节流
      }

      if (!allRows.length) { alert("没有匹配到可导出的数据"); return; }

      const bom = "\ufeff";
      const csv = [headers.join(","), ...allRows.map(r => r.join(","))].join("\n");
      const blob = new Blob([bom + csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const dt = new Date().toISOString().slice(0,19).replace(/[:T]/g,"-");
      a.download = `cases_full_${dt}.csv`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error(e);
      alert("导出失败，请检查网络或后端日志");
    } finally {
      setExportingAll(false);
    }
  };

  // 批量删除
  const handleBulkDelete = async () => {
    if (!selectedIds.size) { alert("请先勾选要删除的病例"); return; }
    if (!confirm(`确定删除选中的 ${selectedIds.size} 条病例？此操作不可恢复。`)) return;
    try {
      setBulkDeleting(true);
      await Promise.all(Array.from(selectedIds).map(id => api.delete(`/api/cases/${id}`)));
      clearSelection();
      await fetchCases();
      alert("删除完成");
    } catch (e) {
      console.error(e);
      alert("部分或全部删除失败，请查看控制台或后端日志");
    } finally {
      setBulkDeleting(false);
    }
  };

  // 单条删除（缓存最新删除用于撤销）
  const handleDeleteOne = async (row) => {
    if (!confirm(`确定删除病例 ${row.id}？此操作不可恢复。`)) return;
    try {
      setDeletingId(row.id);
      setLastDeleted({ id: row.id, data: row }); // 缓存
      await api.delete(`/api/cases/${row.id}`);
      await fetchCases();
    } catch (e) {
      console.error(e);
      alert("删除失败，请查看控制台或后端日志");
      setLastDeleted(null);
    } finally {
      setDeletingId(null);
    }
  };

  // 撤销删除（软还原）
  const handleUndoDelete = async () => {
    if (!lastDeleted) return;
    try {
      // 还原接口：按需改成你的后端路径
      await api.post(`/api/cases/${lastDeleted.id}/restore`);
      setLastDeleted(null);
      await fetchCases();
    } catch (e) {
      console.error(e);
      // 如果后端没有 restore 接口，可以尝试用 PUT/POST 重建（字段以你后端为准）
      alert("撤销失败：请检查后端是否提供 /restore 接口");
    }
  };

  // ===== 工具：输入防抖 =====
  const debounce = (fn, delay = 300) => {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), delay); };
  };

  // ===== 拉取病例列表（服务端分页/搜索） =====
  const fetchCases = async (paramsOverride = {}) => {
    try {
      setLoadingCases(true);
      const res = await api.get("/api/cases", {
        params: { q, page, page_size: pageSize, ...paramsOverride },
      });
      const items = Array.isArray(res.data) ? res.data : (res.data.items || []);
      const totalCount = Array.isArray(res.data) ? items.length : (res.data.total ?? items.length);
      setCases(items);
      setTotal(totalCount);
      clearSelection(); // 翻页/搜索后清选择，避免跨页误删
    } catch (e) {
      console.error("拉取病例失败：", e);
    } finally {
      setLoadingCases(false);
    }
  };

  useEffect(() => { fetchCases(); }, []);
  useEffect(() => {
    const run = debounce(() => { setPage(1); fetchCases({ page: 1 }); }, 300);
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q]);
  useEffect(() => { fetchCases(); }, [page]);

  const formatList = (items) => {
    if (!items) return "";
    if (!Array.isArray(items)) return String(items);

    return items
      .map((item) => {
        if (typeof item === "string") return `- ${item}`;
        return `- ${
          item.name ||
          item.disease ||
          item.label ||
          JSON.stringify(item)
        }`;
      })
      .join("\n");
  };

  const getQuestionList = (questionData) => {
    if (Array.isArray(questionData)) return questionData;
    if (Array.isArray(questionData?.questions)) return questionData.questions;
    return [];
  };

  const getCurrentQuestion = () => {
    const questions = getQuestionList(result?.next_questions);
    return questions[0] || "";
  };

  const applyConsultResult = (data, logLabel = "NORMALIZED AI DATA") => {
    const diseaseData = data.diseases || {};

    const diseaseList = Array.isArray(diseaseData)
      ? diseaseData
      : diseaseData.diseases || [];

    const checks = Array.isArray(diseaseData) ? [] : diseaseData.checks || [];
    const actions = Array.isArray(diseaseData)
      ? data.actions || []
      : diseaseData.actions || data.actions || [];
    const nextQuestionData =
      data.next_questions || (!Array.isArray(diseaseData) ? diseaseData.next_questions : []) || [];
    const nextQuestions = getQuestionList(nextQuestionData);

    console.log(logLabel, {
      risk_level: data.risk_level,
      tree_path: data.tree_path,
      diseaseList,
      checks,
      actions,
      nextQuestions,
    });

    setAnalysis(
      [
        data.tree_path?.length
          ? `诊断路径：${data.tree_path.join(" > ")}`
          : "",
        diseaseList.length
          ? `可能的鉴别诊断：\n${formatList(diseaseList)}`
          : "",
        checks.length ? `建议检查：\n${formatList(checks)}` : "",
      ]
        .filter(Boolean)
        .join("\n\n")
    );

    setTreatment(
      actions.length
        ? `建议处理/治疗：\n${formatList(actions)}`
        : data.treatment || ""
    );

    setPrognosis(
      nextQuestions.length
        ? `下一步追问：\n${formatList(nextQuestions)}`
        : data.prognosis || "需结合体征、影像与实验室检查进一步判断。"
    );
  };

  const truncateText = (value, max = 70) => {
    const text = (value || "").toString().replace(/\s+/g, " ").trim();
    if (!text) return "-";
    return text.length > max ? `${text.slice(0, max)}…` : text;
  };

  const formatSessionDate = (value) => {
    if (!value) return "-";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString("zh-CN", { hour12: false });
  };

  const rememberConsultSession = (sessionId) => {
    const sid = (sessionId || "").trim();
    if (!sid) return;
    setConsultSessionId(sid);
    setSessionInput(sid);
    setSavedSessionId(sid);
    localStorage.setItem("consult_session_id", sid);
  };

  const fetchSessionHistory = async () => {
    try {
      setLoadingHistory(true);
      const res = await api.get("/ai/consult/sessions", { params: { limit: 20 } });
      setSessionHistory(res.data?.items || []);
    } catch (err) {
      console.error("Session history error:", err);
      setErrMsg("历史问诊列表加载失败，请检查后端日志。");
    } finally {
      setLoadingHistory(false);
    }
  };

  const loadSession = async (sessionId) => {
    const sid = (sessionId || sessionInput || "").trim();
    if (!sid) {
      alert("请先输入 session_id，或先创建一次问诊会话。");
      return;
    }

    try {
      setErrMsg("");
      setLoadingSession(true);

      const res = await api.get(`/ai/consult/session/${encodeURIComponent(sid)}`);
      const payload = res.data;
      const data = payload.result || {};

      rememberConsultSession(payload.session_id || sid);
      setChiefComplaint(payload.text || "");
      setConsultAnswers(payload.answers || []);
      setResult(data);
      setFollowupAnswer("");

      if (data && Object.keys(data).length) {
        applyConsultResult(data, "RESTORED AI DATA");
      } else {
        setAnalysis("");
        setTreatment("");
        setPrognosis("");
      }
    } catch (err) {
      console.error("Load session error:", err);
      setErrMsg("恢复会话失败：请确认 session_id 是否正确，或检查后端日志。");
    } finally {
      setLoadingSession(false);
    }
  };

  useEffect(() => {
    const sid = localStorage.getItem("consult_session_id") || "";
    if (sid) {
      setSavedSessionId(sid);
      setSessionInput(sid);
    }
    fetchSessionHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ===== 即时分析（不入库） =====
 const handleAnalyzeSubmit = async (e) => {
  e.preventDefault();

  setErrMsg("");
  setAnalysis("");
  setTreatment("");
  setPrognosis("");
  setResult(null);
  setConsultSessionId(null);
  setConsultAnswers([]);
  setFollowupAnswer("");
  setLoadingFollowup(false);
  setLoadingAnalyze(true);

  try {
    const text = [
      chiefComplaint ? `主诉：${chiefComplaint}` : "",
      history ? `既往史：${history}` : "",
      examFindings ? `体检/化验：${examFindings}` : "",
      species ? `物种：${species}` : "",
      ageInfo ? `年龄：${ageInfo}` : "",
    ]
      .filter(Boolean)
      .join("\n");

    const res = await api.post("/ai/consult/session", {
      text,
    });

    const payload = res.data;
    const data = payload.result || payload;
    console.log("RAW AI DATA =", payload);
    if (payload.session_id) {
      rememberConsultSession(payload.session_id);
    }
    setResult(data);
    setConsultAnswers(payload.answers || []);
    setFollowupAnswer("");
    applyConsultResult(data);
    await fetchSessionHistory();
  } catch (err) {
    console.error("Analyze error:", err);
    setErrMsg("分析请求失败，请稍后重试或检查后端日志。");
  } finally {
    setLoadingAnalyze(false);
  }
};

  const handleFollowupSubmit = async (e) => {
    e.preventDefault();

    const currentQuestion = getCurrentQuestion();
    const answer = followupAnswer.trim();

    if (!currentQuestion) {
      alert("当前没有可提交的追问。");
      return;
    }

    if (!answer) {
      alert("请先填写追问回答。");
      return;
    }

    const nextAnswers = [
      ...consultAnswers,
      {
        question: currentQuestion,
        answer,
      },
    ];

    try {
      setErrMsg("");
      setLoadingFollowup(true);

      let payload;

      if (consultSessionId) {
        const res = await api.post(`/ai/consult/session/${consultSessionId}/answer`, {
          question: currentQuestion,
          answer,
        });
        payload = res.data;
      } else {
        const res = await api.post("/ai/consult/dynamic", {
          text: chiefComplaint,
          answers: nextAnswers,
        });
        payload = res.data;
      }

      const data = payload.result || payload;
      console.log("RAW DYNAMIC AI DATA =", payload);
      const nextSessionId = payload.session_id || consultSessionId || "";
      if (nextSessionId) {
        rememberConsultSession(nextSessionId);
      }
      setResult(data);
      applyConsultResult(data, "NORMALIZED DYNAMIC AI DATA");
      setConsultAnswers(payload.answers || nextAnswers);
      setFollowupAnswer("");
      await fetchSessionHistory();
    } catch (err) {
      console.error("Followup error:", err);
      setErrMsg("追问回答提交失败，请稍后重试或检查后端日志。");
    } finally {
      setLoadingFollowup(false);
    }
  };

  // ===== 新建病例 =====
  const handleCreateCase = async () => {
    if (!patientName || !chiefComplaint) {
      alert("请至少填写病例名与主诉"); return;
    }
    try {
      setLoadingCreate(true);
      const res = await api.post("/api/cases", {
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

  // ===== 重分析并写回 =====
  const handleReAnalyze = async (caseItem) => {
    try {
      setLoadingReAnalyzeId(caseItem.id);
      await api.post(`/api/cases/${caseItem.id}/analyze`, {
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
      alert("病例重分析失败，请查看后端日志");
    } finally {
      setLoadingReAnalyzeId(null);
    }
  };

  const currentQuestion = getCurrentQuestion();

  return (
    <div lang="zh-CN" translate="no" className="notranslate" style={{ fontFamily: "system-ui, -apple-system, Arial", padding: 24, maxWidth: 1000, margin: "0 auto" }}>
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

      {/* ====== 基础信息表单 ====== */}
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

        <div
          style={{
            marginTop: 12,
            padding: 12,
            border: "1px solid #e5e7eb",
            borderRadius: 8,
            background: "#f9fafb",
          }}
        >
          <div style={{ marginBottom: 8, fontSize: 13 }}>
            <strong>当前会话：</strong>{" "}
            {consultSessionId ? (
              <code>{consultSessionId}</code>
            ) : (
              <span style={{ opacity: 0.65 }}>暂无</span>
            )}
            {savedSessionId && !consultSessionId && (
              <span style={{ marginLeft: 12, opacity: 0.75 }}>
                本地最近：{savedSessionId.slice(0, 8)}
              </span>
            )}
          </div>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <input
              value={sessionInput}
              onChange={(e) => setSessionInput(e.target.value)}
              placeholder="输入完整 session_id"
              style={{
                flex: "1 1 260px",
                padding: "8px 10px",
                border: "1px solid #e5e7eb",
                borderRadius: 8,
              }}
            />
            <button
              type="button"
              onClick={() => loadSession(sessionInput)}
              disabled={loadingSession || !sessionInput.trim()}
              style={btnSecondary}
            >
              {loadingSession ? "恢复中…" : "恢复会话"}
            </button>
            <button
              type="button"
              onClick={() => loadSession(savedSessionId)}
              disabled={loadingSession || !savedSessionId}
              style={btnSecondary}
            >
              恢复最近会话
            </button>
            <button
              type="button"
              onClick={fetchSessionHistory}
              disabled={loadingHistory}
              style={btnSecondary}
            >
              {loadingHistory ? "刷新中…" : "刷新历史会话"}
            </button>
          </div>

          <div style={{ marginTop: 10 }}>
            <div style={{ fontWeight: 600, marginBottom: 6 }}>最近历史会话</div>
            {sessionHistory.length ? (
              <div style={{ display: "grid", gap: 6 }}>
                {sessionHistory.map((item) => (
                  <button
                    key={item.session_id}
                    type="button"
                    onClick={() => loadSession(item.session_id)}
                    style={{
                      textAlign: "left",
                      padding: 8,
                      border: "1px solid #e5e7eb",
                      borderRadius: 8,
                      background: "#fff",
                      cursor: "pointer",
                    }}
                  >
                    <div style={{ fontSize: 13 }}>
                      <strong>{item.session_id?.slice(0, 8) || "-"}</strong>
                      <span style={{ marginLeft: 8, opacity: 0.7 }}>
                        {formatSessionDate(item.updated_at || item.created_at)}
                      </span>
                    </div>
                    <div style={{ fontSize: 13, opacity: 0.8 }}>
                      风险：{item.risk_level || "未知"} · 第 {item.round ?? "-"} 轮 · 已回答 {item.answered_count ?? 0} 条
                    </div>
                    <div style={{ fontSize: 13, opacity: 0.75 }}>
                      {truncateText(item.text)}
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <div style={{ opacity: 0.65 }}>暂无历史会话，点击“刷新历史会话”后可查看。</div>
            )}
          </div>
        </div>

        {(analysis || treatment || prognosis) && (
          <div style={{ marginTop: 16 }}>
           <h3>即时分析结果</h3>
      
      {result && (
  <div style={{ marginBottom: 10 }}>
    <strong>风险等级：</strong>
    <span
      style={{
        color:
          result.risk_level === "high" || result.risk_level === "高"
            ? "red"
            : result.risk_level === "medium" || result.risk_level === "中"
            ? "orange"
            : "green",
        fontWeight: "bold",
      }}
    >
      {result.risk_level === "high" || result.risk_level === "高"
        ? "高风险"
        : result.risk_level === "medium" || result.risk_level === "中"
        ? "中风险"
        : result.risk_level === "low" || result.risk_level === "低"
        ? "低风险"
        : result.risk_level || "未知"}
    </span>
  </div>
)}
            
            {analysis && <Block title="分析">{analysis}</Block>}
            {treatment && <Block title="治疗建议">{treatment}</Block>}
            {prognosis && <Block title="预后">{prognosis}</Block>}

            {result && (currentQuestion || result.dynamic) && (
              <div
                style={{
                  marginTop: 12,
                  padding: 12,
                  border: "1px solid #fed7aa",
                  borderRadius: 8,
                  background: "#fff7ed",
                }}
              >
                {result.dynamic && (
                  <div style={{ marginBottom: 8, fontSize: 13 }}>
                    <strong>问诊轮次：</strong>
                    第 {result.dynamic.round ?? "-"} 轮
                    <span style={{ marginLeft: 12 }}>
                      <strong>已回答追问：</strong>
                      {result.dynamic.answered_count ?? consultAnswers.length} 条
                    </span>
                    {consultSessionId && (
                      <span style={{ marginLeft: 12 }}>
                        <strong>会话：</strong>
                        {consultSessionId.slice(0, 8)}
                      </span>
                    )}
                  </div>
                )}

                {currentQuestion ? (
                  <form onSubmit={handleFollowupSubmit}>
                    <div style={{ fontWeight: 600, marginBottom: 6 }}>当前追问：</div>
                    <div style={{ marginBottom: 8 }}>{currentQuestion}</div>
                    <textarea
                      value={followupAnswer}
                      onChange={(e) => setFollowupAnswer(e.target.value)}
                      rows={3}
                      placeholder="请填写对当前追问的回答"
                      disabled={loadingFollowup}
                      style={{
                        width: "100%",
                        boxSizing: "border-box",
                        padding: 8,
                        border: "1px solid #e5e7eb",
                        borderRadius: 8,
                      }}
                    />
                    <button
                      type="submit"
                      disabled={loadingFollowup || !followupAnswer.trim()}
                      style={{ ...btn, marginTop: 8 }}
                    >
                      {loadingFollowup ? "提交中…" : "提交追问回答"}
                    </button>
                  </form>
                ) : (
                  <div style={{ opacity: 0.75 }}>暂无新的追问。</div>
                )}
              </div>
            )}
          </div>
        )}
      </section>

      {/* ====== 列表（搜索+分页 + 批量操作） ====== */}
      <section style={card}>
        <h2 style={h2}>3) 病例列表</h2>

        {/* 搜索 + 操作 */}
        <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8 }}>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="搜索：病例名 / 物种 / 主诉"
            style={{ flex: 1, padding: "8px 10px", border: "1px solid #e5e7eb", borderRadius: 8 }}
          />
          <button onClick={() => { setPage(1); fetchCases({ page: 1 }); }} disabled={loadingCases} style={btn}>
            {loadingCases ? "刷新中…" : "刷新列表"}
          </button>
          <button onClick={exportCSV} style={btnSecondary}>导出 CSV</button>
          <button onClick={exportCSVAll} disabled={exportingAll} style={btnSecondary}>
            {exportingAll ? "导出中…" : "导出全量 CSV"}
          </button>
          <button onClick={selectAllCurrentPage} style={btnSecondary}>本页全选</button>
          <button onClick={clearSelection} style={btnSecondary}>清空选择</button>
          <button onClick={handleBulkDelete} disabled={bulkDeleting || selectedIds.size === 0} style={btnDanger}>
            {bulkDeleting ? "删除中…" : `批量删除(${selectedIds.size})`}
          </button>
          <Link to="/cases/new/edit" style={{ ...btnSecondary, textDecoration:"none", display:"inline-block" }}>
            新建病例
          </Link>
        </div>

        {/* 表格 */}
        {cases.length === 0 ? (
          <p style={{ opacity: 0.7 }}>暂无病例。</p>
        ) : (
          <>
            <table style={table}>
              <thead>
                <tr>
                  <th style={{ width: 52, textAlign: "center" }}>选择</th>
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
                    <td style={{ textAlign: "center" }}>
                      <input
                        type="checkbox"
                        checked={selectedIds.has(c.id)}
                        onChange={() => toggleOne(c.id)}
                      />
                    </td>
                    <td>{c.id}</td>
                    <td>{c.patient_name}</td>
                    <td>{c.species}</td>
                    <td
                      title={c.chief_complaint}
                      style={{ maxWidth: 220, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}
                    >
                      {c.chief_complaint}
                    </td>
                    <td style={{ color: c.analysis ? "#16a34a" : "#999" }}>
                      {c.analysis ? "✓" : "—"}
                    </td>
                    <td>
                      <div style={{ display: "inline-flex", gap: 8 }}>
                        <Link to={`/cases/${c.id}`} style={{ ...btnTiny, textDecoration: "none", display: "inline-block" }}>
                          查看
                        </Link>
                        <Link to={`/cases/${c.id}/edit`} style={{ ...btnTiny, textDecoration: "none", display: "inline-block" }}>
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
                        {/* 打印：跳转详情并自动打印 */}
                        <Link
                          to={`/cases/${c.id}`}
                          state={{ autoPrint: true }}
                          style={{ ...btnTiny, textDecoration: "none", display: "inline-block" }}
                          title="打开详情并自动打印"
                        >
                          打印
                        </Link>
                        {/* 单条删除 */}
                        <button
                          type="button"
                          style={{ ...btnTiny, borderColor: "#ef4444", color: "#ef4444" }}
                          onClick={() => handleDeleteOne(c)}
                          disabled={deletingId === c.id}
                          title="删除该病例"
                        >
                          {deletingId === c.id ? "删除中…" : "删除"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* 分页器 */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 12 }}>
              <div style={{ opacity: 0.7, fontSize: 12 }}>共 {total} 条，{pageSize} 条/页</div>
              <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                <button style={btnTiny} disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>
                  上一页
                </button>
                <span style={{ padding: "6px 10px" }}>{page} / {totalPages}</span>
                <button style={btnTiny} disabled={page >= totalPages} onClick={() => setPage((p) => Math.min(totalPages, p + 1))}>
                  下一页
                </button>
              </div>
            </div>
          </>
        )}
      </section>

      {/* 撤销提示条（最近删除） */}
      {lastDeleted && (
        <div style={undoBar}>
          <div>病例 <b>#{lastDeleted.id}</b> 已删除。</div>
          <div style={{ display: "flex", gap: 8 }}>
            <button onClick={handleUndoDelete} style={btnUndo}>撤销</button>
            <button onClick={() => setLastDeleted(null)} style={btnTiny}>关闭</button>
          </div>
        </div>
      )}
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
        <Route path="/cases/:id" element={<CaseDetail />} />
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
const btnDanger = { padding:"8px 14px", borderRadius:8, border:"1px solid #ef4444", background:"#ef4444", color:"#fff", cursor:"pointer" };
const btnUndo = { padding:"6px 12px", borderRadius:8, border:"1px solid #10b981", background:"#10b981", color:"#fff", cursor:"pointer", fontSize: 12 };
const btnTiny = { padding: "6px 10px", borderRadius: 8, border: "1px solid #64748b", background: "#fff", color: "#111", cursor: "pointer", fontSize: 12 };
const table = { width: "100%", borderCollapse: "collapse" };
const undoBar = {
  position: "fixed",
  left: 16, right: 16, bottom: 16,
  background: "#111827", color: "#fff",
  borderRadius: 12, padding: "10px 14px",
  display: "flex", alignItems: "center", justifyContent: "space-between",
  boxShadow: "0 8px 24px rgba(0,0,0,.2)",
  zIndex: 50,
};
