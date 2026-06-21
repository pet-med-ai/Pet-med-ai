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
