const DRAFT = "pmai.follow-up-draft.v1.";
const ATTEMPT = "pmai.follow-up-attempt.v1.";
const age = 8 * 60 * 60 * 1000;
const token = value => typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
export const validPlanValues = v => v && typeof v.due_date === "string" && v.due_date.length <= 10 &&
  typeof v.note === "string" && v.note.length <= 8000;
const key = (prefix, owner, caseId) => {
  if (typeof owner !== "string" || !owner || owner.length > 320 || !Number.isSafeInteger(caseId) || caseId < 1) throw Error("Invalid identity");
  return prefix + encodeURIComponent(owner) + "." + caseId;
};
function storage() { return window.sessionStorage; }
function validAttempt(value) {
  const r = value?.request;
  return r && /^[a-f0-9]{32}$/.test(r.request_id) && token(r.expected_state_token) && token(r.expected_preview_token) &&
    ["create", "replace", "cancel"].includes(r.action) &&
    (r.action === "cancel" ? r.due_date === null && r.note === null : validPlanValues(r)) &&
    (r.action === "create" ? value.before_id === null : Number.isSafeInteger(value.before_id) && value.before_id > 0) &&
    typeof value.rejected === "boolean";
}
function write(prefix, owner, caseId, value) {
  try {
    const k = key(prefix, owner, caseId);
    const raw = JSON.stringify({ version: 1, owner, caseId, at: Date.now(), value });
    storage().setItem(k, raw);
    return storage().getItem(k) === raw;
  } catch { return false; }
}
function remove(prefix, owner, caseId) {
  try { const k = key(prefix, owner, caseId); storage().removeItem(k); return storage().getItem(k) === null; }
  catch { return false; }
}
export const clearPlanDraft = (owner, caseId) => remove(DRAFT, owner, caseId);
export const clearPlanAttempt = (owner, caseId) => remove(ATTEMPT, owner, caseId);
export function savePlanDraft(owner, caseId, values) {
  if (!validPlanValues(values)) return false;
  if (!values.due_date && !values.note) return clearPlanDraft(owner, caseId);
  const ok = write(DRAFT, owner, caseId, { due_date: values.due_date, note: values.note });
  if (!ok) clearPlanDraft(owner, caseId); // Do not label an older copy as latest.
  return ok;
}
export const savePlanAttempt = (owner, caseId, attempt) => validAttempt(attempt) && write(ATTEMPT, owner, caseId, attempt);
export function loadPlanLocal(owner, caseId, now = Date.now()) {
  const result = { draft: null, attempt: null, blocked: false, message: "" };
  try {
    const raw = storage().getItem(key(ATTEMPT, owner, caseId));
    if (raw) {
      if (raw.length > 45000) throw Error("Oversize");
      const p = JSON.parse(raw);
      if (p.version !== 1 || p.owner !== owner || p.caseId !== caseId || !validAttempt(p.value)) throw Error("Invalid receipt");
      result.attempt = p.value; // Pending requests never expire into a new write.
    }
  } catch {
    result.blocked = true;
    result.message = "待核对请求无法读取，暂不能提交；请先核对服务器记录。";
    return result;
  }
  try {
    const raw = storage().getItem(key(DRAFT, owner, caseId));
    if (raw) {
      if (raw.length > 40000) throw Error("Oversize");
      const p = JSON.parse(raw);
      if (p.version !== 1 || p.owner !== owner || p.caseId !== caseId || !Number.isFinite(p.at) ||
          p.at > now + 60000 || now - p.at >= age || !validPlanValues(p.value)) throw Error("Invalid draft");
      result.draft = p.value;
    }
  } catch {
    clearPlanDraft(owner, caseId);
    result.message = "复查输入草稿不可读取或已过期，请核对后重新填写。";
  }
  return result;
}
export function clearPlanDrafts() {
  try {
    const s = storage();
    for (let i = s.length - 1; i >= 0; i--) { const k = s.key(i); if (k?.startsWith(DRAFT)) s.removeItem(k); }
  } catch { /* The UI also checks account identity before revealing any content. */ }
  // Keep account-partitioned pending requests across logout. Removing them
  // could turn an unknown server outcome into an unprotected new submission.
}
