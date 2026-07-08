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
  const [preventiveCareReminders, setPreventiveCareReminders] = useState([]);
  const [preventiveCarePreview, setPreventiveCarePreview] = useState([]);
  const [preventiveCareLoading, setPreventiveCareLoading] = useState(false);
  const [preventiveCareBusy, setPreventiveCareBusy] = useState("");
  const [preventiveCareStatus, setPreventiveCareStatus] = useState("");
  const [exportingDoc, setExportingDoc] = useState("");
  const [exportStatus, setExportStatus] = useState("");
  const [diagnosticDataSummary, setDiagnosticDataSummary] = useState(null);
  const [diagnosticDataLoading, setDiagnosticDataLoading] = useState(false);
  const [diagnosticDataStatus, setDiagnosticDataStatus] = useState("");
  // --- Diagnostic Assistance Case Detail UI V1 state: start ---
  const [diagnosticAssistancePreview, setDiagnosticAssistancePreview] = useState(null);
  const [diagnosticAssistanceLoading, setDiagnosticAssistanceLoading] = useState(false);
  const [diagnosticAssistanceStatus, setDiagnosticAssistanceStatus] = useState("");
  // --- Diagnostic Assistance Case Detail UI V1 state: end ---
  // --- Case Detail Treatment Framework Preview UI V1 state: start ---
  const [treatmentFrameworkPreview, setTreatmentFrameworkPreview] = useState(null);
  const [treatmentFrameworkLoading, setTreatmentFrameworkLoading] = useState(false);
  const [treatmentFrameworkStatus, setTreatmentFrameworkStatus] = useState("");
  const [confirmedDiagnosisLabel, setConfirmedDiagnosisLabel] = useState("");
  const [confirmedDiagnosisBy, setConfirmedDiagnosisBy] = useState("");
  // --- Case Detail Treatment Framework Preview UI V1 state: end ---

  // --- Case Detail Treatment Framework Signed Review State UI V1 state: start ---
  const [signedReviewStatePreview, setSignedReviewStatePreview] = useState(null);
  const [signedReviewStateLoading, setSignedReviewStateLoading] = useState(false);
  const [signedReviewStateStatus, setSignedReviewStateStatus] = useState("");
  const [signedReviewStateReviewedBy, setSignedReviewStateReviewedBy] = useState("");
  const [signedReviewStateReviewDecision, setSignedReviewStateReviewDecision] = useState("approve_for_clinician_use");
  const [signedReviewStateSignedBy, setSignedReviewStateSignedBy] = useState("");
  const [signedReviewStateSignoffDecision, setSignedReviewStateSignoffDecision] = useState("sign_internal_review");
  const [signedReviewStateAuditRequestId, setSignedReviewStateAuditRequestId] = useState("");
  // --- Case Detail Treatment Framework Signed Review State UI V1 state: end ---
// --- Case Detail Treatment Framework Signed Review State Persistence UI V1 state: start ---
const [signedReviewStatePersistencePreview, setSignedReviewStatePersistencePreview] = useState(null);
const [signedReviewStatePersistenceLoading, setSignedReviewStatePersistenceLoading] = useState(false);
const [signedReviewStatePersistenceStatus, setSignedReviewStatePersistenceStatus] = useState("");
const [signedReviewStatePersistenceRequestedBy, setSignedReviewStatePersistenceRequestedBy] = useState("");
// --- Case Detail Treatment Framework Signed Review State Persistence UI V1 state: end ---
  // --- Case Detail Treatment Framework Signed Review State Persistence Migration UI V1 state: start ---
  const [signedReviewStateMigrationPreview, setSignedReviewStateMigrationPreview] = useState(null);
  const [signedReviewStateMigrationLoading, setSignedReviewStateMigrationLoading] = useState(false);
  const [signedReviewStateMigrationStatus, setSignedReviewStateMigrationStatus] = useState("");
  const [signedReviewStateMigrationRequestedBy, setSignedReviewStateMigrationRequestedBy] = useState("");
  // --- Case Detail Treatment Framework Signed Review State Persistence Migration UI V1 state: end ---





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

  // Case Detail Diagnostic Data Display V1: read-only diagnostic summary panel.
  const fetchDiagnosticDataSummary = async () => {
    if (!data?.id) return;

    try {
      setDiagnosticDataLoading(true);
      const res = await api.get(`/api/diagnostic-data/cases/${data.id}/summary`);
      const payload = res.data || {};
      const counts = payload.counts || {};
      setDiagnosticDataSummary(payload);
      setDiagnosticDataStatus(
        `已加载诊断数据：reports=${counts.reports || 0} · observations=${counts.observations || 0} · imaging=${counts.imaging_studies || 0} · read_only=true · writes_database=false`
      );
    } catch (e) {
      console.error("Diagnostic data summary load failed:", e);
      const detail = e?.response?.data?.detail;
      const msg = typeof detail === "string" ? detail : (detail ? JSON.stringify(detail) : String(e?.message || e));
      setDiagnosticDataStatus(`诊断数据加载失败：${msg}`);
    } finally {
      setDiagnosticDataLoading(false);
    }
  };

  // --- Diagnostic Assistance Case Detail UI V1 actions: start ---
  const buildDiagnosticAssistancePreview = async () => {
    if (!data?.id) return;

    const caseContext = buildDiagnosticAssistanceCaseContext(data);
    const labSummary = buildDiagnosticAssistanceLabSummary(diagnosticDataSummary);
    const imagingSummary = buildDiagnosticAssistanceImagingSummary(diagnosticDataSummary);

    const basePayload = {
      case_id: Number(data.id),
      chief_complaint: data.chief_complaint || "",
      history: data.history || "",
      dynamic_intake: data.history || "",
      exam_findings: data.exam_findings || "",
      case_context: caseContext,
      lab_summary: labSummary,
      lab_abnormal_summary: labSummary,
      imaging_summary: imagingSummary,
      imaging_report_summary: imagingSummary,
      clinician_review_workflow: {
        decision: "case_detail_ui_preview_requires_clinician_review",
        status: "pending_clinician_review",
        human_review_required: true,
        clinician_signoff_required: true,
        final_signoff_persisted: false,
        review_status_persisted: false,
        client_release_allowed: false,
        not_a_diagnosis: true,
        not_a_treatment_plan: true,
        not_a_prescription: true,
      },
      treatment_boundary: {
        decision: "review_only",
        blocked: false,
        human_review_required: true,
        not_a_diagnosis: true,
        not_a_treatment_plan: true,
        not_a_prescription: true,
        not_a_drug_dose_recommendation: true,
        boundary_only: true,
      },
      drug_dose_safety: {
        decision: "dose_output_blocked_in_case_detail_ui",
        returns_drug_dose: false,
        returns_drug_route: false,
        returns_drug_frequency: false,
        requires_human_review: true,
      },
    };

    try {
      setDiagnosticAssistanceLoading(true);
      setDiagnosticAssistanceStatus("正在生成诊断辅助预览：problem list → differential candidates → evidence trace；dry_run=true · writes_database=false");

      const problemRes = await api.post(
        "/api/diagnostic-data/dry-run/problem-list/build",
        basePayload
      );
      const problemPayload = problemRes.data || {};
      const problemList = Array.isArray(problemPayload.problem_list_preview)
        ? problemPayload.problem_list_preview
        : [];

      const differentialRes = await api.post(
        "/api/diagnostic-data/dry-run/differential-diagnosis/candidates/build",
        {
          ...basePayload,
          problem_list_preview: problemList,
          problem_list: problemList,
          upstream_problem_list_preview: problemPayload,
        }
      );
      const differentialPayload = differentialRes.data || {};
      const candidateList = Array.isArray(differentialPayload.differential_diagnosis_candidates_preview)
        ? differentialPayload.differential_diagnosis_candidates_preview
        : [];

      const traceRes = await api.post(
        "/api/diagnostic-data/dry-run/diagnostic-reasoning/evidence-trace/build",
        {
          ...basePayload,
          problem_list_preview: problemList,
          differential_diagnosis_candidates_preview: candidateList,
          differential_candidates_preview: candidateList,
          upstream_problem_list_preview: problemPayload,
          upstream_differential_candidates_preview: differentialPayload,
        }
      );
      const tracePayload = traceRes.data || {};

      const preview = {
        problem_list: problemPayload,
        differential_candidates: differentialPayload,
        evidence_trace: tracePayload,
        built_at: new Date().toISOString(),
        safety_summary: {
          dry_run: true,
          writes_database: false,
          writes_audit_log: false,
          persists_reasoning_trace: false,
          no_final_diagnosis: true,
          no_treatment_plan: true,
          no_prescription: true,
          no_drug_dose: true,
          not_client_facing: true,
          requires_human_review: true,
          clinician_signoff_required: true,
        },
      };

      setDiagnosticAssistancePreview(preview);
      setDiagnosticAssistanceStatus(
        `已生成诊断辅助预览：problem_list=${problemList.length} · differential_candidates=${candidateList.length} · evidence_trace=${Array.isArray(tracePayload.diagnostic_reasoning_evidence_trace_preview) ? tracePayload.diagnostic_reasoning_evidence_trace_preview.length : 0} · dry_run=true · writes_database=false`
      );
    } catch (e) {
      console.error("Diagnostic assistance preview failed:", e);
      const detail = e?.response?.data?.detail;
      const msg = typeof detail === "string" ? detail : (detail ? JSON.stringify(detail) : String(e?.message || e));
      setDiagnosticAssistanceStatus(`诊断辅助预览失败：${msg}`);
      alert(`诊断辅助预览失败：${msg}`);
    } finally {
      setDiagnosticAssistanceLoading(false);
    }
  };
  // --- Diagnostic Assistance Case Detail UI V1 actions: end ---
  // --- Case Detail Treatment Framework Preview UI V1 actions: start ---
  const buildTreatmentFrameworkPreview = async () => {
    if (!data?.id) return;

    const diagnosisLabel = confirmedDiagnosisLabel.trim();
    const confirmedBy = confirmedDiagnosisBy.trim();

    if (!diagnosisLabel || !confirmedBy) {
      setTreatmentFrameworkStatus("请先填写医生确认诊断和确认医生；AI 不确认诊断。requires_clinician_confirmed_diagnosis=true");
      return;
    }

    const diagnosticContext = buildTreatmentFrameworkDiagnosticContext(
      data,
      diagnosticDataSummary,
      diagnosticAssistancePreview
    );

    try {
      setTreatmentFrameworkLoading(true);
      setTreatmentFrameworkStatus("正在生成确诊后治疗框架预览：dry_run=true · writes_database=false · no prescription · no dose/route/frequency");

      const res = await api.post(
        "/api/diagnostic-data/dry-run/confirmed-diagnosis/treatment-framework/build",
        {
          case_id: Number(data.id),
          confirmed_diagnosis_label: diagnosisLabel,
          confirmed_by: confirmedBy,
          confirmation_source: "clinician",
          ai_generated: false,
          diagnostic_context: diagnosticContext,
          case_context: buildDiagnosticAssistanceCaseContext(data),
        }
      );

      const payload = res.data || {};
      setTreatmentFrameworkPreview(payload);
      setTreatmentFrameworkStatus(
        [
          "已生成医生端治疗框架预览",
          "read_only=true",
          "writes_database=false",
          "writes_case_treatment=false",
          "creates_prescription=false",
          "writes_prescription=false",
          "returns_drug_dose=false",
          "returns_drug_route=false",
          "returns_drug_frequency=false",
          "not_client_facing=true",
          "requires_human_review=true",
          "clinician_signoff_required=true",
        ].join(" · ")
      );
    } catch (e) {
      console.error("Treatment framework preview failed:", e);
      const detail = e?.response?.data?.detail;
      const msg = typeof detail === "string" ? detail : (detail ? JSON.stringify(detail) : String(e?.message || e));
      setTreatmentFrameworkStatus(`治疗框架预览失败：${msg}`);
      alert(`治疗框架预览失败：${msg}`);
    } finally {
      setTreatmentFrameworkLoading(false);
    }
  };
  // --- Case Detail Treatment Framework Preview UI V1 actions: end ---

  // --- Case Detail Treatment Framework Signed Review State UI V1 actions: start ---
  const buildTreatmentFrameworkSignedReviewStatePreview = async () => {
    if (!data?.id) return;

    const diagnosisLabel = confirmedDiagnosisLabel.trim();
    const confirmedBy = confirmedDiagnosisBy.trim();
    const reviewedBy = (signedReviewStateReviewedBy || confirmedBy).trim();
    const signedBy = signedReviewStateSignedBy.trim();
    const reviewDecision = signedReviewStateReviewDecision;
    const signoffDecision = signedReviewStateSignoffDecision;
    const frameworkPreview = treatmentFrameworkPreview?.treatment_framework_preview || {};

    if (!diagnosisLabel || !confirmedBy || !reviewedBy || !signedBy) {
      setSignedReviewStateStatus("请先填写医生确认诊断、确认医生、复核医生和签名医生；AI 不确认诊断。requires_clinician_confirmed_diagnosis=true");
      return;
    }

    if (!treatmentFrameworkPreview || Object.keys(frameworkPreview).length === 0) {
      setSignedReviewStateStatus("请先生成治疗框架预览，再生成 signed review state dry-run。signed_review_state_dry_run_only=true");
      return;
    }

    const auditReference = buildSignedReviewStateAuditReference(
      data.id,
      signedReviewStateAuditRequestId
    );

    try {
      setSignedReviewStateLoading(true);
      setSignedReviewStateStatus("正在生成签名复核状态预览：dry_run=true · writes_database=false · signed_review_state_persistence_enabled=false");

      const res = await api.post(
        "/api/diagnostic-data/dry-run/confirmed-diagnosis/treatment-framework/signed-review-state/build",
        {
          case_id: Number(data.id),
          confirmed_diagnosis_label: diagnosisLabel,
          confirmed_by: confirmedBy,
          confirmation_source: "clinician",
          ai_generated: false,
          treatment_framework_preview: frameworkPreview,
          reviewed_by: reviewedBy,
          review_decision: reviewDecision,
          signed_by: signedBy,
          signoff_decision: signoffDecision,
          audit_request_id: auditReference.audit_request_id,
          request_id: auditReference.audit_request_id,
          audit_log_result: auditReference.audit_log_result,
          audit_event: auditReference.audit_event,
          case_context: buildDiagnosticAssistanceCaseContext(data),
        }
      );

      const payload = res.data || {};
      setSignedReviewStatePreview(payload);
      setSignedReviewStateStatus(
        [
          "已生成 signed review state 医生端 dry-run 预览",
          "signed_review_state_dry_run_only=true",
          "signed_review_state_persistence_enabled=false",
          "review_state_persistence_enabled=false",
          "writes_database=false",
          "writes_case_treatment=false",
          "creates_prescription=false",
          "writes_prescription=false",
          "returns_drug_dose=false",
          "returns_drug_route=false",
          "returns_drug_frequency=false",
          "not_client_facing=true",
          "requires_human_review=true",
          "clinician_signoff_required=true",
        ].join(" · ")
      );
    } catch (e) {
      console.error("Treatment framework signed review state preview failed:", e);
      const detail = e?.response?.data?.detail;
      const msg = typeof detail === "string" ? detail : (detail ? JSON.stringify(detail) : String(e?.message || e));
      setSignedReviewStateStatus(`签名复核状态预览失败：${msg}`);
      alert(`签名复核状态预览失败：${msg}`);
    } finally {
      setSignedReviewStateLoading(false);
    }
  };
  // --- Case Detail Treatment Framework Signed Review State UI V1 actions: end ---
