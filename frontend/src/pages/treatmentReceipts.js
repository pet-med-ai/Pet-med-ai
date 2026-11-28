const isUUID = value => typeof value === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(value);
const isHash = value => typeof value === 'string' && /^[0-9a-f]{64}$/.test(value);
const positiveVersion = value => Number.isSafeInteger(value) && value > 0;

export function canonical(value) {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (value !== null && typeof value === 'object') return '{' + Object.keys(value).sort().map(k => JSON.stringify(k) + ':' + canonical(value[k])).join(',') + '}';
  return JSON.stringify(value);
}

async function hashText(text) {
  const data = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return Array.from(new Uint8Array(data), x => x.toString(16).padStart(2, '0')).join('');
}

export function requestHash(value) {
  return hashText(canonical(value));
}

function committedResult(body, submitted) {
  switch (body.operation) {
    case 'draft.save':
      return isUUID(body.plan_id) && isUUID(body.audit_id) && positiveVersion(body.draft_version)
        && body.draft_etag === `"draft:${body.draft_version}"`;
    case 'revision.freeze':
      return isUUID(body.revision_id) && isHash(body.content_hash);
    case 'review':
      return isUUID(body.revision_id) && isUUID(body.review_id) && ['approve', 'request_revision', 'reject'].includes(body.decision)
        && (!submitted || (body.revision_id === submitted.target && body.decision === submitted.decision));
    case 'amend':
      return positiveVersion(body.draft_version) && isUUID(body.base_signature_id)
        && (!submitted || body.base_signature_id === submitted.baseSignatureId);
    case 'sign':
      return isUUID(body.signature_id) && isUUID(body.revision_id) && body.assurance === 'account_attestation'
        && (!submitted || body.revision_id === submitted.target);
    case 'revoke':
      return isUUID(body.signature_id) && isUUID(body.event_id) && (!submitted || body.signature_id === submitted.target);
    default:
      return false;
  }
}

export function matchesTreatmentReceipt({ status, body }, original, source, submitted = null) {
  if (!isHash(original?.key) || !isHash(original.request_hash) || !body
      || body.idempotency_key !== original.key || body.operation !== original.operation) return false;
  if (body.state === 'not_observed') {
    // No row exists yet, so the lookup has no stored request hash to return.
    return source === 'lookup' && status === 202 && !Object.hasOwn(body, 'request_hash') && !Object.hasOwn(body, 'code');
  }
  if (body.request_hash !== original.request_hash) return false;
  switch (body.state) {
    case 'pending':
      return source !== 'cancel' && status === 202 && !Object.hasOwn(body, 'code');
    case 'committed':
      return status === 201 && !Object.hasOwn(body, 'code') && typeof body.etag === 'string'
        && /^"plan:[1-9][0-9]*"$/.test(body.etag) && committedResult(body, submitted);
    case 'cancelled':
      return status === 409 && body.code === 'COMMAND_CANCELLED';
    case 'failed':
      return status >= 400 && status < 500 && status !== 401 && typeof body.code === 'string'
        && /^[A-Z][A-Z0-9_]*$/.test(body.code) && body.code !== 'COMMAND_CANCELLED';
    default:
      return false;
  }
}

function displayableContent(content) {
  const treatment = content?.treatment;
  return content?.schema === 'treatment-content-v1' && typeof content.assessment === 'string'
    && Array.isArray(content.diagnoses) && content.diagnoses.every(item => typeof item?.label === 'string')
    && Array.isArray(treatment?.goals) && treatment.goals.every(value => typeof value === 'string')
    && ['management_text', 'monitoring_text', 'followup_text'].every(field => typeof treatment[field] === 'string');
}

// Aggregates carry the frozen revision and its stored hash. Independent readbacks also carry its canonical bytes.
export function matchesSignedRevision(signature, revision) {
  return isUUID(revision?.id) && signature.revision_id === revision.id
    && isHash(signature.content_hash) && signature.content_hash === revision.content_sha256
    && displayableContent(revision.content);
}

export async function matchesTreatmentSignature({ status, body }, receipt, scope, proof = null) {
  const { signature, revision, terminal_event: event, state } = body || {};
  const sameCase = row => row?.org_id === scope.org_id && row.clinic_id === scope.clinic_id && row.case_id === scope.case_id;
  if (status !== 200 || !sameCase(signature) || !sameCase(revision) || signature.id !== receipt.signature_id
      || !isUUID(signature.plan_id) || signature.plan_id !== revision.plan_id
      || signature.assurance !== 'account_attestation' || !matchesSignedRevision(signature, revision)) return false;
  if (proof && (proof.revision_id !== revision.id || proof.hash !== signature.content_hash)) return false;
  if (state === 'effective') {
    if (event !== null) return false;
  } else if (!['revoked', 'superseded'].includes(state) || !sameCase(event) || event.plan_id !== signature.plan_id
      || event.event !== state || event.signature_id !== signature.id) return false;
  if (receipt.operation === 'sign') {
    if (signature.signer_id !== scope.actor_id || receipt.revision_id !== revision.id) return false;
  } else if (receipt.operation !== 'revoke' || state !== 'revoked' || event.id !== receipt.event_id
      || event.actor_id !== scope.actor_id || (proof && proof.signature_id !== signature.id)) return false;

  if (typeof revision.canonical_utf8 !== 'string') return false;
  // Hash the exact server-frozen bytes. Compare the displayed JSON independent of object key order.
  if (await hashText(revision.canonical_utf8) !== signature.content_hash) return false;
  let frozen;
  try { frozen = JSON.parse(revision.canonical_utf8); } catch { return false; }
  return sameCase(frozen) && frozen.plan_id === signature.plan_id && frozen.revision_id === revision.id
    && canonical(frozen.content) === canonical(revision.content);
}
