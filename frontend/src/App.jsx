// src/App.jsx
import React, { useEffect, useRef, useState } from "react";
import { BrowserRouter as Router, Routes, Route, Link, useSearchParams, useNavigate } from "react-router-dom";
import api from "./api";
import useConsultDraft from "./useConsultDraft";
import { clearDraft } from "./consultDraft";
import { clearManualCreateAttempt } from "./components/ManualCaseCreateReview";
import { caseEditDraftOwner, clearCaseEditDrafts } from "./caseEditDraft";
import ConsultUpdateReview from "./components/ConsultUpdateReview";
import ConsultSaveReview from "./components/ConsultSaveReview";
import { WorkbenchSteps, SavedCasePanel, workbenchSteps } from "./components/ConsultWorkbench";
import CaseDetail from "./pages/CaseDetail";
import CaseEditorPage from "./pages/CaseEditorLite";
import KpiDashboard from "./pages/KpiDashboard";
import WebhookInboxPage from "./pages/WebhookInboxPage";
import EmrImportBatchPlanningPage from "./pages/EmrImportBatchPlanningPage";
import OpsDashboard from "./pages/OpsDashboard";
import PreventiveCareNotificationQueuePage from "./pages/PreventiveCareNotificationQueuePage";
import AutomatedReminderDeliveryManualApprovalPage from "./pages/AutomatedReminderDeliveryManualApprovalPage";

function getErrorDetail(err) {
  const detail = err?.response?.data?.detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item?.msg || JSON.stringify(item)).join("；");
  }
  if (typeof detail === "string") return detail;
  if (detail) return JSON.stringify(detail);
  return "";
}

function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test((value || "").trim());
}

function getSignupErrorMessage(err) {
  const status = err?.response?.status;
  const detail = getErrorDetail(err);

  if (status === 400) return "注册失败：该邮箱可能已存在，请换一个邮箱或直接登录。";
  if (status === 422) return `注册失败：请输入有效邮箱和密码。${detail ? `\n${detail}` : ""}`;
  if (status === 500) return "注册失败：后端服务异常，请查看 Render / 后端日志。";
  return `注册失败：请检查网络或后端服务。${detail ? `\n${detail}` : ""}`;
}

function getLoginErrorMessage(err) {
  const status = err?.response?.status;
  const detail = getErrorDetail(err);

  if (status === 401) return "登录失败：邮箱或密码错误。";
  if (status === 422) return `登录失败：请输入有效邮箱和密码。${detail ? `\n${detail}` : ""}`;
  if (status === 500) return "登录失败：后端服务异常，请查看 Render / 后端日志。";
  return `登录失败：请检查网络或后端服务。${detail ? `\n${detail}` : ""}`;
}

