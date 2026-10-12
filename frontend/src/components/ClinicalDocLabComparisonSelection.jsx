import React from 'react';
import CaseLabComparison from './CaseLabComparison';
import { documentSelection } from '../labComparisonDocuments';
import { deltaStates } from '../labComparison';

export default function ClinicalDocLabComparisonSelection({ mode, payload, onSelect, ...props }) {
  if (mode !== 'preview') return <section aria-label="选择文书检验前后对照">
    <p>本次门诊病历最多纳入一对项目。选择、可比条件核实和全篇文书核对分别进行。</p>
    <CaseLabComparison {...props} onSelect={(saved, request, preview) => onSelect(documentSelection(saved, request, preview))}/>
  </section>;
  return <section aria-label="文书检验前后对照附节" style={{ overflowWrap: 'anywhere', whiteSpace: 'pre-wrap' }}>
    <h3>检验前后对照附节 · 医生本次明确选择</h3>
    <p>草稿 · 待医生核对 · 尚未签署。方法与采样条件确认仅用于本次文书，不代表医生验收。</p>
    {['a', 'b'].map(key => { const row = payload[key]; return <article key={key} aria-label={`文书对照 ${key.toUpperCase()}`}>
      <h4>{key.toUpperCase()} · {row.title}</h4>
      <p>病例 #{payload.case_id} · 记录 ID {row.id} · 报告根 ID {row.root_id} · 版本 {row.version} · 项目序号 {row.item.index}</p>
      <dl>{[['panel','检验组合'],['specimen','样本类型'],['laboratory','实验室'],['device','设备'],['collected_at','采样时间'],['reported_at','报告时间'],['note','报告备注原文']].map(([k,l]) => <React.Fragment key={k}><dt>{l}</dt><dd>{row.report[k] || '未填写'}</dd></React.Fragment>)}
        { [['name','项目名称'],['result_type','结果类型'],['value','结果原文'],['unit','单位'],['reference','参考范围原文'],['reference_low','参考下限'],['reference_high','参考上限'],['reference_unit','参考单位'],['flag','原始标记'],['position','原文位置']].map(([k,l]) => <React.Fragment key={k}><dt>{l}</dt><dd>{row.item[k] || '未填写'}</dd></React.Fragment>)}</dl>
      <p>核对账号：{row.reviewed_by} · 核对时间：{row.reviewed_at}</p>
      <p>来源文件：{row.source.name} · SHA-256：{row.source.sha256}</p><p>保存版本标识：{row.token}</p>
    </article>; })}
    <p>差值 B−A：<strong>{payload.result.delta.value}</strong> {payload.result.delta.unit} · {deltaStates[payload.result.delta.state]}</p>
    {payload.result.reference_changed && <p>参考范围不同，请分别回看；两侧参考范围不会互相套用。</p>}
    <p>数值变化不等于病情变化；不自动诊断，不进行单位换算。</p><p>规则版本：{payload.rules} · 附节版本：{payload.schema}</p>
  </section>;
}