// --- Case Detail Treatment Framework Signed Review State Persistence UI V1 actions: start ---
const buildTreatmentFrameworkSignedReviewStatePersistencePreview = async () => {
  if (!data?.id) return;

  const diagnosisLabel = confirmedDiagnosisLabel.trim();
  const confirmedBy = confirmedDiagnosisBy.trim();
  const requestedBy = (
    signedReviewStatePersistenceRequestedBy ||
    signedReviewStateSignedBy ||
    signedReviewStateReviewedBy ||
    confirmedBy
  ).trim();
  const frameworkPreview = treatmentFrameworkPreview?.treatment_framework_preview || {};
  const signedState = signedReviewStatePreview?.signed_review_state_preview || {};

  if (!diagnosisLabel || !confirmedBy || !requestedBy) {
    setSignedReviewStatePersistenceStatus("请先填写医生确认诊断、确认医生和申请医生；AI 不确认诊断。requires_clinician_confirmed_diagnosis=true");
    return;
  }

  if (!treatmentFrameworkPreview || Object.keys(frameworkPreview).length === 0) {
    setSignedReviewStatePersistenceStatus("请先生成治疗框架预览。persistence_dry_run_only=true");
    return;
  }

  if (!signedReviewStatePreview || Object.keys(signedState).length === 0) {
    setSignedReviewStatePersistenceStatus("请先生成 signed review state preview，再生成 persistence dry-run preview。signed_review_state_persistence_enabled=false");
    return;
  }

  const payload = buildSignedReviewStatePersistencePayload({
    data,
    diagnosisLabel,
    confirmedBy,
    treatmentFrameworkPreview,
    signedReviewStatePreview,
    reviewedBy: signedReviewStateReviewedBy || confirmedBy,
    reviewDecision: signedReviewStateReviewDecision,
    signedBy: signedReviewStateSignedBy || requestedBy,
    signoffDecision: signedReviewStateSignoffDecision,
    requestedBy,
    auditRequestId: signedReviewStateAuditRequestId,
  });

  try {
    setSignedReviewStatePersistenceLoading(true);
    setSignedReviewStatePersistenceStatus("正在生成 signed review state persistence dry-run 预览：writes_database=false · signed_review_state_persistence_enabled=false");

    const res = await api.post(
      "/api/diagnostic-data/dry-run/confirmed-diagnosis/treatment-framework/signed-review-state/persistence/prepare",
      payload
    );

    const responsePayload = res.data || {};
    setSignedReviewStatePersistencePreview(responsePayload);
    setSignedReviewStatePersistenceStatus(
      [
        "已生成 signed review state persistence dry-run preview",
        "persistence_dry_run_only=true",
        "persistence_enabled=false",
        "signed_review_state_persistence_enabled=false",
        "review_state_persistence_enabled=false",
        "writes_database=false",
        "writes_case_treatment=false",
        "creates_prescription=false",
        "writes_prescription=false",
        "returns_drug_dose=false",
        "returns_drug_route=false",
        "returns_drug_frequency=false",
        "not_client_facing=true",
        "requires_human_review=true",
        "clinician_signoff_required=true",
      ].join(" · ")
    );
  } catch (e) {
    console.error("Treatment framework signed review state persistence preview failed:", e);
    const detail = e?.response?.data?.detail;
    const msg = typeof detail === "string" ? detail : (detail ? JSON.stringify(detail) : String(e?.message || e));
    setSignedReviewStatePersistenceStatus(`签名复核状态持久化 dry-run 预览失败：${msg}`);
    alert(`签名复核状态持久化 dry-run 预览失败：${msg}`);
  } finally {
    setSignedReviewStatePersistenceLoading(false);
  }
};
// --- Case Detail Treatment Framework Signed Review State Persistence UI V1 actions: end ---
  // --- Case Detail Treatment Framework Signed Review State Persistence Migration UI V1 actions: start ---
  const buildTreatmentFrameworkSignedReviewStateMigrationPreview = async () => {
    if (!data?.id) return;

    const diagnosisLabel = confirmedDiagnosisLabel.trim();
    const confirmedBy = confirmedDiagnosisBy.trim();
    const migrationRequestedBy = (
      signedReviewStateMigrationRequestedBy ||
      signedReviewStatePersistenceRequestedBy ||
      signedReviewStateSignedBy ||
      confirmedBy
    ).trim();
    const frameworkPreview = treatmentFrameworkPreview?.treatment_framework_preview || {};
    const signedState = signedReviewStatePreview?.signed_review_state_preview || {};
    const persistencePreview = signedReviewStatePersistencePreview?.persistence_dry_run_preview || {};

    if (!diagnosisLabel || !confirmedBy || !migrationRequestedBy) {
      setSignedReviewStateMigrationStatus("请先填写医生确认诊断、确认医生和 migration dry-run 申请医生；AI 不确认诊断。requires_clinician_confirmed_diagnosis=true");
      return;
    }

    if (!treatmentFrameworkPreview || Object.keys(frameworkPreview).length === 0) {
      setSignedReviewStateMigrationStatus("请先生成治疗框架预览。migration_dry_run_only=true");
      return;
    }

    if (!signedReviewStatePreview || Object.keys(signedState).length === 0) {
      setSignedReviewStateMigrationStatus("请先生成 signed review state preview。migration_enabled=false");
      return;
    }

    if (!signedReviewStatePersistencePreview || Object.keys(persistencePreview).length === 0) {
      setSignedReviewStateMigrationStatus("请先生成 signed review state persistence dry-run preview，再生成 migration dry-run preview。schema_change_enabled=false");
      return;
    }

    const payload = buildSignedReviewStateMigrationPayload({
      data,
      diagnosisLabel,
      confirmedBy,
      treatmentFrameworkPreview,
      signedReviewStatePreview,
      signedReviewStatePersistencePreview,
      migrationRequestedBy,
    });

    try {
      setSignedReviewStateMigrationLoading(true);
      setSignedReviewStateMigrationStatus("正在生成 signed review state migration dry-run 预览：migration_enabled=false · schema_change_enabled=false · writes_database=false");

      const res = await api.post(
        "/api/diagnostic-data/dry-run/confirmed-diagnosis/treatment-framework/signed-review-state/persistence/migration/dry-run",
        payload
      );

      const responsePayload = res.data || {};
      setSignedReviewStateMigrationPreview(responsePayload);
      setSignedReviewStateMigrationStatus(
        [
          "已生成 signed review state persistence migration dry-run preview",
          "migration_dry_run_only=true",
          "migration_enabled=false",
          "migration_file_created=false",
          "schema_change_enabled=false",
          "persistence_enabled=false",
          "signed_review_state_persistence_enabled=false",
          "review_state_persistence_enabled=false",
          "writes_database=false",
          "writes_case_treatment=false",
          "creates_prescription=false",
          "writes_prescription=false",
          "returns_drug_dose=false",
          "returns_drug_route=false",
          "returns_drug_frequency=false",
          "not_client_facing=true",
          "requires_human_review=true",
          "clinician_signoff_required=true",
        ].join(" · ")
      );
    } catch (e) {
      console.error("Treatment framework signed review state migration preview failed:", e);
      const detail = e?.response?.data?.detail;
      const msg = typeof detail === "string" ? detail : (detail ? JSON.stringify(detail) : String(e?.message || e));
      setSignedReviewStateMigrationStatus(`签名复核状态 migration dry-run 预览失败：${msg}`);
      alert(`签名复核状态 migration dry-run 预览失败：${msg}`);
    } finally {
      setSignedReviewStateMigrationLoading(false);
    }
  };
  // --- Case Detail Treatment Framework Signed Review State Persistence Migration UI V1 actions: end ---




  // Preventive Care Reminder UI V1: in-app reminders only; sends_external_message=false.
  const fetchPreventiveCareReminders = async () => {
    if (!data?.id) return;

    try {
      setPreventiveCareLoading(true);
      const res = await api.get("/api/preventive-care/reminders", {
        params: {
          case_id: Number(data.id),
          page: 1,
          page_size: 20,
        },
      });
      const items = Array.isArray(res.data?.items) ? res.data.items : [];
      setPreventiveCareReminders(items);
      setPreventiveCareStatus(`已加载 ${items.length} 条站内提醒 · sends_external_message=false`);
    } catch (e) {
      console.error("Preventive care reminders load failed:", e);
      setPreventiveCareStatus("预防保健提醒加载失败");
    } finally {
      setPreventiveCareLoading(false);
    }
  };

  const runPreventiveCareDryRun = async () => {
    if (!data?.id) return;

    try {
      setPreventiveCareBusy("dry-run");
      setPreventiveCareStatus("正在计算疫苗/驱虫提醒预览…");

      const res = await api.post("/api/preventive-care/dry-run", {
        case_id: Number(data.id),
        as_of_date: new Date().toISOString().slice(0, 10),
        include_active: false,
        pet: {
          pet_name: derived.patientName !== "—" ? derived.patientName : undefined,
          species: derived.species !== "—" ? derived.species : undefined,
          life_stage: "adult",
        },
      });

      const items = Array.isArray(res.data?.items) ? res.data.items : [];
      setPreventiveCarePreview(items);
      setPreventiveCareStatus(`已生成 ${items.length} 条预览 · writes_database=false · sends_external_message=false`);
    } catch (e) {
      console.error("Preventive care dry-run failed:", e);
      const detail = e?.response?.data?.detail;
      const msg = typeof detail === "string" ? detail : (detail ? JSON.stringify(detail) : String(e?.message || e));
      setPreventiveCareStatus(`提醒预览失败：${msg}`);
      alert(`提醒预览失败：${msg}`);
    } finally {
      setPreventiveCareBusy("");
    }
  };

  const createPreventiveCareReminderFromPreview = async (item) => {
    if (!data?.id || !item?.category) return;

    try {
      setPreventiveCareBusy(`create-${item.rule_id || item.category}`);
      const body = {
        case_id: Number(data.id),
        category: item.category,
        rule_id: item.rule_id || undefined,
        source_rule_id: item.source_rule_id || item.rule_id || undefined,
        status: item.status === "overdue" ? "overdue" : "active",
        due_date: item.due_date ? `${item.due_date}T00:00:00Z` : undefined,
        due_window_start: item.due_window_start ? `${item.due_window_start}T00:00:00Z` : undefined,
        due_window_end: item.due_window_end ? `${item.due_window_end}T00:00:00Z` : undefined,
        reminder_lead_days: item.reminder_lead_days,
        note: `由 Preventive Care dry-run 创建：${item.category} / ${item.rule_id || ""}`,
        metadata: {
          source: "preventive-care-ui-v1",
          dry_run_status: item.status,
          reason: item.reason,
          writes_case_database: false,
          sends_external_message: false,
        },
      };

      await api.post("/api/preventive-care/reminders", body);
      setPreventiveCareStatus("已创建站内提醒 · sends_external_message=false");
      await fetchPreventiveCareReminders();
    } catch (e) {
      console.error("Preventive care reminder create failed:", e);
      alert("创建站内提醒失败：" + String(e?.message || e));
    } finally {
      setPreventiveCareBusy("");
    }
  };

  const completePreventiveCareReminder = async (reminder) => {
    try {
      setPreventiveCareBusy(`complete-${reminder.reminder_id}`);
      await api.post(`/api/preventive-care/reminders/${reminder.reminder_id}/complete`, {
        event_type: reminder.category || "preventive_care_completed",
        event_date: new Date().toISOString(),
        clinician_id: "UI-OPERATOR",
        note: "由病例详情页标记完成；不发送外部消息。",
        metadata: {
          source: "preventive-care-ui-v1",
          sends_external_message: false,
        },
      });
      setPreventiveCareStatus("提醒已完成");
      await fetchPreventiveCareReminders();
    } catch (e) {
      console.error("Preventive care reminder complete failed:", e);
      alert("完成提醒失败：" + String(e?.message || e));
    } finally {
      setPreventiveCareBusy("");
    }
  };

  const snoozePreventiveCareReminder = async (reminder) => {
    try {
      setPreventiveCareBusy(`snooze-${reminder.reminder_id}`);
      const due = new Date();
      due.setDate(due.getDate() + 14);
      await api.post(`/api/preventive-care/reminders/${reminder.reminder_id}/snooze`, {
        due_date: due.toISOString(),
        reason: "病例详情页手动延后14天",
        note: "站内提醒延后；不发送外部消息。",
      });
      setPreventiveCareStatus("提醒已延后14天");
      await fetchPreventiveCareReminders();
    } catch (e) {
      console.error("Preventive care reminder snooze failed:", e);
      alert("延后提醒失败：" + String(e?.message || e));
    } finally {
      setPreventiveCareBusy("");
    }
  };

  const dismissPreventiveCareReminder = async (reminder) => {
    try {
      setPreventiveCareBusy(`dismiss-${reminder.reminder_id}`);
      await api.post(`/api/preventive-care/reminders/${reminder.reminder_id}/dismiss`, {
        reason: "病例详情页手动关闭",
        note: "关闭本次站内提醒；不发送外部消息。",
      });
      setPreventiveCareStatus("提醒已关闭");
      await fetchPreventiveCareReminders();
    } catch (e) {
      console.error("Preventive care reminder dismiss failed:", e);
      alert("关闭提醒失败：" + String(e?.message || e));
    } finally {
      setPreventiveCareBusy("");
    }
  };

  const disablePreventiveCareReminder = async (reminder) => {
    if (!confirm("确定禁用这条提醒？这会把该提醒标记为 client_opt_out。")) return;

    try {
      setPreventiveCareBusy(`disable-${reminder.reminder_id}`);
      await api.post(`/api/preventive-care/reminders/${reminder.reminder_id}/disable`, {
        reason: "客户暂不接收该提醒",
        note: "禁用本条站内提醒；不发送外部消息。",
      });
      setPreventiveCareStatus("提醒已禁用 · client_opt_out=true");
      await fetchPreventiveCareReminders();
    } catch (e) {
      console.error("Preventive care reminder disable failed:", e);
      alert("禁用提醒失败：" + String(e?.message || e));
    } finally {
      setPreventiveCareBusy("");
    }
  };

  useEffect(() => {
    if (!data?.id) return;
    fetchPreventiveCareReminders();
  }, [data?.id]);

  useEffect(() => {
    if (!data?.id) return;
    fetchDiagnosticDataSummary();
  }, [data?.id]);

  // Clinical Docs Export UI V1: read-only DOCX download from Case detail.
  const exportClinicalDoc = async (templateId, label) => {
    if (!data?.id) {
      alert("病例尚未加载，无法导出。");
      return;
    }

    try {
      setExportingDoc(templateId);
      setExportStatus(`正在生成${label}…`);

      const res = await api.post(
        "/api/clinical-docs/render",
        {
          case_id: Number(data.id),
          template_id: templateId,
          output: "docx",
        },
        {
          responseType: "blob",
        }
      );

      const disposition = res.headers?.["content-disposition"] || res.headers?.["Content-Disposition"] || "";
      const hash = res.headers?.["x-pmai-document-hash"] || res.headers?.["X-PMAI-Document-Hash"] || "";
      const match = disposition.match(/filename="?([^";]+)"?/i);
      const fallbackName = `${label.replace(/[\\/\s]+/g, "-")}-case-${data.id}${hash ? `-${hash}` : ""}.docx`;
      const filename = decodeURIComponent(match?.[1] || fallbackName);

      const blob = new Blob(
        [res.data],
        { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" }
      );
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);

      setExportStatus(`${label}已生成：${filename}`);
    } catch (e) {
      console.error("Clinical doc export failed:", e);
      const detail = e?.response?.data?.detail;
      const msg = typeof detail === "string" ? detail : (detail ? JSON.stringify(detail) : String(e?.message || e));
      setExportStatus(`${label}导出失败`);
      alert(`${label}导出失败：${msg}`);
    } finally {
      setExportingDoc("");
    }
  };

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
          <button
            type="button"
            onClick={() => exportClinicalDoc("admission_hospitalization_record_bilingual", "入院/住院记录")}
            disabled={Boolean(exportingDoc)}
            style={btnDoc}
          >
            {exportingDoc === "admission_hospitalization_record_bilingual" ? "生成中…" : "导出入院/住院记录 DOCX"}
          </button>
          <button
            type="button"
            onClick={() => exportClinicalDoc("discharge_summary_bilingual", "出院小结")}
            disabled={Boolean(exportingDoc)}
            style={btnDoc}
          >
            {exportingDoc === "discharge_summary_bilingual" ? "生成中…" : "导出出院小结 DOCX"}
          </button>
          <button onClick={doDelete} disabled={deleting} style={btnDanger}>
            {deleting ? "删除中…" : "删除"}
          </button>
        </div>
        <div style={{ opacity: .6, fontSize: 12 }}>
          后端：{import.meta.env.VITE_API_BASE}
        </div>
      </div>

      {exportStatus && (
        <div className="clinical-doc-export-status screen-only">
          {exportStatus}
        </div>
      )}

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

      <Section title="诊断数据 / Diagnostic Data">
        <DiagnosticDataPanel
          summary={diagnosticDataSummary}
          loading={diagnosticDataLoading}
          status={diagnosticDataStatus}
          onRefresh={fetchDiagnosticDataSummary}
        />
      </Section>

      {/* --- Diagnostic Assistance Case Detail UI V1 section: start --- */}
      <Section title="诊断辅助预览 / Diagnostic Assistance Preview">
        <DiagnosticAssistancePanel
          preview={diagnosticAssistancePreview}
          loading={diagnosticAssistanceLoading}
          status={diagnosticAssistanceStatus}
          onBuild={buildDiagnosticAssistancePreview}
        />
      </Section>
      {/* --- Diagnostic Assistance Case Detail UI V1 section: end --- */}
      {/* --- Case Detail Treatment Framework Preview UI V1 section: start --- */}
      <Section title="确诊后治疗框架预览 / Treatment Framework Preview">
        <TreatmentFrameworkPreviewPanel
          confirmedDiagnosisLabel={confirmedDiagnosisLabel}
          onConfirmedDiagnosisLabelChange={setConfirmedDiagnosisLabel}
          confirmedDiagnosisBy={confirmedDiagnosisBy}
          onConfirmedDiagnosisByChange={setConfirmedDiagnosisBy}
          preview={treatmentFrameworkPreview}
          loading={treatmentFrameworkLoading}
          status={treatmentFrameworkStatus}
          onBuild={buildTreatmentFrameworkPreview}
        />
      </Section>
      {/* --- Case Detail Treatment Framework Preview UI V1 section: end --- */}

      {/* --- Case Detail Treatment Framework Signed Review State UI V1 section: start --- */}
      <Section title="治疗框架签名复核状态预览 / Signed Review State Preview">
        <TreatmentFrameworkSignedReviewStatePanel
          treatmentFrameworkPreview={treatmentFrameworkPreview}
          preview={signedReviewStatePreview}
          loading={signedReviewStateLoading}
          status={signedReviewStateStatus}
          reviewedBy={signedReviewStateReviewedBy}
          onReviewedByChange={setSignedReviewStateReviewedBy}
          reviewDecision={signedReviewStateReviewDecision}
          onReviewDecisionChange={setSignedReviewStateReviewDecision}
          signedBy={signedReviewStateSignedBy}
          onSignedByChange={setSignedReviewStateSignedBy}
          signoffDecision={signedReviewStateSignoffDecision}
          onSignoffDecisionChange={setSignedReviewStateSignoffDecision}
          auditRequestId={signedReviewStateAuditRequestId}
          onAuditRequestIdChange={setSignedReviewStateAuditRequestId}
          onBuild={buildTreatmentFrameworkSignedReviewStatePreview}
        />
      </Section>
      {/* --- Case Detail Treatment Framework Signed Review State UI V1 section: end --- */}
{/* --- Case Detail Treatment Framework Signed Review State Persistence UI V1 section: start --- */}
<Section title="签名复核状态持久化预览 / Signed Review State Persistence Preview">
  <TreatmentFrameworkSignedReviewStatePersistencePanel
    signedReviewStatePreview={signedReviewStatePreview}
    preview={signedReviewStatePersistencePreview}
    loading={signedReviewStatePersistenceLoading}
    status={signedReviewStatePersistenceStatus}
    requestedBy={signedReviewStatePersistenceRequestedBy}
    onRequestedByChange={setSignedReviewStatePersistenceRequestedBy}
    onBuild={buildTreatmentFrameworkSignedReviewStatePersistencePreview}
  />
