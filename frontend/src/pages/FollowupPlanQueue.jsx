import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { initialFilter, shanghaiDate, dateBounds, query, validQueue, readQueue, planLocation, message } from '../followupPlanQueue';
import * as contacts from '../followupContactQueue';
import FollowupContactQueueSummary from '../components/FollowupContactQueueSummary';

export default function FollowupPlanQueue() {
  const [token, setToken] = useState(() => localStorage.getItem('token') || '');
  const [revision, setRevision] = useState(0), [active, setActive] = useState(true);
  useEffect(() => {
    let day = shanghaiDate();
    const refresh = () => { day = shanghaiDate(); setToken(localStorage.getItem('token') || ''); setActive(true); setRevision(n => n + 1); };
    const blur = () => setActive(false);
    const visibility = () => { if (globalThis.document?.visibilityState === 'hidden') blur(); else refresh(); };
    const storage = e => { if (e.key === 'token' || e.key === null) refresh(); };
    window.addEventListener('focus', refresh); window.addEventListener('blur', blur); window.addEventListener('storage', storage);
    globalThis.document?.addEventListener?.('visibilitychange', visibility);
    const timer = setInterval(() => { if (day !== shanghaiDate() || token !== (localStorage.getItem('token') || '')) refresh(); }, 1000);
    timer.unref?.();
    return () => { clearInterval(timer); window.removeEventListener('focus', refresh); window.removeEventListener('blur', blur); window.removeEventListener('storage', storage); globalThis.document?.removeEventListener?.('visibilitychange', visibility); };
  }, [token]);
  return <main style={{ maxWidth: 960, margin: '0 auto', padding: 20, overflowWrap: 'anywhere', fontFamily: 'system-ui, sans-serif' }}>
    <Link to='/'>返回首页</Link><h1>复查计划工作清单</h1>
    <p>仅列出当前账号病例的当前计划。日期按上海日历；计划日期已过不代表未复查、病情风险或已联系宠主。</p>
    {!token ? <p>请先登录后查看复查计划清单。</p> : <Queue key={token} token={token} revision={revision} active={active} />}
  </main>;
}

