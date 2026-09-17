// src/pages/CaseEditorLite.jsx
import React, { useEffect, useRef, useState } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import api from "../api";
import ManualCaseCreateReview from "../components/ManualCaseCreateReview";
import CaseEditReview from "../components/CaseEditReview";
import { caseEditDraftOwner, clearCaseEditDraft, clearCaseEditDrafts, readCaseEditDraft, writeCaseEditDraft } from "../caseEditDraft";

const EMPTY_FORM = {
  patient_name: "",
  species: "dog",
  sex: "",
  age_info: "",
  breed: "",
  weight: "",
  coat_color: "",
  owner_name: "",
  owner_phone: "",
  chief_complaint: "",
  history: "",
  exam_findings: "",
  analysis: "",
  treatment: "",
  prognosis: "",
};

export default function CaseEditorLite() {
  const { id } = useParams();
  return <CaseEditor key={id || "new"} id={id} />;
}

function CaseEditor({ id }) {
  const navigate = useNavigate();
  const location = useLocation();
  const isNew = !id || id === "new";

  const [form, setForm] = useState(() => {
    const seed = location.state?.manualCase;
    return isNew && seed?.owner && seed.owner === caseEditDraftOwner()
      ? normalizeCase(seed.values || {}) : EMPTY_FORM;
  });
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(!isNew);
  const [error, setError] = useState("");
  const [editState, setEditState] = useState(null);
  const [reloadVersion, setReloadVersion] = useState(0);
  const [draftOwner] = useState(() => caseEditDraftOwner());
  const [initialDraft] = useState(() => isNew ? { draft: null, error: "" } : readCaseEditDraft(draftOwner, Number(id)));
  const [draftOffer, setDraftOffer] = useState(initialDraft.draft);
  const [draftMessage, setDraftMessage] = useState(initialDraft.error);
  const [restoring, setRestoring] = useState(false);
  const mounted = useRef(false), recoveryBusy = useRef(false);
  const identityChanged = !!draftOwner && draftOwner !== caseEditDraftOwner();
  const formRef = useRef(form); formRef.current = form;
  const editRef = useRef(editState); editRef.current = editState;
  const modifiedFields = (values = formRef.current, state = editRef.current) => {
    const initial = normalizeCase(state?.before);
    return Object.fromEntries(Object.entries(values).filter(([key, value]) => value !== initial[key]));
  };
  const keepDraft = (values, state = editRef.current) => {
    if (isNew || !state) return;
    if (!draftOwner || draftOwner !== caseEditDraftOwner()) {
      clearCaseEditDraft(Number(id));
      setDraftMessage("无法确认当前账号，编辑草稿未暂存。请检查登录状态。");
      return;
    }
    const changes = modifiedFields(values, state);
    const ok = writeCaseEditDraft(draftOwner, Number(id), changes);
    setDraftMessage(ok ? (Object.keys(changes).length ? "修改已暂存在本标签页，尚未保存到病例。" : "") : "浏览器无法暂存最新修改，刷新或离开可能丢失输入。请先完成病例保存。");
  };
  const applyState = (state, values) => {
    editRef.current = state; formRef.current = values;
    setEditState(state); setForm(values);
  };
  const verifiedEdit = state => {
    applyState(state, normalizeCase(state.before));
    const cleared = clearCaseEditDraft(Number(id));
    setDraftMessage(cleared ? "修改已保存并回读，本病例编辑草稿已清除。" : "修改已保存并回读，但浏览器未能清除编辑草稿。");
  };
  const reloadEdit = state => {
    const changes = modifiedFields();
    const values = { ...normalizeCase(state.before), ...changes };
    applyState(state, values); keepDraft(values, state);
  };
  const validState = state => state?.case_id === Number(id) && state.case_token && state.before;

  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    if (isNew || typeof window === "undefined") return;
    const changed = event => {
      if (event.key === "token" || event.key === null) { clearCaseEditDrafts(); window.location.reload(); }
    };
    window.addEventListener("storage", changed);
    return () => window.removeEventListener("storage", changed);
  }, [isNew]);
  const hasPendingInput = !isNew && (draftOffer || (editState && Object.keys(modifiedFields()).length > 0));
  useEffect(() => {
    if (!hasPendingInput || typeof window === "undefined") return;
    const warn = event => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [!!hasPendingInput]);

  async function restoreDraft() {
    if (!draftOffer || saving || recoveryBusy.current || !draftOwner || draftOwner !== caseEditDraftOwner()) return;
    recoveryBusy.current = true; setRestoring(true); setDraftMessage("");
    try {
      const { data } = await api.get(`/api/cases/${id}/edit-state`, { timeout: 15000 });
      if (!mounted.current || draftOwner !== caseEditDraftOwner()) return;
      if (!validState(data)) throw new Error("Invalid case state");
      const remaining = Object.fromEntries(Object.entries(draftOffer.changes).filter(([key, value]) => data.before[key] !== value));
      const values = { ...normalizeCase(data.before), ...remaining };
      applyState(data, values); setDraftOffer(null); setError("");
      if (Object.keys(remaining).length) {
        keepDraft(values, data);
        setDraftMessage(previous => previous + " 已恢复编辑输入；服务器内容可能已更新，请重新核对后保存。");
      } else {
        const cleared = clearCaseEditDraft(Number(id));
        setDraftMessage("草稿中的修改与服务器一致，未再次提交保存。" + (cleared ? "编辑草稿已清除。" : "浏览器未能清除编辑草稿。"));
      }
    } catch {
      if (mounted.current) setDraftMessage("暂时无法读取最新病例，编辑草稿仍保留。请检查登录状态或网络后重试恢复。");
    } finally {
      recoveryBusy.current = false;
      if (mounted.current) setRestoring(false);
    }
  }
  function discardDraft() {
    if (restoring || saving) return;
    if (!clearCaseEditDraft(Number(id))) { setDraftMessage("浏览器未能清除编辑草稿，请稍后重试。"); return; }
    setDraftOffer(null); setDraftMessage("已丢弃本地编辑草稿，服务器病例未改动。");
  }

  useEffect(() => {
    if (isNew) {
      setEditState(null);
      setLoading(false);
      return;
    }

    let stop = false;
    (async () => {
      try {
        setLoading(true);
        setError("");
        setEditState(null);
        const res = await api.get(`/api/cases/${id}/edit-state`, { timeout: 15000 });
        if (!stop) {
          if (!validState(res.data)) throw new Error("病例读取结果不完整");
          applyState(res.data, normalizeCase(res.data.before));
        }
      } catch (e) {
        if (!stop) setError(getErrorText(e));
      } finally {
        if (!stop) setLoading(false);
      }
    })();

    return () => { stop = true; };
  }, [id, isNew, reloadVersion]);

  const setField = (key, value) => {
    if (draftOffer || restoring || identityChanged || saving) return;
    const values = { ...formRef.current, [key]: value };
    formRef.current = values; setForm(values); keepDraft(values);
  };

  if (loading) return <div style={{ padding: 24 }}>加载中…</div>;

  return (
    <div
      lang="zh-CN"
      translate="no"
      className="notranslate"
      style={{ padding: 24, maxWidth: 980, margin: "0 auto", fontFamily: "system-ui, -apple-system, Arial" }}
    >
      <h1 style={{ marginTop: 0 }}>{isNew ? "新建病例" : `编辑病例 #${id}`}</h1>

      <div style={toolbar}>
        <button type="button" disabled={saving || restoring} onClick={() => navigate("/")} style={btn}>返回首页</button>
        {!isNew && <button type="button" disabled={saving || restoring} onClick={() => navigate(`/cases/${id}`)} style={btnSecondary}>查看详情</button>}
      </div>

      {error && <div style={errorBox}>{error}</div>}
      {!isNew && <section aria-label="病例编辑草稿" style={{ ...card, marginBottom: 16 }}>
        <p>编辑草稿仅在本标签页保留，8 小时有效；恢复后需要重新核对保存。关闭标签页或更换设备不保证恢复。</p>
        {identityChanged && <p role="alert">登录账号已变化，请重新打开页面。</p>}
        {draftOffer && <>
          <strong>发现本病例未保存的编辑草稿</strong>
          <p>恢复会重新读取病例，再带回本次修改；保存前请对照服务器内容，尤其是完整病史。</p>
          <button type="button" disabled={restoring || saving || identityChanged} onClick={restoreDraft}>{restoring ? "正在读取最新病例…" : "恢复本病例编辑草稿"}</button>{" "}
          <button type="button" disabled={restoring || saving} onClick={discardDraft}>丢弃编辑草稿</button>
        </>}
        {draftMessage && <p role="status">{draftMessage}</p>}
      </section>}

      <fieldset disabled={saving || restoring || identityChanged || !!draftOffer || (!isNew && !editState)} style={{ border: 0, padding: 0, margin: 0, minWidth: 0 }}>
      <section style={card}>
        <h3 style={h3}>一、病例基础信息</h3>
        <div style={grid3}>
          <Field label="病例名 / 宠物名（必填）">
            <input value={form.patient_name} onChange={(e) => setField("patient_name", e.target.value)} placeholder="如：乐乐 / Lucky" />
          </Field>
          <Field label="物种">
            <select value={form.species} onChange={(e) => setField("species", e.target.value)}>
              <option value="dog">dog</option>
              <option value="cat">cat</option>
              <option value="other">other</option>
            </select>
          </Field>
          <Field label="性别">
            <input value={form.sex} onChange={(e) => setField("sex", e.target.value)} placeholder="M / F / 已绝育等" />
          </Field>
          <Field label="年龄信息">
            <input value={form.age_info} onChange={(e) => setField("age_info", e.target.value)} placeholder="如 4y / 6m" />
          </Field>
          <Field label="品种 / 宠物信息">
            <input value={form.breed} onChange={(e) => setField("breed", e.target.value)} placeholder="如 贵宾 / 英短 / 混种" />
          </Field>
          <Field label="体重">
            <input value={form.weight} onChange={(e) => setField("weight", e.target.value)} placeholder="如 5.2kg" />
          </Field>
          <Field label="毛色">
            <input value={form.coat_color} onChange={(e) => setField("coat_color", e.target.value)} placeholder="如 白色 / 虎斑" />
          </Field>
          <Field label="主人姓名">
            <input value={form.owner_name} onChange={(e) => setField("owner_name", e.target.value)} placeholder="如 张三" />
          </Field>
          <Field label="主人电话">
            <input value={form.owner_phone} onChange={(e) => setField("owner_phone", e.target.value)} placeholder="如 13800000000" />
          </Field>
        </div>
      </section>

      <section style={card}>
        <h3 style={h3}>二、主诉 / 病史 / 检查</h3>
        <Field label="主诉（必填）">
          <textarea rows={3} value={form.chief_complaint} onChange={(e) => setField("chief_complaint", e.target.value)} placeholder="如：小狗频繁呕吐，精神差，腹部胀" />
        </Field>
        <Field label="既往史 / 动态问诊追问记录">
          <textarea rows={6} value={form.history} onChange={(e) => setField("history", e.target.value)} />
        </Field>
        <Field label="体检 / 化验 / 来源信息">
          <textarea rows={5} value={form.exam_findings} onChange={(e) => setField("exam_findings", e.target.value)} />
        </Field>
      </section>

      <section style={card}>
        <h3 style={h3}>三、AI 分析 / 治疗 / 随访</h3>
        <Field label="AI 分析">
          <textarea rows={7} value={form.analysis} onChange={(e) => setField("analysis", e.target.value)} />
        </Field>
        <Field label="治疗建议">
          <textarea rows={5} value={form.treatment} onChange={(e) => setField("treatment", e.target.value)} />
        </Field>
        <Field label="风险提示 / 后续随访">
          <textarea rows={5} value={form.prognosis} onChange={(e) => setField("prognosis", e.target.value)} />
        </Field>
      </section>

      </fieldset>
      {!isNew && editState && !draftOffer && !identityChanged && <CaseEditReview key={id} caseId={Number(id)} baseline={editState} changes={modifiedFields()} onVerified={verifiedEdit} onReload={reloadEdit} onBusyChange={setSaving} />}
      {!isNew && !editState && <button type="button" onClick={() => setReloadVersion(n => n + 1)}>重新读取病例</button>}
      {isNew && <ManualCaseCreateReview values={form} onLockChange={setSaving}
        onNew={() => { formRef.current = EMPTY_FORM; setForm(EMPTY_FORM); }} />}

    </div>
  );
}

