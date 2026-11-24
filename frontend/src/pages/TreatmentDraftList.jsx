import React from 'react';

const labelOf = item => typeof item === 'string' ? item : item.label;
const newItem = (text, diagnosis) => diagnosis ? { label: text, code_system: null, code: null } : text;

export function draftListItems(items, edit, diagnosis, keepPlaceholders = false) {
  if (edit === undefined) return items;
  if (typeof edit === 'string') {
    return edit.split('\n').filter(text => keepPlaceholders || text.length > 0).map(text => newItem(text, diagnosis));
  }
  return edit.flatMap(({ text, source }) => {
    // An existing value, including a previously stored blank goal, round-trips exactly.
    if (source !== undefined && text === labelOf(source)) return [source];
    return keepPlaceholders || text.length > 0 ? [newItem(text, diagnosis)] : [];
  });
}

export default function TreatmentDraftList({ items, edit, onChange, diagnosis = false }) {
  const name = diagnosis ? '诊断' : '治疗目标';
  const label = diagnosis ? '治疗诊断' : '治疗目标';
  // Joining these records would erase coded row identity or a stored item boundary.
  const needsRows = items.some(item => {
    const text = labelOf(item);
    return text.length === 0 || /[\r\n]/.test(text) || (diagnosis && (item.code_system != null || item.code != null));
  });
  if (!needsRows) {
    const value = edit ?? items.map(labelOf).join('\n');
    return <p><label>{name}（每行一项）<textarea aria-label={label} value={value}
      onChange={event => onChange(event.target.value)} /></label></p>;
  }

  const rows = edit ?? items.map((source, key) => ({ key, source, text: labelOf(source) }));
  function move(index, offset) {
    const next = rows.slice();
    [next[index], next[index + offset]] = [next[index + offset], next[index]];
    onChange(next);
  }
  return <div role="group" aria-label={name + '列表'}>
    <p>{name}（每格一项，可在格内换行）</p>
    {rows.map((row, index) => <div key={row.key}>
      <label>{name} {index + 1}<textarea aria-label={index === 0 ? label : label + ' ' + (index + 1)} value={row.text}
        onChange={event => onChange(rows.map(item => item.key === row.key ? { ...item, text: event.target.value } : item))} /></label>
      {diagnosis && (row.source?.code_system || row.source?.code) && <small>
        {row.text === row.source.label
          ? '诊断编码：' + [row.source.code_system, row.source.code].filter(Boolean).join(' · ')
          : '诊断名称已改动，保存时清除原编码。'}
      </small>}
      <button type="button" aria-label={`上移${name} ${index + 1}`} disabled={index === 0} onClick={() => move(index, -1)}>上移</button>
      <button type="button" aria-label={`下移${name} ${index + 1}`} disabled={index + 1 === rows.length} onClick={() => move(index, 1)}>下移</button>
      <button type="button" aria-label={`移除${name} ${index + 1}`} onClick={() => onChange(rows.filter(item => item.key !== row.key))}>移除</button>
    </div>)}
    <button type="button" onClick={() => onChange([...rows, { key: Math.max(-1, ...rows.map(row => row.key)) + 1, text: '' }])}>添加{name}</button>
  </div>;
}
