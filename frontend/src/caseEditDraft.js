import { draftOwner } from "./consultDraft";

export const CASE_EDIT_DRAFT_PREFIX = "pmai.case-edit-draft.v1.";
export const CASE_EDIT_DRAFT_MAX_AGE = 8 * 60 * 60 * 1000;
const MAX_LENGTH = 250000;
const fields = new Set(["patient_name", "species", "sex", "age_info", "breed", "weight", "coat_color", "owner_name", "owner_phone", "chief_complaint", "history", "exam_findings", "analysis", "treatment", "prognosis"]);
const keyFor = caseId => {
  if (!Number.isSafeInteger(caseId) || caseId <= 0) throw new Error("Invalid case");
  return CASE_EDIT_DRAFT_PREFIX + caseId;
};
const cleanChanges = changes => {
  if (!changes || typeof changes !== "object" || Array.isArray(changes)) throw new Error("Invalid changes");
  const entries = Object.entries(changes);
  if (entries.some(([key, value]) => !fields.has(key) || typeof value !== "string" || value.length > 100000)) throw new Error("Invalid field");
  const result = Object.fromEntries(entries);
  if (JSON.stringify(result).length > MAX_LENGTH) throw new Error("Oversize");
  return result;
};

// This partitions local drafts only. Restoring still requires an authenticated
// read of the exact case, then a new server preview and explicit confirmation.
export function caseEditDraftOwner() {
  try { return draftOwner(localStorage.getItem("token")); } catch { return null; }
}

export function clearCaseEditDraft(caseId, storage) {
  try { (storage || window.sessionStorage).removeItem(keyFor(caseId)); return true; } catch { return false; }
}

export function clearCaseEditDrafts(storage) {
  try {
    storage = storage || window.sessionStorage;
    for (let i = storage.length - 1; i >= 0; i--) {
      const key = storage.key(i);
      if (key?.startsWith(CASE_EDIT_DRAFT_PREFIX)) storage.removeItem(key);
    }
    return true;
  } catch { return false; }
}

export function readCaseEditDraft(owner, caseId, storage, now = Date.now()) {
  try {
    storage = storage || window.sessionStorage;
    const raw = storage.getItem(keyFor(caseId));
    if (!raw) return { draft: null, error: "" };
    if (!owner) { clearCaseEditDraft(caseId, storage); return { draft: null, error: "" }; }
    if (raw.length > MAX_LENGTH + 2000) throw new Error("Oversize");
    const item = JSON.parse(raw);
    if (item.owner !== owner) { clearCaseEditDraft(caseId, storage); return { draft: null, error: "" }; }
    if (item.version !== 1 || item.caseId !== caseId || !Number.isFinite(item.updatedAt) || now - item.updatedAt > CASE_EDIT_DRAFT_MAX_AGE || item.updatedAt > now + 60000) throw new Error("Expired or invalid");
    const changes = cleanChanges(item.changes);
    return { draft: Object.keys(changes).length ? { changes, updatedAt: item.updatedAt } : null, error: "" };
  } catch {
    if (storage) clearCaseEditDraft(caseId, storage);
    return { draft: null, error: "编辑草稿不可读取或已过期；请检查服务器内容后继续。" };
  }
}

export function writeCaseEditDraft(owner, caseId, changes, storage, now = Date.now()) {
  try {
    storage = storage || window.sessionStorage;
    if (typeof owner !== "string" || !owner || owner.length > 320) throw new Error("Invalid owner");
    const clean = cleanChanges(changes);
    if (!Object.keys(clean).length) return clearCaseEditDraft(caseId, storage);
    storage.setItem(keyFor(caseId), JSON.stringify({ version: 1, owner, caseId, updatedAt: now, changes: clean }));
    return true;
  } catch {
    if (storage) clearCaseEditDraft(caseId, storage); // Never present an older copy as current.
    return false;
  }
}