</Section>
{/* --- Case Detail Treatment Framework Signed Review State Persistence UI V1 section: end --- */}
      {/* --- Case Detail Treatment Framework Signed Review State Persistence Migration UI V1 section: start --- */}
      <Section title="签名复核状态迁移 dry-run 预览 / Signed Review State Migration Preview">
        <TreatmentFrameworkSignedReviewStateMigrationPanel
          signedReviewStatePersistencePreview={signedReviewStatePersistencePreview}
          preview={signedReviewStateMigrationPreview}
          loading={signedReviewStateMigrationLoading}
          status={signedReviewStateMigrationStatus}
          requestedBy={signedReviewStateMigrationRequestedBy}
          onRequestedByChange={setSignedReviewStateMigrationRequestedBy}
          onBuild={buildTreatmentFrameworkSignedReviewStateMigrationPreview}
        />
      </Section>
      {/* --- Case Detail Treatment Framework Signed Review State Persistence Migration UI V1 section: end --- */}




      <Section title="八、预防保健提醒 / Preventive Care">
        <PreventiveCarePanel
          reminders={preventiveCareReminders}
          preview={preventiveCarePreview}
          loading={preventiveCareLoading}
          busy={preventiveCareBusy}
          status={preventiveCareStatus}
          onRefresh={fetchPreventiveCareReminders}
          onDryRun={runPreventiveCareDryRun}
          onCreateFromPreview={createPreventiveCareReminderFromPreview}
          onComplete={completePreventiveCareReminder}
          onSnooze={snoozePreventiveCareReminder}
          onDismiss={dismissPreventiveCareReminder}
          onDisable={disablePreventiveCareReminder}
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

function DiagnosticDataPanel({ summary, loading, status, onRefresh }) {
  const counts = summary?.counts || {};
  const reports = Array.isArray(summary?.reports) ? summary.reports : [];
  const observations = Array.isArray(summary?.observations) ? summary.observations : [];
  const imagingStudies = Array.isArray(summary?.imaging_studies) ? summary.imaging_studies : [];
  const hasAny = reports.length > 0 || observations.length > 0 || imagingStudies.length > 0;

  return (
    <div className="diagnostic-data-panel">
      <div className="diagnostic-data-actions screen-only">
        <button type="button" style={btnSecondary} onClick={onRefresh} disabled={loading}>
          {loading ? "加载中…" : "刷新诊断数据"}
        </button>
      </div>

      <div className="diagnostic-data-status">
        {status || "只读展示 DiagnosticReport / Observation / ImagingStudy，不写数据库。read_only=true · writes_database=false"}
      </div>

      <div className="diagnostic-data-counts">
        <div className="diagnostic-data-count-card">
          <div className="diagnostic-data-count-value">{counts.reports || 0}</div>
          <div className="diagnostic-data-count-label">Diagnostic Reports</div>
        </div>
        <div className="diagnostic-data-count-card">
          <div className="diagnostic-data-count-value">{counts.observations || 0}</div>
          <div className="diagnostic-data-count-label">Observations</div>
        </div>
        <div className="diagnostic-data-count-card">
          <div className="diagnostic-data-count-value">{counts.imaging_studies || 0}</div>
          <div className="diagnostic-data-count-label">Imaging Studies</div>
        </div>
      </div>

      {!hasAny ? (
        <div className="diagnostic-data-empty">
          暂无结构化检验/影像记录。可先通过 dry-run fixture parser 验证解析预览；本面板只读取已存在的 0009 诊断数据。
        </div>
      ) : (
        <div className="diagnostic-data-grid">
          <DiagnosticDataList
            title="Reports"
            empty="暂无 DiagnosticReport"
            items={reports.slice(0, 5)}
            renderItem={(item) => (
              <>
                <div className="diagnostic-data-item-title">{safeText(item.title || formatReportType(item.report_type))}</div>
                <div className="diagnostic-data-item-meta">
                  类型：{formatReportType(item.report_type)} · 状态：{safeText(item.status)} · 来源：{safeText(item.source_type)}
                </div>
                <div className="diagnostic-data-item-safe">ai_summary_status={safeText(item.ai_summary_status)}</div>
              </>
            )}
          />
          <DiagnosticDataList
            title="Abnormal / Recent Observations"
            empty="暂无 Observation"
            items={observations.slice(0, 8)}
            renderItem={(item) => (
              <>
                <div className="diagnostic-data-item-title">{safeText(item.display_name)}</div>
                <div className="diagnostic-data-item-meta">
                  {formatObservationValue(item)} · {formatAbnormalFlag(item.abnormal_flag)} · {safeText(item.unit)}
                </div>
                <div className="diagnostic-data-item-safe">code={safeText(item.code)} · review_status={safeText(item.review_status)}</div>
              </>
            )}
          />
          <DiagnosticDataList
            title="Imaging Metadata"
            empty="暂无 ImagingStudy"
            items={imagingStudies.slice(0, 5)}
            renderItem={(item) => (
              <>
                <div className="diagnostic-data-item-title">
                  {safeText(item.modality)} · {safeText(item.body_part)}
                </div>
                <div className="diagnostic-data-item-meta">
                  taken_at={formatDiagnosticDate(item.taken_at)} · abnormal={formatAbnormalFlag(item.abnormal_flag)}
                </div>
                <div className="diagnostic-data-item-safe">study_uid={safeText(item.study_uid)} · review_status={safeText(item.review_status)}</div>
              </>
            )}
          />
        </div>
      )}

      <div className="diagnostic-data-safety">
        read_only=true · writes_database=false · creates_case=false · executes_real_lab_ingest=false · executes_real_dicom_ingest=false · executes_real_device_ingest=false
      </div>
    </div>
  );
}

