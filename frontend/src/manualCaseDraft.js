export const MANUAL_DRAFT_KEY = "pmai.manual-case-draft.v1";
export const MANUAL_DRAFT_MAX_AGE = 8 * 60 * 60 * 1000;
const MAX_LENGTH = 250000;
const fields = ["patient_name", "species", "sex", "age_info", "breed", "weight", "coat_color", "owner_name", "owner_phone", "chief_complaint", "history", "exam_findings", "analysis", "treatment", "prognosis"];
const validOwner = owner => typeof owner === "string" && owner.length > 0 && owner.length <= 320;
function cleanValues(values) {
  if (!values || typeof values !== "object" || Array.isArray(values) || Object.keys(values).some(key => !fields.includes(key))) throw Error("Invalid fields");
  const result = Object.fromEntries(fields.map(key => {
    if (typeof values[key] !== "string" || values[key].length > 100000) throw Error("Invalid text");
    return [key, values[key]];
  }));
  if (JSON.stringify(result).length > MAX_LENGTH) throw Error("Oversize");
  return result;
}
export const hasManualDraftInput = values => fields.some(key => values[key] !== (key === "species" ? "dog" : ""));
export function clearManualCaseDraft(storage) {
  try { (storage || window.sessionStorage).removeItem(MANUAL_DRAFT_KEY); return true; } catch { return false; }
}
export function writeManualCaseDraft(owner, values, storage, now = Date.now()) {
  try {
    storage = storage || window.sessionStorage;
    if (!validOwner(owner)) throw Error("Invalid owner");
    const clean = cleanValues(values);
    if (!hasManualDraftInput(clean)) return clearManualCaseDraft(storage);
    storage.setItem(MANUAL_DRAFT_KEY, JSON.stringify({ version: 1, owner, updatedAt: now, values: clean }));
    return true;
  } catch {
    if (storage) clearManualCaseDraft(storage);
    return false;
  }
}
export function readManualCaseDraft(owner, storage, now = Date.now()) {
  try {
    storage = storage || window.sessionStorage;
    const raw = storage.getItem(MANUAL_DRAFT_KEY);
    if (!raw) return { draft: null, error: "" };
    // This is a local partition, never a server authentication mechanism.
    if (!validOwner(owner)) return { draft: null, error: "" };
    if (raw.length > MAX_LENGTH + 2000) throw Error("Oversize");
    const item = JSON.parse(raw);
    if (item.owner !== owner) { clearManualCaseDraft(storage); return { draft: null, error: "" }; }
    if (item.version !== 1 || !Number.isFinite(item.updatedAt) || now - item.updatedAt >= MANUAL_DRAFT_MAX_AGE || item.updatedAt > now + 60000) throw Error("Expired or invalid");
    const values = cleanValues(item.values);
    return { draft: hasManualDraftInput(values) ? { values, updatedAt: item.updatedAt } : null, error: "" };
  } catch {
    const cleared = storage && clearManualCaseDraft(storage);
    return { draft: null, error: "新建输入草稿不可读取或已过期。" + (cleared ? "" : "浏览器未能清除旧草稿，请勿将其视为最新输入。") };
  }
}
