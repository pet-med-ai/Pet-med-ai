import {contactClient, validList, validRecord, same} from './followupContacts';

export const documentContactSchema = 'clinical-followup-contact-documents-cw-b21-v1';
export async function readDocumentContacts(caseId, token, signal) {
  const value = await contactClient(caseId, token, signal)('get');
  if (!validList(value, caseId)) throw Error('随访记录或来源不完整，暂不能纳入文书。');
  return value;
}
export function documentContactSelection(list, row) {
  if (!validList(list, list?.case_id) || !validRecord(row, list.case_id) || row.state !== 'recorded' ||
      !list.records.some(r => same(r, row))) throw Error('该随访不是当前有效版本，请刷新后重新核对。');
  const source = list.plans.find(p => p.id === row.source.id);
  const request = {id:row.id, version:row.version, token:row.token, source_token:source.token, case_token:list.case_token};
  return structuredClone({request, expected:{schema:documentContactSchema, case_id:list.case_id,
    timezone:'Asia/Shanghai', selection:request, case:list.case, record:row}});
}
export function validDocumentContact(payload, choice, caseId) {
  if (!choice) return payload === undefined;
  if (!payload || typeof payload !== 'object' || Array.isArray(payload) ||
      typeof payload.audit_token !== 'string' || !/^[a-f0-9]{64}$/.test(payload.audit_token)) return false;
  const {audit_token, ...facts} = payload;
  return choice.expected?.case_id === caseId && choice.expected.schema === documentContactSchema &&
    choice.expected.timezone === 'Asia/Shanghai' && validRecord(choice.expected.record, caseId) &&
    choice.expected.record.state === 'recorded' && same(choice.request, choice.expected.selection) &&
    same(facts, choice.expected);
}