function normalizeCase(data = {}) {
  const ageFromLegacy = [
    data?.patient?.ageYears ? `${data.patient.ageYears}y` : "",
    data?.patient?.ageMonths ? `${data.patient.ageMonths}m` : "",
  ].filter(Boolean).join(" ");

  const examFromLegacy = [
    data.exam,
    data.labs ? `实验室：${data.labs}` : "",
    data.imaging ? `影像学：${data.imaging}` : "",
  ].filter(Boolean).join("\n\n");

  return {
    patient_name: data.patient_name || data?.patient?.name || "",
    species: normalizeSpecies(data.species || data?.patient?.species || "dog"),
    sex: data.sex || data?.patient?.sex || "",
    age_info: data.age_info || ageFromLegacy || "",
    breed: data.breed || data?.patient?.breed || "",
    weight: data.weight || data?.patient?.weightKg || "",
    coat_color: data.coat_color || "",
    owner_name: data.owner_name || data?.owner?.name || "",
    owner_phone: data.owner_phone || data?.owner?.phone || "",
    chief_complaint: data.chief_complaint || data.complaint || "",
    history: data.history || "",
    exam_findings: data.exam_findings || examFromLegacy || "",
    analysis: data.analysis || data.assessment || "",
    treatment: data.treatment || data.plan || "",
    prognosis: data.prognosis || "",
  };
}

