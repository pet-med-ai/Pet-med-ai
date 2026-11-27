import React, { useEffect, useImperativeHandle, useRef, useState } from 'react';
import './TreatmentWorkspace.css';
import TreatmentDraftList, { draftListItems } from './TreatmentDraftList';
import { matchesTreatmentReceipt, matchesTreatmentSignature, requestHash } from './treatmentReceipts';
export { canonical, requestHash } from './treatmentReceipts';

const base = (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '');
const empty = () => ({ schema: 'treatment-content-v1', diagnoses: [], assessment: '', treatment: { goals: [], management_text: '', monitoring_text: '', followup_text: '' }, linked_orders: [], provenance: { ai_generation_ids: [], voice_transcript_revision_ids: [] } });
const newKey = () => Array.from(crypto.getRandomValues(new Uint8Array(32)), x => x.toString(16).padStart(2, '0')).join('');
const draftPrecondition = aggregate => aggregate.draft ? aggregate.draft_etag : '*';
const versionsDiffer = (frozen, current) => frozen != null && current != null && frozen !== current;
const signatureLabels = { effective: '有效', revoked: '已作废', superseded: '已由新签署替代', unknown: '状态待核对' };
function signatureState(aggregate, id) {
  const active = aggregate.plan?.active_signature_id === id;
  const event = aggregate.events.find(e => e.signature_id === id);
  if (active && !event) return 'effective';
  if (!active && (event?.event === 'revoked' || event?.event === 'superseded')) return event.event;
  return 'unknown';
}
function readbackStillCurrent(aggregate, readback) {
  const { id, revision_id } = readback.signature;
  return aggregate.signatures.some(s => s.id === id && s.revision_id === revision_id)
    && signatureState(aggregate, id) === readback.state;
}
const textStyle = { whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' };
function selectableListText(text) {
  // The final empty line needs a line box for native selection to include its newline.
  return text.endsWith('\n') ? <>{text}<br aria-hidden="true" /></> : text;
}
function ContentView({ content, localLists }) {
  return <dl style={textStyle}>
    <dt>诊断</dt><dd>{typeof localLists?.diagnoses === 'string' ? selectableListText(localLists.diagnoses)
      : <ol className="treatment-content-items" aria-label="诊断条目">
        {content.diagnoses.map(({ label, code_system, code }, index) => <li key={index}>
          <span>{selectableListText(label)}</span>
          {(typeof code_system === 'string' || typeof code === 'string') && <dl className="treatment-diagnosis-codes">
            {typeof code_system === 'string' && <><dt>编码体系</dt><dd>{selectableListText(code_system)}</dd></>}
            {typeof code === 'string' && <><dt>编码</dt><dd>{selectableListText(code)}</dd></>}
          </dl>}
        </li>)}
      </ol>}</dd>
    <dt>评估</dt><dd>{content.assessment}</dd>
    <dt>治疗目标</dt><dd>{typeof localLists?.goals === 'string' ? selectableListText(localLists.goals)
      : <ol className="treatment-content-items" aria-label="治疗目标条目">
        {content.treatment.goals.map((goal, index) => <li key={index}>
          {goal === '' ? <br aria-hidden="true" /> : selectableListText(goal)}
        </li>)}
      </ol>}</dd>
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

export default function TreatmentWorkspace({ token, scope, caseId, workspaceRef }) {
  const path = `/organizations/${scope.org_id}/clinics/${scope.clinic_id}/cases/${caseId}`;
  const [data, setData] = useState(null), [content, setContent] = useState(empty);
  const [recordCurrent, setRecordCurrent] = useState(false);
  const [listEdits, setListEdits] = useState({});
  const [editBase, setEditBase] = useState(null), [rejectedDraft, setRejectedDraft] = useState(false);
  const dirty = editBase !== null;
  const draftConflict = dirty && (rejectedDraft || (data && editBase !== draftPrecondition(data)));
  const [busy, setBusy] = useState(false), [expired, setExpired] = useState(false);
  const [revokeChecked, setRevokeChecked] = useState(false);
  const [checked, setChecked] = useState(false), [password, setPassword] = useState(''), [reason, setReason] = useState('');
  const [message, setMessage] = useState(''), [pending, setPending] = useState(null), [verified, setVerified] = useState(null);
  const work = useRef({ epoch: 0, controller: null }), storage = useRef(null), pendingRef = useRef(null);
  useImperativeHandle(workspaceRef, () => ({
    dirty,
    refreshWhenIdle() {
      if (busy || expired || pendingRef.current) return;
      setReason('');
      return refresh();
    },
  }));
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
  async function request(suffix, t, method = 'GET', body, headers = {}, receipt = false) {
    const response = await fetch(base + '/api/v2' + suffix, { method, signal: t.signal, cache: 'no-store', credentials: 'omit',
      headers: { Authorization: `Bearer ${token}`, ...(body === undefined ? {} : { 'Content-Type': 'application/json' }), ...headers },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
    if (method === 'GET' && suffix === path + '/treatment' && (response.status === 403 || response.status === 404)) {
      throw Object.assign(new Error('当前无法查看此病例的治疗记录。'), { aggregateDenied: true });
    }
    // A proxy or expired session can return a 401 without a JSON body.
    const result = response.status === 401 ? await response.json().catch(() => null) : await response.json();
    if (!t.current()) throw Object.assign(new Error('stale'), { stale: true });
    // Only business endpoints return terminal command receipts with a 4xx status.
    if (response.status === 401 || (!response.ok && !receipt)) {
      const rejectedPassword = response.status === 401 && suffix === '/auth/reauthenticate'
        && result?.code === 'REAUTHENTICATION_FAILED' && !Object.hasOwn(result, 'state') && !Object.hasOwn(result, 'challenge_id');
      throw Object.assign(new Error(result?.code || result?.detail || '读取失败'), { status: response.status, code: result?.code, rejectedPassword });
    }
    return { status: response.status, body: result };
  }
  function failed(error, t) {
    if (!t.current() || error.stale || error.name === 'AbortError') return;
    setChecked(false); setRevokeChecked(false); setPassword(''); setVerified(null);
    if (error.aggregateDenied) {
      setData(null); setContent(empty()); setListEdits({}); setEditBase(null); setRejectedDraft(false); setReason('');
      setMessage(error.message);
    } else if (error.status === 401) {
      if (error.rejectedPassword) {
        setMessage('再次认证未通过，本次操作尚未提交。请重新核对并输入当前账号密码。');
        return;
      }
      setExpired(true); setData(null);
      const next = pendingRef.current
        ? '请退出后使用同一账号重新登录，再查询原请求。'
        : '请退出后重新登录，再打开本病例。';
      setMessage('登录已失效。原文仅供复制保留；原预览、勾选和认证已失效。' + next);
    } else setMessage(pendingRef.current ? '结果尚未确认，请查询原请求；不要重复提交。' : errors[error.code] || String(error.message));
  }
  async function load(t, replaceDraft = true, committedDraftETag = null) {
    if (!t.current()) return;
    setRecordCurrent(false); setVerified(null); setChecked(false); setRevokeChecked(false); setPassword('');
    const g = (await request(path + '/treatment', t)).body;
    if (!t.current()) return;
    const partition = `pmai:treatment:${g.actor_id}:${scope.org_id}:${scope.clinic_id}:${caseId}`;
    storage.current = partition; setData(g); setRecordCurrent(true); setExpired(false);
    if (replaceDraft || (committedDraftETag && committedDraftETag === draftPrecondition(g))) {
      setListEdits({}); setContent(g.draft?.content || empty()); setEditBase(null); setRejectedDraft(false);
    }
    if (!pendingRef.current) {
      try { const saved = JSON.parse(sessionStorage.getItem(partition) || 'null');
        if (saved && /^[0-9a-f]{64}$/.test(saved.key) && /^[0-9a-f]{64}$/.test(saved.request_hash) && ['draft.save','revision.freeze','review','sign','amend','revoke'].includes(saved.operation)) remember(saved);
      } catch { /* No clinical state is restored from storage. */ }
    }
    return g;
  }
  async function refresh(discardEdits = false) {
    const t = task(); setBusy(true); setMessage('');
    try { await load(t, !dirty || discardEdits); } catch (e) { failed(e, t); } finally { if (t.current()) setBusy(false); }
  }
  useEffect(() => {
    setListEdits({});
    storage.current = null; pendingRef.current = null; setPending(null); setData(null); setContent(empty()); setEditBase(null); setRejectedDraft(false); setVerified(null); setExpired(false); setChecked(false); setRevokeChecked(false); setPassword('');
    const t = task(); setBusy(true);
    load(t).catch(e => failed(e, t)).finally(() => { if (t.current()) setBusy(false); });
    return () => { work.current.epoch++; work.current.controller?.abort(); };
  }, [token, path]);
  function markEdited() {
    setEditBase(current => current ?? draftPrecondition(data));
    setChecked(false); setRevokeChecked(false); setPassword(''); setVerified(null);
  }
  function edit(next) { setContent(next); markEdited(); }
  function editList(field, value) {
    setListEdits(previous => ({ ...previous, [field]: value }));
    markEdited();
  }
  function currentContent(keepPlaceholders = false) {
    return { ...content,
      diagnoses: draftListItems(content.diagnoses, listEdits.diagnoses, true, keepPlaceholders),
      treatment: { ...content.treatment, goals: draftListItems(content.treatment.goals, listEdits.goals, false, keepPlaceholders) },
    };
  }
  async function reconcile(response, t, source, submitted = null) {
    if (!t.current()) return;
    const original = pendingRef.current;
    if (!matchesTreatmentReceipt(response, original, source, submitted)) throw new Error('无法核对原请求的回执。');
    const out = response.body;
    if (out.state === 'pending' || out.state === 'not_observed') { setMessage('结果仍待核对。未观察到结果不表示未保存；可继续查询或取消原请求。'); return; }
    if (out.state !== 'committed') {
      if (original.operation === 'draft.save' && out.code === 'VERSION_MISMATCH' && dirty) setRejectedDraft(true);
      remember(null); setMessage(errors[out.code] || out.code || '操作未完成，请重新读取后核对。'); await load(t, !dirty); return;
    }
    let verifiedSignature = null;
    if (original.operation === 'sign' || original.operation === 'revoke') {
      const readback = await request(path + '/treatment/signatures/' + out.signature_id, t);
      const expected = { org_id: scope.org_id, clinic_id: scope.clinic_id, case_id: caseId, actor_id: data.actor_id };
      if (!await matchesTreatmentSignature(readback, out, expected, submitted?.proof)) throw new Error('无法独立核对签署结果。');
      if (!t.current()) return;
      verifiedSignature = readback.body;
    }
    // A newer draft may already exist by the time this save's receipt is read.
    const savedDraftETag = original.operation === 'draft.save' ? out.draft_etag : null;
    const aggregate = await load(t, !dirty, savedDraftETag);
    if (!t.current()) return;
    remember(null);
    if (verifiedSignature && !readbackStillCurrent(aggregate, verifiedSignature)) {
      setVerified(null); setMessage('已独立回读签署。最新治疗记录未确认同一签署状态，请核对当前签署和签署历史。');
    } else {
      setVerified(verifiedSignature); setMessage('已从服务端核对保存结果。');
    }
  }
  async function submit(operation, target, suffix, body, method = 'POST', proof = null) {
    if (locked || pendingRef.current || !data || (operation === 'draft.save' && draftConflict)) return;
    const t = task(); setBusy(true); setMessage(''); setVerified(null);
    const precondition = operation === 'draft.save' ? (editBase ?? draftPrecondition(data)) : data.etag;
    try {
      if (proof) {
        const challenge = await request('/auth/reauthenticate', t, 'POST', { org_id: scope.org_id, clinic_id: scope.clinic_id, case_id: caseId,
          revision_id: proof.revision_id, content_hash: proof.hash, action: operation, target_signature_id: proof.signature_id || null, password });
        if (!t.current()) return;
        if (challenge.status !== 200 || typeof challenge.body?.challenge_id !== 'string' || !challenge.body.challenge_id.trim() || Object.hasOwn(challenge.body, 'state')) {
          throw new Error('再次认证结果无法核实，请重新核对并认证。');
        }
        body = { ...body, challenge_id: challenge.body.challenge_id }; setPassword('');
      }
      const key = newKey();
      const request_hash = await requestHash({ actor_id: data.actor_id, scope: { org_id: scope.org_id, clinic_id: scope.clinic_id, case_id: caseId }, operation, target, precondition, body });
      if (!t.current()) return;
      remember({ key, operation, request_hash });
      setChecked(false); setRevokeChecked(false); setPassword('');
      const headers = { 'Idempotency-Key': key, [precondition === '*' ? 'If-None-Match' : 'If-Match']: precondition };
      const out = await request(path + '/treatment' + suffix, t, method, body, headers, true);
      await reconcile(out, t, 'submit', { target, decision: body.decision, baseSignatureId: body.base_signature_id, proof });
    } catch (e) { failed(e, t); }
    finally { if (t.current()) { setBusy(false); setPassword(''); } }
  }
  async function recover(cancel = false) {
    if (busy || expired || !pending || !data) return;
    const t = task(); setBusy(true);
    try {
      const suffix = path + '/commands/' + pending.key + (cancel ? '/cancel' : '?operation=' + pending.operation);
      const out = await request(suffix, t, cancel ? 'POST' : 'GET', cancel ? { operation: pending.operation, request_hash: pending.request_hash, reason: reason || '用户取消原请求' } : undefined, {}, true);
      await reconcile(out, t, cancel ? 'cancel' : 'lookup');
    } catch (e) { failed(e, t); } finally { if (t.current()) setBusy(false); }
  }
  const rev = data?.revisions.find(r => r.id === data.plan?.head_revision_id);
  const staleDraft = rev && rev.draft_version !== data?.draft?.draft_version;
  const staleSource = rev?.origin === 'clinical' && (
    versionsDiffer(rev.source_manifest.case?.clinical_epoch, data.source_epoch)
    || versionsDiffer(rev.source_manifest.policy?.version, data.policy.version)
  );
  const review = data?.reviews.find(r => r.revision_id === rev?.id);
  const activeId = data?.plan?.active_signature_id;
  const states = new Map(data?.signatures.map(s => [s.id, signatureState(data, s.id)]));
  const active = recordCurrent && states.get(activeId) === 'effective' ? data.signatures.find(s => s.id === activeId) : null;
  const activeRevision = data?.revisions.find(r => r.id === active?.revision_id);
  const uncertainStatus = (!!activeId && states.get(activeId) !== 'effective') || [...states.values()].includes('unknown');
  // Discard fetches a new draft and replaces local edits only after a successful read.
  const discardLocked = busy || expired || !!pending || uncertainStatus;
  const locked = discardLocked || !recordCurrent;
  const canEdit = data?.allowed_actions.edit && !locked;
  const cannotConfirmRevision = locked || dirty || staleDraft || staleSource || rev?.origin !== 'clinical';
  return <section className="treatment-workspace" aria-label="治疗签署" style={{ marginTop: 32, padding: 20, border: '1px solid #a7bac9', borderRadius: 12 }}>
    <h2>治疗记录与院内账号确认</h2>
    <p>{scope.org_name}／{scope.clinic_name} · 病例 #{caseId}</p>
    <p>医生审核后以院内账号确认签署。此入口不执行处方、不调用证书签名服务。</p>
    {message && <p role="status">{message}</p>}{busy && <p role="status">正在核对……</p>}
    {pending && <aside><p>待核对请求：{pending.key}</p>{busy && <button onClick={() => { task(); setBusy(false); setPassword(''); setChecked(false); setRevokeChecked(false); setMessage('已停止等待，原请求仍需查询或取消。'); }}>停止等待（保留原请求）</button>}<button disabled={busy || expired || !data} onClick={() => recover()}>查询原请求</button>{' '}
      <button disabled={busy || expired || !data} onClick={() => recover(true)}>取消原请求</button></aside>}
    {expired ? <section><h3>未保存原文 · 只读保留</h3><ContentView content={currentContent(true)} localLists={listEdits} /></section> : <>
      <button disabled={busy} onClick={() => refresh()}>重新读取治疗记录</button>
      {data && <>
        <p>审核账号：{data.profile?.display_name || '当前账号无已核验医生档案'} · {data.policy.review_policy === 'two_person' ? '另一位医生签署' : '允许同一医生审核签署'}</p>
        {(uncertainStatus || (!recordCurrent && !busy)) && <p role="alert">签署状态待核对，请重新读取治疗记录。</p>}
        {data.policy.required_assurance === 'certificate_signature' && <p role="alert">本院要求证书签名，当前不能签署。</p>}
        {active && <section aria-label="当前有效签署"><h3>当前有效签署 · 版本 {activeRevision?.revision_no}</h3><p>{active.clinician_snapshot.display_name} · {active.signed_at} · 已确认签署 · 院内账号确认</p>{activeRevision && <ContentView content={activeRevision.content} />}</section>}
        <fieldset disabled={!canEdit || (!!active && data.draft?.amendment_of !== active.id)}><legend>治疗草稿</legend>
          <TreatmentDraftList diagnosis items={content.diagnoses} edit={listEdits.diagnoses} onChange={value => editList('diagnoses', value)} />
          <p><label>评估原文<textarea aria-label="治疗评估" value={content.assessment} onChange={e => edit({ ...content, assessment: e.target.value })} /></label></p>
          <TreatmentDraftList items={content.treatment.goals} edit={listEdits.goals} onChange={value => editList('goals', value)} />
          {[["management_text",'治疗措施'],['monitoring_text','监测安排'],['followup_text','复查安排']].map(([key,label]) => <p key={key}><label>{label}<textarea aria-label={label} value={content.treatment[key]} onChange={e => edit({ ...content, treatment: { ...content.treatment, [key]: e.target.value } })} /></label></p>)}
          <button disabled={!!draftConflict} onClick={() => submit('draft.save','draft','/draft',{ content: currentContent() },'PATCH')}>保存治疗草稿</button>
        </fieldset>
        <button disabled={!canEdit || dirty || !data.draft || (!!active && data.draft.amendment_of !== active.id)} onClick={() => submit('revision.freeze','revisions','/revisions',{ draft_version: data.draft.draft_version, expected_source_epoch: data.source_epoch })}>冻结版本供核对</button>
        {draftConflict ? <section aria-label="草稿版本冲突"><p role="alert">服务端治疗草稿已更新。本页保留你的原文，请先复制需要保留的修改，再载入服务器草稿。</p>
          <button disabled={discardLocked} onClick={() => refresh(true)}>放弃本页修改并载入服务器草稿</button></section>
          : dirty && <p>有尚未保存的修改。保存后才能冻结和签署。</p>}
        {rev && <section aria-label="冻结版本"><h3>冻结版本 {rev.revision_no} · {rev.origin === 'legacy_import' ? '历史原文，未经签署' : '待核对治疗内容'}</h3>
          <ContentView content={rev.content} />
          <p>来源病例：{rev.source_manifest.case?.patient_name || "历史病例"} · 资料版本 {rev.source_manifest.case?.clinical_epoch || "历史快照"} · 诊断报告 {rev.source_manifest.diagnostic_reports?.length || 0} 份</p>
          <details><summary>查看冻结来源资料</summary><pre style={textStyle}>{JSON.stringify(rev.source_manifest, null, 2)}</pre></details>
          {staleDraft && <p>草稿已修改，此冻结版本不能继续审核或签署。</p>}
          {staleSource && <p role="alert">冻结后病例资料或签署规则已变化，请重新冻结版本后再审核或签署。</p>}
          <p style={textStyle}>内容校验值：{rev.content_sha256}</p>
          {review && <p>审核：{review.clinician_snapshot.display_name} · {({ approve: '审核通过', request_revision: '要求修订', reject: '审核拒绝' })[review.decision]} · {review.reason}</p>}
          <label><input aria-label="已核对冻结版本" type="checkbox" checked={checked} disabled={cannotConfirmRevision} onChange={e => setChecked(e.target.checked)} />我已核对病例、完整原文、来源资料及本次操作</label>
          <p><label>审核／修订／作废原因<input aria-label="操作原因" value={reason} disabled={locked} onChange={e => setReason(e.target.value)} /></label></p>
          {!review && ['approve','request_revision','reject'].map((decision,i) => <button key={decision} disabled={cannotConfirmRevision || !checked || !reason.trim() || !data.allowed_actions.review} onClick={() => submit('review',rev.id,`/revisions/${rev.id}/reviews`,{ decision, reason })}>{['审核通过','要求修订','审核拒绝'][i]}</button>)}
          <p><label>再次输入当前账号密码<input aria-label="签署认证密码" type="password" autoComplete="off" value={password} disabled={locked} onChange={e => setPassword(e.target.value)} /></label></p>
          <button disabled={cannotConfirmRevision || !checked || !password || !data.allowed_actions.sign || review?.decision !== 'approve' || data.signatures.some(s => s.revision_id === rev.id)} onClick={() => submit('sign',rev.id,`/revisions/${rev.id}/signatures`,{ review_id: review.id, content_hash: rev.content_sha256 },'POST',{ revision_id: rev.id, hash: rev.content_sha256 })}>再次认证并确认签署</button>
        </section>}
        {active && <section><p><label><input type="checkbox" aria-label="已核对待作废签署" checked={revokeChecked} disabled={locked} onChange={e => setRevokeChecked(e.target.checked)} />我已核对当前有效签署（版本 {activeRevision?.revision_no}）及作废原因</label></p><p><button disabled={!canEdit || !reason.trim() || data.draft?.amendment_of === active.id} onClick={() => submit('amend','amendments','/amendments',{ base_signature_id: active.id, reason })}>创建修订草稿</button>{' '}
          <button disabled={locked || !revokeChecked || !password || !reason.trim() || !data.allowed_actions.sign} onClick={() => submit('revoke',active.id,`/signatures/${active.id}/revocations`,{ reason },'POST',{ revision_id: active.revision_id, hash: active.content_hash, signature_id: active.id })}>再次认证并作废签署</button></p></section>}
        <h3>签署历史</h3>
        {data.signatures.map(signature => {
          const version = data.revisions.find(r => r.id === signature.revision_id)?.revision_no;
          const state = !recordCurrent && signature.id === activeId ? 'unknown' : states.get(signature.id);
          const revocation = state === 'revoked' && data.events.find(e => e.signature_id === signature.id && e.event === 'revoked');
          return <div key={signature.id}>
            <p>版本 {version} · {signature.clinician_snapshot.display_name} · {signature.signed_at} · {signatureLabels[state]} · 院内账号确认</p>
            {revocation && <details>
              <summary>{version == null ? '查看作废记录' : `查看版本 ${version} 的作废记录`}</summary>
              <dl style={textStyle}>
                <dt>作废账号 ID</dt><dd>{revocation.actor_id ?? '未提供'}</dd>
                <dt>作废时间</dt><dd>{revocation.created_at ?? '未提供'}</dd>
                <dt>作废原因</dt><dd>{revocation.reason ?? '未提供'}</dd>
              </dl>
            </details>}
          </div>;
        })}
      </>}
    </>}
    {verified && <aside aria-label="独立回读签署"><p>已独立回读签署：{verified.signature.id} · {verified.state} · 院内账号确认</p><ContentView content={verified.revision.content} /></aside>}
  </section>;
}
