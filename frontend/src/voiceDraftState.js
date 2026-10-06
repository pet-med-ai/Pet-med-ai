export const voiceIdentity = context => JSON.stringify([context.owner, context.sessionId, context.caseId || null, context.patientName.trim() || "未命名病例", context.species]);
export const voiceRevision = (context, text) => JSON.stringify([voiceIdentity(context), context.revision || null, text]);
export const voiceReady = (draft, context, text) => !draft?.entries?.length || (draft.identity === voiceIdentity(context) && draft.reviewedRevision === voiceRevision(context, text));
export const voicePayload = draft => (draft?.entries || []).map(({ receipt, original_text, edited_text }) => ({ receipt, original_text, edited_text, reviewed: true }));
export const appendVoice = (text, segment) => text + (text ? "\n\n" : "") + segment;
// Only doctor-confirmed text enters tab recovery, never audio or unconfirmed responses.
// Restoring provenance always discards the approval and requires a new review.
export function cleanVoiceDraft(value) {
  if (value == null) return null;
  if (!Array.isArray(value.entries) || value.entries.length > 20 || typeof value.identity !== "string" || value.identity.length > 1200) throw Error("Invalid voice draft");
  const entries = value.entries.map(item => {
    for (const key of ["receipt", "original_text", "edited_text"]) if (typeof item[key] !== "string" || !item[key] || item[key].length > 4000) throw Error("Invalid voice provenance");
    return { receipt: item.receipt, original_text: item.original_text, edited_text: item.edited_text };
  });
  return { identity: value.identity, entries, reviewedRevision: null };
}

export async function sha256(text) {
  return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text))), b => b.toString(16).padStart(2, "0")).join("");
}
