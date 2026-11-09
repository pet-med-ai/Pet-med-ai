import React, { useEffect, useRef, useState } from 'react';
import './TreatmentWorkspace.css';

const base = (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '');
const empty = () => ({ schema: 'treatment-content-v1', diagnoses: [], assessment: '', treatment: { goals: [], management_text: '', monitoring_text: '', followup_text: '' }, linked_orders: [], provenance: { ai_generation_ids: [], voice_transcript_revision_ids: [] } });
export function canonical(value) {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (value !== null && typeof value === 'object') return '{' + Object.keys(value).sort().map(k => JSON.stringify(k) + ':' + canonical(value[k])).join(',') + '}';
  return JSON.stringify(value);
}
export async function requestHash(value) {
  const data = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(canonical(value)));
  return Array.from(new Uint8Array(data), x => x.toString(16).padStart(2, '0')).join('');
}
const newKey = () => Array.from(crypto.getRandomValues(new Uint8Array(32)), x => x.toString(16).padStart(2, '0')).join('');
const textStyle = { whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' };
function ContentView({ content }) {
  return <dl style={textStyle}>
    <dt>诊断</dt><dd>{content.diagnoses.map(x => x.label).join('\n')}</dd>
    <dt>评估</dt><dd>{content.assessment}</dd><dt>治疗目标</dt><dd>{content.treatment.goals.join('\n')}</dd>
    <dt>治疗措施</dt><dd>{content.treatment.management_text}</dd>
    <dt>监测</dt><dd>{content.treatment.monitoring_text}</dd><dt>复查</dt><dd>{content.treatment.followup_text}</dd>
  </dl>;
}
const errors = {
  SOURCE_CHANGED: '病例、诊断资料或签署规则已变化。请重新读取并冻结新版本。', DRAFT_CHANGED: '草稿已修改，请冻结新版本后重新审核。', VERSION_MISMATCH: '另一个操作已更新此记录，请重新读取后核对。',
  SECOND_CLINICIAN_REQUIRED: '本院要求由另一位已核验医生签署。', CLINICAL_PERMISSION_REQUIRED: '当前账号没有此项临床权限。',
  ASSURANCE_UNAVAILABLE: '本院要求证书签名；当前入口尚未接入证书服务。', CHALLENGE_INVALID: '再次认证已失效，请重新核对并认证。',
  COMMAND_CANCELLED: '原请求已取消，不会继续提交。', INCOMPLETE_TREATMENT: '请填写诊断和治疗措施后再冻结版本。',
  AMENDMENT_REQUIRED: '已签署内容需要先创建修订草稿。', SESSION_EXPIRED: '登录已失效。', REAUTHENTICATION_FAILED: '再次认证失败。',
};

export default function TreatmentWorkspace({ token, scope, caseId }) {
  const path = `/organizations/${scope.org_id}/clinics/${scope.clinic_id}/cases/${caseId}`;
  const [data, setData] = useState(null), [content, setContent] = useState(empty);
  const [dirty, setDirty] = useState(false), [busy, setBusy] = useState(false), [expired, setExpired] = useState(false);
  const [revokeChecked, setRevokeChecked] = useState(false);
  const [checked, setChecked] = useState(false), [password, setPassword] = useState(''), [reason, setReason] = useState('');
  const [message, setMessage] = useState(''), [pending, setPending] = useState(null), [verified, setVerified] = useState(null);
  const work = useRef({ epoch: 0, controller: null }), storage = useRef(null), pendingRef = useRef(null);
  function task() {
    work.current.controller?.abort(); const controller = new AbortController(); const epoch = ++work.current.epoch;
    work.current.controller = controller;
    return { signal: controller.signal, current: () => work.current.epoch === epoch };
  }
  function remember(value) {
    pendingRef.current = value; setPending(value);
    // Only partitioned keys and hashes, never clinical text, passwords or tokens.
    if (storage.current) {
      try { value ? sessionStorage.setItem(storage.current, JSON.stringify(value)) : sessionStorage.removeItem(storage.current); }
      catch { setMessage('浏览器未保留恢复标识，请保持当前标签页。'); }
    }
  }
  async function request(suffix, t, method = 'GET', body, headers = {}) {
    const response = await fetch(base + '/api/v2' + suffix, { method, signal: t.signal, cache: 'no-store', credentials: 'omit',
      headers: { Authorization: `Bearer ${token}`, ...(body === undefined ? {} : { 'Content-Type': 'application/json' }), ...headers },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
    const result = await response.json();
    if (!t.current()) throw Object.assign(new Error('stale'), { stale: true });
    // Receipts can have a terminal 4xx status; keep their state for reconciliation.
    if (!response.ok && !result.state) throw Object.assign(new Error(result.code || result.detail || '读取失败'), { status: response.status, code: result.code });
    return { status: response.status, body: result };
  }
  function failed(error, t) {
    if (!t.current() || error.stale || error.name === 'AbortError') return;
    setChecked(false); setRevokeChecked(false); setPassword(''); setVerified(null);
    if (error.status === 401) { setExpired(true); setData(null); setMessage('登录已失效。原文仅供复制保留；原预览、勾选和认证已失效。请退出后使用同一账号重新登录，再查询原请求。'); }
    else setMessage(errors[error.code] || (pendingRef.current ? '结果尚未确认，请查询原请求；不要重复提交。' : String(error.message)));
  }
  async function load(t, replaceDraft = true) {
    const g = (await request(path + '/treatment', t)).body;
    if (!t.current()) return;
    const partition = `pmai:treatment:${g.actor_id}:${scope.org_id}:${scope.clinic_id}:${caseId}`;
    storage.current = partition; setData(g); setExpired(false); setChecked(false); setRevokeChecked(false); setPassword('');
    if (replaceDraft) { setContent(g.draft?.content || empty()); setDirty(false); }
    if (!pendingRef.current) {
      try { const saved = JSON.parse(sessionStorage.getItem(partition) || 'null');
        if (saved && /^[0-9a-f]{64}$/.test(saved.key) && /^[0-9a-f]{64}$/.test(saved.request_hash) && ['draft.save','revision.freeze','review','sign','amend','revoke'].includes(saved.operation)) remember(saved);
      } catch { /* No clinical state is restored from storage. */ }
    }
  }
  async function refresh() {
    const t = task(); setBusy(true); setMessage('');
    try { await load(t, !dirty); } catch (e) { failed(e, t); } finally { if (t.current()) setBusy(false); }
  }
  useEffect(() => {
    storage.current = null; pendingRef.current = null; setPending(null); setData(null); setContent(empty()); setDirty(false); setVerified(null); setExpired(false); setChecked(false); setRevokeChecked(false); setPassword('');
    const t = task(); setBusy(true);
    load(t).catch(e => failed(e, t)).finally(() => { if (t.current()) setBusy(false); });
    return () => { work.current.epoch++; work.current.controller?.abort(); };
  }, [token, path]);
  function edit(next) { setContent(next); setDirty(true); setChecked(false); setRevokeChecked(false); setPassword(''); setVerified(null); }
  async function reconcile(out, t, replaceDraft = true) {
    if (!t.current()) return;
    if (out.state === 'pending' || out.state === 'not_observed') { setMessage('结果仍待核对。未观察到结果不表示未保存；可继续查询或取消原请求。'); return; }
    if (out.state !== 'committed') {
      remember(null); setMessage(errors[out.code] || out.code || '操作未完成，请重新读取后核对。'); await load(t, false); return;
    }
    if (out.signature_id) {
      // Success requires an independent authorized GET of the frozen signature.
      const frozen = (await request(path + '/treatment/signatures/' + out.signature_id, t)).body;
      setVerified(frozen);
    }
    await load(t, replaceDraft);
    remember(null); setMessage('已从服务端核对保存结果。');
  }
  async function submit(operation, target, suffix, body, method = 'POST', proof = null) {
    if (busy || expired || pendingRef.current || !data) return;
    const t = task(); setBusy(true); setMessage(''); setVerified(null);
    const precondition = operation === 'draft.save' ? (data.draft ? data.draft_etag : '*') : data.etag;
    try {
      if (proof) {
        const challenge = await request('/auth/reauthenticate', t, 'POST', { org_id: scope.org_id, clinic_id: scope.clinic_id, case_id: caseId,
          revision_id: proof.revision_id, content_hash: proof.hash, action: operation, target_signature_id: proof.signature_id || null, password });
        if (!t.current()) return;
        body = { ...body, challenge_id: challenge.body.challenge_id }; setPassword('');
      }
      const key = newKey();
      const request_hash = await requestHash({ actor_id: data.actor_id, scope: { org_id: scope.org_id, clinic_id: scope.clinic_id, case_id: caseId }, operation, target, precondition, body });
      if (!t.current()) return;
      remember({ key, operation, request_hash });
      setChecked(false); setRevokeChecked(false); setPassword('');
      const headers = { 'Idempotency-Key': key, [precondition === '*' ? 'If-None-Match' : 'If-Match']: precondition };
      const out = await request(path + '/treatment' + suffix, t, method, body, headers);
      if (!out.body.state) { remember(null); throw new Error('服务返回了无法核对的结果。'); }
      await reconcile(out.body, t);
    } catch (e) { failed(e, t); }
    finally { if (t.current()) { setBusy(false); setPassword(''); } }
  }
  async function recover(cancel = false) {
    if (busy || expired || !pending) return;
    const t = task(); setBusy(true);
    try {
      const suffix = path + '/commands/' + pending.key + (cancel ? '/cancel' : '?operation=' + pending.operation);
      const out = await request(suffix, t, cancel ? 'POST' : 'GET', cancel ? { operation: pending.operation, request_hash: pending.request_hash, reason: reason || '用户取消原请求' } : undefined);
      await reconcile(out.body, t, !dirty);
    } catch (e) { failed(e, t); } finally { if (t.current()) setBusy(false); }
  }
  const rev = data?.revisions.find(r => r.id === data.plan?.head_revision_id);
  const staleDraft = rev && rev.draft_version !== data?.draft?.draft_version;
  const review = data?.reviews.find(r => r.revision_id === rev?.id);
  const active = data?.signatures.find(s => s.id === data.plan?.active_signature_id);
  const activeRevision = data?.revisions.find(r => r.id === active?.revision_id);
  const locked = busy || expired || !!pending;
  const canEdit = data?.allowed_actions.edit && !locked;
  return <section className="treatment-workspace" aria-label="治疗签署" style={{ marginTop: 32, padding: 20, border: '1px solid #a7bac9', borderRadius: 12 }}>
    <h2>治疗记录与院内账号确认</h2>
    <p>{scope.org_name}／{scope.clinic_name} · 病例 #{caseId}</p>
    <p>医生审核后以院内账号确认签署。此入口不执行处方、不调用证书签名服务。</p>
    {message && <p role="status">{message}</p>}{busy && <p role="status">正在核对……</p>}
    {pending && <aside><p>待核对请求：{pending.key}</p>{busy && <button onClick={() => { task(); setBusy(false); setPassword(''); setChecked(false); setRevokeChecked(false); setMessage('已停止等待，原请求仍需查询或取消。'); }}>停止等待（保留原请求）</button>}<button disabled={busy || expired} onClick={() => recover()}>查询原请求</button>{' '}
      <button disabled={busy || expired} onClick={() => recover(true)}>取消原请求</button></aside>}
    {expired ? <section><h3>未保存原文 · 只读保留</h3><ContentView content={content} /></section> : <>
      <button disabled={busy} onClick={refresh}>重新读取治疗记录</button>
      {data && <>
        <p>审核账号：{data.profile?.display_name || '当前账号无已核验医生档案'} · {data.policy.review_policy === 'two_person' ? '另一位医生签署' : '允许同一医生审核签署'}</p>
        {data.policy.required_assurance === 'certificate_signature' && <p role="alert">本院要求证书签名，当前不能签署。</p>}
        {active && <section aria-label="当前有效签署"><h3>当前有效签署 · 版本 {activeRevision?.revision_no}</h3><p>{active.clinician_snapshot.display_name} · {active.signed_at} · 已确认签署 · 院内账号确认</p>{activeRevision && <ContentView content={activeRevision.content} />}</section>}
        <fieldset disabled={!canEdit || (!!active && data.draft?.amendment_of !== active.id)}><legend>治疗草稿</legend>
          <p><label>诊断（每行一项）<textarea aria-label="治疗诊断" value={content.diagnoses.map(x => x.label).join('\n')} onChange={e => edit({ ...content, diagnoses: e.target.value.split('\n').filter(Boolean).map(label => ({ label, code_system: null, code: null })) })} /></label></p>
          <p><label>评估原文<textarea aria-label="治疗评估" value={content.assessment} onChange={e => edit({ ...content, assessment: e.target.value })} /></label></p>
          <p><label>治疗目标（每行一项）<textarea aria-label="治疗目标" value={content.treatment.goals.join('\n')} onChange={e => edit({ ...content, treatment: { ...content.treatment, goals: e.target.value.split('\n').filter(Boolean) } })} /></label></p>
          {[["management_text",'治疗措施'],['monitoring_text','监测安排'],['followup_text','复查安排']].map(([key,label]) => <p key={key}><label>{label}<textarea aria-label={label} value={content.treatment[key]} onChange={e => edit({ ...content, treatment: { ...content.treatment, [key]: e.target.value } })} /></label></p>)}
          <button onClick={() => submit('draft.save','draft','/draft',{ content },'PATCH')}>保存治疗草稿</button>
        </fieldset>
        <button disabled={!canEdit || dirty || !data.draft || (!!active && data.draft.amendment_of !== active.id)} onClick={() => submit('revision.freeze','revisions','/revisions',{ draft_version: data.draft.draft_version, expected_source_epoch: data.source_epoch })}>冻结版本供核对</button>
        {dirty && <p>有尚未保存的修改。保存后才能冻结和签署。</p>}
        {rev && <section aria-label="冻结版本"><h3>冻结版本 {rev.revision_no} · {rev.origin === 'legacy_import' ? '历史原文，未经签署' : '待核对治疗内容'}</h3>
          <ContentView content={rev.content} />
          <p>来源病例：{rev.source_manifest.case?.patient_name || "历史病例"} · 资料版本 {rev.source_manifest.case?.clinical_epoch || "历史快照"} · 诊断报告 {rev.source_manifest.diagnostic_reports?.length || 0} 份</p>
          <details><summary>查看冻结来源资料</summary><pre style={textStyle}>{JSON.stringify(rev.source_manifest, null, 2)}</pre></details>
          {staleDraft && <p>草稿已修改，此冻结版本不能继续审核或签署。</p>}
          <p style={textStyle}>内容校验值：{rev.content_sha256}</p>
          {review && <p>审核：{review.clinician_snapshot.display_name} · {({ approve: '审核通过', request_revision: '要求修订', reject: '审核拒绝' })[review.decision]} · {review.reason}</p>}
          <label><input aria-label="已核对冻结版本" type="checkbox" checked={checked} disabled={locked || dirty || staleDraft || rev.origin !== 'clinical'} onChange={e => setChecked(e.target.checked)} />我已核对病例、完整原文、来源资料及本次操作</label>
          <p><label>审核／修订／作废原因<input aria-label="操作原因" value={reason} disabled={locked} onChange={e => setReason(e.target.value)} /></label></p>
          {!review && ['approve','request_revision','reject'].map((decision,i) => <button key={decision} disabled={locked || dirty || staleDraft || !checked || !reason.trim() || !data.allowed_actions.review} onClick={() => submit('review',rev.id,`/revisions/${rev.id}/reviews`,{ decision, reason })}>{['审核通过','要求修订','审核拒绝'][i]}</button>)}
          <p><label>再次输入当前账号密码<input aria-label="签署认证密码" type="password" autoComplete="off" value={password} disabled={locked} onChange={e => setPassword(e.target.value)} /></label></p>
          <button disabled={locked || dirty || staleDraft || !checked || !password || !data.allowed_actions.sign || review?.decision !== 'approve' || data.signatures.some(s => s.revision_id === rev.id)} onClick={() => submit('sign',rev.id,`/revisions/${rev.id}/signatures`,{ review_id: review.id, content_hash: rev.content_sha256 },'POST',{ revision_id: rev.id, hash: rev.content_sha256 })}>再次认证并确认签署</button>
        </section>}
        {active && <section><p><label><input type="checkbox" aria-label="已核对待作废签署" checked={revokeChecked} disabled={locked} onChange={e => setRevokeChecked(e.target.checked)} />我已核对当前有效签署（版本 {activeRevision?.revision_no}）及作废原因</label></p><p><button disabled={!canEdit || !reason.trim() || data.draft?.amendment_of === active.id} onClick={() => submit('amend','amendments','/amendments',{ base_signature_id: active.id, reason })}>创建修订草稿</button>{' '}
          <button disabled={locked || !revokeChecked || !password || !reason.trim() || !data.allowed_actions.sign} onClick={() => submit('revoke',active.id,`/signatures/${active.id}/revocations`,{ reason },'POST',{ revision_id: active.revision_id, hash: active.content_hash, signature_id: active.id })}>再次认证并作废签署</button></p></section>}
        <h3>签署历史</h3>{data.signatures.map(s => <p key={s.id}>版本 {data.revisions.find(r => r.id === s.revision_id)?.revision_no} · {s.clinician_snapshot.display_name} · {s.signed_at} · {({ revoked:'已作废',superseded:'已由新签署替代' })[data.events.find(e => e.signature_id === s.id)?.event] || '有效'} · 院内账号确认</p>)}
      </>}
    </>}
    {verified && <aside aria-label="独立回读签署"><p>已独立回读签署：{verified.signature.id} · {verified.state} · 院内账号确认</p><ContentView content={verified.revision.content} /></aside>}
  </section>;
}