/** ===== 首页 Home 组件 ===== */
export function Home() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  // ===== 登录区 =====
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const isAuthed = !!localStorage.getItem("token");

  const handleLogin = async (e) => {
    e.preventDefault();

    const cleanEmail = email.trim();
    if (!isValidEmail(cleanEmail)) {
      alert("请输入有效邮箱，例如 name@example.com");
      return;
    }

    if (!password) {
      alert("请输入密码");
      return;
    }

    try {
      clearDraft();
      clearCaseEditDrafts();
      localStorage.removeItem("consult_session_id");
      localStorage.removeItem("token");

      const form = new FormData();
      form.append("username", cleanEmail);
      form.append("password", password);
      const res = await api.post("/auth/login", form);

      localStorage.setItem("token", res.data.access_token);
      alert("登录成功");
      window.location.reload();
    } catch (err) {
      console.error(err);
      alert(getLoginErrorMessage(err));
    }
  };

  const handleSignup = async () => {
    const cleanEmail = email.trim();
    if (!isValidEmail(cleanEmail)) {
      alert("请输入有效邮箱，例如 name@example.com");
      return;
    }

    if (!password || password.length < 6) {
      alert("密码至少 6 位");
      return;
    }

    try {
      await api.post("/auth/signup", { email: cleanEmail, password, full_name: "" });
      alert("注册成功，请登录");
    } catch (err) {
      console.error(err);
      alert(getSignupErrorMessage(err));
    }
  };

  const handleLogout = () => {
    clearDraft();
    clearCaseEditDrafts();
    clearManualCreateAttempt();
    localStorage.removeItem("consult_session_id");
    localStorage.removeItem("token");
    window.location.reload();
  };

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
  const [sessionRiskFilter, setSessionRiskFilter] = useState("all");
  const [sessionSavedFilter, setSessionSavedFilter] = useState("all");
  const [sessionPage, setSessionPage] = useState(1);
  const [sessionPageSize] = useState(20);
  const [sessionTotal, setSessionTotal] = useState(0);
  const [deletingSessionId, setDeletingSessionId] = useState(null);
  const [consultAnswers, setConsultAnswers] = useState([]);
  const [followupAnswer, setFollowupAnswer] = useState("");
  const [structuredIntakeAnswers, setStructuredIntakeAnswers] = useState({});
  const [lastStructuredIntakeSubmission, setLastStructuredIntakeSubmission] = useState(null);
  const [loadingAnalyze, setLoadingAnalyze] = useState(false);
  const [loadingFollowup, setLoadingFollowup] = useState(false);
  const [errMsg, setErrMsg] = useState("");
  const [auditReviewAction, setAuditReviewAction] = useState("accepted");
  const [auditReviewReason, setAuditReviewReason] = useState("");
  const [auditReviewNote, setAuditReviewNote] = useState("");
  const [auditClinicianId, setAuditClinicianId] = useState("");
  const [auditSubmitting, setAuditSubmitting] = useState(false);
  const [auditLogReceipt, setAuditLogReceipt] = useState(null);

  const [patientName, setPatientName] = useState("");
  const [species, setSpecies] = useState("dog");
  const [sex, setSex] = useState("");
  const [ageInfo, setAgeInfo] = useState("");
  const [breed, setBreed] = useState("");
  const [weight, setWeight] = useState("");
  const [coatColor, setCoatColor] = useState("");
  const [ownerName, setOwnerName] = useState("");
  const [ownerPhone, setOwnerPhone] = useState("");

  // ===== 列表 搜索 + 分页 =====
  const [q, setQ] = useState("");
  const [riskFilter, setRiskFilter] = useState("all");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [cases, setCases] = useState([]);
  const [total, setTotal] = useState(0);
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const [loadingCases, setLoadingCases] = useState(false);
  const [savedConsultCaseId, setSavedConsultCaseId] = useState(null);
  const [consultSaveReceipt, setConsultSaveReceipt] = useState(null);
  const [workbenchStep, setWorkbenchStep] = useState(1);
  const [workbenchBusy, setWorkbenchBusy] = useState(false);
  const [reviewNavigationVersion, setReviewNavigationVersion] = useState(0);
  const stepHeading = useRef(null);
  useEffect(() => { stepHeading.current?.focus(); }, [workbenchStep]);
  const changeWorkbenchStep = (next) => {
    if (workbenchBusy) return;
    if (next === 1 && workbenchStep === 2) setReviewNavigationVersion(value => value + 1);
    setWorkbenchStep(next);
  };

  const [historyAddendum, setHistoryAddendum] = useState("");
  const [recoveredDraftNotes, setRecoveredDraftNotes] = useState("");
  const [draftRestoreMessage, setDraftRestoreMessage] = useState("");
  const [restoringDraft, setRestoringDraft] = useState(false);
  const draftSnapshot = {
    fields: { patientName, species, sex, ageInfo, breed, weight, coatColor, ownerName, ownerPhone, chiefComplaint, history, historyAddendum, examFindings, auditReviewAction, auditReviewReason, auditReviewNote, auditClinicianId },
    sessionId: consultSessionId,
    sessionContext: JSON.stringify([consultAnswers, result?.next_questions ?? [], result?.structured_intake?.template_key ?? null]),
    followupAnswer, structuredAnswers: structuredIntakeAnswers,
    lastSubmission: lastStructuredIntakeSubmission, recoveredNotes: recoveredDraftNotes,
  };
  const draft = useConsultDraft(draftSnapshot, loadingSession || loadingAnalyze || loadingFollowup || restoringDraft);

  const [loadingReAnalyzeId, setLoadingReAnalyzeId] = useState(null);

  // ===== 批量选择 / 导出 / 批量删除 =====
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [bulkDeleting, setBulkDeleting] = useState(false);

  // ===== 单条删除 / 撤销 =====
  const [deletingId, setDeletingId] = useState(null);     // 正在删除的行
  const [lastDeleted, setLastDeleted] = useState(null);   // { id, data } 最近删除的完整对象（用于撤销）

  const getCaseRiskMeta = (caseItem) => {
    const raw = [
      caseItem?.analysis,
      caseItem?.prognosis,
      caseItem?.treatment,
    ]
      .filter(Boolean)
      .join("\n");

    if (/高风险|风险(?:等级|提示)?[:：]\s*高|high/i.test(raw)) {
      return { key: "high", label: "高风险" };
    }
    if (/中风险|风险(?:等级|提示)?[:：]\s*中|medium/i.test(raw)) {
      return { key: "medium", label: "中风险" };
    }
    if (/低风险|风险(?:等级|提示)?[:：]\s*低|low/i.test(raw)) {
      return { key: "low", label: "低风险" };
    }

    return { key: "unknown", label: "未记录" };
  };

  const getRiskBadgeStyle = (riskKey) => {
    const base = {
      display: "inline-block",
      padding: "2px 8px",
      borderRadius: 999,
      fontSize: 12,
      fontWeight: 700,
      border: "1px solid #e5e7eb",
      whiteSpace: "nowrap",
    };

    if (riskKey === "high") return { ...base, color: "#991b1b", background: "#fef2f2", borderColor: "#fecaca" };
    if (riskKey === "medium") return { ...base, color: "#9a3412", background: "#fff7ed", borderColor: "#fed7aa" };
    if (riskKey === "low") return { ...base, color: "#166534", background: "#f0fdf4", borderColor: "#bbf7d0" };
    return { ...base, color: "#475569", background: "#f8fafc" };
  };

  const isDynamicCase = (caseItem) => {
    const raw = [
      caseItem?.history,
      caseItem?.exam_findings,
      caseItem?.analysis,
      caseItem?.prognosis,
    ]
      .filter(Boolean)
      .join("\n");

    return /动态问诊|原始会话|后续追问|风险等级/.test(raw);
  };

  const matchesCaseFilters = (caseItem) => {
    const riskKey = getCaseRiskMeta(caseItem).key;
    const sourceKey = isDynamicCase(caseItem) ? "dynamic" : "manual";

    return (
      (riskFilter === "all" || riskFilter === riskKey) &&
      (sourceFilter === "all" || sourceFilter === sourceKey)
    );
  };

  const toggleOne = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };
  const selectAllCurrentPage = () => setSelectedIds(new Set(cases.filter(matchesCaseFilters).map((c) => c.id)));
  const clearSelection = () => setSelectedIds(new Set());

  const wrap = (v) => {
    const s = (v ?? "").toString();
    if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
    return s;
  };

  // 导出当前页 CSV
  const exportCSV = () => {
    const exportRows = visibleCases;
    if (!exportRows.length) { alert("当前没有可导出的数据"); return; }
    const headers = ["id","patient_name","species","breed","weight","coat_color","owner_name","owner_phone","risk_level","source","chief_complaint","has_analysis"];
    const rows = exportRows.map(c => [
      c.id,
      wrap(c.patient_name),
      wrap(c.species),
      wrap(c.breed),
      wrap(c.weight),
      wrap(c.coat_color),
      wrap(c.owner_name),
      wrap(c.owner_phone),
      wrap(getCaseRiskMeta(c).label),
      isDynamicCase(c) ? "dynamic_consult" : "manual",
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

      const headers = ["id","patient_name","species","breed","weight","coat_color","owner_name","owner_phone","chief_complaint","has_analysis"];
      const allRows = [];
      const pageSizeAll = 200; // 建议 100~500
      let cur = 1;
      let totalCount = null;

      while (cur <= MAX_PAGES) {
        const res = await api.get("/api/cases", {
          params: {
            q,
            page: cur,
            page_size: pageSizeAll,
            risk: riskFilter !== "all" ? riskFilter : undefined,
            source: sourceFilter !== "all" ? sourceFilter : undefined,
          },
        });
        const items = Array.isArray(res.data) ? res.data : (res.data.items || []);
        if (totalCount == null) totalCount = Array.isArray(res.data) ? items.length : (res.data.total ?? items.length);
        for (const c of items) {
          allRows.push([
            c.id,
            wrap(c.patient_name),
            wrap(c.species),
            wrap(c.breed),
            wrap(c.weight),
            wrap(c.coat_color),
            wrap(c.owner_name),
            wrap(c.owner_phone),
            wrap(c.chief_complaint),
            c.analysis ? "1" : "0",
          ]);
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

  const buildCaseListParams = (paramsOverride = {}) => ({
    q,
    page,
    page_size: pageSize,
    risk: riskFilter !== "all" ? riskFilter : undefined,
    source: sourceFilter !== "all" ? sourceFilter : undefined,
    ...paramsOverride,
  });

  // ===== 拉取病例列表（服务端分页/搜索） =====
  const caseListTimer = useRef(null);
  const fetchCases = async (paramsOverride = {}) => {
    clearTimeout(caseListTimer.current);
    caseListTimer.current = null;
    if (!localStorage.getItem("token")) {
      setCases([]);
      setTotal(0);
      clearSelection();
      return;
    }
    try {
      setLoadingCases(true);
      const res = await api.get("/api/cases", {
        params: buildCaseListParams(paramsOverride),
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

  const caseListFilters = useRef({ q, riskFilter, sourceFilter });
  useEffect(() => {
    const previous = caseListFilters.current;
    const filtersChanged = previous.q !== q || previous.riskFilter !== riskFilter || previous.sourceFilter !== sourceFilter;
    caseListFilters.current = { q, riskFilter, sourceFilter };
    if (filtersChanged && page !== 1) {
      setPage(1);
      return;
    }
    if (!isAuthed) return;
    // One cancellable load for mount, search, filters and pagination.
    caseListTimer.current = setTimeout(() => fetchCases(), 300);
    return () => clearTimeout(caseListTimer.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, riskFilter, sourceFilter, page, isAuthed]);

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

  const getSessionRiskMeta = (item) => {
    const raw = String(item?.risk_level || "").trim();
    if (/高|high/i.test(raw)) return { key: "high", label: "高风险" };
    if (/中|medium/i.test(raw)) return { key: "medium", label: "中风险" };
    if (/低|low/i.test(raw)) return { key: "low", label: "低风险" };
    return { key: "unknown", label: raw || "未记录" };
  };

  const getSessionRiskBadgeStyle = (riskKey) => {
    const base = {
      display: "inline-block",
      padding: "2px 8px",
      borderRadius: 999,
      fontSize: 12,
      fontWeight: 700,
      border: "1px solid #e5e7eb",
      whiteSpace: "nowrap",
    };

    if (riskKey === "high") return { ...base, color: "#991b1b", background: "#fef2f2", borderColor: "#fecaca" };
    if (riskKey === "medium") return { ...base, color: "#9a3412", background: "#fff7ed", borderColor: "#fed7aa" };
    if (riskKey === "low") return { ...base, color: "#166534", background: "#f0fdf4", borderColor: "#bbf7d0" };
    return { ...base, color: "#475569", background: "#f8fafc" };
  };

  const matchesSessionFilters = (item) => {
    const riskKey = getSessionRiskMeta(item).key;
    const savedKey = item?.case_id ? "saved" : "unsaved";

    return (
      (sessionRiskFilter === "all" || sessionRiskFilter === riskKey) &&
      (sessionSavedFilter === "all" || sessionSavedFilter === savedKey)
    );
  };

  const rememberConsultSession = (sessionId) => {
    const sid = (sessionId || "").trim();
    if (!sid) return;
    setConsultSessionId(sid);
    setSessionInput(sid);
    setSavedSessionId(sid);
    localStorage.setItem("consult_session_id", sid);
  };

  const fetchSessionHistory = async (paramsOverride = {}) => {
    if (!localStorage.getItem("token")) {
      setSessionHistory([]);
      setSessionTotal(0);
      return;
    }

    const nextPage = paramsOverride.page ?? sessionPage;
    const nextPageSize = paramsOverride.page_size ?? sessionPageSize;

    try {
      setLoadingHistory(true);
      const res = await api.get("/api/ai/consult/sessions", {
        params: {
          page: nextPage,
          page_size: nextPageSize,
          risk: sessionRiskFilter !== "all" ? sessionRiskFilter : undefined,
          saved: sessionSavedFilter !== "all" ? sessionSavedFilter : undefined,
          ...paramsOverride,
        },
      });

      setSessionHistory(res.data?.items || []);
      setSessionTotal(res.data?.total ?? (res.data?.items || []).length);
      setSessionPage(res.data?.page ?? nextPage);
    } catch (err) {
      console.error("Session history error:", err);
      if (err.response?.status !== 401) {
        setErrMsg("历史问诊列表加载失败，请检查后端日志。");
      }
    } finally {
      setLoadingHistory(false);
    }
  };

  const applyDraftFields = fields => {
    setPatientName(fields.patientName || ""); setSpecies(fields.species || "dog");
    setSex(fields.sex || ""); setAgeInfo(fields.ageInfo || ""); setBreed(fields.breed || "");
    setWeight(fields.weight || ""); setCoatColor(fields.coatColor || "");
    setOwnerName(fields.ownerName || ""); setOwnerPhone(fields.ownerPhone || "");
    setChiefComplaint(fields.chiefComplaint || ""); setHistory(fields.history || "");
    setHistoryAddendum(fields.historyAddendum || "");
    setExamFindings(fields.examFindings || ""); setAuditClinicianId(fields.auditClinicianId || "");
    setAuditReviewAction(["accepted", "modified", "rejected"].includes(fields.auditReviewAction) ? fields.auditReviewAction : "accepted");
    setAuditReviewReason(fields.auditReviewReason || ""); setAuditReviewNote(fields.auditReviewNote || "");
  };

  const restoreLocalDraft = async () => {
    if (!draft.offer || restoringDraft || !draft.owner) return;
    const snapshot = draft.offer.data;
    try {
      setRestoringDraft(true); setDraftRestoreMessage("");
      let payload = null;
      if (snapshot.sessionId) {
        const response = await api.get(`/api/ai/consult/session/${encodeURIComponent(snapshot.sessionId)}`, { timeout: 15000 });
        payload = response.data;
        if (payload.session_id !== snapshot.sessionId) throw new Error("Session mismatch");
      }
      const data = payload?.result || null;
      const currentContext = JSON.stringify([payload?.answers || [], data?.next_questions ?? [], data?.structured_intake?.template_key ?? null]);
      const changed = !!payload && currentContext !== snapshot.sessionContext;
      // Old pending answers must not be submitted to a newer/different question.
      const pending = changed && (snapshot.followupAnswer || Object.keys(snapshot.structuredAnswers).length)
        ? ["原问诊已变化，以下未提交内容需重新整理：", snapshot.followupAnswer, JSON.stringify(snapshot.structuredAnswers, null, 2)].filter(Boolean).join("\n") : "";
      setConsultSessionId(payload?.session_id || null);
      if (payload) rememberConsultSession(payload.session_id);
      setResult(data); setConsultAnswers(payload?.answers || []);
      setSavedConsultCaseId(payload?.case_id || null);
      setAnalysis(""); setTreatment(""); setPrognosis("");
      if (data) applyConsultResult(data, "DRAFT RESTORED FROM CURRENT SESSION");
      resetAuditReviewState(); setConsultSaveReceipt(null);
      applyDraftFields(snapshot.fields);
      setFollowupAnswer(changed ? "" : snapshot.followupAnswer);
      setStructuredIntakeAnswers(changed ? {} : snapshot.structuredAnswers);
      setLastStructuredIntakeSubmission(changed ? null : snapshot.lastSubmission);
      setRecoveredDraftNotes([snapshot.recoveredNotes, pending].filter(Boolean).join("\n\n"));
      setReviewNavigationVersion(value => value + 1); setWorkbenchStep(1);
      const nextParams = new URLSearchParams(searchParams); nextParams.delete("restore_session_id");
      setSearchParams(nextParams, { replace: true });
      draft.accepted();
      setDraftRestoreMessage(payload?.case_id
        ? `已恢复输入；原问诊已绑定病例 #${payload.case_id}，请查看已有病例后再核对更新。草稿未自动写入病例。`
        : "草稿输入已恢复，请重新覆核 AI 建议并核对保存内容；恢复操作没有写入病例。");
    } catch {
      setDraftRestoreMessage("暂时无法读取原问诊，草稿仍保留。请检查登录状态或网络后重试恢复。");
    } finally { setRestoringDraft(false); }
  };

  const loadSession = async (sessionId) => {
    const sid = (sessionId || sessionInput || "").trim();
    if (!sid) {
      alert("请先输入 session_id，或先创建一次问诊会话。");
      return;
    }

    if (!localStorage.getItem("token")) {
      alert("请先登录后恢复历史问诊");
      return;
    }

    const hasUnsavedInput = Object.entries(draftSnapshot.fields).some(([key, value]) => !["species", "auditReviewAction"].includes(key) && value.trim()) || followupAnswer || recoveredDraftNotes || Object.values(structuredIntakeAnswers).some(value => value.trim());
    if (sid !== consultSessionId && hasUnsavedInput && !confirm("切换问诊会替换当前页面输入及本页草稿。请先保存需要保留的内容。继续切换？")) return;
    try {
      setErrMsg("");
      setLoadingSession(true);

      const res = await api.get(`/api/ai/consult/session/${encodeURIComponent(sid)}`);
      const payload = res.data;
      const data = payload.result || {};

      applyDraftFields({});
      setRecoveredDraftNotes(""); setDraftRestoreMessage("");
      rememberConsultSession(payload.session_id || sid);
      setChiefComplaint(payload.text || "");
      setConsultAnswers(payload.answers || []);
      setResult(data);
      setFollowupAnswer("");
      setStructuredIntakeAnswers({});
      resetAuditReviewState();
      setLastStructuredIntakeSubmission(null);
      setConsultSaveReceipt(null);
      setSavedConsultCaseId(payload.case_id || null);
      setWorkbenchStep(1);

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

  useEffect(() => {
    if (!localStorage.getItem("token")) return;
    setSessionPage(1);
    fetchSessionHistory({ page: 1 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionRiskFilter, sessionSavedFilter]);

  useEffect(() => {
    const sid = (searchParams.get("restore_session_id") || "").trim();
    if (!sid || draft.offer || restoringDraft) return;

    if (!localStorage.getItem("token")) {
      setSessionInput(sid);
      setErrMsg("请先登录后恢复来源问诊。登录后可继续使用该会话 ID 恢复。");
      return;
    }

    loadSession(sid);

    const nextParams = new URLSearchParams(searchParams);
    nextParams.delete("restore_session_id");
    setSearchParams(nextParams, { replace: true });

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, setSearchParams, draft.offer, restoringDraft]);

  const handleDeleteConsultSession = async (sessionId) => {
    const sid = (sessionId || "").trim();
    if (!sid) return;

    if (!confirm("确定删除这条未保存为病例的问诊？此操作不可恢复。")) return;

    try {
      setErrMsg("");
      setDeletingSessionId(sid);

      await api.delete(`/api/ai/consult/session/${encodeURIComponent(sid)}`);

      if (consultSessionId === sid) {
        setConsultSessionId(null);
        setResult(null);
        setConsultAnswers([]);
        setFollowupAnswer("");
        setAnalysis("");
        setTreatment("");
        setPrognosis("");
        setSavedConsultCaseId(null);
      }

      if (savedSessionId === sid) {
        setSavedSessionId("");
        setSessionInput("");
        localStorage.removeItem("consult_session_id");
      }

      await fetchSessionHistory();
      alert("已删除未保存问诊");
    } catch (err) {
      console.error("Delete consult session error:", err);
      if (err.response?.status === 400) {
        alert("已保存为病例的问诊不能删除，请从病例详情继续追溯。");
      } else if (err.response?.status === 401) {
        alert("请先登录后删除问诊");
      } else {
        alert("删除问诊失败，请检查后端日志");
      }
    } finally {
      setDeletingSessionId(null);
    }
  };

  // ===== 即时分析（不入库） =====
 const handleAnalyzeSubmit = async (e) => {
  e.preventDefault();
  if (historyAddendum.trim()) { alert("医生病史补记尚未保存，请先在第二步核对更新，或清空补记后再开始新的分析。"); return; }

  setErrMsg("");
  setAnalysis("");
  setTreatment("");
  setPrognosis("");
  setResult(null);
  setConsultSessionId(null);
  setConsultAnswers([]);
  setSavedConsultCaseId(null);
  setFollowupAnswer("");
  setStructuredIntakeAnswers({});
  resetAuditReviewState();
  setLastStructuredIntakeSubmission(null);
  setConsultSaveReceipt(null);
  setLoadingFollowup(false);
  setLoadingAnalyze(true);
  setWorkbenchStep(1);

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

    const sessionCreatePath = localStorage.getItem("token")
      ? "/api/ai/consult/session"
      : "/ai/consult/session";

    const res = await api.post(sessionCreatePath, {
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


  const resetAuditReviewState = () => {
    setAuditReviewAction("accepted");
    setAuditReviewReason("");
    setAuditReviewNote("");
    setAuditLogReceipt(null);
  };

  const confidenceFromRisk = (riskValue) => {
    const raw = String(riskValue || "").trim();
    if (/高|high/i.test(raw)) return 0.85;
    if (/中|medium/i.test(raw)) return 0.55;
    if (/低|low/i.test(raw)) return 0.25;
    return null;
  };

  const buildAuditSuggestedAction = () => {
    const parts = [
      result?.risk_level ? `风险等级：${result.risk_level}` : "",
      analysis ? `分析：\n${analysis}` : "",
      treatment ? `治疗建议：\n${treatment}` : "",
      prognosis ? `预后 / 后续追问：\n${prognosis}` : "",
    ].filter(Boolean);
    return parts.join("\n\n").trim();
  };

  const currentAuditSuggestedAction = buildAuditSuggestedAction();
  const auditReviewRequired = Boolean(result && isAuthed && !auditLogReceipt?.log_id);

  const handleSubmitAiReviewAudit = async () => {
    if (!localStorage.getItem("token")) {
      alert("请先登录后进行 AI 建议人工覆核");
      return;
    }
    if (!result) {
      alert("当前没有可覆核的 AI 结果");
      return;
    }

    const clinician = auditClinicianId.trim();
    const requiresReason = auditReviewAction === "modified" || auditReviewAction === "rejected";
    const reason = auditReviewReason.trim();
    const note = auditReviewNote.trim();

    if (!clinician) {
      alert("请填写临床人员 ID / 签名");
      return;
    }
    if (requiresReason && (!reason || note.length < 10)) {
      alert("修改或拒绝 AI 建议时，必须选择理由，并填写至少 10 字说明。");
      return;
    }

    const requestId = `ui-review-${consultSessionId || "adhoc"}-${Date.now()}`;
    const payload = {
      request_id: requestId,
      patient_token: consultSessionId ? `consult:${consultSessionId}` : null,
      clinician_id: clinician,
      model_version: "pet-med-ai-frontend-review-v1",
      confidence: confidenceFromRisk(result?.risk_level),
      suggested_action: currentAuditSuggestedAction || "暂无 AI 建议摘要",
      action_taken: auditReviewAction,
      override_reason: requiresReason ? reason : "",
      note: note || (auditReviewAction === "accepted" ? "医生接受 AI 建议。" : ""),
      case_id: savedConsultCaseId || null,
      session_uid: consultSessionId || null,
      event_type: "ai_review",
      source: "pet-med-ai-frontend",
      metadata: {
        ui_version: "ai-review-audit-ui-v1",
        risk_level: result?.risk_level || null,
        review_action: auditReviewAction,
        has_structured_intake: Boolean(result?.structured_intake),
      },
    };

    try {
      setErrMsg("");
      setAuditSubmitting(true);
      const res = await api.post("/api/audit-log", payload);
      setAuditLogReceipt(res.data || {});
      setConsultSaveReceipt(null);
      alert(`已写入审计日志：${res.data?.log_id || ""}`);
    } catch (err) {
      console.error("AI review audit error:", err);
      if (err.response?.status === 401) {
        alert("请先登录后写入审计日志");
      } else if (err.response?.status === 422) {
        alert("审计日志参数校验失败，请检查临床签名、置信度和必填字段。");
      } else {
        alert("写入审计日志失败，请检查后端日志");
      }
    } finally {
      setAuditSubmitting(false);
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
    const structuredIntakePayload = buildStructuredIntakeSubmission(result?.structured_intake, structuredIntakeAnswers);

    try {
      setErrMsg("");
      setLoadingFollowup(true);

      let payload;

      if (consultSessionId) {
        const answerPath = localStorage.getItem("token")
          ? `/api/ai/consult/session/${consultSessionId}/answer`
          : `/ai/consult/session/${consultSessionId}/answer`;

        const res = await api.post(answerPath, {
          question: currentQuestion,
          answer,
          structured_intake_answers: structuredIntakePayload,
        });
        payload = res.data;
      } else {
        const res = await api.post("/ai/consult/dynamic", {
          text: chiefComplaint,
          answers: nextAnswers,
          structured_intake_answers: structuredIntakePayload,
        });
        payload = res.data;
      }

      if (structuredIntakePayload) setLastStructuredIntakeSubmission(structuredIntakePayload);
      const data = payload.result || payload;
      console.log("RAW DYNAMIC AI DATA =", payload);
      const nextSessionId = payload.session_id || consultSessionId || "";
      if (nextSessionId) {
        rememberConsultSession(nextSessionId);
      }
      setResult(data);
      applyConsultResult(data, "NORMALIZED DYNAMIC AI DATA");
      setConsultAnswers(payload.answers || nextAnswers);
      setSavedConsultCaseId(payload.case_id || savedConsultCaseId || null);
      setFollowupAnswer("");
      setStructuredIntakeAnswers({});
      resetAuditReviewState();
      setConsultSaveReceipt(null);
      await fetchSessionHistory();
    } catch (err) {
      console.error("Followup error:", err);
      setErrMsg("追问回答提交失败，请稍后重试或检查后端日志。");
    } finally {
      setLoadingFollowup(false);
    }
  };

  const buildConsultSaveCasePayload = () => {
    const structuredIntakePayload = buildStructuredIntakeSubmission(result?.structured_intake, structuredIntakeAnswers) || lastStructuredIntakeSubmission;

    return {
      chief_complaint: chiefComplaint,
      history,
      patient_name: patientName?.trim() || "未命名病例",
      species: species || "dog",
      sex: sex || null,
      age_info: ageInfo || null,
      breed: breed || null,
      weight: weight || null,
      coat_color: coatColor || null,
      owner_name: ownerName || null,
      owner_phone: ownerPhone || null,
      exam_findings: examFindings || null,
      structured_intake_answers: structuredIntakePayload || null,
    };
  };

  // ===== 新建病例 =====
  const handleCreateCase = () => {
    if (consultSessionId || loadingAnalyze || result) return;
    const owner = caseEditDraftOwner();
    if (!owner) { alert("请先登录，再核对新建病例。"); return; }
    navigate("/cases/new/edit", { state: { manualCase: { owner, values: {
      patient_name: patientName, species, sex, age_info: ageInfo, breed, weight,
      coat_color: coatColor, owner_name: ownerName, owner_phone: ownerPhone,
      chief_complaint: chiefComplaint, history, exam_findings: examFindings,
    } } } });
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

  const visibleCases = cases;
  const highRiskCount = cases.filter((item) => getCaseRiskMeta(item).key === "high").length;
  const dynamicCaseCount = cases.filter(isDynamicCase).length;

  const filteredSessionHistory = sessionHistory;
  const savedSessionCount = sessionHistory.filter((item) => item.case_id).length;
  const unsavedSessionCount = sessionHistory.length - savedSessionCount;
  const highRiskSessionCount = sessionHistory.filter((item) => getSessionRiskMeta(item).key === "high").length;
  const sessionTotalPages = Math.max(1, Math.ceil((sessionTotal || 0) / sessionPageSize));

  const currentQuestion = getCurrentQuestion();

  const workbenchValues = [consultSessionId, chiefComplaint, history, examFindings, patientName, species, sex, ageInfo, breed, weight, coatColor, ownerName, ownerPhone, consultAnswers, result, followupAnswer, structuredIntakeAnswers, auditLogReceipt];
  const workbenchRevision = JSON.stringify([...workbenchValues, historyAddendum]);
  const currentReadback = consultSaveReceipt?.sessionId === consultSessionId && consultSaveReceipt?.verified ? consultSaveReceipt : null;

  return (
    <div lang="zh-CN" translate="no" className="notranslate doctor-workbench">
      <header className="workbench-header">
        <div><span className="workbench-brand">Pet-Med-AI · 医生工作台</span><h1>一次问诊，核对后保存</h1><p>整理病史，核对本次内容，再回看已保存病例。</p></div>
        <details><summary>其他工作入口</summary><div className="workbench-actions">
          <Link to="/kpi" style={btnSecondary}>运维 KPI 仪表盘</Link>
          <Link to="/preventive-care/notification-queue" style={btnSecondary}>预防保健待联系队列</Link>
        </div></details>
        {/* Automated Reminder Delivery remains internal dry-run only; no clinic navigation link. */}
      </header>

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

      <section aria-label="本标签页草稿" className="workbench-secondary">
        {draft.offer ? <>
          <strong>发现本页未完成草稿</strong>
          <p>暂存时间：{new Date(draft.offer.updatedAt).toLocaleString("zh-CN")}。恢复后需要重新覆核和确认。</p>
          <div className="workbench-actions">
            <button type="button" disabled={restoringDraft} onClick={restoreLocalDraft}>{restoringDraft ? "正在恢复草稿…" : "恢复本页草稿"}</button>
            <button type="button" disabled={restoringDraft} onClick={() => { if (confirm("放弃这份本标签页草稿并重新填写？不会删除已保存病例。")) { draft.discard(); setDraftRestoreMessage(""); } }}>放弃草稿并重新填写</button>
          </div>
        </> : <p role="status">{draft.message || (draft.owner ? "填写后会暂存本标签页草稿。" : "登录后可暂存本标签页草稿。")}</p>}
        {draftRestoreMessage && <p role="status">{draftRestoreMessage}</p>}
        <p style={{ fontSize: 12 }}>草稿仅供当前标签页恢复，最长保留 8 小时；退出会清除。跨设备或关闭标签页后的恢复不保证，正式记录仍需核对保存。</p>
      </section>
      <fieldset disabled={!!draft.offer || restoringDraft} style={{ border: 0, padding: 0, margin: 0, minWidth: 0 }}>
      <WorkbenchSteps step={workbenchStep} onChange={changeWorkbenchStep} hasSession={!!consultSessionId} hasReadback={!!currentReadback} busy={workbenchBusy} patientName={patientName} species={species} ageInfo={ageInfo} />
      <h2 ref={stepHeading} tabIndex={-1} className="workbench-stage-title">{workbenchSteps[workbenchStep - 1]}</h2>
      <div hidden={workbenchStep !== 1} data-workbench-panel="1">
      {/* ====== 基础信息表单 ====== */}
      <section style={card}>
        <h2 style={h2}>宠物与主人信息</h2>
        <div className="intake-grid">
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
          <Field label="品种 / 宠物信息">
            <input value={breed} onChange={(e) => setBreed(e.target.value)} placeholder="如 贵宾 / 英短 / 混种" />
          </Field>
          <Field label="体重">
            <input value={weight} onChange={(e) => setWeight(e.target.value)} placeholder="如 5.2kg" />
          </Field>
          <Field label="毛色">
            <input value={coatColor} onChange={(e) => setCoatColor(e.target.value)} placeholder="如 白色 / 虎斑" />
          </Field>
          <Field label="主人姓名">
            <input value={ownerName} onChange={(e) => setOwnerName(e.target.value)} placeholder="如 张三" />
          </Field>
          <Field label="主人电话">
            <input value={ownerPhone} onChange={(e) => setOwnerPhone(e.target.value)} placeholder="如 13800000000" />
          </Field>
        </div>
      </section>

      {/* ====== 分析表单 ====== */}
      <section style={card}>
        <h2 style={h2}>宠主陈述与医生记录</h2>
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
          <div style={{ display: "flex", gap: 12, marginTop: 8, flexWrap: "wrap" }}>
            <button type="submit" disabled={loadingAnalyze} style={btn}>
              {loadingAnalyze ? "分析中…" : "提交分析（不入库）"}
            </button>
            <button type="button" onClick={handleCreateCase} disabled={loadingAnalyze || !!consultSessionId || !!result} style={btnSecondary}>
              {consultSessionId || result ? "请在第二步核对后保存" : "手工新建（核对后保存）"}
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
            
            {result?.structured_intake && (
              <StructuredIntakeBlock
                intake={result.structured_intake}
                answers={structuredIntakeAnswers}
                onChange={setStructuredIntakeAnswers}
                onSnapshot={setLastStructuredIntakeSubmission}
                onAppendHistory={(text) => {
                  const clean = String(text || "").trim();
                  if (!clean) return;
                  setHistory((prev) => [prev, clean].filter(Boolean).join("\n\n"));
                }}
              />
            )}
            {analysis && <Block title="分析">{analysis}</Block>}
            {treatment && <Block title="治疗建议">{treatment}</Block>}
            {prognosis && <Block title="预后">{prognosis}</Block>}
            {result && (
              <AiReviewAuditBlock
                result={result}
                suggestedAction={currentAuditSuggestedAction}
                reviewAction={auditReviewAction}
                setReviewAction={setAuditReviewAction}
                reason={auditReviewReason}
                setReason={setAuditReviewReason}
                note={auditReviewNote}
                setNote={setAuditReviewNote}
                clinicianId={auditClinicianId}
                setClinicianId={setAuditClinicianId}
                submitting={auditSubmitting}
                receipt={auditLogReceipt}
                onSubmit={handleSubmitAiReviewAudit}
              />
            )}

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

      {(savedConsultCaseId || historyAddendum) && <section aria-label="医生病史补记" className="workbench-secondary">
        <h3>给已保存病例追加病史</h3>
        <p>请只填写本次新增内容。第二步默认只追加病史，保留已保存的其他内容；需要同时同步问诊结果时，请在第二步明确选择。补记不会自动重新分析 AI 建议。</p>
        <label style={{ display: "block" }}>本次医生病史补记
          <textarea value={historyAddendum} onChange={e => setHistoryAddendum(e.target.value)} maxLength={20000} rows={5} style={{ display: "block", width: "100%", boxSizing: "border-box" }} placeholder="例如：复诊补充的症状、用药经过、主人新提供的病史" />
        </label>
        <p style={{ fontSize: 13 }}>首页其他字段的修改仍是草稿，更新病例不会自动写回这些修改。完全相同的补记不会重复追加。</p>
      </section>}
      {recoveredDraftNotes && <section aria-label="待重新整理的草稿补充" className="workbench-warning">
        <h3>原问诊已更新，以下补充尚未提交</h3>
        <p>请按当前问题重新整理；以下原文保留供核对，不会自动随回答提交。</p>
        <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{recoveredDraftNotes}</pre>
      </section>}
      <p>未填写不代表正常。草稿暂存不等于病例已保存，请完成第二步核对。</p>
      <div className="workbench-actions"><button type="button" className="workbench-primary" disabled={!consultSessionId || workbenchBusy} onClick={() => changeWorkbenchStep(2)}>进入保存前核对 →</button></div>
      </div>

      <div hidden={workbenchStep !== 2} data-workbench-panel="2">
        <p>核对预览后再确认保存；返回修改会取消原确认。</p>
        {(result || consultSessionId) && (
          <div
            style={{
              marginTop: 12,
              padding: 12,
              border: "1px solid #bfdbfe",
              borderRadius: 8,
              background: "#eff6ff",
            }}
          >
            {!savedConsultCaseId && (
              <ConsultSaveReview
                key={consultSessionId}
                sessionId={consultSessionId}
                onReturnToEdit={() => changeWorkbenchStep(1)}
                onWorkingChange={setWorkbenchBusy}
                contentRevision={workbenchRevision}
                payload={buildConsultSaveCasePayload()}
                revision={JSON.stringify([reviewNavigationVersion, consultAnswers, result, followupAnswer, auditLogReceipt, auditReviewAction, auditReviewReason, auditReviewNote, auditClinicianId])}
                allowed={isAuthed && !auditReviewRequired}
                blocked={loadingSession || loadingAnalyze || loadingFollowup || auditSubmitting || !consultSessionId || !chiefComplaint.trim()}
                hasPendingAnswers={!!followupAnswer.trim()}
                onSaved={async (record, receipt) => {
                  if (!receipt.inputsChanged && !recoveredDraftNotes) draft.markSaved();
                  setConsultSaveReceipt({ sessionId: consultSessionId, caseId: record.id, verified: true, inputsChanged: receipt.inputsChanged, record, revision: workbenchRevision, mode: "create" });
                  setWorkbenchStep(3);
                  setSavedConsultCaseId(record.id);
                  await fetchCases({ page: 1 });
                  await fetchSessionHistory();
                }}
                onBound={(caseId) => {
                  setConsultSaveReceipt({ sessionId: consultSessionId, caseId, verified: false });
                  setSavedConsultCaseId(caseId);
                }}
              />
            )}

            {savedConsultCaseId && (
              <ConsultUpdateReview
                key={`${consultSessionId}:${savedConsultCaseId}`}
                sessionId={consultSessionId}
                onReturnToEdit={() => changeWorkbenchStep(1)}
                onWorkingChange={setWorkbenchBusy}
                contentRevision={workbenchRevision}
                caseId={savedConsultCaseId}
                historyAddendum={historyAddendum}
                allowed={isAuthed && !auditReviewRequired}
                blocked={loadingSession || loadingAnalyze || loadingFollowup || auditSubmitting}
                hasPendingAnswers={!!followupAnswer.trim() || Object.values(structuredIntakeAnswers).some(value => value != null && String(value).trim() !== "")}
                revision={JSON.stringify([reviewNavigationVersion, consultSessionId, consultAnswers, result, chiefComplaint, history, examFindings, patientName, species, sex, ageInfo, breed, weight, coatColor, ownerName, ownerPhone, followupAnswer, structuredIntakeAnswers, auditLogReceipt, auditReviewAction, auditReviewReason, auditReviewNote, auditClinicianId, loadingSession, loadingAnalyze, loadingFollowup, auditSubmitting])}
                onUpdated={async (record, receipt) => {
                  const cleared = historyAddendum === receipt.historyAddendum;
                  if (cleared) setHistoryAddendum("");
                  setConsultSaveReceipt({ sessionId: consultSessionId, caseId: record.id, verified: true, record, revision: JSON.stringify([...workbenchValues, cleared ? "" : historyAddendum]), mode: "update", inputsChanged: receipt.inputsChanged });
                  setWorkbenchStep(3);
                  await fetchCases({ page: 1 }); await fetchSessionHistory();
                }}
              />
            )}

          </div>
        )}


        <div className="workbench-actions"><button type="button" disabled={workbenchBusy} onClick={() => changeWorkbenchStep(1)}>回到问诊整理</button></div>
      </div>
      <div hidden={workbenchStep !== 3} data-workbench-panel="3">
        <SavedCasePanel receipt={currentReadback} hasUnsavedChanges={!!currentReadback && (currentReadback.inputsChanged || currentReadback.revision !== workbenchRevision)} onContinue={() => changeWorkbenchStep(1)} />
      </div>
      <details className="workbench-secondary"><summary>历史问诊与会话恢复</summary>
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
              onClick={() => fetchSessionHistory({ page: sessionPage })}
              disabled={loadingHistory}
              style={btnSecondary}
            >
              {loadingHistory ? "刷新中…" : "刷新历史会话"}
            </button>
          </div>

          <div style={{ marginTop: 10 }}>
            <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginBottom: 6 }}>
              <div style={{ fontWeight: 600 }}>最近历史会话</div>
              <select
                value={sessionRiskFilter}
                onChange={(e) => setSessionRiskFilter(e.target.value)}
                style={{ padding: "5px 8px", border: "1px solid #e5e7eb", borderRadius: 8, fontSize: 13 }}
                title="按风险等级筛选问诊"
              >
                <option value="all">全部风险</option>
                <option value="high">高风险</option>
                <option value="medium">中风险</option>
                <option value="low">低风险</option>
                <option value="unknown">未记录风险</option>
              </select>
              <select
                value={sessionSavedFilter}
                onChange={(e) => setSessionSavedFilter(e.target.value)}
                style={{ padding: "5px 8px", border: "1px solid #e5e7eb", borderRadius: 8, fontSize: 13 }}
                title="按是否已保存病例筛选问诊"
              >
                <option value="all">全部状态</option>
                <option value="saved">已保存病例</option>
                <option value="unsaved">未保存病例</option>
              </select>
            </div>

            <div style={{ marginBottom: 8, fontSize: 13, opacity: 0.72 }}>
              当前显示 {filteredSessionHistory.length} / {sessionTotal} 条
              <span style={{ marginLeft: 10 }}>本页高风险：{highRiskSessionCount} 条</span>
              <span style={{ marginLeft: 10 }}>本页已保存：{savedSessionCount} 条</span>
              <span style={{ marginLeft: 10 }}>本页未保存：{unsavedSessionCount} 条</span>
            </div>

            {sessionTotal > 0 ? (
              filteredSessionHistory.length ? (
                <div style={{ display: "grid", gap: 6 }}>
                  {filteredSessionHistory.map((item) => {
                    const risk = getSessionRiskMeta(item);
                    return (
                      <div
                        key={item.session_id}
                        style={{
                          textAlign: "left",
                          padding: 8,
                          border: "1px solid #e5e7eb",
                          borderRadius: 8,
                          background: "#fff",
                        }}
                      >
                        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", fontSize: 13 }}>
                          <button
                            type="button"
                            onClick={() => loadSession(item.session_id)}
                            style={{ ...btnTiny, fontWeight: 700 }}
                            title="恢复该问诊"
                          >
                            {item.session_id?.slice(0, 8) || "-"}
                          </button>
                          <span style={getSessionRiskBadgeStyle(risk.key)}>{risk.label}</span>
                          <span style={{ opacity: 0.7 }}>{formatSessionDate(item.updated_at || item.created_at)}</span>
                          <span style={{ opacity: 0.8 }}>第 {item.round ?? "-"} 轮 · 已回答 {item.answered_count ?? 0} 条</span>
                          {item.case_id ? (
                            <Link
                              to={`/cases/${item.case_id}`}
                              style={{ ...btnTiny, textDecoration: "none", display: "inline-block" }}
                            >
                              查看病例 #{item.case_id}
                            </Link>
                          ) : (
                            <>
                              <span style={{ fontSize: 12, color: "#b45309" }}>未保存病例</span>
                              <button
                                type="button"
                                onClick={() => handleDeleteConsultSession(item.session_id)}
                                disabled={deletingSessionId === item.session_id}
                                style={{ ...btnTiny, borderColor: "#ef4444", color: "#b91c1c", background: "#fff" }}
                                title="删除未保存问诊"
                              >
                                {deletingSessionId === item.session_id ? "删除中…" : "删除问诊"}
                              </button>
                            </>
                          )}
                        </div>
                        <button
                          type="button"
                          onClick={() => loadSession(item.session_id)}
                          style={{
                            marginTop: 6,
                            padding: 0,
                            border: 0,
                            background: "transparent",
                            cursor: "pointer",
                            textAlign: "left",
                            fontSize: 13,
                            opacity: 0.75,
                          }}
                          title="点击恢复该问诊"
                        >
                          {truncateText(item.text)}
                        </button>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div style={{ opacity: 0.65 }}>当前筛选条件下暂无历史会话。</div>
              )
            ) : (
              <div style={{ opacity: 0.65 }}>暂无历史会话，点击“刷新历史会话”后可查看。</div>
            )}

            <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginTop: 8 }}>
              <button
                type="button"
                onClick={() => fetchSessionHistory({ page: Math.max(1, sessionPage - 1) })}
                disabled={loadingHistory || sessionPage <= 1}
                style={btnTiny}
              >
                上一页
              </button>
              <span style={{ fontSize: 13, opacity: 0.75 }}>
                第 {sessionPage} / {sessionTotalPages} 页
              </span>
              <button
                type="button"
                onClick={() => fetchSessionHistory({ page: Math.min(sessionTotalPages, sessionPage + 1) })}
                disabled={loadingHistory || sessionPage >= sessionTotalPages}
                style={btnTiny}
              >
                下一页
              </button>
            </div>
          </div>
        </div>

      </details>
      <details className="workbench-secondary"><summary>病例列表与检索</summary>
      {/* ====== 列表（搜索+分页 + 批量操作） ====== */}
      <section style={card}>
        <h2 style={h2}>病例列表</h2>
        {!isAuthed ? <p role="status">请先登录后查看病例列表。</p> : <>
        {/* 搜索 + 操作 */}
        <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8 }}>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="搜索：病例名 / 物种 / 主诉"
            style={{ flex: 1, padding: "8px 10px", border: "1px solid #e5e7eb", borderRadius: 8 }}
          />
          <select
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            style={{ padding: "8px 10px", border: "1px solid #e5e7eb", borderRadius: 8 }}
            title="按风险等级筛选"
          >
            <option value="all">全部风险</option>
            <option value="high">高风险</option>
            <option value="medium">中风险</option>
            <option value="low">低风险</option>
            <option value="unknown">未记录风险</option>
          </select>
          <select
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
            style={{ padding: "8px 10px", border: "1px solid #e5e7eb", borderRadius: 8 }}
            title="按病例来源筛选"
          >
            <option value="all">全部来源</option>
            <option value="dynamic">动态问诊</option>
            <option value="manual">手动录入</option>
          </select>
          <button onClick={() => { if (page !== 1) setPage(1); else fetchCases({ page: 1 }); }} disabled={loadingCases} style={btn}>
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

        <div style={{ marginBottom: 8, fontSize: 13, opacity: 0.75 }}>
          当前显示 {visibleCases.length} / {total} 条
          <span style={{ marginLeft: 12 }}>高风险：{highRiskCount} 条</span>
          <span style={{ marginLeft: 12 }}>动态问诊病例：{dynamicCaseCount} 条</span>
        </div>

        {/* 表格 */}
        {visibleCases.length === 0 ? (
          <p style={{ opacity: 0.7 }}>{cases.length === 0 ? "暂无病例。" : "当前筛选条件下暂无病例。"}</p>
        ) : (
          <>
            <table style={table}>
              <thead>
                <tr>
                  <th style={{ width: 52, textAlign: "center" }}>选择</th>
                  <th>ID</th>
                  <th>病例名</th>
                  <th>物种</th>
                  <th>风险</th>
                  <th>来源</th>
                  <th>主诉</th>
                  <th>已存分析</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {visibleCases.map((c) => (
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
                    <td>
                      <span style={getRiskBadgeStyle(getCaseRiskMeta(c).key)}>
                        {getCaseRiskMeta(c).label}
                      </span>
                    </td>
                    <td>{isDynamicCase(c) ? "动态问诊" : "手动录入"}</td>
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
        </>}
      </section>

      </details>

      </fieldset>

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
        <Route path="/kpi" element={<KpiDashboard />} />
        <Route path="/ops" element={<OpsDashboard />} />
        <Route path="/webhooks/emr/inbox" element={<WebhookInboxPage />} />
        <Route path="/emr/import-batches" element={<EmrImportBatchPlanningPage />} />
        <Route path="/preventive-care/notification-queue" element={<PreventiveCareNotificationQueuePage />} />
        <Route path="*" element={<div style={{ padding: 24 }}>页面不存在（404）。</div>} />
              {/* Commercial Launch Feature Scope Lock V1: route remains for internal dry-run until Access Review adds authorization. */}
        <Route path="/automated-reminder-delivery/manual-approval" element={<AutomatedReminderDeliveryManualApprovalPage />} />
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


function AiReviewAuditBlock({
  result,
  suggestedAction,
  reviewAction,
  setReviewAction,
  reason,
  setReason,
  note,
  setNote,
  clinicianId,
  setClinicianId,
  submitting,
  receipt,
  onSubmit,
}) {
  if (!result) return null;

  const requiresReason = reviewAction === "modified" || reviewAction === "rejected";
  const canSubmit = Boolean(clinicianId.trim()) && (!requiresReason || (reason.trim() && note.trim().length >= 10));

  return (
    <div style={{ marginTop: 12, padding: 12, border: "1px solid #a7f3d0", borderRadius: 10, background: "#ecfdf5" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "flex-start", flexWrap: "wrap" }}>
        <div>
          <div style={{ fontWeight: 800, marginBottom: 4 }}>AI 建议人工覆核</div>
          <div style={{ fontSize: 13, opacity: 0.78 }}>
            保存病例前需由医生确认 AI 建议，并写入 append-only 审计日志。
          </div>
        </div>
        {receipt?.log_id && (
          <div style={{ fontSize: 12, color: "#047857", fontWeight: 700, textAlign: "right" }}>
            已写入审计<br />
            <code>{String(receipt.log_id).slice(0, 12)}</code>
          </div>
        )}
      </div>

      <div style={{ marginTop: 10 }}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 4 }}>模型建议摘要</div>
        <pre style={{ margin: 0, padding: 10, border: "1px solid #bbf7d0", borderRadius: 8, background: "#fff", whiteSpace: "pre-wrap", fontFamily: "inherit", fontSize: 13, lineHeight: 1.6, maxHeight: 180, overflow: "auto" }}>
          {suggestedAction || "暂无 AI 建议摘要"}
        </pre>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 10 }}>
        <Field label="临床人员 ID / 签名">
          <input
            value={clinicianId}
            onChange={(e) => setClinicianId(e.target.value)}
            placeholder="如 HS-0001 / Dr.Zhao"
            disabled={Boolean(receipt?.log_id) || submitting}
          />
        </Field>

        <Field label="处理动作">
          <select
            value={reviewAction}
            onChange={(e) => setReviewAction(e.target.value)}
            disabled={Boolean(receipt?.log_id) || submitting}
          >
            <option value="accepted">接受建议</option>
            <option value="modified">接受并修改</option>
            <option value="rejected">拒绝并替代</option>
          </select>
        </Field>
      </div>

      {requiresReason && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <Field label="修改 / 拒绝理由">
            <select
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              disabled={Boolean(receipt?.log_id) || submitting}
            >
              <option value="">请选择理由</option>
              <option value="影像学不一致">影像学不一致</option>
              <option value="实验室指标矛盾">实验室指标矛盾</option>
              <option value="主诉与体征不符">主诉与体征不符</option>
              <option value="药物禁忌">药物禁忌</option>
              <option value="费用与依从性">费用与依从性</option>
              <option value="其他">其他</option>
            </select>
          </Field>
          <Field label="补充说明 / 替代方案">
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={3}
              placeholder="至少 10 字；说明医生修改或拒绝 AI 建议的依据"
              disabled={Boolean(receipt?.log_id) || submitting}
            />
          </Field>
        </div>
      )}

      {!requiresReason && (
        <Field label="补充说明（可选）">
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={2}
            placeholder="可补充医生确认意见"
            disabled={Boolean(receipt?.log_id) || submitting}
          />
        </Field>
      )}

      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginTop: 8 }}>
        <button
          type="button"
          onClick={onSubmit}
          disabled={submitting || Boolean(receipt?.log_id) || !canSubmit}
          style={btn}
        >
          {submitting ? "写入中…" : receipt?.log_id ? "审计已写入" : "确认覆核并写入审计"}
        </button>
        <span style={{ fontSize: 12, opacity: 0.7 }}>
          提交后不可更改；如需补充，请新增一条覆核记录。
        </span>
      </div>

      {requiresReason && !canSubmit && (
        <div style={{ marginTop: 6, fontSize: 12, color: "#b45309" }}>
          修改或拒绝时，必须选择理由，并填写至少 10 字说明。
        </div>
      )}
    </div>
  );
}

function structuredAnswerKey(sectionKey, questionKey) {
  return `${sectionKey || "section"}.${questionKey || "question"}`;
}

function setStructuredAnswerValue(answers, key, value) {
  return { ...answers, [key]: value };
}

function countStructuredAnswers(answers = {}) {
  return Object.values(answers).filter((value) => String(value || "").trim()).length;
}

function buildStructuredIntakeSubmission(intake, answers = {}) {
  if (!intake || !Array.isArray(intake.sections)) return null;
  if (intake.fillable === false) return null;

  const sections = intake.sections
    .map((section) => {
      const sectionAnswers = (section.questions || [])
        .map((question) => {
          const key = structuredAnswerKey(section.key, question.key);
          const answer = String(answers[key] || "").trim();
          if (!answer) return null;
          return {
            key: question.key,
            label: question.label,
            answer,
            answer_type: question.answer_type || "text",
            required: Boolean(question.required),
            triggered: Boolean(question.triggered),
          };
        })
        .filter(Boolean);

      if (!sectionAnswers.length) return null;
      return {
        key: section.key,
        title: section.title,
        answers: sectionAnswers,
      };
    })
    .filter(Boolean);

  if (!sections.length) return null;

  return {
    version: intake.version || "exotic-structured-intake-v1",
    template_key: intake.template_key,
    label: intake.label,
    sections,
  };
}

function formatStructuredIntakeSubmissionForHistory(submission) {
  if (!submission || !Array.isArray(submission.sections)) return "";
  const rows = [];

  for (const section of submission.sections) {
    const sectionTitle = section.title || section.key || "未命名分组";
    for (const item of section.answers || []) {
      const answer = String(item.answer || "").trim();
      if (!answer) continue;
      rows.push({
        sectionTitle,
        label: item.label || item.key || "未命名问题",
        answer,
        required: Boolean(item.required),
        triggered: Boolean(item.triggered),
      });
    }
  }

  if (!rows.length) return "";

  const template = submission.label || submission.template_key || "结构化问诊模板";
  const title = submission.category === "companion" || ["dog", "cat"].includes(submission.template_key)
    ? "犬猫结构化问诊记录"
    : "异宠结构化问诊记录";

  const lines = [`【${title}】`, `结构化问诊模板：${template}`];
  let currentSection = "";

  for (const row of rows) {
    if (row.sectionTitle !== currentSection) {
      currentSection = row.sectionTitle;
      lines.push(`【${currentSection}】`);
    }
    const flags = [];
    if (row.required) flags.push("必填");
    if (row.triggered) flags.push("命中特征");
    const flagText = flags.length ? `（${flags.join("、")}）` : "";
    lines.push(`- ${row.label}${flagText}：${row.answer}`);
  }

  return lines.join("\n").trim();
}

async function copyStructuredTextToClipboard(text) {
  const clean = String(text || "").trim();
  if (!clean) return false;
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(clean);
    return true;
  }

  const textarea = document.createElement("textarea");
  textarea.value = clean;
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  const ok = document.execCommand("copy");
  textarea.remove();
  return ok;
}

function StructuredIntakeBlock({ intake, answers = {}, onChange, onAppendHistory, onSnapshot }) {
  if (!intake || !Array.isArray(intake.sections) || intake.sections.length === 0) return null;

  const activeFeatures = Array.isArray(intake.active_features) ? intake.active_features : [];
  const redFlags = Array.isArray(intake.red_flag_prompts) ? intake.red_flag_prompts : [];
  const fillable = intake.fillable !== false;
  const answeredCount = fillable ? countStructuredAnswers(answers) : 0;
  const totalQuestions = intake.sections.reduce((sum, section) => sum + (section.questions || []).length, 0);
  const requiredQuestions = intake.sections.reduce(
    (sum, section) => sum + (section.questions || []).filter((question) => question.required).length,
    0
  );
  const requiredAnswered = intake.sections.reduce(
    (sum, section) => sum + (section.questions || []).filter((question) => {
      if (!question.required) return false;
      const key = structuredAnswerKey(section.key, question.key);
      return String(answers[key] || "").trim();
    }).length,
    0
  );
  const submission = fillable ? buildStructuredIntakeSubmission(intake, answers) : null;
  const historyPreview = formatStructuredIntakeSubmissionForHistory(submission);

  const handleChange = (sectionKey, questionKey, value) => {
    if (!onChange) return;
    const key = structuredAnswerKey(sectionKey, questionKey);
    onChange((prev) => setStructuredAnswerValue(prev || {}, key, value));
  };

  const handleClear = () => {
    if (onChange) onChange({});
  };

  const handleAppendToHistory = () => {
    if (!historyPreview) return;
    if (onSnapshot && submission) onSnapshot(submission);
    if (onAppendHistory) onAppendHistory(historyPreview);
  };

  const handleCopyPreview = async () => {
    if (!historyPreview) return;
    if (onSnapshot && submission) onSnapshot(submission);
    const ok = await copyStructuredTextToClipboard(historyPreview);
    alert(ok ? "已复制结构化问诊文本" : "复制失败，请手动选择文本复制");
  };

  return (
    <div style={{ marginTop: 12, padding: 12, border: "1px solid #cbd5e1", borderRadius: 8, background: "#f8fafc" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "flex-start", flexWrap: "wrap" }}>
        <div>
          <div style={{ fontWeight: 700, marginBottom: 4 }}>结构化问诊模板</div>
          <div style={{ fontSize: 13, opacity: 0.78, marginBottom: 8 }}>
            {intake.label || intake.template_key || "异宠模板"}
            {intake.summary ? `｜${intake.summary}` : ""}
          </div>
        </div>
        <div style={{ fontSize: 12, opacity: 0.72, textAlign: "right" }}>
          {fillable ? (
            <>
              已填写 {answeredCount} / {totalQuestions} 项<br />
              必填 {requiredAnswered} / {requiredQuestions} 项
            </>
          ) : (
            <>展示 {totalQuestions} 项<br />必填提示 {requiredQuestions} 项</>
          )}
        </div>
      </div>

      {activeFeatures.length > 0 && (
        <div style={{ fontSize: 12, marginBottom: 8, opacity: 0.75 }}>
          命中特征：{activeFeatures.join("、")}
        </div>
      )}

      {redFlags.length > 0 && (
        <div style={{ marginBottom: 10, padding: 8, border: "1px dashed #f59e0b", borderRadius: 8, background: "#fffbeb" }}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 4 }}>红旗提醒</div>
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {redFlags.map((item, idx) => (
              <li key={idx} style={{ fontSize: 13, lineHeight: 1.6 }}>{item}</li>
            ))}
          </ul>
        </div>
      )}

      <div style={{ display: "grid", gap: 8 }}>
        {intake.sections.map((section) => (
          <div key={section.key} style={{ border: "1px solid #e5e7eb", borderRadius: 8, background: "#fff", padding: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center", marginBottom: 6 }}>
              <strong>{section.title}</strong>
              <span style={{ fontSize: 12, opacity: 0.65 }}>
                必填 {section.required_count || 0} 项 · 命中 {section.triggered_count || 0} 项
              </span>
            </div>

            <div style={{ display: "grid", gap: 8 }}>
              {(section.questions || []).map((question) => {
                const key = structuredAnswerKey(section.key, question.key);
                const value = answers[key] || "";
                return (
                  <label key={question.key} style={{ display: "block" }}>
                    <div style={{ lineHeight: 1.55, marginBottom: 4 }}>
                      <span style={{ fontWeight: question.triggered ? 700 : 600 }}>{question.label}</span>
                      {question.required && <span style={{ marginLeft: 6, fontSize: 12, color: "#b91c1c" }}>必填</span>}
                      {question.triggered && <span style={{ marginLeft: 6, fontSize: 12, color: "#0369a1" }}>已命中</span>}
                    </div>
                    {!fillable ? (
                      <div style={{ padding: 8, border: "1px dashed #cbd5e1", borderRadius: 8, background: question.triggered ? "#eff6ff" : "#f8fafc", fontSize: 13, lineHeight: 1.6 }}>
                        待采集：{question.placeholder || question.label}
                      </div>
                    ) : question.options && Array.isArray(question.options) ? (
                      <select
                        value={value}
                        onChange={(e) => handleChange(section.key, question.key, e.target.value)}
                        style={{ width: "100%", padding: 8, border: "1px solid #e5e7eb", borderRadius: 8 }}
                      >
                        <option value="">请选择 / 待补充</option>
                        {question.options.map((option) => (
                          <option key={option.value || option} value={option.value || option}>{option.label || option}</option>
                        ))}
                      </select>
                    ) : (
                      <textarea
                        rows={2}
                        value={value}
                        onChange={(e) => handleChange(section.key, question.key, e.target.value)}
                        placeholder="填写本项结构化病史；提交追问时会随本轮上下文发给 AI"
                        style={{ width: "100%", boxSizing: "border-box", padding: 8, border: "1px solid #e5e7eb", borderRadius: 8 }}
                      />
                    )}
                    {question.clinical_reason && (
                      <div style={{ fontSize: 12, opacity: 0.68, marginTop: 3 }}>临床意义：{question.clinical_reason}</div>
                    )}
                  </label>
                );
              })}
            </div>
          </div>
        ))}
      </div>


      {fillable && historyPreview && (
        <div style={{ marginTop: 10, border: "1px solid #bfdbfe", background: "#eff6ff", borderRadius: 8, padding: 10 }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center", flexWrap: "wrap", marginBottom: 6 }}>
            <strong style={{ fontSize: 13 }}>结构化答案病史预览</strong>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button type="button" onClick={handleAppendToHistory} style={btnTiny}>
                写入病史
              </button>
              <button type="button" onClick={handleCopyPreview} style={btnTiny}>
                复制文本
              </button>
            </div>
          </div>
          <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontFamily: "inherit", fontSize: 13, lineHeight: 1.6 }}>
            {historyPreview}
          </pre>
        </div>
      )}

      <div style={{ marginTop: 8, display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <div style={{ fontSize: 12, opacity: 0.65 }}>
          {fillable ? "这些答案不会作为独立病例字段保存；提交追问时会作为本轮 AI 上下文一起发送。" : "本阶段仅展示犬猫结构化问诊清单；后续 V2 再开放填写并随追问提交。"}
        </div>
        <button type="button" onClick={handleClear} disabled={!answeredCount} style={btnTiny}>
          清空结构化答案
        </button>
      </div>

      {intake.disclaimer && <div style={{ marginTop: 8, fontSize: 12, opacity: 0.65 }}>{intake.disclaimer}</div>}
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
