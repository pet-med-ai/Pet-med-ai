import React from 'react';
import { Link } from 'react-router-dom';
import { methods, outcomes, sourceStates } from '../followupContacts';
import { contactLocation, sourceLocation } from '../followupContactQueue';

const text = { whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' };
function Identity({ label, value }) {
  return <p>{label}：{value.patient_name || '未填写患者名'} · {value.species || '未填写物种'} · {value.sex || '未填写性别'} · {value.age_info || '未填写年龄'} · {value.breed || '未填写品种'} · 宠主 {value.owner_name || '未填写'}</p>;
}
export default function FollowupContactQueueSummary({ item }) {
  const { counts, latest } = item.contacts;
  return <section aria-label='人工随访登记摘要'>
    <p>本版计划有效登记：{counts.current} 条 · 历史计划有效登记：{counts.historical} 条</p>
    {counts.current + counts.historical === 0 && <p>暂无有效登记；不表示从未联系，旧版本和撤销记录可在病例中回看。</p>}
    {['current', 'historical'].map(key => {
      const r = latest[key]; if (!r) return null;
      const s = r.source, label = key === 'current' ? '本版计划最近联系' : '历史计划最近联系';
      return <article key={key} aria-label={label}>
        <p>{label}：{r.data.occurred_at}（上海） · {methods[r.data.method]} · {outcomes[r.data.outcome]}</p>
        <details><summary>展开{label}原文</summary>
          <Identity label='当前病例身份' value={item.case}/><Identity label='联系登记时身份' value={r.case}/>
          <p style={text}>联系原文：{r.data.note}</p><p style={text}>后续安排：{r.data.next_action || '未填写'}</p>
          <p style={text}>更正原因：{r.reason || '首次登记'}</p>
          <p>登记账号 {r.recorded_by} · {r.recorded_at} · 联系 #{r.id} / 根 #{r.root_id} / 版本 {r.version}</p>
          <p>历史来源计划 #{s.id} / 根 #{s.root_id} / 版本 {s.version} · {sourceStates[s.state]}</p>
          <Identity label='来源保存时身份' value={s.case}/>
          <p>来源计划日期：{s.data.planned_date}</p><p style={text}>来源复查目的：{s.data.purpose}</p>
          <ul>{s.data.items.map((value, i) => <li key={i} style={text}>{value}</li>)}</ul>
          <p style={text}>来源提前返回条件：{s.data.return_conditions || '未填写'}</p><p style={text}>来源备注：{s.data.note || '未填写'}</p>
          <p>来源核对账号 {s.reviewed_by} · {s.reviewed_at}</p>
        </details>
        <p><Link to={contactLocation(item.case.id, r)}>回看随访 #{r.id} 版本 {r.version}</Link></p>
        <p><Link to={sourceLocation(item.case.id, r)}>回看来源计划 #{s.id} 版本 {s.version}</Link></p>
      </article>;
    })}
    <p>联系仅表示已登记事实，不表示已复诊、检查完成或病情改善；历史来源不替代当前计划。</p>
  </section>;
}