function normalizeSpecies(value) {
  if (value === "canine") return "dog";
  if (value === "feline") return "cat";
  if (["dog", "cat", "other"].includes(value)) return value;
  return "other";
}

function getErrorText(err) {
  const detail = err?.response?.data?.detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item?.msg || JSON.stringify(item)).join("；");
  }
  if (typeof detail === "string") return detail;
  if (detail) return JSON.stringify(detail);
  return String(err);
}

function Field({ label, children }) {
  return (
    <label style={{ display: "block", marginTop: 12 }}>
      <div style={{ fontSize: 13, opacity: .8, marginBottom: 4 }}>{label}</div>
      {children}
    </label>
  );
}

const toolbar = {
  display: "flex",
  gap: 10,
  alignItems: "center",
  flexWrap: "wrap",
  margin: "8px 0 14px",
};

const card = {
  background: "#fff",
  border: "1px solid #e5e7eb",
  borderRadius: 12,
  padding: 16,
  marginTop: 16,
};

const h3 = { margin: "0 0 8px" };

const grid3 = {
  display: "grid",
  gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
  gap: 12,
};

const btn = {
  padding: "8px 14px",
  borderRadius: 8,
  border: "1px solid #64748b",
  background: "#fff",
  cursor: "pointer",
};

const btnSecondary = {
  ...btn,
  border: "1px solid #111",
  background: "#fff",
};

const errorBox = {
  color: "crimson",
  background: "#fff1f2",
  border: "1px solid #fecdd3",
  borderRadius: 10,
  padding: 10,
  margin: "8px 0",
};
