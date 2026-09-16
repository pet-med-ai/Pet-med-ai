export const DRAFT_KEY = "pmai.consult-draft.v1";
export const DRAFT_MAX_AGE = 8 * 60 * 60 * 1000;
const MAX_LENGTH = 250000;
export const draftFields = ["patientName", "species", "sex", "ageInfo", "breed", "weight", "coatColor", "ownerName", "ownerPhone", "chiefComplaint", "history", "examFindings", "auditReviewAction", "auditReviewReason", "auditReviewNote", "auditClinicianId"];
const plain = value => !!value && typeof value === "object" && !Array.isArray(value);
const text = (value, max = 100000) => typeof value === "string" && value.length <= max;

// Cache partition only, not authentication. Every restored session is read via
// the authenticated API; local data can never restore a review or save receipt.
export function draftOwner(token, now = Date.now()) {
  try {
    const part = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const claims = JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(part), c => c.charCodeAt(0))));
    return text(claims.sub, 320) && claims.sub && Number.isFinite(claims.exp) && claims.exp * 1000 > now ? claims.sub : null;
  } catch { return null; }
}

function cleanSubmission(value) {
  if (value == null) return null;
  if (!plain(value) || !Array.isArray(value.sections) || value.sections.length > 60) throw new Error("Invalid submission");
  const str = v => { if (!text(v)) throw new Error("Invalid text"); return v; };
  return {
    version: str(value.version || ""), template_key: str(value.template_key || ""), label: str(value.label || ""),
    sections: value.sections.map(section => {
      if (!plain(section) || !Array.isArray(section.answers) || section.answers.length > 200) throw new Error("Invalid answers");
      return { key: str(section.key || ""), title: str(section.title || ""), answers: section.answers.map(a => ({
        key: str(a.key || ""), label: str(a.label || ""), answer: str(a.answer), answer_type: str(a.answer_type || "text"), required: !!a.required, triggered: !!a.triggered,
      })) };
    }),
  };
}

export function cleanDraft(value) {
  if (!plain(value) || !plain(value.fields)) throw new Error("Invalid draft");
  const fields = Object.fromEntries(draftFields.map(key => {
    const v = value.fields[key] ?? "";
    if (!text(v)) throw new Error("Invalid field");
    return [key, v];
  }));
  if (!(value.sessionId === null || text(value.sessionId, 200))) throw new Error("Invalid session");
  if (!text(value.followupAnswer) || !text(value.sessionContext) || !text(value.recoveredNotes)) throw new Error("Invalid pending input");
  if (!plain(value.structuredAnswers) || Object.keys(value.structuredAnswers).length > 500) throw new Error("Invalid structured input");
  const structuredAnswers = Object.fromEntries(Object.entries(value.structuredAnswers).map(([key, v]) => {
    if (!text(key, 300) || !text(v, 20000)) throw new Error("Invalid structured answer");
    return [key, v];
  }));
  const data = { fields, sessionId: value.sessionId, followupAnswer: value.followupAnswer, sessionContext: value.sessionContext, structuredAnswers, lastSubmission: cleanSubmission(value.lastSubmission), recoveredNotes: value.recoveredNotes };
  if (JSON.stringify(data).length > MAX_LENGTH) throw new Error("Draft too large");
  return data;
}

export function hasDraftContent(data) {
  return !!data.sessionId || draftFields.some(key => !["species", "auditReviewAction"].includes(key) && data.fields[key].trim()) || !!data.followupAnswer.trim() || Object.values(data.structuredAnswers).some(v => v.trim()) || !!data.recoveredNotes;
}

export function clearDraft(storage) {
  try { storage = storage || window.sessionStorage; storage.removeItem(DRAFT_KEY); return true; } catch { return false; }
}

export function readDraft(owner, storage, now = Date.now()) {
  try {
    storage = storage || window.sessionStorage;
    const raw = storage.getItem(DRAFT_KEY);
    if (!raw) return { draft: null, error: "" };
    if (!owner) { clearDraft(storage); return { draft: null, error: "" }; }
    if (raw.length > MAX_LENGTH + 2000) throw new Error("Oversize");
    const item = JSON.parse(raw);
    if (item.owner !== owner) { clearDraft(storage); return { draft: null, error: "" }; }
    if (item.version !== 1 || !Number.isFinite(item.updatedAt) || now - item.updatedAt > DRAFT_MAX_AGE || item.updatedAt > now + 60000) throw new Error("Expired or invalid");
    return { draft: { data: cleanDraft(item.data), updatedAt: item.updatedAt }, error: "" };
  } catch {
    if (storage) clearDraft(storage);
    return { draft: null, error: "草稿不可读取或已过期；请检查输入后继续。" };
  }
}

export function writeDraft(owner, data, storage, now = Date.now()) {
  try {
    storage = storage || window.sessionStorage;
    if (!owner) return false;
    const clean = cleanDraft(data);
    if (!hasDraftContent(clean)) return clearDraft(storage);
    storage.setItem(DRAFT_KEY, JSON.stringify({ version: 1, owner, updatedAt: now, data: clean }));
    return true;
  } catch {
    if (storage) clearDraft(storage); // Avoid presenting an older copy as current.
    return false;
  }
}
