import { cleanDiarrheaDraft, appendDiarrheaHistory } from "./diarrheaIntakeState";
export const INTAKE_LABELS = { diarrhea: "腹泻", appetite_weight: "食欲下降／消瘦", polyuria_polydipsia: "多饮多尿", cough_breathing: "咳嗽／呼吸困难", syncope_seizure: "晕厥／抽搐" };
export const intakeKey = draft => draft?.template?.key || "diarrhea";
export function cleanIntakeDraft(value) {
  if (value == null) return null;
  const key = intakeKey(value);
  if (key === "diarrhea") return cleanDiarrheaDraft(value);
  const version = value.template?.version;
  if (!Object.hasOwn(INTAKE_LABELS, key) || typeof version !== "string" || !version.startsWith(key + "-intake-") || value.binding?.intakeKey !== key) throw Error("Invalid intake binding");
  // Reuse M7's raw text/state/size validation; preserve the distinct family in the result.
  const clean = cleanDiarrheaDraft({ ...value, template: { ...value.template, version: version.replace(key + "-intake-", "diarrhea-intake-") } });
  return { ...clean, template: { ...clean.template, key, version }, binding: { ...clean.binding, intakeKey: key } };
}
export const intakeSignature = value => JSON.stringify(cleanIntakeDraft(value));
export const intakeContextMatches = (draft, context) => !!draft && intakeKey(draft) === (context.intakeKey || "diarrhea") && Object.keys(draft.binding).every(key => draft.binding[key] === context[key]);
export function intakeRequest(draft) {
  const d = cleanIntakeDraft(draft);
  return { version: d.template.version, fingerprint: d.template.fingerprint, species: d.template.species, answers: d.answers };
}
export const intakeReviewed = (draft, review, context) => !!review && intakeContextMatches(draft, context) && review.signature === intakeSignature(draft);
export { appendDiarrheaHistory as appendIntakeHistory };
