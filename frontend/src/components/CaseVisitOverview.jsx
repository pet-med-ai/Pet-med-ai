import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";
import { overviewDestinations, overviewMessage, overviewStates, readOverview } from "../visitOverview";
import { states as planStates } from "../followupPlan";

const box = { padding: 16, margin: "12px 0", border: "1px solid #ccd5d1", borderRadius: 8, overflowWrap: "anywhere" };
const groups = { attachments: "原件", lab: "检验", imaging: "影像" };

export default function CaseVisitOverview(props) {
  return <Overview key={JSON.stringify([props.caseId, props.requestToken])} {...props} />;
}

function Overview({ caseId, requestToken, sourceRevision = 0, onNavigate }) {
  const [saved, setSaved] = useState(null), [message, setMessage] = useState(""), [busy, setBusy] = useState(false);
  const active = useRef(false), epoch = useRef(0), controller = useRef(null), refresh = useRef(null);
  const current = () => active.current && Boolean(requestToken) && localStorage.getItem("token") === requestToken;
  refresh.current = async () => {
    const attempt = ++epoch.current;
    controller.current?.abort(); controller.current = new AbortController();
    setSaved(null); setMessage("");
    if (!current()) { setBusy(false); setMessage("登录已变化，请重新打开病例。"); return; }
    setBusy(true);
    try {
      const result = await readOverview(caseId, requestToken, controller.current.signal);
      if (current() && attempt === epoch.current) setSaved({ result, revision: sourceRevision });
    } catch (error) {
      if (active.current && attempt === epoch.current) setMessage(current() ? overviewMessage(error) : "登录已变化，请重新打开病例。");
    } finally { if (active.current && attempt === epoch.current) setBusy(false); }
  };
  useEffect(() => {
    active.current = true; refresh.current();
    const focus = () => refresh.current();
    const storage = event => { if (event.key === "token" || event.key === null) refresh.current(); };
    window.addEventListener("focus", focus); window.addEventListener("storage", storage);
    return () => { active.current = false; epoch.current++; controller.current?.abort(); window.removeEventListener("focus", focus); window.removeEventListener("storage", storage); };
  }, [caseId, requestToken]);
  useEffect(() => {
    // Invalidate even if the editor saves successfully but its subsequent list GET
    // fails before onChanged. Only observe the existing operation; never submit it.
    const affects = config => {
      const method = config?.method?.toLowerCase(), url = config?.url;
      return (method === "post" && (["attachments", "manual-lab", "manual-imaging", "followup-plan"].some(kind => url === `/api/cases/${caseId}/${kind}/confirm`) ||
        ["edit-confirm", "confirm-edit", "analyze"].some(kind => url === `/api/cases/${caseId}/${kind}`))) ||
        (["put", "patch", "delete"].includes(method) && url === `/api/cases/${caseId}`);
    };
    const request = api.interceptors.request.use(config => {
      if (current() && affects(config)) {
        epoch.current++; controller.current?.abort(); setSaved(null); setBusy(false);
        setMessage("资料操作已开始，正在等待重新读取。");
      }
      return config;
    });
    const success = response => { if (current() && affects(response.config)) refresh.current(); return response; };
    const failure = error => { if (current() && affects(error.config)) refresh.current(); return Promise.reject(error); };
    const response = api.interceptors.response.use(success, failure);
    return () => { api.interceptors.request.eject(request); api.interceptors.response.eject(response); };
  }, [caseId, requestToken]);
  const previousRevision = useRef(sourceRevision);
  useEffect(() => {
    if (previousRevision.current !== sourceRevision) { previousRevision.current = sourceRevision; refresh.current(); }
  }, [sourceRevision]);
  const data = current() && saved?.revision === sourceRevision ? saved.result : null;
  function destination(target, key, plan) {
    if (!data?.navigation_targets.includes(target)) return null;
    if (target === "edit") return <Link key={key} to={`/cases/${caseId}/edit`} target="_blank" rel="noopener noreferrer" onClick={event => { if (!current()) event.preventDefault(); }}>{overviewDestinations[target]}</Link>;
    return <button key={key} type="button" onClick={event => { if (current() && data) onNavigate?.(target, event, plan && { id: plan.id, version: plan.version }); }}>{plan ? `回看计划 #${plan.id} 版本 ${plan.version}` : overviewDestinations[target]}</button>;
  }
  return <section aria-label="就诊资料总览" style={box}>
    <h2>就诊资料总览</h2>
    <p>只显示服务器已保存资料，本地未保存草稿未纳入。这里的“已有记录”不代表已确认诊断。</p>
    <p>未记录检查不代表必须检查；本页不评定病例完整度，也不代替医生核对。</p>
    <button type="button" onClick={() => refresh.current()}>刷新就诊资料总览</button>
    <p role="status" aria-live="polite">{busy ? "正在读取总览…" : message}</p>
    {data && <>
      <p>病例 #{data.case_id} · {data.identity.patient_name || "动物名未填写"} · {data.identity.species || "物种未填写"}</p>
      <p>宠主 {data.identity.owner_name || "未填写"} · 联系方式 {data.identity.owner_phone || "未填写"} · 性别 {data.identity.sex || "未填写"} · 品种 {data.identity.breed || "未填写"} · 毛色 {data.identity.coat_color || "未填写"} · 年龄 {data.identity.age_info || "未填写"} · 体重 {data.identity.weight || "未填写"}</p>
      <p>读取时间：<time dateTime={data.read_at}>{data.read_at}</time>。这是读取时的快照，后续变更请刷新。</p>
      <h3>基础病历</h3>
      <table style={{ width: "100%" }}><thead><tr><th>内容</th><th>记录状态</th><th>已保存原文</th></tr></thead><tbody>
        {data.fields.map(field => <tr key={field.key}><th>{field.label}</th><td>{overviewStates[field.state]}</td><td>{field.state === "recorded" ? <details><summary>查看{field.label}原文</summary><div style={{ whiteSpace: "pre-wrap" }}>{field.value}</div></details> : overviewStates[field.state]}</td></tr>)}
      </tbody></table>
      <p>{destination("edit")}。在新标签页编辑，保留当前各面板的未保存草稿。</p>
      <h3>资料提示</h3>
      {data.notices.length ? <ul>{data.notices.map((notice, i) => <li key={i}>{notice.label} · {destination(notice.target)}</li>)}</ul> : <p>当前未发现本页可识别的资料缺项；仍需医生核对。</p>}
      {Object.entries(groups).map(([key, label]) => {
        const group = data.groups[key];
        return <section key={key} aria-label={`${label}资料状态`} style={box}>
          <h3>{label}</h3>{destination(key)}
          {group.status === "disabled" ? <p>模块未启用，无法判断记录有无。</p> : <>
            <p>{Object.entries(group.counts).map(([state, count]) => `${overviewStates[state]} ${count}`).join(" · ")}</p>
            {key !== "attachments" && <p>当前数量按报告根去重；旧版本单独列出。</p>}
            {group.legacy_count > 0 && <p>另有 {group.legacy_count} 条旧式资料，请回原入口核对；未将它们认作已核对原件或报告。</p>}
            {!group.records.length && <p>暂无本流程已保存的{label}记录。</p>}
            {group.records.map(row => <article key={row.id} style={box}>
              <strong>{row.title || row.metadata?.title || row.name}</strong> · {overviewStates[row.state]}{row.version ? ` · 版本 ${row.version}` : ""}
              {key === "attachments" ? <p>文件 {row.name}</p> : <>
                <p>原件 {row.source.name} · 来源状态 {overviewStates[row.source_state]} · 核对账号 {row.reviewed_by} · 核对时间 {row.reviewed_at}</p>
                {row.reason && <p>更正或撤销原因：{row.reason}</p>}
              </>}
              <details><summary>查看来源指纹</summary><code>{row.sha256 || row.source.sha256}</code></details>
              {destination(key)}
            </article>)}
          </>}
        </section>;
      })}
      {!data.groups.followup ? <p>本次总览未提供复查计划信息，请从复查计划入口核对。</p> :
        <section aria-label="复查计划资料状态" style={box}>
          <h3>复查计划</h3>
          <p>仅显示本流程已保存的人工计划；计划不代表已复查、预约或联系宠主。</p>
          {data.groups.followup.status === "disabled" ? <p>复查计划模块未启用，无法判断记录有无。</p> : <>
            <p>{Object.entries(data.groups.followup.counts).map(([state, count]) => `${planStates[state]} ${count}`).join(" · ")}</p>
            {!data.groups.followup.records.length && <p>暂无本流程复查计划记录；不代表无需复查。</p>}
            {data.groups.followup.records.map(row => <article key={row.id} style={box} aria-label={`复查计划记录 ${row.id} 版本 ${row.version}`}>
              <h4>计划 #{row.id} · 版本 {row.version} · {planStates[row.state]}</h4>
              <p>计划复查日期（上海）：{row.data.planned_date} · 复查项目 {row.data.items.length} 项</p>
              <details><summary>查看复查计划原文</summary><dl style={{whiteSpace: "pre-wrap"}}>
                <dt>复查目的</dt><dd>{row.data.purpose}</dd>
                <dt>复查项目</dt><dd><ol>{row.data.items.map((item, i) => <li key={i}>{item}</li>)}</ol></dd>
                <dt>提前返回条件</dt><dd>{row.data.return_conditions || "未填写"}</dd>
                <dt>备注</dt><dd>{row.data.note || "未填写"}</dd>
              </dl></details>
              <p>根记录 #{row.root_id} · 核对账号 {row.reviewed_by} · 核对时间 {row.reviewed_at}</p>
              {row.reason && <p style={{whiteSpace: "pre-wrap"}}>更正原因：{row.reason}</p>}
              {row.withdrawal && <p style={{whiteSpace: "pre-wrap"}}>撤销原因：{row.withdrawal.reason} · 账号 {row.withdrawal.by} · 时间 {row.withdrawal.at}</p>}
              <details><summary>查看计划内容标识</summary><code>{row.token}</code></details>
              {destination("followup", undefined, row)}
            </article>)}
          </>}
          {destination("followup")}
        </section>}
      <h3>返回文书核对</h3><p>报告默认不选择；请在原流程中核对完整草稿后再下载。</p>
      {destination("outpatient")}{destination("owner_summary")}
    </>}
  </section>;
}
