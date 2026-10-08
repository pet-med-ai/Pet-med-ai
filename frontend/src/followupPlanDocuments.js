import { followupClient, same, validList, validPlan } from './followupPlan';

export const documentPlanSchema = 'clinical-followup-plan-documents-cw-b15-v1';
export async function readDocumentPlans(caseId, token, signal) {
  const value = await followupClient(caseId, token, signal)('get');
  if (!validList(value, caseId)) throw Error('复查计划数据不完整，暂不能纳入文书。');
  return value;
}
export function documentPlanSelection(list, row) {
  if (!validList(list, list?.case_id) || !validPlan(row, list.case_id) || row.state !== 'planned' ||
      !list.plans.some(p => same(p, row))) throw Error('该计划不是当前有效版本，请刷新后重新核对。');
  const request = { id: row.id, version: row.version, token: row.token };
  return structuredClone({ request, expected: {
    schema: documentPlanSchema, case_id: list.case_id, timezone: 'Asia/Shanghai', selection: request, plan: row,
  } });
}
export function validDocumentPlan(payload, choice, caseId) {
  if (!choice) return payload === undefined;
  return choice.expected?.case_id === caseId && choice.expected?.schema === documentPlanSchema &&
    choice.expected?.timezone === 'Asia/Shanghai' && validPlan(choice.expected.plan, caseId) &&
    choice.expected.plan.state === 'planned' && same(choice.request, choice.expected.selection) &&
    same(choice.request, {id:choice.expected.plan.id, version:choice.expected.plan.version, token:choice.expected.plan.token}) &&
    same(payload, choice.expected);
}
