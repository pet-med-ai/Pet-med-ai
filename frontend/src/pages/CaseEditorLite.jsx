// src/pages/CaseEditorLite.jsx
import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import api from "../api";

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
  const navigate = useNavigate();
  const isNew = !id || id === "new";

  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(!isNew);
  const [error, setError] = useState("");

  useEffect(() => {
    if (isNew) {
      setForm(EMPTY_FORM);
      setLoading(false);
      return;
    }

    let stop = false;
    (async () => {
      try {
        setLoading(true);
        setError("");
        const res = await api.get(`/api/cases/${id}`);
        if (!stop) setForm(normalizeCase(res.data));
      } catch (e) {
        if (!stop) setError(getErrorText(e));
      } finally {
        if (!stop) setLoading(false);
      }
    })();

    return () => { stop = true; };
  }, [id, isNew]);

  const setField = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const buildPayload = () => ({
    patient_name: form.patient_name.trim(),
    species: form.species || "dog",
    sex: emptyToNull(form.sex),
    age_info: emptyToNull(form.age_info),
    breed: emptyToNull(form.breed),
    weight: emptyToNull(form.weight),
    coat_color: emptyToNull(form.coat_color),
    owner_name: emptyToNull(form.owner_name),
    owner_phone: emptyToNull(form.owner_phone),
    chief_complaint: form.chief_complaint.trim(),
    history: emptyToNull(form.history),
    exam_findings: emptyToNull(form.exam_findings),
    analysis: emptyToNull(form.analysis),
    treatment: emptyToNull(form.treatment),
    prognosis: emptyToNull(form.prognosis),
  });

  const validate = () => {
    if (!form.patient_name.trim()) {
      alert("请填写病例名 / 宠物名");
      return false;
    }
    if (!form.chief_complaint.trim()) {
      alert("请填写主诉");
      return false;
    }
    return true;
  };

  const save = async ({ goDetail = false } = {}) => {
    if (!validate()) return;

    try {
      setSaving(true);
      setError("");

      const payload = buildPayload();
      let saved;

      if (isNew) {
        const res = await api.post("/api/cases", payload);
        saved = res.data;
        alert(`创建成功：病例ID = ${saved.id}`);
        if (goDetail) {
          navigate(`/cases/${saved.id}`);
        } else {
          navigate(`/cases/${saved.id}/edit`, { replace: true });
        }
      } else {
        const res = await api.put(`/api/cases/${id}`, payload);
        saved = res.data;
        setForm(normalizeCase(saved));
        alert("已保存");
        if (goDetail) navigate(`/cases/${id}`);
      }
    } catch (e) {
      setError(getErrorText(e));
      alert("保存失败，请查看页面错误或后端日志");
    } finally {
      setSaving(false);
    }
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
        <button type="button" onClick={() => navigate("/")} style={btn}>返回首页</button>
        {!isNew && <button type="button" onClick={() => navigate(`/cases/${id}`)} style={btnSecondary}>查看详情</button>}
        <span style={{ fontSize: 12, opacity: 0.65 }}>后端：{import.meta.env.VITE_API_BASE}</span>
      </div>

      {error && <div style={errorBox}>{error}</div>}

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

      <div style={{ display: "flex", gap: 12, marginTop: 16, flexWrap: "wrap" }}>
        <button type="button" onClick={() => save()} disabled={saving} style={btnPrimary}>
          {saving ? "保存中…" : "保存"}
        </button>
        <button type="button" onClick={() => save({ goDetail: true })} disabled={saving} style={btnSecondary}>
          保存并查看详情
        </button>
        <button type="button" onClick={() => navigate("/")} style={btn}>返回首页</button>
      </div>
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

function emptyToNull(value) {
  const text = (value ?? "").toString().trim();
  return text ? text : null;
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

const btnPrimary = {
  ...btn,
  border: "1px solid #0ea5e9",
  background: "#0ea5e9",
  color: "#fff",
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
