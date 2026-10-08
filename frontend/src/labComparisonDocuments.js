import { comparisonRules, itemSelection, validateComparison, validatePreview } from './labComparison';
export const documentComparisonSchema = 'clinical-lab-comparison-documents-cw-b13-v1';
const rowFields = ['id', 'root_id', 'version', 'token', 'title', 'reviewed_by', 'reviewed_at', 'source', 'report'];
const canonical = value => JSON.stringify(value, function (_key, v) {
  return v && typeof v === 'object' && !Array.isArray(v) ? Object.fromEntries(Object.keys(v).sort().map(k => [k, v[k]])) : v;
});
export function documentSelection(saved, request, preview) {
  validateComparison(saved, saved.case_id); validatePreview(preview, saved, request);
  if (!preview.can_calculate || request.doctor_confirmed !== true) throw Error('请先核实方法与采样条件，并取得可比预览。');
  const side = key => {
    const row = saved.reports.find(r => r.id === request[key].id);
    const item = row?.items.find(i => canonical(itemSelection(row, i)) === canonical(request[key]));
    if (!row || !item) throw Error('已选版本无法确认，请重新选择。');
    return { ...Object.fromEntries(rowFields.map(k => [k, row[k]])), item };
  };
  return JSON.parse(JSON.stringify({ request, expected: {
    schema: documentComparisonSchema, rules: comparisonRules, case_id: saved.case_id,
    selection: request, a: side('a'), b: side('b'), result: {
      can_calculate: preview.can_calculate, reasons: preview.reasons, delta: preview.delta, reference_changed: preview.reference_changed,
    },
  } }));
}
export function validDocumentComparison(payload, choice, caseId) {
  if (!choice) return payload === undefined;
  return choice.expected?.case_id === caseId && payload?.schema === documentComparisonSchema &&
    canonical(payload) === canonical(choice.expected);
}
