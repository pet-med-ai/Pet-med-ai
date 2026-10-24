import React from "react";

const states = { positive: "当前记录", negative: "明确否定", unknown: "未知／待核对", historical: "既往记录／时间待核对", conflict: "状态与原文冲突" };
export default function ConsultEvidence({ evidence }) {
  if (!evidence) return null;
  return <section aria-label="问诊输入依据">
    {evidence.needs_review && <p role="status">输入依据待核对，未知或矛盾记录不能视为正常。</p>}
    <details><summary>查看记录来源与判断状态</summary>
      {(evidence.conflicts || []).length > 0 && <p>同一症状存在肯定与否定记录，请核对时间及当前情况。</p>}
      {(evidence.records || []).map((row, i) => <div key={i}>
        <strong>{row.source} · {states[row.state] || "待核对"}</strong>
        {row.question && <p>问题：{row.question}</p>}
        <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{row.raw || "未填写原文"}</pre>
      </div>)}
    </details>
  </section>;
}
