// Only raw clinician input is recoverable. Reviews and save receipts stay in memory.
export const DIARRHEA_STATES = ["unfilled", "not_asked", "observed", "absent", "uncertain", "unobservable"];
const plain = v => !!v && typeof v === "object" && !Array.isArray(v);
const str = (v, max) => typeof v === "string" && v.length <= max;
export function cleanDiarrheaDraft(value) {
  if (value == null) return null;
  const t = value.template, b = value.binding;
  if (!plain(value) || !plain(t) || !plain(b) || !plain(value.answers) ||
      !str(t.version, 100) || !t.version.startsWith("diarrhea-intake-") || !/^[a-f0-9]{64}$/.test(t.fingerprint) ||
      !["dog", "cat"].includes(t.species) || !Array.isArray(t.questions) || !t.questions.length || t.questions.length > 50 ||
      !str(b.owner, 320) || !b.owner || !str(b.patientName, 100000) || b.species !== t.species ||
      !(b.sessionId === null || str(b.sessionId, 200))) throw Error("Invalid diarrhea draft");
  const seen = new Set();
  const questions = t.questions.map(q => {
    if (!plain(q) || !str(q.key, 100) || !q.key || seen.has(q.key) || !str(q.label, 300) ||
        !["text", "presence"].includes(q.kind) || (q.when && !seen.has(q.when))) throw Error("Invalid diarrhea question");
    seen.add(q.key);
    return { key: q.key, label: q.label, kind: q.kind, ...(q.when ? { when: q.when } : {}) };
  });
  if (Object.keys(value.answers).some(key => !seen.has(key))) throw Error("Unknown diarrhea answer");
  const answers = Object.fromEntries(questions.map(q => {
    const a = value.answers[q.key] ?? { state: "unfilled", text: "" };
    if (!plain(a) || !DIARRHEA_STATES.includes(a.state) || (a.state === "absent" && q.kind !== "presence") || !str(a.text, 6000)) throw Error("Invalid diarrhea answer");
    return [q.key, { state: a.state, text: a.text }];
  }));
  if (Object.values(answers).reduce((n, a) => n + a.text.length, 0) > 40000) throw Error("Diarrhea draft too large");
  return { template: { version: t.version, fingerprint: t.fingerprint, species: t.species, questions },
    binding: { owner: b.owner, patientName: b.patientName, species: b.species, sessionId: b.sessionId }, answers };
}
export const diarrheaSignature = value => JSON.stringify(cleanDiarrheaDraft(value));
export const diarrheaContextMatches = (draft, context) => !!draft && Object.keys(draft.binding).every(key => draft.binding[key] === context[key]);
export function diarrheaRequest(draft) {
  const d = cleanDiarrheaDraft(draft);
  return { version: d.template.version, fingerprint: d.template.fingerprint, species: d.template.species, answers: d.answers };
}
export function diarrheaReviewed(draft, review, context) {
  return !!review && diarrheaContextMatches(draft, context) && review.signature === diarrheaSignature(draft);
}
export function appendDiarrheaHistory(history, block) {
  if (!block || ("\n\n" + (history || "") + "\n\n").includes("\n\n" + block + "\n\n")) return history || "";
  return (history || "") + (history ? "\n\n" : "") + block;
}