function DiagnosticDataList({ title, empty, items, renderItem }) {
  return (
    <div className="diagnostic-data-subblock">
      <div className="diagnostic-data-subtitle">{title}</div>
      {items.length === 0 ? (
        <div className="diagnostic-data-empty-small">{empty}</div>
      ) : (
        <div className="diagnostic-data-list">
          {items.map((item, index) => (
            <div className="diagnostic-data-item" key={item.report_id || item.observation_id || item.imaging_study_id || index}>
              {renderItem(item)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// --- Diagnostic Assistance Case Detail UI V1 components: start ---
function DiagnosticAssistancePanel({ preview, loading, status, onBuild }) {
  const problemPayload = preview?.problem_list || {};
  const differentialPayload = preview?.differential_candidates || {};
  const tracePayload = preview?.evidence_trace || {};
  const problemItems = Array.isArray(problemPayload.problem_list_preview) ? problemPayload.problem_list_preview : [];
  const candidateItems = Array.isArray(differentialPayload.differential_diagnosis_candidates_preview)
    ? differentialPayload.differential_diagnosis_candidates_preview
    : [];
  const traceItems = Array.isArray(tracePayload.diagnostic_reasoning_evidence_trace_preview)
    ? tracePayload.diagnostic_reasoning_evidence_trace_preview
    : [];
  const evidenceIndex = Array.isArray(tracePayload.evidence_source_index) ? tracePayload.evidence_source_index : [];

  return (
    <div className="diagnostic-assistance-panel">
      <div className="diagnostic-assistance-actions screen-only">
        <button type="button" style={btnDoc} onClick={onBuild} disabled={loading}>
          {loading ? "生成中…" : "生成诊断辅助预览"}
        </button>
      </div>

      <div className="diagnostic-assistance-status">
        {status || "医生复核用 dry-run 预览；不写数据库、不生成最终诊断、不生成治疗方案、不写处方、不输出药物剂量。"}
      </div>

      <div className="diagnostic-assistance-boundary">
        dry_run=true · writes_database=false · writes_audit_log=false · persists_reasoning_trace=false · not_a_diagnosis=true · not_a_treatment_plan=true · not_a_prescription=true · not_client_facing=true · requires_human_review=true
      </div>

      {!preview ? (
        <div className="diagnostic-assistance-empty">
          尚未生成诊断辅助预览。点击按钮后会依次调用 Problem List、Differential Candidates、Evidence Trace 三个 dry-run endpoint；不会保存到 Case、DiagnosticReport、Observation、ImagingStudy 或 audit log。
        </div>
      ) : (
        <>
          <div className="diagnostic-assistance-counts">
            <DiagnosticAssistanceCount label="Problem List" value={problemItems.length} />
            <DiagnosticAssistanceCount label="Differential Candidates" value={candidateItems.length} />
            <DiagnosticAssistanceCount label="Evidence Trace" value={traceItems.length} />
            <DiagnosticAssistanceCount label="Evidence Sources" value={evidenceIndex.length} />
          </div>

          <div className="diagnostic-assistance-grid">
            <DiagnosticAssistanceList title="Problem List Preview" empty="暂无 problem list preview" items={problemItems.slice(0, 8)} renderItem={(item, index) => (
              <>
                <div className="diagnostic-assistance-item-title">{safeText(item.title || item.problem_title || `Problem ${index + 1}`)}</div>
                <div className="diagnostic-assistance-item-meta">
                  category={safeText(item.category)} · severity_hint={safeText(item.severity_hint)} · requires_clinician_review={String(item.requires_clinician_review !== false)}
                </div>
                <EvidenceSnippetList items={item.evidence_sources} />
              </>
            )} />

            <DiagnosticAssistanceList title="Differential Candidates Preview" empty="暂无 differential candidates preview" items={candidateItems.slice(0, 8)} renderItem={(item, index) => (
              <>
                <div className="diagnostic-assistance-item-title">{safeText(item.candidate_label || item.candidate_key || `Candidate ${index + 1}`)}</div>
                <div className="diagnostic-assistance-item-meta">
                  system={safeText(item.system_category)} · severity_hint={safeText(item.severity_hint)} · evidence_fit_hint={safeText(item.evidence_fit_hint)}
                </div>
                <EvidenceSnippetList items={item.supporting_evidence_sources || item.evidence_sources} />
              </>
            )} />

            <DiagnosticAssistanceList title="Evidence Trace Preview" empty="暂无 evidence trace preview" items={traceItems.slice(0, 8)} renderItem={(item, index) => (
              <>
                <div className="diagnostic-assistance-item-title">{safeText(item.candidate_label || item.candidate_key || `Trace ${index + 1}`)}</div>
                <div className="diagnostic-assistance-item-meta">
                  trace_id={safeText(item.trace_id)} · fit={safeText(item.evidence_fit_hint)} · severity_hint={safeText(item.severity_hint)}
                </div>
                <TraceStepList items={item.reasoning_trace_steps} />
                <ReviewQuestionList items={item.review_questions} />
              </>
            )} />
          </div>

          <DiagnosticAssistanceQualityGates
            problemGate={problemPayload.quality_gate}
            candidateGate={differentialPayload.quality_gate}
            traceGate={tracePayload.quality_gate}
          />
        </>
      )}
    </div>
  );
}

function DiagnosticAssistanceCount({ label, value }) {
  return (
    <div className="diagnostic-assistance-count-card">
      <div className="diagnostic-assistance-count-value">{value || 0}</div>
      <div className="diagnostic-assistance-count-label">{label}</div>
    </div>
  );
}

function DiagnosticAssistanceList({ title, empty, items, renderItem }) {
  return (
    <div className="diagnostic-assistance-subblock">
      <div className="diagnostic-assistance-subtitle">{title}</div>
      {items.length === 0 ? (
        <div className="diagnostic-assistance-empty-small">{empty}</div>
      ) : (
        <div className="diagnostic-assistance-list">
          {items.map((item, index) => (
            <div className="diagnostic-assistance-item" key={item.problem_id || item.candidate_key || item.trace_id || index}>
              {renderItem(item, index)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function EvidenceSnippetList({ items }) {
  const evidenceItems = Array.isArray(items) ? items.slice(0, 3) : [];
  if (!evidenceItems.length) return null;
  return (
    <ul className="diagnostic-assistance-evidence-list">
      {evidenceItems.map((item, index) => (
        <li key={`${item.source_type || "source"}-${index}`}>
          {safeText(item.source_type)}.{safeText(item.field)}：{safeText(item.snippet)}
        </li>
      ))}
    </ul>
  );
}

function TraceStepList({ items }) {
  const steps = Array.isArray(items) ? items.slice(0, 4) : [];
  if (!steps.length) return null;
  return (
    <ol className="diagnostic-assistance-trace-list">
      {steps.map((item, index) => (
        <li key={index}>{safeText(item.step || item.text || item)}</li>
      ))}
    </ol>
  );
}

function ReviewQuestionList({ items }) {
  const questions = Array.isArray(items) ? items.slice(0, 3) : [];
  if (!questions.length) return null;
  return (
    <div className="diagnostic-assistance-review-questions">
      <div className="diagnostic-assistance-mini-title">复核问题</div>
      {questions.map((item, index) => (
        <div key={index}>• {safeText(item.question || item)}</div>
      ))}
    </div>
  );
}

function DiagnosticAssistanceQualityGates({ problemGate, candidateGate, traceGate }) {
  const gates = [
    ["Problem List", problemGate],
    ["Differential Candidates", candidateGate],
    ["Evidence Trace", traceGate],
  ];
  return (
    <div className="diagnostic-assistance-quality-gates">
      {gates.map(([label, gate]) => (
        <div className="diagnostic-assistance-quality-card" key={label}>
          <div className="diagnostic-assistance-quality-title">{label}</div>
          <div>status={safeText(gate?.status)}</div>
          <div>decision={safeText(gate?.decision)}</div>
          <div>requires_human_review={String(gate?.requires_human_review !== false && gate?.requires_clinician_review !== false)}</div>
        </div>
      ))}
    </div>
  );
}
// --- Diagnostic Assistance Case Detail UI V1 components: end ---

// --- Case Detail Treatment Framework Preview UI V1 components: start ---
function TreatmentFrameworkPreviewPanel({
  confirmedDiagnosisLabel,
  onConfirmedDiagnosisLabelChange,
  confirmedDiagnosisBy,
  onConfirmedDiagnosisByChange,
  preview,
  loading,
  status,
  onBuild,
}) {
  const framework = preview?.treatment_framework_preview || {};
  const qualityGate = preview?.quality_gate || {};
  const safety = preview?.safety || {};
  const confirmedDiagnosis = preview?.confirmed_diagnosis || {};
  const hasPreview = Boolean(preview);

  return (
    <div className="treatment-framework-panel">
      <div className="treatment-framework-form screen-only">
        <label className="treatment-framework-label">
          <span>医生确认诊断 / Clinician confirmed diagnosis</span>
          <textarea
            value={confirmedDiagnosisLabel}
            onChange={(event) => onConfirmedDiagnosisLabelChange(event.target.value)}
            className="treatment-framework-textarea"
            placeholder="只填写医生已经确认的诊断；AI 不确认诊断。"
            rows={2}
          />
        </label>
        <label className="treatment-framework-label">
          <span>确认医生 / Confirmed by</span>
          <input
            value={confirmedDiagnosisBy}
            onChange={(event) => onConfirmedDiagnosisByChange(event.target.value)}
            className="treatment-framework-input"
            placeholder="clinician-id / doctor name"
          />
        </label>
        <button type="button" style={btnDoc} onClick={onBuild} disabled={loading}>
          {loading ? "生成中…" : "生成治疗框架预览"}
        </button>
      </div>

      <div className="treatment-framework-status">
        {status || "医生端 dry-run 预览；必须先由 clinician confirmed diagnosis 触发。不会写 Case.treatment，不写处方，不输出剂量、频率或给药途径。"}
      </div>

      <div className="treatment-framework-boundary">
        confirmation_source=clinician · ai_generated=false · read_only=true · writes_database=false · writes_case_treatment=false · creates_prescription=false · writes_prescription=false · returns_drug_dose=false · returns_drug_route=false · returns_drug_frequency=false · not_client_facing=true · requires_human_review=true · clinician_signoff_required=true
      </div>

      {!hasPreview ? (
        <div className="treatment-framework-empty">
          尚未生成治疗框架预览。输入医生确认诊断后，按钮只调用 dry-run endpoint 并在本页展示医生复核草案；不会保存到病例、治疗字段、处方或客户端输出。
        </div>
      ) : (
        <>
          <div className="treatment-framework-confirmed">
            <div className="treatment-framework-mini-title">确认诊断来源</div>
            <div>label={safeText(confirmedDiagnosis.label)}</div>
            <div>confirmed_by={safeText(confirmedDiagnosis.confirmed_by)}</div>
            <div>confirmation_source={safeText(confirmedDiagnosis.confirmation_source)}</div>
            <div>ai_generated={String(confirmedDiagnosis.ai_generated === true ? true : false)}</div>
          </div>

          <div className="treatment-framework-grid">
            <TreatmentFrameworkList title="Treatment Goals" items={framework.treatment_goals} />
            <TreatmentFrameworkList title="Supportive Care Categories" items={framework.supportive_care_categories} />
            <TreatmentFrameworkList title="Monitoring Parameters" items={framework.monitoring_parameters} />
            <TreatmentFrameworkList title="Recheck Plan Categories" items={framework.recheck_plan_categories} />
            <TreatmentFrameworkList title="Contraindication Checks" items={framework.contraindication_checks} />
            <TreatmentFrameworkList title="Referral / Hospitalization Triggers" items={framework.referral_or_hospitalization_triggers} />
            <TreatmentFrameworkList title="Procedure / Surgery Review Points" items={framework.procedure_or_surgery_review_points} />
            <TreatmentFrameworkList title="Nutrition / Environment Support" items={framework.nutrition_and_environment_support_points} />
            <TreatmentFrameworkList title="Clinician Client-Communication Topics" items={framework.client_communication_topics_for_clinician_review} />
            <TreatmentFrameworkList title="Medication Class Review Needed" items={framework.medication_class_review_needed} />
          </div>

          <TreatmentFrameworkSafetyGrid qualityGate={qualityGate} safety={safety} />
        </>
      )}
    </div>
  );
}

function TreatmentFrameworkList({ title, items }) {
  const normalized = normalizeTreatmentFrameworkItems(items);
  return (
    <div className="treatment-framework-subblock">
      <div className="treatment-framework-subtitle">{title}</div>
      {normalized.length === 0 ? (
        <div className="treatment-framework-empty-small">暂无条目；需医生结合体检、检验和影像补充。</div>
      ) : (
        <ul className="treatment-framework-list">
          {normalized.map((item, index) => (
            <li key={`${title}-${index}`}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function TreatmentFrameworkSafetyGrid({ qualityGate, safety }) {
  const rows = [
    ["quality_gate.status", qualityGate?.status],
    ["requires_confirmed_diagnosis", qualityGate?.requires_confirmed_diagnosis],
    ["blocks_prescription", qualityGate?.blocks_prescription],
    ["blocks_dose", qualityGate?.blocks_dose],
    ["blocks_route_frequency", qualityGate?.blocks_route_frequency],
    ["writes_database", safety?.writes_database],
    ["writes_case_treatment", safety?.writes_case_treatment],
    ["creates_prescription", safety?.creates_prescription],
    ["writes_prescription", safety?.writes_prescription],
    ["returns_drug_dose", safety?.returns_drug_dose],
    ["returns_drug_route", safety?.returns_drug_route],
    ["returns_drug_frequency", safety?.returns_drug_frequency],
    ["not_client_facing", safety?.not_client_facing],
    ["requires_human_review", safety?.requires_human_review],
    ["clinician_signoff_required", safety?.clinician_signoff_required],
  ];

  return (
    <div className="treatment-framework-safety-grid">
      {rows.map(([label, value]) => (
        <div className="treatment-framework-safety-card" key={label}>
          <div className="treatment-framework-safety-label">{label}</div>
          <div className="treatment-framework-safety-value">{String(value)}</div>
        </div>
      ))}
    </div>
  );
}
// --- Case Detail Treatment Framework Preview UI V1 components: end ---

// --- Case Detail Treatment Framework Signed Review State UI V1 components: start ---
function TreatmentFrameworkSignedReviewStatePanel({
  treatmentFrameworkPreview,
  preview,
  loading,
  status,
  reviewedBy,
  onReviewedByChange,
  reviewDecision,
  onReviewDecisionChange,
  signedBy,
  onSignedByChange,
  signoffDecision,
  onSignoffDecisionChange,
  auditRequestId,
  onAuditRequestIdChange,
  onBuild,
}) {
  const hasFrameworkPreview = Boolean(treatmentFrameworkPreview?.treatment_framework_preview);
  const state = preview?.signed_review_state_preview || {};
  const qualityGate = preview?.quality_gate || {};
  const safety = preview?.safety || {};
  const reviewContext = preview?.review_context || {};
  const hasPreview = Boolean(preview);

  return (
    <div className="signed-review-state-panel">
      <div className="signed-review-state-form screen-only">
        <label className="signed-review-state-label">
          <span>复核医生 / Reviewed by</span>
          <input
            value={reviewedBy}
            onChange={(event) => onReviewedByChange(event.target.value)}
            className="signed-review-state-input"
            placeholder="reviewer clinician id / doctor name"
          />
        </label>
        <label className="signed-review-state-label">
          <span>复核决定 / Review decision</span>
          <select
            value={reviewDecision}
            onChange={(event) => onReviewDecisionChange(event.target.value)}
            className="signed-review-state-input"
          >
            <option value="approve_for_clinician_use">approve_for_clinician_use</option>
            <option value="request_revision">request_revision</option>
            <option value="reject">reject</option>
          </select>
        </label>
        <label className="signed-review-state-label">
          <span>签名医生 / Signed by</span>
          <input
            value={signedBy}
            onChange={(event) => onSignedByChange(event.target.value)}
            className="signed-review-state-input"
            placeholder="signing clinician id / doctor name"
          />
        </label>
        <label className="signed-review-state-label">
          <span>签名决定 / Signoff decision</span>
          <select
            value={signoffDecision}
            onChange={(event) => onSignoffDecisionChange(event.target.value)}
            className="signed-review-state-input"
          >
            <option value="sign_internal_review">sign_internal_review</option>
            <option value="request_revision">request_revision</option>
            <option value="reject">reject</option>
          </select>
        </label>
        <label className="signed-review-state-label">
          <span>Audit request id / optional dry-run reference</span>
          <input
            value={auditRequestId}
            onChange={(event) => onAuditRequestIdChange(event.target.value)}
            className="signed-review-state-input"
            placeholder="optional; auto-generated if empty"
          />
        </label>
        <button type="button" style={btnDoc} onClick={onBuild} disabled={loading || !hasFrameworkPreview}>
          {loading ? "生成中…" : "生成签名复核状态预览"}
        </button>
      </div>

      <div className="signed-review-state-status">
        {status || "医生端 signed review state dry-run 预览；先生成 Treatment Framework Preview，再生成签名复核状态预览。不会写数据库、不会写 Case.treatment、不会生成处方。"}
      </div>

      <div className="signed-review-state-boundary">
        endpoint=/api/diagnostic-data/dry-run/confirmed-diagnosis/treatment-framework/signed-review-state/build · confirmation_source=clinician · ai_generated=false · signed_review_state_dry_run_only=true · signed_review_state_persistence_enabled=false · review_state_persistence_enabled=false · writes_database=false · writes_case_treatment=false · creates_prescription=false · writes_prescription=false · returns_drug_dose=false · returns_drug_route=false · returns_drug_frequency=false · not_client_facing=true · requires_human_review=true · clinician_signoff_required=true
      </div>

      {!hasFrameworkPreview && (
        <div className="signed-review-state-empty">
          需要先生成“确诊后治疗框架预览”。本面板只读取现有 preview 并调用 signed review state dry-run endpoint，不保存签名状态。
        </div>
      )}

      {!hasPreview ? (
        <div className="signed-review-state-empty">
          尚未生成 signed review state preview。该状态只是医生端 dry-run 展示，不启用真实 persistence，也不释放给客户端。
        </div>
      ) : (
        <>
          <div className="signed-review-state-grid">
            <SignedReviewStateCard label="state_preview_id" value={state.state_preview_id} />
            <SignedReviewStateCard label="signed_review_status" value={state.signed_review_status} />
            <SignedReviewStateCard label="review_decision" value={state.review_decision || reviewContext.review_decision} />
            <SignedReviewStateCard label="reviewed_by" value={state.reviewed_by || reviewContext.reviewed_by} />
            <SignedReviewStateCard label="signoff_decision" value={state.signoff_decision} />
            <SignedReviewStateCard label="signed_by" value={state.signed_by} />
            <SignedReviewStateCard label="signed_at_preview" value={state.signed_at_preview} />
            <SignedReviewStateCard label="dry_run" value={state.dry_run} />
            <SignedReviewStateCard label="persisted" value={state.persisted} />
            <SignedReviewStateCard label="signed_review_state_persisted" value={state.signed_review_state_persisted} />
            <SignedReviewStateCard label="case_treatment_persisted" value={state.case_treatment_persisted} />
            <SignedReviewStateCard label="client_release_allowed" value={state.client_release_allowed} />
          </div>

          <TreatmentFrameworkSignedReviewStateSafetyGrid qualityGate={qualityGate} safety={safety} />
        </>
      )}
    </div>
  );
}

function SignedReviewStateCard({ label, value }) {
  return (
    <div className="signed-review-state-card">
      <div className="signed-review-state-card-label">{label}</div>
      <div className="signed-review-state-card-value">{String(value ?? "—")}</div>
    </div>
  );
}

function TreatmentFrameworkSignedReviewStateSafetyGrid({ qualityGate, safety }) {
  const rows = [
    ["quality_gate.status", qualityGate?.status],
    ["audit_log_reference_present", qualityGate?.audit_log_reference_present],
    ["signed_review_state_preview_only", qualityGate?.signed_review_state_preview_only],
    ["review_state_persistence_enabled", qualityGate?.review_state_persistence_enabled],
    ["writes_database", safety?.writes_database],
    ["writes_case_treatment", safety?.writes_case_treatment],
    ["persists_treatment_framework", safety?.persists_treatment_framework],
    ["creates_prescription", safety?.creates_prescription],
    ["writes_prescription", safety?.writes_prescription],
    ["returns_drug_dose", safety?.returns_drug_dose],
    ["returns_drug_route", safety?.returns_drug_route],
    ["returns_drug_frequency", safety?.returns_drug_frequency],
    ["creates_signed_review_state", safety?.creates_signed_review_state],
    ["persists_signed_review_state", safety?.persists_signed_review_state],
    ["not_client_facing", safety?.not_client_facing],
    ["requires_human_review", safety?.requires_human_review],
    ["clinician_signoff_required", safety?.clinician_signoff_required],
  ];
  return (
    <div className="signed-review-state-safety-grid">
      {rows.map(([label, value]) => (
        <SignedReviewStateCard key={label} label={label} value={value} />
      ))}
    </div>
  );
}
// --- Case Detail Treatment Framework Signed Review State UI V1 components: end ---
// --- Case Detail Treatment Framework Signed Review State Persistence UI V1 components: start ---
function TreatmentFrameworkSignedReviewStatePersistencePanel({
  signedReviewStatePreview,
  preview,
  loading,
  status,
  requestedBy,
  onRequestedByChange,
  onBuild,
}) {
  const hasSignedStatePreview = Boolean(signedReviewStatePreview?.signed_review_state_preview);
  const persistencePreview = preview?.persistence_dry_run_preview || {};
  const qualityGate = preview?.quality_gate || {};
  const safety = preview?.safety || {};
  const hasPreview = Boolean(preview);

  return (
    <div className="signed-review-state-persistence-panel">
      <div className="signed-review-state-persistence-form screen-only">
        <label className="signed-review-state-persistence-label">
          <span>持久化 dry-run 申请医生 / Requested by</span>
          <input
            value={requestedBy}
            onChange={(event) => onRequestedByChange(event.target.value)}
            className="signed-review-state-persistence-input"
            placeholder="requesting clinician id / doctor name"
          />
        </label>
        <button type="button" style={btnDoc} onClick={onBuild} disabled={loading || !hasSignedStatePreview}>
          {loading ? "生成中…" : "生成持久化 dry-run 预览"}
        </button>
      </div>

      <div className="signed-review-state-persistence-status">
        {status || "医生端 persistence dry-run 预览；先生成 signed review state preview。不会写数据库、不会写病例治疗字段、不会生成处方。"}
      </div>

      <div className="signed-review-state-persistence-boundary">
        endpoint=/api/diagnostic-data/dry-run/confirmed-diagnosis/treatment-framework/signed-review-state/persistence/prepare · persistence_dry_run_only=true · persistence_enabled=false · signed_review_state_persistence_enabled=false · review_state_persistence_enabled=false · writes_database=false · writes_case_treatment=false · creates_prescription=false · writes_prescription=false · returns_drug_dose=false · returns_drug_route=false · returns_drug_frequency=false · not_client_facing=true · requires_human_review=true · clinician_signoff_required=true
      </div>

      {!hasSignedStatePreview && (
        <div className="signed-review-state-persistence-empty">
          需要先生成 signed review state preview。本面板只调用 persistence dry-run endpoint，不保存任何状态。
        </div>
      )}

      {!hasPreview ? (
        <div className="signed-review-state-persistence-empty">
          尚未生成 signed review state persistence dry-run preview。该结果只用于医生端上线前复核，不启用真实 persistence。
        </div>
      ) : (
        <>
          <div className="signed-review-state-persistence-grid">
            <SignedReviewStateCard label="preview_id" value={persistencePreview.preview_id} />
            <SignedReviewStateCard label="operation" value={persistencePreview.operation} />
            <SignedReviewStateCard label="dry_run" value={persistencePreview.dry_run} />
            <SignedReviewStateCard label="persisted" value={persistencePreview.persisted} />
            <SignedReviewStateCard label="will_write_now" value={persistencePreview.will_write_now} />
            <SignedReviewStateCard label="writes_database" value={persistencePreview.writes_database} />
            <SignedReviewStateCard label="signed_review_state_persistence_enabled" value={persistencePreview.signed_review_state_persistence_enabled} />
            <SignedReviewStateCard label="review_state_persistence_enabled" value={persistencePreview.review_state_persistence_enabled} />
            <SignedReviewStateCard label="migration_readiness_required" value={persistencePreview.migration_readiness_required} />
            <SignedReviewStateCard label="future_migration_required" value={persistencePreview.future_migration_required} />
            <SignedReviewStateCard label="audit_log_reference_present" value={persistencePreview.audit_log_reference_present} />
            <SignedReviewStateCard label="rollback_evidence_required" value={persistencePreview.rollback_evidence_required} />
          </div>

          <TreatmentFrameworkSignedReviewStatePersistenceSafetyGrid qualityGate={qualityGate} safety={safety} />
        </>
      )}
    </div>
  );
}

function TreatmentFrameworkSignedReviewStatePersistenceSafetyGrid({ qualityGate, safety }) {
  const rows = [
    ["quality_gate.status", qualityGate?.status],
    ["signed_review_state_persistence_preview_only", qualityGate?.signed_review_state_persistence_preview_only],
    ["signed_review_state_persistence_enabled", qualityGate?.signed_review_state_persistence_enabled],
    ["review_state_persistence_enabled", qualityGate?.review_state_persistence_enabled],
    ["writes_database", safety?.writes_database],
    ["writes_case_treatment", safety?.writes_case_treatment],
    ["persists_treatment_framework", safety?.persists_treatment_framework],
    ["creates_prescription", safety?.creates_prescription],
    ["writes_prescription", safety?.writes_prescription],
    ["returns_drug_dose", safety?.returns_drug_dose],
    ["returns_drug_route", safety?.returns_drug_route],
    ["returns_drug_frequency", safety?.returns_drug_frequency],
    ["creates_signed_review_state", safety?.creates_signed_review_state],
    ["persists_signed_review_state", safety?.persists_signed_review_state],
    ["not_client_facing", safety?.not_client_facing],
    ["requires_human_review", safety?.requires_human_review],
    ["clinician_signoff_required", safety?.clinician_signoff_required],
  ];
  return (
    <div className="signed-review-state-persistence-safety-grid">
      {rows.map(([label, value]) => (
        <SignedReviewStateCard key={label} label={label} value={value} />
      ))}
    </div>
  );
}
// --- Case Detail Treatment Framework Signed Review State Persistence UI V1 components: end ---
// --- Case Detail Treatment Framework Signed Review State Persistence Migration UI V1 components: start ---
function TreatmentFrameworkSignedReviewStateMigrationPanel({
  signedReviewStatePersistencePreview,
  preview,
  loading,
  status,
  requestedBy,
  onRequestedByChange,
  onBuild,
}) {
  const hasPersistencePreview = Boolean(signedReviewStatePersistencePreview?.persistence_dry_run_preview);
  const migrationPlan = preview?.migration_plan_preview || {};
  const qualityGate = preview?.quality_gate || {};
  const safety = preview?.safety || {};
  const schemaPlan = migrationPlan.future_schema_plan || {};
  const hasPreview = Boolean(preview);

  return (
    <div className="signed-review-state-migration-panel">
      <div className="signed-review-state-migration-form screen-only">
        <label className="signed-review-state-migration-label">
          <span>Migration dry-run 申请医生 / Requested by</span>
          <input
            value={requestedBy}
            onChange={(event) => onRequestedByChange(event.target.value)}
            className="signed-review-state-migration-input"
            placeholder="requesting clinician id / doctor name"
          />
        </label>
        <button type="button" style={btnDoc} onClick={onBuild} disabled={loading || !hasPersistencePreview}>
          {loading ? "生成中…" : "生成 migration dry-run 预览"}
        </button>
      </div>

      <div className="signed-review-state-migration-status">
        {status || "医生端 migration dry-run 预览；先生成 signed review state persistence dry-run preview。不会执行 migration、不会改 schema、不会写数据库。"}
      </div>

      <div className="signed-review-state-migration-boundary">
        endpoint=/api/diagnostic-data/dry-run/confirmed-diagnosis/treatment-framework/signed-review-state/persistence/migration/dry-run · migration_dry_run_only=true · migration_enabled=false · migration_file_created=false · schema_change_enabled=false · persistence_enabled=false · signed_review_state_persistence_enabled=false · review_state_persistence_enabled=false · writes_database=false · writes_case_treatment=false · creates_prescription=false · writes_prescription=false · returns_drug_dose=false · returns_drug_route=false · returns_drug_frequency=false · not_client_facing=true · requires_human_review=true · clinician_signoff_required=true
      </div>

      {!hasPersistencePreview && (
        <div className="signed-review-state-migration-empty">
          需要先生成 signed review state persistence dry-run preview。本面板只调用 migration dry-run endpoint，不创建 migration 文件、不改 schema。
        </div>
      )}

      {!hasPreview ? (
        <div className="signed-review-state-migration-empty">
          尚未生成 migration dry-run preview。该结果只用于医生端上线前复核，不执行 Alembic migration。
        </div>
      ) : (
        <>
          <div className="signed-review-state-migration-grid">
            <SignedReviewStateCard label="preview_id" value={migrationPlan.preview_id} />
            <SignedReviewStateCard label="target_table" value={migrationPlan.target_table} />
            <SignedReviewStateCard label="operation" value={migrationPlan.operation} />
            <SignedReviewStateCard label="dry_run" value={migrationPlan.dry_run} />
            <SignedReviewStateCard label="migration_enabled" value={migrationPlan.migration_enabled} />
            <SignedReviewStateCard label="migration_file_created" value={migrationPlan.migration_file_created} />
            <SignedReviewStateCard label="schema_change_enabled" value={migrationPlan.schema_change_enabled} />
            <SignedReviewStateCard label="will_apply_migration" value={migrationPlan.will_apply_migration} />
            <SignedReviewStateCard label="writes_database" value={migrationPlan.writes_database} />
            <SignedReviewStateCard label="rollback_plan_required" value={migrationPlan.rollback_plan_required} />
            <SignedReviewStateCard label="backup_restore_evidence_required" value={migrationPlan.backup_restore_evidence_required} />
            <SignedReviewStateCard label="authenticated_smoke_required_before_write" value={migrationPlan.authenticated_smoke_required_before_write} />
          </div>

          <div className="signed-review-state-migration-schema">
            <div className="signed-review-state-migration-schema-title">Future schema plan preview</div>
            <SignedReviewStateMigrationList title="Columns" items={schemaPlan.columns_preview} />
            <SignedReviewStateMigrationList title="Indexes" items={schemaPlan.indexes_preview} />
            <SignedReviewStateMigrationList title="Foreign keys" items={schemaPlan.foreign_keys_preview} />
            <SignedReviewStateMigrationList title="Rollback plan" items={migrationPlan.rollback_plan_preview} />
            <SignedReviewStateMigrationList title="Forbidden write targets" items={migrationPlan.forbidden_write_targets} />
          </div>

          <TreatmentFrameworkSignedReviewStateMigrationSafetyGrid qualityGate={qualityGate} safety={safety} />
        </>
      )}
    </div>
  );
}

function SignedReviewStateMigrationList({ title, items }) {
  const normalized = normalizeTreatmentFrameworkItems(items);
  return (
    <div className="signed-review-state-migration-list-block">
      <div className="signed-review-state-migration-list-title">{title}</div>
      {normalized.length === 0 ? (
        <div className="signed-review-state-migration-empty-small">暂无 dry-run 计划条目。</div>
      ) : (
        <ul className="signed-review-state-migration-list">
          {normalized.map((item, index) => (
            <li key={`${title}-${index}`}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function TreatmentFrameworkSignedReviewStateMigrationSafetyGrid({ qualityGate, safety }) {
  const rows = [
    ["quality_gate.status", qualityGate?.status],
    ["migration_dry_run_only", qualityGate?.migration_dry_run_only],
    ["migration_enabled", qualityGate?.migration_enabled],
    ["migration_file_created", qualityGate?.migration_file_created],
    ["schema_change_enabled", qualityGate?.schema_change_enabled],
    ["writes_database", safety?.writes_database],
    ["writes_case_treatment", safety?.writes_case_treatment],
    ["persists_treatment_framework", safety?.persists_treatment_framework],
    ["creates_prescription", safety?.creates_prescription],
    ["writes_prescription", safety?.writes_prescription],
    ["returns_drug_dose", safety?.returns_drug_dose],
    ["returns_drug_route", safety?.returns_drug_route],
    ["returns_drug_frequency", safety?.returns_drug_frequency],
    ["persists_signed_review_state", safety?.persists_signed_review_state],
    ["not_client_facing", safety?.not_client_facing],
    ["requires_human_review", safety?.requires_human_review],
    ["clinician_signoff_required", safety?.clinician_signoff_required],
  ];
  return (
    <div className="signed-review-state-migration-safety-grid">
      {rows.map(([label, value]) => (
        <SignedReviewStateCard key={label} label={label} value={value} />
      ))}
    </div>
  );
}
// --- Case Detail Treatment Framework Signed Review State Persistence Migration UI V1 components: end ---





function PreventiveCarePanel({
  reminders,
  preview,
  loading,
  busy,
  status,
  onRefresh,
  onDryRun,
  onCreateFromPreview,
  onComplete,
  onSnooze,
  onDismiss,
  onDisable,
}) {
  const actionablePreview = Array.isArray(preview) ? preview.slice(0, 8) : [];
  const reminderItems = Array.isArray(reminders) ? reminders : [];

  return (
    <div className="preventive-care-panel">
      <div className="preventive-care-actions screen-only">
        <button type="button" style={btnSecondary} onClick={onRefresh} disabled={loading || Boolean(busy)}>
          {loading ? "加载中…" : "刷新站内提醒"}
        </button>
        <button type="button" style={btnDoc} onClick={onDryRun} disabled={Boolean(busy)}>
          {busy === "dry-run" ? "计算中…" : "生成疫苗/驱虫提醒预览"}
        </button>
      </div>

      <div className="preventive-care-status">
        {status || "站内提醒功能仅用于预防保健复核，不发送短信/微信/邮件。sends_external_message=false"}
      </div>

      {actionablePreview.length > 0 && (
        <div className="preventive-care-subblock">
          <div className="preventive-care-subtitle">Dry-run 预览 / Reminder Preview</div>
          <div className="preventive-care-list">
            {actionablePreview.map((item) => (
              <div className="preventive-care-item" key={`${item.rule_id}-${item.due_date}`}>
                <div>
                  <div className="preventive-care-title">
                    {formatPreventiveCategory(item.category)} · {formatPreventiveStatus(item.status)}
                  </div>
                  <div className="preventive-care-meta">
                    到期：{item.due_date || "—"}　规则：{item.rule_id || "—"}　原因：{item.reason || "—"}
                  </div>
                  <div className="preventive-care-safe">
                    writes_database=false · sends_external_message=false · clinician confirmation required
                  </div>
                </div>
                <button
                  type="button"
                  className="screen-only"
                  style={btnSmall}
                  disabled={Boolean(busy)}
                  onClick={() => onCreateFromPreview(item)}
                >
                  创建站内提醒
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="preventive-care-subblock">
        <div className="preventive-care-subtitle">已建站内提醒 / Existing In-app Reminders</div>
        {reminderItems.length === 0 ? (
          <div className="preventive-care-empty">暂无站内提醒。可先生成 dry-run 预览，再创建提醒。</div>
        ) : (
          <div className="preventive-care-list">
            {reminderItems.map((item) => (
              <div className="preventive-care-item" key={item.reminder_id}>
                <div>
                  <div className="preventive-care-title">
                    {formatPreventiveCategory(item.category)} · {formatPreventiveStatus(item.status)}
                  </div>
                  <div className="preventive-care-meta">
                    到期：{formatDateOnly(item.due_date)}　宠物：{item.pet_name || "—"}　ID：{item.reminder_id}
                  </div>
                  <div className="preventive-care-safe">
                    sends_external_message=false · creates_case=false · updates_case=false
                  </div>
                </div>
                <div className="preventive-care-row-actions screen-only">
                  <button type="button" style={btnTiny} disabled={Boolean(busy)} onClick={() => onComplete(item)}>完成</button>
                  <button type="button" style={btnTiny} disabled={Boolean(busy)} onClick={() => onSnooze(item)}>延后14天</button>
                  <button type="button" style={btnTiny} disabled={Boolean(busy)} onClick={() => onDismiss(item)}>关闭</button>
                  <button type="button" style={btnTinyDanger} disabled={Boolean(busy)} onClick={() => onDisable(item)}>禁用提醒</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
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

function formatDateOnly(value) {
  if (!value) return "—";
  return String(value).slice(0, 10);
}

function formatDiagnosticDate(value) {
  if (!value) return "—";
  return String(value).replace("T", " ").slice(0, 16);
}

function formatReportType(value) {
  const map = {
    lab: "检验报告",
    cbc: "CBC",
    chemistry: "生化",
    imaging: "影像报告",
    device: "设备数据",
    manual: "手工记录",
  };
  return map[value] || value || "诊断报告";
}

function formatAbnormalFlag(value) {
  const text = String(value || "").trim();
  if (!text) return "未标记";
  const map = {
    high: "升高",
    low: "降低",
    abnormal: "异常",
    critical: "危急",
    normal: "正常",
  };
  return map[text.toLowerCase()] || text;
}

function formatObservationValue(item) {
  if (item?.value_numeric !== null && item?.value_numeric !== undefined && item?.value_numeric !== "") {
    return String(item.value_numeric);
  }
  return safeText(item?.value_text);
}

function formatPreventiveCategory(value) {
  const map = {
    canine_core_vaccine: "犬核心疫苗",
    canine_rabies: "犬狂犬疫苗",
    feline_core_vaccine: "猫核心疫苗",
    feline_rabies: "猫狂犬疫苗",
    internal_deworming: "体内驱虫",
    external_parasite_prevention: "体外寄生虫预防",
    fecal_exam: "粪检",
    annual_preventive_exam: "年度体检",
    heartworm_test_placeholder: "心丝虫检测",
  };
  return map[value] || value || "预防保健";
}

function formatPreventiveStatus(value) {
  const map = {
    active: "未到期",
    due_soon: "即将到期",
    due: "已到期",
    overdue: "逾期",
    completed: "已完成",
    snoozed: "已延后",
    dismissed: "已关闭",
    disabled: "已禁用",
    opted_out: "已退订",
    draft: "草稿",
  };
  return map[value] || value || "未记录";
}


// --- Diagnostic Assistance Case Detail UI V1 helpers: start ---
function buildDiagnosticAssistanceCaseContext(data) {
  return {
    case_id: data?.id ? Number(data.id) : undefined,
    patient_name: data?.patient_name || data?.patient?.name || "",
    species: data?.species || data?.patient?.species || "",
    sex: data?.sex || "",
    age_info: data?.age_info || "",
    breed: data?.breed || "",
    weight: data?.weight || "",
    chief_complaint: data?.chief_complaint || "",
    history: data?.history || "",
    exam_findings: data?.exam_findings || "",
    source: "diagnostic_assistance_case_detail_ui_v1",
    dry_run_only: true,
    writes_database: false,
    not_client_facing: true,
  };
}

function buildDiagnosticAssistanceLabSummary(summary) {
  const reports = Array.isArray(summary?.reports) ? summary.reports : [];
  const observations = Array.isArray(summary?.observations) ? summary.observations : [];
  const labReports = reports.filter((item) => /lab|cbc|chem|blood|urine|diagnostic/i.test(String(item?.report_type || item?.title || "")));
  const abnormalObservations = observations.filter((item) => {
    const flag = String(item?.abnormal_flag || "").toLowerCase();
    return flag && flag !== "normal";
  }).slice(0, 12);

  return {
    headline: labReports.length || abnormalObservations.length
      ? "Structured diagnostic data present for clinician review"
      : "No structured lab abnormality loaded in Case Detail UI",
    summary: [
      `reports=${reports.length}`,
      `observations=${observations.length}`,
      `abnormal_observations=${abnormalObservations.length}`,
    ].join(" · "),
    abnormal_findings: abnormalObservations.map((item) => ({
      name: item.display_name || item.code || "observation",
      code: item.code || "",
      value: item.value_numeric ?? item.value_text ?? "",
      unit: item.unit || "",
      abnormal_flag: item.abnormal_flag || "",
      interpretation: item.interpretation || "",
    })),
    review_recommendations: [
      "Clinician must verify lab source, units, reference intervals, and sample timing.",
    ],
    quality_gate: {
      status: "PASS",
      source: "case_detail_ui_preview",
      writes_database: false,
      requires_human_review: true,
    },
    dry_run_only: true,
    writes_database: false,
  };
}

function buildDiagnosticAssistanceImagingSummary(summary) {
  const imagingStudies = Array.isArray(summary?.imaging_studies) ? summary.imaging_studies : [];
  const abnormalStudies = imagingStudies.filter((item) => {
    const flag = String(item?.abnormal_flag || "").toLowerCase();
    return flag && flag !== "normal";
  }).slice(0, 8);

  return {
    headline: imagingStudies.length
      ? "Structured imaging metadata present for clinician review"
      : "No structured imaging metadata loaded in Case Detail UI",
    summary: `imaging_studies=${imagingStudies.length} · abnormal_imaging=${abnormalStudies.length}`,
    imaging_findings: abnormalStudies.map((item) => ({
      modality: item.modality || "",
      body_part: item.body_part || "",
      abnormal_flag: item.abnormal_flag || "",
      report_text: item.report_text || item.ai_summary || "",
      review_status: item.review_status || "",
    })),
    review_recommendations: [
      "Clinician must verify imaging report text, modality, body part, and review status.",
    ],
    quality_gate: {
      status: "PASS",
      source: "case_detail_ui_preview",
      writes_database: false,
      requires_human_review: true,
    },
    dry_run_only: true,
    writes_database: false,
  };
}
// --- Diagnostic Assistance Case Detail UI V1 helpers: end ---

// --- Case Detail Treatment Framework Preview UI V1 helpers: start ---
function buildTreatmentFrameworkDiagnosticContext(data, diagnosticDataSummary, diagnosticAssistancePreview) {
  const counts = diagnosticDataSummary?.counts || {};
  const problemPayload = diagnosticAssistancePreview?.problem_list || {};
  const differentialPayload = diagnosticAssistancePreview?.differential_candidates || {};
  const tracePayload = diagnosticAssistancePreview?.evidence_trace || {};

  return {
    source: "case_detail_treatment_framework_preview_ui_v1",
    dry_run_only: true,
    read_only: true,
    writes_database: false,
    writes_case_treatment: false,
    creates_prescription: false,
    writes_prescription: false,
    returns_drug_dose: false,
    returns_drug_route: false,
    returns_drug_frequency: false,
    not_client_facing: true,
    requires_human_review: true,
    clinician_signoff_required: true,
    diagnostic_data_counts: {
      reports: counts.reports || 0,
      observations: counts.observations || 0,
      imaging_studies: counts.imaging_studies || 0,
    },
    lab_context: buildDiagnosticAssistanceLabSummary(diagnosticDataSummary),
    imaging_context: buildDiagnosticAssistanceImagingSummary(diagnosticDataSummary),
    diagnostic_assistance_context: {
      problem_list_preview_count: Array.isArray(problemPayload.problem_list_preview) ? problemPayload.problem_list_preview.length : 0,
      differential_candidates_preview_count: Array.isArray(differentialPayload.differential_diagnosis_candidates_preview) ? differentialPayload.differential_diagnosis_candidates_preview.length : 0,
      evidence_trace_preview_count: Array.isArray(tracePayload.diagnostic_reasoning_evidence_trace_preview) ? tracePayload.diagnostic_reasoning_evidence_trace_preview.length : 0,
      diagnostic_assistance_available: Boolean(diagnosticAssistancePreview),
    },
    case_snapshot: buildDiagnosticAssistanceCaseContext(data),
  };
}

function normalizeTreatmentFrameworkItems(value) {
  if (Array.isArray(value)) {
    return value.map(formatTreatmentFrameworkItem).filter(Boolean);
  }
  if (value && typeof value === "object") {
    return Object.entries(value)
      .map(([key, item]) => `${key}: ${formatTreatmentFrameworkItem(item)}`)
      .filter(Boolean);
  }
  const text = String(value || "").trim();
  return text ? [text] : [];
}

function formatTreatmentFrameworkItem(item) {
  if (item === null || item === undefined) return "";
  if (typeof item === "string") return item;
  if (typeof item === "number" || typeof item === "boolean") return String(item);
  if (Array.isArray(item)) return item.map(formatTreatmentFrameworkItem).filter(Boolean).join("；");
  if (typeof item === "object") {
    const primary = item.title || item.label || item.name || item.category || item.goal || item.parameter || item.topic;
    const detail = item.detail || item.description || item.reason || item.review_note || item.clinician_review_note;
    return [primary, detail].filter(Boolean).join("：") || JSON.stringify(item);
  }
  return String(item);
}
// --- Case Detail Treatment Framework Preview UI V1 helpers: end ---
// --- Case Detail Treatment Framework Signed Review State Persistence UI V1 helpers: start ---
function buildSignedReviewStatePersistencePayload({
  data,
  diagnosisLabel,
  confirmedBy,
  treatmentFrameworkPreview,
  signedReviewStatePreview,
  reviewedBy,
  reviewDecision,
  signedBy,
  signoffDecision,
  requestedBy,
  auditRequestId,
}) {
  const auditReference = buildSignedReviewStateAuditReference(data?.id, auditRequestId);
  return {
    case_id: Number(data.id),
    confirmed_diagnosis_label: diagnosisLabel,
    confirmed_by: confirmedBy,
    confirmation_source: "clinician",
    ai_generated: false,
    treatment_framework_preview: treatmentFrameworkPreview?.treatment_framework_preview || {},
    signed_review_state_preview: signedReviewStatePreview?.signed_review_state_preview || {},
    reviewed_by: reviewedBy,
    review_decision: reviewDecision,
    signed_by: signedBy,
    signoff_decision: signoffDecision,
    persistence_requested_by: requestedBy,
    audit_request_id: auditReference.audit_request_id,
    request_id: auditReference.audit_request_id,
    audit_log_result: auditReference.audit_log_result,
    audit_event: auditReference.audit_event,
    persistence_dry_run_only: true,
    persistence_enabled: false,
    signed_review_state_persistence_enabled: false,
    review_state_persistence_enabled: false,
    writes_database: false,
    writes_case_treatment: false,
    creates_prescription: false,
    writes_prescription: false,
    returns_drug_dose: false,
    returns_drug_route: false,
    returns_drug_frequency: false,
    not_client_facing: true,
    requires_human_review: true,
    clinician_signoff_required: true,
  };
}
// --- Case Detail Treatment Framework Signed Review State Persistence UI V1 helpers: end ---
// --- Case Detail Treatment Framework Signed Review State Persistence Migration UI V1 helpers: start ---
function buildSignedReviewStateMigrationPayload({
  data,
  diagnosisLabel,
  confirmedBy,
  treatmentFrameworkPreview,
  signedReviewStatePreview,
  signedReviewStatePersistencePreview,
  migrationRequestedBy,
}) {
  return {
    case_id: Number(data.id),
    confirmed_diagnosis_label: diagnosisLabel,
    confirmed_by: confirmedBy,
    confirmation_source: "clinician",
    ai_generated: false,
    treatment_framework_preview: treatmentFrameworkPreview?.treatment_framework_preview || {},
    signed_review_state_preview: signedReviewStatePreview?.signed_review_state_preview || {},
    persistence_dry_run_preview: signedReviewStatePersistencePreview?.persistence_dry_run_preview || {},
    migration_dry_run_requested_by: migrationRequestedBy,
    requested_by: migrationRequestedBy,
    migration_design_acknowledged: true,
    migration_readiness_review_completed: true,
    migration_dry_run_only: true,
    migration_enabled: false,
    migration_file_created: false,
    schema_change_enabled: false,
    persistence_enabled: false,
    signed_review_state_persistence_enabled: false,
    review_state_persistence_enabled: false,
    writes_database: false,
    writes_case_treatment: false,
    creates_prescription: false,
    writes_prescription: false,
    returns_drug_dose: false,
    returns_drug_route: false,
    returns_drug_frequency: false,
    not_client_facing: true,
    requires_human_review: true,
    clinician_signoff_required: true,
  };
}
// --- Case Detail Treatment Framework Signed Review State Persistence Migration UI V1 helpers: end ---



// --- Case Detail Treatment Framework Signed Review State UI V1 helpers: start ---
function buildSignedReviewStateAuditReference(caseId, auditRequestId) {
  const cleanId = String(auditRequestId || "").trim();
  const requestId = cleanId || `case-detail-signed-review-audit-${caseId || "case"}-${Date.now()}`;
  return {
    audit_request_id: requestId,
    audit_log_result: {
      decision: "audit_log_append_preview",
      dry_run: true,
      will_append_audit_log: false,
      persisted: false,
      append_only: true,
      request_id: requestId,
      writes_database: false,
      writes_audit_log: false,
    },
    audit_event: {
      request_id: requestId,
      event_type: "treatment_framework_review",
      source: "case_detail_treatment_framework_signed_review_state_ui_v1",
      metadata: {
        dry_run: true,
        writes_database: false,
        writes_audit_log: false,
        append_only_audit_log: true,
        signed_review_state_dry_run_only: true,
        signed_review_state_persistence_enabled: false,
        review_state_persistence_enabled: false,
        not_client_facing: true,
      },
    },
  };
}
// --- Case Detail Treatment Framework Signed Review State UI V1 helpers: end ---



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
const btnDoc = { ...btn, border: "1px solid #0f3b2e", background: "#0f3b2e", color: "#fff" };
const btnDanger = { ...btn, border: "1px solid #ef4444", background: "#ef4444", color: "#fff" };
const btnSmall = { ...btn, padding: "6px 10px", fontSize: 12, border: "1px solid #0f3b2e", color: "#0f3b2e", background: "#fff" };
const btnTiny = { ...btn, padding: "5px 8px", fontSize: 12 };
const btnTinyDanger = { ...btnTiny, border: "1px solid #ef4444", background: "#fff", color: "#b91c1c" };

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

  .clinical-doc-export-status {
    border: 1px solid #bbf7d0;
    background: #f0fdf4;
    color: #166534;
    border-radius: 12px;
    padding: 10px 12px;
    margin: 10px 0;
    font-size: 13px;
    font-weight: 700;
  }

  .diagnostic-data-panel {
    display: grid;
    gap: 12px;
  }
  .diagnostic-data-actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
  .diagnostic-data-status {
    border: 1px solid #bae6fd;
    background: #f0f9ff;
    color: #075985;
    border-radius: 12px;
    padding: 10px 12px;
    font-size: 13px;
    font-weight: 700;
  }
  .diagnostic-data-counts {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
  }
  .diagnostic-data-count-card {
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    background: #fff;
    padding: 10px 12px;
  }
  .diagnostic-data-count-value {
    font-size: 24px;
    font-weight: 900;
    color: #0f172a;
  }
  .diagnostic-data-count-label {
    font-size: 12px;
    color: #64748b;
  }
  .diagnostic-data-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
  }
  .diagnostic-data-subblock {
    display: grid;
    gap: 8px;
  }
  .diagnostic-data-subtitle {
    font-size: 14px;
    font-weight: 900;
    color: #0f172a;
  }
  .diagnostic-data-list {
    display: grid;
    gap: 8px;
  }
  .diagnostic-data-item {
    border: 1px solid #e5e7eb;
    background: #f8fafc;
    border-radius: 12px;
    padding: 10px 12px;
  }
  .diagnostic-data-item-title {
    font-weight: 850;
    color: #0f172a;
    margin-bottom: 4px;
  }
  .diagnostic-data-item-meta {
    font-size: 12px;
    color: #475569;
    word-break: break-word;
  }
  .diagnostic-data-item-safe {
    margin-top: 4px;
    font-size: 11px;
    color: #166534;
  }
  .diagnostic-data-empty, .diagnostic-data-empty-small {
    border: 1px dashed #cbd5e1;
    border-radius: 12px;
    padding: 10px 12px;
    color: #64748b;
    background: #fff;
  }
  .diagnostic-data-empty-small {
    font-size: 12px;
  }
  .diagnostic-data-safety {
    font-size: 11px;
    color: #166534;
  }
  @media (max-width: 760px) {
    .diagnostic-data-counts, .diagnostic-data-grid { grid-template-columns: 1fr; }
  }

  /* --- Diagnostic Assistance Case Detail UI V1 styles: start --- */
  .diagnostic-assistance-panel {
    display: grid;
    gap: 12px;
  }
  .diagnostic-assistance-actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
  .diagnostic-assistance-status {
    border: 1px solid #c7d2fe;
    background: #eef2ff;
    color: #3730a3;
    border-radius: 12px;
    padding: 10px 12px;
    font-size: 13px;
    font-weight: 800;
  }
  .diagnostic-assistance-boundary {
    border: 1px solid #bbf7d0;
    background: #f0fdf4;
    color: #166534;
    border-radius: 12px;
    padding: 9px 11px;
    font-size: 11px;
    font-weight: 700;
    line-height: 1.5;
  }
  .diagnostic-assistance-counts {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 8px;
  }
  .diagnostic-assistance-count-card {
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    background: #fff;
    padding: 10px 12px;
  }
  .diagnostic-assistance-count-value {
    font-size: 24px;
    font-weight: 900;
    color: #0f172a;
  }
  .diagnostic-assistance-count-label {
    font-size: 12px;
    color: #64748b;
  }
  .diagnostic-assistance-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
  }
  .diagnostic-assistance-subblock {
    display: grid;
    gap: 8px;
  }
  .diagnostic-assistance-subtitle {
    font-size: 14px;
    font-weight: 900;
    color: #0f172a;
  }
  .diagnostic-assistance-list {
    display: grid;
    gap: 8px;
  }
  .diagnostic-assistance-item {
    border: 1px solid #e5e7eb;
    background: #f8fafc;
    border-radius: 12px;
    padding: 10px 12px;
  }
  .diagnostic-assistance-item-title {
    font-weight: 850;
    color: #0f172a;
    margin-bottom: 4px;
  }
  .diagnostic-assistance-item-meta {
    font-size: 12px;
    color: #475569;
    word-break: break-word;
  }
  .diagnostic-assistance-evidence-list,
  .diagnostic-assistance-trace-list {
    margin: 8px 0 0;
    padding-left: 18px;
    font-size: 12px;
    color: #334155;
  }
  .diagnostic-assistance-review-questions {
    margin-top: 8px;
    border-top: 1px solid #e5e7eb;
    padding-top: 8px;
    font-size: 12px;
    color: #334155;
  }
  .diagnostic-assistance-mini-title {
    font-weight: 800;
    color: #0f172a;
    margin-bottom: 4px;
  }
  .diagnostic-assistance-empty,
  .diagnostic-assistance-empty-small {
    border: 1px dashed #cbd5e1;
    border-radius: 12px;
    padding: 10px 12px;
    color: #64748b;
    background: #fff;
  }
  .diagnostic-assistance-empty-small {
    font-size: 12px;
  }
  .diagnostic-assistance-quality-gates {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
  }
  .diagnostic-assistance-quality-card {
    border: 1px solid #e5e7eb;
    background: #fff;
    border-radius: 12px;
    padding: 10px 12px;
    font-size: 12px;
    color: #475569;
    word-break: break-word;
  }
  .diagnostic-assistance-quality-title {
    color: #0f172a;
    font-weight: 900;
    margin-bottom: 4px;
  }
  @media (max-width: 900px) {
    .diagnostic-assistance-counts,
    .diagnostic-assistance-grid,
    .diagnostic-assistance-quality-gates { grid-template-columns: 1fr; }
  }
  /* --- Diagnostic Assistance Case Detail UI V1 styles: end --- */


  /* --- Case Detail Treatment Framework Preview UI V1 styles: start --- */
  .treatment-framework-panel {
    display: grid;
    gap: 12px;
  }
  .treatment-framework-form {
    display: grid;
    gap: 10px;
  }
  .treatment-framework-label {
    display: grid;
    gap: 5px;
    font-size: 13px;
    font-weight: 800;
    color: #0f172a;
  }
  .treatment-framework-input,
  .treatment-framework-textarea {
    width: 100%;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    padding: 9px 10px;
    font: inherit;
    background: #fff;
    color: #0f172a;
  }
  .treatment-framework-status {
    border: 1px solid #fde68a;
    background: #fffbeb;
    color: #92400e;
    border-radius: 12px;
    padding: 10px 12px;
    font-size: 13px;
    font-weight: 800;
  }
  .treatment-framework-boundary {
    border: 1px solid #bbf7d0;
    background: #f0fdf4;
    color: #166534;
    border-radius: 12px;
    padding: 9px 11px;
    font-size: 11px;
    font-weight: 700;
    line-height: 1.5;
  }
  .treatment-framework-empty,
  .treatment-framework-empty-small {
    border: 1px dashed #cbd5e1;
    border-radius: 12px;
    padding: 10px 12px;
    color: #64748b;
    background: #fff;
  }
  .treatment-framework-empty-small {
    font-size: 12px;
  }
  .treatment-framework-confirmed {
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 10px 12px;
    background: #f8fafc;
    font-size: 12px;
    color: #334155;
    display: grid;
    gap: 3px;
  }
  .treatment-framework-mini-title {
    font-weight: 900;
    color: #0f172a;
    margin-bottom: 3px;
  }
  .treatment-framework-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }
  .treatment-framework-subblock {
    display: grid;
    gap: 8px;
  }
  .treatment-framework-subtitle {
    font-size: 14px;
    font-weight: 900;
    color: #0f172a;
  }
  .treatment-framework-list {
    margin: 0;
    padding-left: 18px;
    display: grid;
    gap: 6px;
    font-size: 13px;
    color: #334155;
  }
  .treatment-framework-safety-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
  }
  .treatment-framework-safety-card {
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    background: #fff;
    padding: 9px 10px;
  }
  .treatment-framework-safety-label {
    font-size: 11px;
    color: #64748b;
    word-break: break-word;
  }
  .treatment-framework-safety-value {
    font-size: 13px;
    font-weight: 900;
    color: #0f172a;
  }
  @media (max-width: 900px) {
    .treatment-framework-grid,
    .treatment-framework-safety-grid { grid-template-columns: 1fr; }
  }
  /* --- Case Detail Treatment Framework Preview UI V1 styles: end --- */

  /* --- Case Detail Treatment Framework Signed Review State UI V1 styles: start --- */
  .signed-review-state-panel {
    display: grid;
    gap: 12px;
  }
  .signed-review-state-form {
    display: grid;
    gap: 10px;
  }
  .signed-review-state-label {
    display: grid;
    gap: 5px;
    font-size: 13px;
    font-weight: 800;
    color: #0f172a;
  }
  .signed-review-state-input {
    width: 100%;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    padding: 9px 10px;
    font: inherit;
    background: #fff;
    color: #0f172a;
  }
  .signed-review-state-status {
    border: 1px solid #c7d2fe;
    background: #eef2ff;
    color: #3730a3;
    border-radius: 12px;
    padding: 10px 12px;
    font-size: 13px;
    font-weight: 800;
  }
  .signed-review-state-boundary {
    border: 1px solid #bbf7d0;
    background: #f0fdf4;
    color: #166534;
    border-radius: 12px;
    padding: 9px 11px;
    font-size: 11px;
    font-weight: 700;
    line-height: 1.5;
  }
  .signed-review-state-empty {
    border: 1px dashed #cbd5e1;
    border-radius: 12px;
    padding: 10px 12px;
    color: #64748b;
    background: #fff;
  }
  .signed-review-state-grid,
  .signed-review-state-safety-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
  }
  .signed-review-state-card {
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    background: #fff;
    padding: 9px 10px;
  }
  .signed-review-state-card-label {
    font-size: 11px;
    color: #64748b;
    word-break: break-word;
  }
  .signed-review-state-card-value {
    font-size: 13px;
    font-weight: 900;
    color: #0f172a;
    word-break: break-word;
  }
  @media (max-width: 900px) {
    .signed-review-state-grid,
    .signed-review-state-safety-grid { grid-template-columns: 1fr; }
  }
  /* --- Case Detail Treatment Framework Signed Review State UI V1 styles: end --- */
/* --- Case Detail Treatment Framework Signed Review State Persistence UI V1 styles: start --- */
.signed-review-state-persistence-panel {
  display: grid;
  gap: 12px;
}
.signed-review-state-persistence-form {
  display: grid;
  gap: 10px;
}
.signed-review-state-persistence-label {
  display: grid;
  gap: 5px;
  font-size: 13px;
  font-weight: 800;
  color: #0f172a;
}
.signed-review-state-persistence-input {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 9px 10px;
  font: inherit;
  background: #fff;
  color: #0f172a;
}
.signed-review-state-persistence-status {
  border: 1px solid #bfdbfe;
  background: #eff6ff;
  color: #1e3a8a;
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 13px;
  font-weight: 800;
}
.signed-review-state-persistence-boundary {
  border: 1px solid #bbf7d0;
  background: #f0fdf4;
  color: #166534;
  border-radius: 12px;
  padding: 9px 11px;
  font-size: 11px;
  font-weight: 700;
  line-height: 1.5;
}
.signed-review-state-persistence-empty {
  border: 1px dashed #cbd5e1;
  border-radius: 12px;
  padding: 10px 12px;
  color: #64748b;
  background: #fff;
}
.signed-review-state-persistence-grid,
.signed-review-state-persistence-safety-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}
@media (max-width: 900px) {
  .signed-review-state-persistence-grid,
  .signed-review-state-persistence-safety-grid { grid-template-columns: 1fr; }
}
/* --- Case Detail Treatment Framework Signed Review State Persistence UI V1 styles: end --- */

/* --- Case Detail Treatment Framework Signed Review State Persistence Migration UI V1 styles: start --- */
.signed-review-state-migration-panel {
  display: grid;
  gap: 12px;
}
.signed-review-state-migration-form {
  display: grid;
  gap: 10px;
}
.signed-review-state-migration-label {
  display: grid;
  gap: 5px;
  font-size: 13px;
  font-weight: 800;
  color: #0f172a;
}
.signed-review-state-migration-input {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 9px 10px;
  font: inherit;
  background: #fff;
  color: #0f172a;
}
.signed-review-state-migration-status {
  border: 1px solid #ddd6fe;
  background: #f5f3ff;
  color: #5b21b6;
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 13px;
  font-weight: 800;
}
.signed-review-state-migration-boundary {
  border: 1px solid #bbf7d0;
  background: #f0fdf4;
  color: #166534;
  border-radius: 12px;
  padding: 9px 11px;
  font-size: 11px;
  font-weight: 700;
  line-height: 1.5;
}
.signed-review-state-migration-empty,
.signed-review-state-migration-empty-small {
  border: 1px dashed #cbd5e1;
  border-radius: 12px;
  padding: 10px 12px;
  color: #64748b;
  background: #fff;
}
.signed-review-state-migration-empty-small {
  font-size: 12px;
}
.signed-review-state-migration-grid,
.signed-review-state-migration-safety-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}
.signed-review-state-migration-schema {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 10px 12px;
  background: #fff;
  display: grid;
  gap: 10px;
}
.signed-review-state-migration-schema-title {
  font-weight: 900;
  color: #0f172a;
}
.signed-review-state-migration-list-block {
  display: grid;
  gap: 6px;
}
.signed-review-state-migration-list-title {
  font-size: 13px;
  font-weight: 900;
  color: #334155;
}
.signed-review-state-migration-list {
  margin: 0;
  padding-left: 18px;
  display: grid;
  gap: 4px;
  font-size: 12px;
  color: #475569;
}
@media (max-width: 900px) {
  .signed-review-state-migration-grid,
  .signed-review-state-migration-safety-grid { grid-template-columns: 1fr; }
}
/* --- Case Detail Treatment Framework Signed Review State Persistence Migration UI V1 styles: end --- */





  .preventive-care-panel {
    display: grid;
    gap: 12px;
  }
  .preventive-care-actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
  .preventive-care-status {
    border: 1px solid #bbf7d0;
    background: #f0fdf4;
    color: #166534;
    border-radius: 12px;
    padding: 10px 12px;
    font-size: 13px;
    font-weight: 700;
  }
  .preventive-care-subblock {
    display: grid;
    gap: 8px;
  }
  .preventive-care-subtitle {
    font-size: 14px;
    font-weight: 800;
    color: #0f172a;
  }
  .preventive-care-list {
    display: grid;
    gap: 8px;
  }
  .preventive-care-item {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    align-items: flex-start;
    border: 1px solid #e5e7eb;
    background: #f8fafc;
    border-radius: 12px;
    padding: 10px 12px;
  }
  .preventive-care-title {
    font-weight: 800;
    color: #0f172a;
    margin-bottom: 4px;
  }
  .preventive-care-meta {
    font-size: 12px;
    color: #475569;
    word-break: break-word;
  }
  .preventive-care-safe {
    margin-top: 4px;
    font-size: 11px;
    color: #166534;
  }
  .preventive-care-empty {
    border: 1px dashed #cbd5e1;
    border-radius: 12px;
    padding: 10px 12px;
    color: #64748b;
    background: #fff;
  }
  .preventive-care-row-actions {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

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
