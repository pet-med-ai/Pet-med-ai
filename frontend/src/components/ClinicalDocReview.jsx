import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";
import { draftOwner } from "../consultDraft";

const fields = [
  ["visit.case_id", "病例编号"], ["visit.pet_name", "动物名称"],
  ["visit.species", "物种"], ["visit.age", "年龄"], ["visit.sex", "性别"],
  ["visit.weight", "体重"], ["visit.complaint", "主诉"], ["visit.history", "病史原文"],
  ["visit.exam", "查体记录"], ["visit.assessment", "评估内容（非最终诊断）"],
  ["visit.plan", "诊疗计划原文"], ["visit.notes", "预后与补充说明"],
  ["visit.follow_up", "复查安排状态"], ["export.account_id", "导出账号（非签名）"],
];

export default function ClinicalDocReview({ caseId, templateId, label, requestToken, onDownload, onClose }) {
  const [preview, setPreview] = useState(null);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const active = useRef(false), pending = useRef(false), generation = useRef(0), heading = useRef(null);
  const callbacks = useRef({ onDownload, onClose });
  callbacks.current = { onDownload, onClose };
  const current = stamp => active.current && generation.current === stamp &&
    Boolean(requestToken) && localStorage.getItem("token") === requestToken;

  async function load() {
    if (pending.current || !active.current || localStorage.getItem("token") !== requestToken) return;
    pending.current = true;
    const stamp = ++generation.current;
    setBusy(true); setPreview(null); setConfirmed(false); setMessage("正在读取已保存的草稿内容…");
    try {
      const { data } = await api.post("/api/clinical-docs/render-preview", {
        case_id: caseId, template_id: templateId, output: "docx",
      }, { timeout: 15000, expectedAuthOwner: draftOwner(requestToken) });
      if (!current(stamp)) return;
      if (data.case_id !== caseId || data.template_id !== templateId ||
          !/^[a-f0-9]{64}$/.test(data.content_snapshot || "") ||
          data.context?.["visit.case_id"] !== String(caseId) ||
          !fields.every(([key]) => typeof data.context?.[key] === "string") ||
          !Array.isArray(data.missing_required_keys) || data.missing_required_keys.length || data.writes_database !== false) {
        throw new Error("未收到可核对的完整草稿，当前服务可能尚未支持。请重新读取，暂不能确认下载。");
      }
      setPreview(data); setMessage("");
    } catch (error) {
      if (current(stamp)) {
        const detail = error.response?.data?.detail;
        setMessage(typeof detail === "string" ? detail : error.message || "读取草稿失败，请重试。");
      }
    } finally {
      if (current(stamp)) { pending.current = false; setBusy(false); }
    }
  }

  useEffect(() => {
    active.current = true;
    pending.current = false;
    heading.current?.focus();
    void load();
    return () => { active.current = false; generation.current++; };
  }, [caseId, templateId, requestToken]);

  function leave() {
    active.current = false; generation.current++;
  }

  async function download() {
    const stamp = generation.current;
    if (pending.current || !current(stamp) || !preview || !confirmed) return;
    pending.current = true; setBusy(true); setConfirmed(false); setMessage("正在生成已核对的草稿…");
    try {
      const result = await callbacks.current.onDownload(preview.content_snapshot, () => current(stamp));
      if (!current(stamp)) return;
      setPreview(null);
      setMessage(result?.ok ? "已生成本次核对的草稿；仍未签署。再次下载请重新读取并核对。" :
        result?.status === 409 ? "病例或模板内容已变化，原确认已失效。请重新读取并核对草稿。" :
          `${result?.message || "下载未完成"}；请重新读取并核对草稿后重试。`);
    } finally {
      if (current(stamp)) { pending.current = false; setBusy(false); }
    }
  }

  return <section aria-label="文书草稿内容核对" className="screen-only"
    style={{ margin: "20px 0", padding: 18, border: "2px solid #93c5fd", borderRadius: 10 }}>
    <h2 ref={heading} tabIndex={-1}>核对{label}</h2>
    <p>瀚森宠物医院 · 草稿，待医生核对、尚未签署。本页核对已保存内容；Word/WPS 的分页请在下载后检查。</p>
    <button type="button" onClick={() => { leave(); callbacks.current.onClose(); }}>关闭草稿核对</button>{" "}
    <Link to={`/cases/${caseId}/edit`} onClick={leave}>返回病例更正</Link>{" "}
    <button type="button" disabled={busy} onClick={load}>重新读取草稿</button>
    {message && <p role="status" aria-live="polite">{message}</p>}
    {preview && <div>
      {fields.map(([key, title]) => <section key={key} aria-label={title + "核对内容"}>
        <h3>{title}</h3>
        <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere", font: "inherit", lineHeight: 1.6 }}>{preview.context[key]}</pre>
      </section>)}
      <label><input type="checkbox" checked={confirmed} disabled={busy}
        onChange={event => setConfirmed(event.target.checked)} /> 已核对本次草稿内容（仍未签署）</label>{" "}
      <button type="button" disabled={busy || !confirmed} onClick={download}>确认并下载草稿 DOCX</button>
    </div>}
  </section>;
}
