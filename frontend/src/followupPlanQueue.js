import api from './api';
import { draftOwner } from './consultDraft';
import { validData, same } from './followupPlan';

export const schema = 'clinical-followup-plan-queue-cw-b18-v1';
export const initialFilter = () => ({ range: 'today', state: 'all', start: '', end: '' });
export const shanghaiDate = (now = new Date()) => new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit' }).format(now);
const id = n => Number.isSafeInteger(n) && n > 0;
const hash = s => typeof s === 'string' && /^[a-f0-9]{64}$/.test(s);
const keys = (v, names) => v && typeof v === 'object' && !Array.isArray(v) && Object.keys(v).sort().join('|') === [...names].sort().join('|');
const stamp = s => typeof s === 'string' && /(Z|[+-]\d\d:\d\d)$/.test(s) && Number.isFinite(Date.parse(s));
export function calendar(s) {
  if (typeof s !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(s) || s < '0001-01-01') return false;
  const d = new Date(s + 'T00:00:00Z'); return Number.isFinite(+d) && d.toISOString().slice(0, 10) === s;
}
export function dateBounds(filter, today) {
  if (!calendar(today) || !['today', 'next7', 'past', 'all', 'custom'].includes(filter.range) || !['all', 'planned', 'needs_review'].includes(filter.state)) return null;
  let start = null, end = null;
  const add = n => { const d = new Date(today + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };
  if (filter.range === 'custom') {
    if (!calendar(filter.start) || !calendar(filter.end) || filter.start > filter.end) return null;
    start = filter.start; end = filter.end;
  }
  if (['today', 'next7'].includes(filter.range)) { start = today; end = filter.range === 'today' ? today : today > '9999-12-25' ? '9999-12-31' : add(6); }
  if (filter.range === 'past') end = today > '0001-01-01' ? add(-1) : null;
  return { range: filter.range, start, end, state: filter.state };
}
export function query(filter, page = 1, pageSize = 20, snapshot = null) {
  const params = { range: filter.range, state: filter.state, page, page_size: pageSize };
  if (filter.range === 'custom') { params.start = filter.start; params.end = filter.end; }
  if (snapshot) params.snapshot = snapshot;
  return params;
}
export function validQueue(v, filter, page, size, snapshot = null) {
  if (!(keys(v, ['schema','as_of_date','timezone','read_at','filters','page','page_size','total','items','snapshot','limits','writes_database']) &&
      v.schema === schema && calendar(v.as_of_date) && v.timezone === 'Asia/Shanghai' && stamp(v.read_at) && shanghaiDate(new Date(v.read_at)) === v.as_of_date &&
      same(v.filters, dateBounds(filter, v.as_of_date)) && v.page === page && v.page_size === size && id(page) && id(size) && size <= 50 &&
      Number.isInteger(v.total) && v.total >= 0 && v.total <= 200 && hash(v.snapshot) && (!snapshot || snapshot === v.snapshot) &&
      same(v.limits, { cases: 200, versions: 10000, per_case: 50 }) && v.writes_database === false && Array.isArray(v.items) &&
      v.items.length === Math.min(size, Math.max(0, v.total - (page - 1) * size)))) return false;
  const identities = ['patient_name','species','sex','age_info','breed','owner_name'];
  const seen = new Set(); let previous = null;
  for (const item of v.items) {
    if (!keys(item, ['case','plan']) || !keys(item.case, ['id', ...identities]) || !id(item.case.id) || seen.has(item.case.id) || !identities.every(k => item.case[k] === null || typeof item.case[k] === 'string')) return false;
    seen.add(item.case.id); const p = item.plan;
    if (!(keys(p, ['id','root_id','version','state','data','reviewed_by','reviewed_at','reason']) && id(p.id) && id(p.root_id) && id(p.version) && p.version <= 50 &&
        ['planned','needs_review'].includes(p.state) && validData(p.data) && typeof p.reviewed_by === 'string' && /^[1-9]\d*$/.test(p.reviewed_by) && stamp(p.reviewed_at) &&
        typeof p.reason === 'string' && [...p.reason].length <= 500 && (p.version === 1 || p.reason.trim()))) return false;
    const day = p.data.planned_date, f = v.filters;
    if ((f.start && day < f.start) || (f.end && day > f.end) || (f.range === 'past' && day >= v.as_of_date) || (f.state !== 'all' && p.state !== f.state)) return false;
    const order = [day, item.case.id, p.id];
    if (previous && (order[0] < previous[0] || (order[0] === previous[0] && order[1] <= previous[1]))) return false;
    previous = order;
  }
  return true;
}
export const planLocation = item => `/cases/${item.case.id}?followup_plan=${item.plan.id}&followup_version=${item.plan.version}`;
export async function readQueue(token, params, signal) {
  if (!token || localStorage.getItem('token') !== token) throw Error('登录账号已变化，请重新读取。');
  const result = await api.get('/api/followup-plan-queue', { params, signal, timeout: 30000, expectedAuthOwner: draftOwner(token) });
  if (localStorage.getItem('token') !== token) throw Error('登录账号已变化，请重新读取。');
  return result.data;
}
export function message(error) {
  const code = error?.response?.data?.detail;
  return ({ followup_plan_queue_disabled: '复查计划清单暂未启用。', followup_plans_disabled: '复查计划暂未启用。',
    followup_invalid_saved_data: '保存记录结构异常，清单无法完整读取，请核对记录。', followup_queue_scale_limit: '已超过本次试用规模上限，无法提供完整清单。',
    followup_queue_snapshot_changed: '病例、计划或日期已变化，正在重新读取第 1 页。', followup_queue_database_unavailable: '清单服务暂不可用，请重试读取。' })[code] ||
    (error?.response?.status === 401 ? '登录已失效，请重新登录。' : error?.response?.status === 422 ? '请核对日期范围和分页条件。' : '清单读取失败，请重试读取。');
}
