import api from './api';
import { draftOwner } from './consultDraft';
import { same, validData as validPlan } from './followupPlan';
import { validData as validContact } from './followupContacts';
import { schema as planSchema, query as planQuery, validQueue as validPlans, message as planMessage } from './followupPlanQueue';

export const schema = 'clinical-followup-contact-queue-cw-b23-v1';
export const contactStates = { all: '全部登记情况', current: '有本版计划登记', historical_only: '仅历史计划有登记', none: '暂无有效登记' };
const keys = (v, names) => v !== null && typeof v === 'object' && !Array.isArray(v) && Object.keys(v).sort().join('|') === [...names].sort().join('|');
const id = n => Number.isSafeInteger(n) && n > 0;
const version = n => id(n) && n <= 50;
const account = s => typeof s === 'string' && /^[1-9][0-9]*$/.test(s);
const stamp = s => typeof s === 'string' && /(Z|[+-]\d\d:\d\d)$/.test(s) && Number.isFinite(Date.parse(s));
const fields = ['patient_name', 'species', 'sex', 'age_info', 'breed', 'owner_name'];
const identity = (v, cid) => keys(v, ['id', ...fields]) && id(cid) && v.id === cid && fields.every(k => v[k] === null || typeof v[k] === 'string');
const reason = (s, n) => typeof s === 'string' && [...s].length <= 500 && (n === 1 || Boolean(s.trim())) && !/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f\ud800-\udfff\ufffe\uffff]/u.test(s);
export const limits = { cases: 200, versions: 10000, per_case: 50, contact_versions: 10000, contact_per_case: 50, audits: 20000, audits_per_case: 100 };

function validRecord(r, cid, plan, current) {
  if (!keys(r, ['id','root_id','version','state','token','data','recorded_by','recorded_at','reason','case','source']) ||
      !id(r.id) || !id(r.root_id) || r.root_id > r.id || !version(r.version) || (r.version === 1 && r.root_id !== r.id) ||
      r.state !== 'recorded' || typeof r.token !== 'string' || !/^[a-f0-9]{64}$/.test(r.token) || !validContact(r.data) ||
      !account(r.recorded_by) || !stamp(r.recorded_at) || !reason(r.reason, r.version) || !identity(r.case, cid)) return false;
  const s = r.source;
  if (!keys(s, ['id','root_id','version','data','reviewed_by','reviewed_at','case','state']) ||
      !id(s.id) || !id(s.root_id) || s.root_id > s.id || !version(s.version) || (s.version === 1 && s.root_id !== s.id) ||
      !validPlan(s.data) || !identity(s.case, cid) || !account(s.reviewed_by) || !stamp(s.reviewed_at) ||
      !['planned','needs_review','superseded','withdrawn'].includes(s.state)) return false;
  const matches = ['id','root_id','version'].every(k => s[k] === plan[k]);
  return current ? matches && s.state === plan.state && same(s.data, plan.data) && s.reviewed_by === plan.reviewed_by && s.reviewed_at === plan.reviewed_at
    : !matches && ['superseded','withdrawn'].includes(s.state);
}

export function query(filter, state = 'all', page = 1, size = 20, snapshot = null) {
  return { ...planQuery(filter, page, size, snapshot), include_followup_contacts: 'true', contact_state: state };
}

export function validQueue(v, filter, state, page, size, snapshot = null) {
  if (!v || v.schema !== schema || !Object.hasOwn(contactStates, state) ||
      !same(v.limits, limits) || !keys(v.filters, ['range','start','end','state','contact_state']) || v.filters.contact_state !== state || !Array.isArray(v.items)) return false;
  const { contact_state: _, ...baseFilters } = v.filters;
  const base = { ...v, schema: planSchema, filters: baseFilters, limits: { cases: 200, versions: 10000, per_case: 50 },
    items: v.items.map(item => ({ case: item?.case, plan: item?.plan })) };
  if (!validPlans(base, filter, page, size, snapshot)) return false;
  for (const item of v.items) {
    const g = item.contacts;
    if (!keys(item, ['case','plan','contacts']) || !keys(g, ['counts','latest']) || !keys(g.counts, ['current','historical']) || !keys(g.latest, ['current','historical'])) return false;
    const c = g.counts;
    if (!Object.values(c).every(n => Number.isInteger(n) && n >= 0 && n <= 50) || c.current + c.historical > 50) return false;
    for (const key of ['current','historical']) {
      if (c[key] === 0 ? g.latest[key] !== null : !validRecord(g.latest[key], item.case.id, item.plan, key === 'current')) return false;
    }
    if (g.latest.current && g.latest.historical && g.latest.current.root_id === g.latest.historical.root_id) return false;
    if (state === 'current' && c.current === 0 || state === 'historical_only' && (c.current !== 0 || c.historical === 0) || state === 'none' && c.current + c.historical !== 0) return false;
  }
  return true;
}

export async function readQueue(token, params, signal) {
  return (await api.get('/api/followup-plan-queue', { params, signal, timeout: 30000, expectedAuthOwner: draftOwner(token) })).data;
}
export const contactLocation = (cid, r) => `/cases/${cid}?followup_contact=${r.id}&followup_contact_version=${r.version}`;
export const sourceLocation = (cid, r) => `/cases/${cid}?followup_plan=${r.source.id}&followup_version=${r.source.version}`;
export function message(error) {
  return ({ followup_contact_queue_disabled: '人工随访清单暂未启用。', followup_contacts_disabled: '人工随访记录暂未启用。',
    followup_contact_queue_scale_limit: '联系记录超过本次试用规模上限，无法提供完整清单。',
    contact_invalid_saved_data: '联系、来源或审计记录异常，无法完整读取清单。' })[error?.response?.data?.detail] || planMessage(error);
}
