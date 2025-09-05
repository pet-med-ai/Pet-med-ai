// src/pages/CaseEditorLite.jsx
import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE || "https://pet-med-ai-backend.onrender.com";

export default function CaseEditorLite() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isNew = !id || id === "new";

  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(!isNew);
  const [error, setError] = useState("");

  const [form, setForm] = useState({
    status: "draft",
    patient: { name: "", species: "canine", breed: "", sex: "Unknown", ageYears: "", ageMonths: "", weightKg: "", microchip: "" },
    owner: { name: "", phone: "", email: "" },
    complaint: "",
    history: "",
    vitals: { tempC: "", hr: "", rr: "", sbp: "" },
    exam: "",
    labs: "",
    imaging: "",
    diagnoses: [],
    assessment: "",
    plan: "",
    medications: [],
    procedures: [],
    followUpDate: "",
    attachments: [],
    pinned: false
  });

  // 初次加载已有病例
  useEffect(() => {
    if (isNew) return;
    let stop = false;
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/cases/${id}`, { credentials: "include" });
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        if (!stop) setForm((f) => ({ ...f, ...data }));
      } catch (e) {
        setError(String(e));
      } finally {
        if (!stop) setLoading(false);
      }
    })();
    return () => { stop = true; };
  }, [id, isNew]);

  const set = (path, value) => {
    setForm((prev) => {
      const next = { ...prev };
      const segs = path.split(".");
      let cur = next;
      for (let i = 0; i < segs.length - 1; i++) cur = cur[segs[i]];
      cur[segs[segs.length - 1]] = value;
      return next;
    });
  };

  const save = async () => {
    setSaving(true);
    setError("");
    try {
      const body = JSON.stringify(form);
      if (isNew) {
        const res = await fetch(`${API_BASE}/api/cases`, { method: "POST", headers: { "Content-Type": "application/json" }, credentials: "include", body });
        if (!res.ok) throw new Error(await res.text());
        const created = await res.json();
        navigate(`/cases/${created.id}/edit`, { replace: true });
      } else {
        const res = await fetch(`${API_BASE}/api/cases/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, credentials: "include", body });
        if (!res.ok) throw new Error(await res.text());
        alert("已保存");
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  // 简单的附件上传（可选）
  const onFiles = async (files) => {
    try {
      const uploaded = [];
      for (const file of files) {
        const fd = new FormData();
        fd.append("file", file);
        const res = await fetch(`${API_BASE}/api/files`, { method: "POST", body: fd, credentials: "include" });
        if (!res.ok) throw new Error(await res.text());
        uploaded.push(await res.json());
      }
      set("attachments", [...form.attachments, ...uploaded]);
    } catch (e) {
      setError(String(e));
    }
  };

  if (loading) return <div style={{ padding: 24 }}>加载中…</div>;

  return (
    <div style={{ padding: 24, maxWidth: 960, margin: "0 auto", fontFamily: "system-ui, -apple-system, Arial" }}>
      <h1 style={{ marginTop: 0 }}>病例编辑（简化版）</h1>
      {error && <div style={{ color: "crimson", margin: "8px 0" }}>{error}</div>}

      <section style={card}>
        <h3 style={h3}>患者信息</h3>
        <div style={grid2}>
          <Field label="昵称">
            <input value={form.patient.name} onChange={(e)=>set("patient.name", e.target.value)} />
          </Field>
          <Field label="种属">
            <select value={form.patient.species} onChange={(e)=>set("patient.species", e.target.value)}>
              <option value="canine">犬</option><option value="feline">猫</option><option value="other">其他</option>
            </select>
          </Field>
          <Field label="品种"><input value={form.patient.breed} onChange={(e)=>set("patient.breed", e.target.value)} /></Field>
          <Field label="性别">
            <select value={form.patient.sex} onChange={(e)=>set("patient.sex", e.target.value)}>
              <option value="M">公</option><option value="MN">公绝育</option><option value="F">母</option><option value="FN">母绝育</option><option value="Unknown">未知</option>
            </select>
          </Field>
          <Field label="年龄（年/月）">
            <div style={{ display:"flex", gap:8 }}>
              <input type="number" placeholder="年" value={form.patient.ageYears||""} onChange={(e)=>set("patient.ageYears", e.target.value)} style={{ width:80 }}/>
              <input type="number" placeholder="月" value={form.patient.ageMonths||""} onChange={(e)=>set("patient.ageMonths", e.target.value)} style={{ width:80 }}/>
            </div>
          </Field>
          <Field label="体重(kg)">
            <input type="number" step="0.1" value={form.patient.weightKg||""} onChange={(e)=>set("patient.weightKg", e.target.value)} />
          </Field>
          <Field label="芯片">
            <input value={form.patient.microchip} onChange={(e)=>set("patient.microchip", e.target.value)} />
          </Field>
        </div>
      </section>

      <section style={card}>
        <h3 style={h3}>主人信息</h3>
        <div style={grid2}>
          <Field label="姓名"><input value={form.owner.name} onChange={(e)=>set("owner.name", e.target.value)} /></Field>
          <Field label="电话"><input value={form.owner.phone} onChange={(e)=>set("owner.phone", e.target.value)} /></Field>
          <Field label="邮箱"><input type="email" value={form.owner.email} onChange={(e)=>set("owner.email", e.target.value)} /></Field>
        </div>
      </section>

      <section style={card}>
        <h3 style={h3}>就诊信息</h3>
        <Field label="主诉"><textarea rows={3} value={form.complaint} onChange={(e)=>set("complaint", e.target.value)} /></Field>
        <Field label="现病史"><textarea rows={4} value={form.history} onChange={(e)=>set("history", e.target.value)} /></Field>
        <div style={grid4}>
          <Field label="体温℃"><input type="number" step="0.1" value={form.vitals.tempC||""} onChange={(e)=>set("vitals.tempC", e.target.value)} /></Field>
          <Field label="心率"><input type="number" value={form.vitals.hr||""} onChange={(e)=>set("vitals.hr", e.target.value)} /></Field>
          <Field label="呼吸"><input type="number" value={form.vitals.rr||""} onChange={(e)=>set("vitals.rr", e.target.value)} /></Field>
          <Field label="收缩压"><input type="number" value={form.vitals.sbp||""} onChange={(e)=>set("vitals.sbp", e.target.value)} /></Field>
        </div>
      </section>

      <section style={card}>
        <h3 style={h3}>检查与诊疗</h3>
        <Field label="体检"><textarea rows={4} value={form.exam} onChange={(e)=>set("exam", e.target.value)} /></Field>
        <Field label="实验室"><textarea rows={4} value={form.labs} onChange={(e)=>set("labs", e.target.value)} /></Field>
        <Field label="影像学"><textarea rows={3} value={form.imaging} onChange={(e)=>set("imaging", e.target.value)} /></Field>
        <Field label="诊断（逗号分隔）">
          <input value={form.diagnoses?.join(", ")||""}
                 onChange={(e)=>set("diagnoses", e.target.value.split(",").map(s=>s.trim()).filter(Boolean))}/>
        </Field>
        <Field label="评估"><textarea rows={4} value={form.assessment} onChange={(e)=>set("assessment", e.target.value)} /></Field>
        <Field label="计划"><textarea rows={4} value={form.plan} onChange={(e)=>set("plan", e.target.value)} /></Field>
      </section>

      <section style={card}>
        <h3 style={h3}>附件</h3>
        <input type="file" multiple onChange={(e)=>onFiles(e.target.files)} />
        <ul style={{ marginTop: 8 }}>
          {(form.attachments || []).map((a)=>(
            <li key={a.id}><a href={a.url} target="_blank" rel="noreferrer">{a.name}</a></li>
          ))}
        </ul>
      </section>

      <div style={{ display:"flex", gap:12, marginTop:16 }}>
        <button onClick={save} disabled={saving} style={btnPrimary}>{saving ? "保存中…" : "保存"}</button>
        {!isNew && <button onClick={()=>navigate("/")} style={btn}>返回首页</button>}
      </div>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label style={{ display:"block", marginTop:12 }}>
      <div style={{ fontSize:13, opacity:.8, marginBottom:4 }}>{label}</div>
      {children}
    </label>
  );
}

const card = { background:"#fff", border:"1px solid #e5e7eb", borderRadius:12, padding:16, marginTop:16 };
const h3 = { margin:"0 0 8px" };
const grid2 = { display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 };
const grid4 = { display:"grid", gridTemplateColumns:"repeat(4, 1fr)", gap:12 };
const btn = { padding:"8px 14px", borderRadius:8, border:"1px solid #64748b", background:"#fff", cursor:"pointer" };
const btnPrimary = { padding:"8px 14px", borderRadius:8, border:"1px solid #0ea5e9", background:"#0ea5e9", color:"#fff", cursor:"pointer" };