function Queue({ token, revision, active }) {
  const [includeContacts, setIncludeContacts] = useState(false), [contactState, setContactState] = useState('all');
  const [filter, setFilter] = useState(initialFilter), [custom, setCustom] = useState({ start: '', end: '' });
  const [cursor, setCursor] = useState({ page: 1, snapshot: null });
  const [size, setSize] = useState(20), [attempt, setAttempt] = useState(0);
  const [list, setList] = useState(null), [error, setError] = useState(''), [notice, setNotice] = useState(''), [busy, setBusy] = useState(false);
  const epoch = useRef(0), previousRevision = useRef(revision);
  const valid = Boolean(dateBounds(filter, shanghaiDate()));
  useEffect(() => {
    const current = ++epoch.current, abort = new AbortController(), day = shanghaiDate();
    setList(null); setError(''); setBusy(false);
    if (previousRevision.current !== revision) { previousRevision.current = revision; setCursor({ page: 1, snapshot: null }); return () => abort.abort(); }
    if (!active || !valid) return () => abort.abort();
    setBusy(true);
    const currentRequest = () => epoch.current === current && !abort.signal.aborted && localStorage.getItem('token') === token;
    const read = includeContacts ? contacts.readQueue : readQueue;
    const params = includeContacts ? contacts.query(filter, contactState, cursor.page, size, cursor.snapshot) : query(filter, cursor.page, size, cursor.snapshot);
    read(token, params, abort.signal).then(value => {
      if (!currentRequest()) return;
      if (day !== shanghaiDate()) { setCursor({ page: 1, snapshot: null }); return; }
      const validResponse = includeContacts ? contacts.validQueue(value, filter, contactState, cursor.page, size, cursor.snapshot) : validQueue(value, filter, cursor.page, size, cursor.snapshot);
      if (!validResponse || value.as_of_date !== day) throw Error('Invalid queue response');
      setList(value);
    }).catch(err => {
      if (!currentRequest()) return;
      if (err?.response?.data?.detail === 'followup_queue_snapshot_changed') { setNotice(message(err)); setCursor({ page: 1, snapshot: null }); }
      else setError(includeContacts ? contacts.message(err) : message(err));
    }).finally(() => { if (currentRequest()) setBusy(false); });
    return () => { abort.abort(); ++epoch.current; };
  }, [token, revision, active, filter, cursor, size, attempt, valid, includeContacts, contactState]);
  const apply = next => { setNotice(''); setFilter(next); setCursor({ page: 1, snapshot: null }); };
  const visibleList = active && list && list.as_of_date === shanghaiDate() && (includeContacts ? contacts.validQueue(list, filter, contactState, cursor.page, size, cursor.snapshot) : validQueue(list, filter, cursor.page, size, cursor.snapshot));
  const refresh = () => { setNotice(''); setCursor({ page: 1, snapshot: null }); setAttempt(n => n + 1); };
  return <>
    <label><input type='checkbox' aria-label='显示人工随访记录' checked={includeContacts} onChange={e => { setIncludeContacts(e.target.checked); setContactState('all'); setNotice(''); setCursor({ page: 1, snapshot: null }); }}/>显示人工随访记录</label>
    {includeContacts && <label style={{ display: 'block' }}>登记情况 <select aria-label='随访登记情况' value={contactState} onChange={e => { setContactState(e.target.value); setNotice(''); setCursor({ page: 1, snapshot: null }); }}>
      {Object.entries(contacts.contactStates).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
    </select></label>}
    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'end' }}>
      <label>日期范围 <select aria-label='计划日期范围' value={filter.range} onChange={e => apply({ ...filter, ...custom, range: e.target.value })}>
        <option value='today'>今天</option><option value='next7'>未来 7 天（含今天）</option><option value='past'>早于今天</option><option value='custom'>自定义日期</option><option value='all'>全部日期</option>
      </select></label>
      <label>状态 <select aria-label='计划有效状态' value={filter.state} onChange={e => apply({ ...filter, state: e.target.value })}>
        <option value='all'>全部状态</option><option value='planned'>已核对</option><option value='needs_review'>需重新核对</option>
      </select></label>
      <label>每页 <select aria-label='每页条数' value={size} onChange={e => { setSize(Number(e.target.value)); setCursor({ page: 1, snapshot: null }); }}>
        {[20, 50].map(n => <option key={n} value={n}>{n} 条</option>)}
      </select></label>
      <button type='button' onClick={refresh}>刷新清单</button>
    </div>
    {filter.range === 'custom' && <fieldset><legend>自定义日期（含起止日）</legend>
      <label>开始 <input aria-label='计划开始日期' type='date' value={custom.start} onChange={e => { const next = { ...custom, start: e.target.value }; setCustom(next); apply({ ...filter, ...next }); }} /></label>
      <label>结束 <input aria-label='计划结束日期' type='date' value={custom.end} onChange={e => { const next = { ...custom, end: e.target.value }; setCustom(next); apply({ ...filter, ...next }); }} /></label>
    </fieldset>}
    {!valid && <p role='alert'>请选择有效的起止日期，开始日期不能晚于结束日期。</p>}
    {notice && <p role='status'>{notice}</p>}
    {!active && <p role='status'>清单已失效，返回窗口后重新读取。</p>}
    {busy && <p role='status'>正在读取复查计划清单…</p>}
    {error && <p role='alert'>{error} <button type='button' onClick={refresh}>重试读取清单</button></p>}
    {visibleList && <>
      <p>上海日期 {list.as_of_date} · 共 {list.total} 个病例计划 · 第 {list.page} 页</p>
      {list.total === 0 && <p>当前筛选下没有计划记录；空清单不等于无需复查。</p>}
      <ol style={{ paddingLeft: 24 }} start={(list.page - 1) * size + 1}>
        {list.items.map(item => <li key={item.case.id} style={{ margin: '16px 0', padding: 14, border: '1px solid #cad5d2', borderRadius: 8 }}>
          <strong>{item.case.patient_name || '未填写患者名'} · {item.case.species || '未填写物种'} · 病例 #{item.case.id}</strong>
          <p>宠主：{item.case.owner_name || '未填写'} · 计划日期：{item.plan.data.planned_date} · 版本 {item.plan.version}</p>
          <p>{item.plan.state === 'needs_review' ? '病例资料已变化 · 需重新核对' : '已核对保存 · 计划待执行'}</p>
          <p style={{ whiteSpace: 'pre-wrap' }}>复查目的：{item.plan.data.purpose}</p>
          <details><summary>展开完整计划原文</summary>
            <ul>{item.plan.data.items.map((value, i) => <li key={i} style={{ whiteSpace: 'pre-wrap' }}>{value}</li>)}</ul>
            <p style={{ whiteSpace: 'pre-wrap' }}>提前返回条件：{item.plan.data.return_conditions || '未填写'}</p>
            <p style={{ whiteSpace: 'pre-wrap' }}>备注：{item.plan.data.note || '未填写'}</p>
            <p style={{ whiteSpace: 'pre-wrap' }}>更正原因：{item.plan.reason || '首次保存'}</p>
            <p>保存账号 {item.plan.reviewed_by} · {item.plan.reviewed_at} · 计划 #{item.plan.id} / 根 #{item.plan.root_id}</p>
          </details>
          <Link to={planLocation(item)}>打开病例 #{item.case.id} 的计划 #{item.plan.id} 版本 {item.plan.version}</Link>
          {includeContacts && <FollowupContactQueueSummary item={item}/>}
        </li>)}
      </ol>
      <nav aria-label='清单分页' style={{ display: 'flex', gap: 12 }}>
        <button type='button' disabled={list.page <= 1} onClick={() => setCursor({ page: list.page - 1, snapshot: list.snapshot })}>上一页</button>
        <button type='button' disabled={list.page * size >= list.total} onClick={() => setCursor({ page: list.page + 1, snapshot: list.snapshot })}>下一页</button>
      </nav>
    </>}
  </>;
}
