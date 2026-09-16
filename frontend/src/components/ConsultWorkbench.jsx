import React from "react";
import { Link } from "react-router-dom";
import "./ConsultWorkbench.css";

export const workbenchSteps = ["问诊整理", "保存前核对", "病例回看"];

export function WorkbenchSteps({ step, onChange, hasSession, hasReadback, busy, patientName, species, ageInfo }) {
  return <>
    <nav aria-label="问诊工作台步骤" className="workbench-steps">
      {workbenchSteps.map((label, index) => <button
        key={label} type="button" aria-current={step === index + 1 ? "step" : undefined}
        disabled={busy || (index === 1 && !hasSession) || (index === 2 && !hasReadback)}
        onClick={() => onChange(index + 1)}
      ><span className="step-number" aria-hidden="true">0{index + 1}</span><span>{label}</span></button>)}
    </nav>
    <div className="workbench-patient" aria-label="当前问诊对象">
      <strong>{patientName || "填写宠物信息，开始本次问诊"}</strong>
      <span>{({ dog: "犬", cat: "猫", other: "其他物种" })[species] || species} · {ageInfo || "年龄未填写"}</span>
      <span>{hasSession ? "本次问诊进行中" : "尚未开始问诊"}</span>
    </div>
  </>;
}

export function SavedCasePanel({ receipt, hasUnsavedChanges, onContinue }) {
  if (!receipt?.verified || !receipt.record) return <p>完成保存并回读核对后，可在这里查看本次保存内容。</p>;
  const record = receipt.record;
  return <section aria-label="本次保存回读" className="workbench-readback">
    <div className="readback-success">
      <div><span>病例编号</span><h3>#{record.id} · {record.patient_name || "未命名病例"}</h3></div>
      <p role="status">已回读病例 #{record.id}，{receipt.mode === "update" ? "本次更新的六项内容" : "基本信息与本次核对内容"}一致。</p>
    </div>
    <p>下方显示服务器实际回读的内容。</p>
    {hasUnsavedChanges && <p role="status" className="workbench-warning">当前输入另有修改，尚未保存；下方仍是上次回读的病例内容。</p>}
    {[["chief_complaint", "主诉"], ["history", "完整病史"], ["exam_findings", "体检 / 化验"]].map(([key, label]) =>
      <section key={key} aria-label={label} className="readback-field"><h3>{label}</h3><pre>{record[key] || "未填写"}</pre></section>
    )}
    <div className="workbench-actions">
      <Link to={`/cases/${record.id}`} className="workbench-primary">查看已保存病例 #{record.id} →</Link>
      <button type="button" onClick={onContinue}>继续补充本次问诊</button>
    </div>
  </section>;
}
