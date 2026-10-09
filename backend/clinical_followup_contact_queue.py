"""CW-B23: explicitly selected contact facts in one bounded read-only plan queue."""
from datetime import datetime, timezone
import os

from models import FollowUp, AuditLog
import clinical_followup_plans as plans
import clinical_followup_contacts as contacts
import clinical_followup_plan_queue as queue

SCHEMA = 'clinical-followup-contact-queue-cw-b23-v1'
MAX_CONTACTS, MAX_AUDITS = 10000, 20000
CONTACT_STATES = {'all', 'current', 'historical_only', 'none'}
LIMITS = {'cases': queue.MAX_CASES, 'versions': queue.MAX_ROWS, 'per_case': plans.MAX_VERSIONS,
          'contact_versions': MAX_CONTACTS, 'contact_per_case': contacts.MAX_VERSIONS,
          'audits': MAX_AUDITS, 'audits_per_case': contacts.MAX_VERSIONS * 2}


def ensure_enabled():
    if (os.getenv('FOLLOWUP_CONTACT_QUEUE_ENABLED') != '1'
            or os.getenv('FOLLOWUP_CONTACT_QUEUE_SYNTHETIC_ONLY') != '1'
            or os.getenv('ENVIRONMENT') not in {'test', 'development'}
            or os.getenv('RENDER', '').lower() == 'true'):
        raise plans.PlanError('followup_contact_queue_disabled', 503)
    queue.ensure_enabled()
    contacts.ensure_enabled()


def prefetched_contacts(db, cases):
    return db.query(FollowUp).filter(FollowUp.case_id.in_([c.id for c in cases]),
        contacts.namespace(FollowUp.status, FollowUp.channel)).order_by(FollowUp.id).limit(MAX_CONTACTS + 1).all()


def prefetched_audits(db, cases):
    return db.query(AuditLog).filter(AuditLog.case_id.in_([c.id for c in cases]),
        AuditLog.source == contacts.SOURCE).order_by(AuditLog.log_id).limit(MAX_AUDITS + 1).all()


def identity(value):
    return {key: value[key] for key in ('id', *queue.IDENTITY)}


def summary(record):
    source = record['source']
    return {**{key: record[key] for key in ('id', 'root_id', 'version', 'state', 'token', 'data',
            'recorded_by', 'recorded_at', 'reason')}, 'case': identity(record['case_snapshot']),
            'source': {**{key: source[key] for key in ('id', 'root_id', 'version', 'data', 'reviewed_by', 'reviewed_at')},
                       'case': identity(source['case_snapshot']), 'state': record['source_state']}}


def audit_fingerprint(row):
    # ORM attribute keys include extra_data (SQL column name is metadata).
    return {field.key: (value.isoformat() if isinstance(value, datetime) else value)
            for field in AuditLog.__mapper__.column_attrs for value in [getattr(row, field.key)]}


def listing(uid, params):
    ensure_enabled()
    params = dict(params)
    if params.pop('include_followup_contacts', None) != 'true':
        raise plans.PlanError('followup_queue_invalid_parameters', 422)
    state = params.pop('contact_state', 'all')
    if state not in CONTACT_STATES: raise plans.PlanError('followup_queue_invalid_filter', 422)
    now = queue.datetime.now(timezone.utc)
    today = now.astimezone(plans.LOCAL).date()
    selected, page, size, expected = queue.filters(params, today)
    selected = {**selected, 'contact_state': state}
    with queue.read_transaction() as db:
        cases = queue.owned_cases(db, uid)
        if len(cases) > queue.MAX_CASES: raise plans.PlanError('followup_queue_scale_limit', 409)
        plan_rows = queue.prefetched_rows(db, cases) if cases else []
        if len(plan_rows) > queue.MAX_ROWS: raise plans.PlanError('followup_queue_scale_limit', 409)
        contact_rows = prefetched_contacts(db, cases) if cases else []
        if len(contact_rows) > MAX_CONTACTS: raise plans.PlanError('followup_contact_queue_scale_limit', 409)
        audits = prefetched_audits(db, cases) if cases else []
        if len(audits) > MAX_AUDITS: raise plans.PlanError('followup_contact_queue_scale_limit', 409)
        grouped = {c.id: [[], [], []] for c in cases}
        for group, rows in enumerate((plan_rows, contact_rows, audits)):
            for row in rows:
                if row.case_id not in grouped: raise plans.PlanError('contact_invalid_saved_data', 409)
                grouped[row.case_id][group].append(row)
        items, fingerprint = [], []
        for case in cases:
            pr, cr, ar = grouped[case.id]
            sources = [plans.public(row, meta, case) for row, meta in plans.validated_records(pr, case)]
            records = [contacts.public(row, meta, sources)
                       for row, meta in contacts.validated_records(cr, ar, case, sources)]
            fingerprint.append({'case': plans.case_snapshot(case), 'plans': [p['token'] for p in sources],
                                'contacts': [r['token'] for r in records], 'audits': [audit_fingerprint(a) for a in ar]})
            for plan in sources:
                if plan['stored_state'] != 'planned': continue
                groups = {'current': [], 'historical': []}
                for record in records:
                    if record['state'] != 'recorded': continue
                    current = all(record['source'][key] == plan[key] for key in ('id', 'root_id', 'version'))
                    groups['current' if current else 'historical'].append(record)
                counts = {key: len(values) for key, values in groups.items()}
                latest = {key: summary(max(values, key=lambda r: (contacts.contact_time(r['data']['occurred_at']), r['id'])))
                          if values else None for key, values in groups.items()}
                items.append({'case': identity(plans.case_snapshot(case)),
                    'plan': {key: plan[key] for key in ('id', 'root_id', 'version', 'state', 'data', 'reviewed_by', 'reviewed_at', 'reason')},
                    'contacts': {'counts': counts, 'latest': latest}})
        snapshot = plans.digest({'schema': SCHEMA, 'owner': uid, 'date': today.isoformat(), 'filters': selected,
                                  'page_size': size, 'records': fingerprint})
        if expected is not None and expected != snapshot: raise plans.PlanError('followup_queue_snapshot_changed', 409)
        items.sort(key=lambda item: (item['plan']['data']['planned_date'], item['case']['id'], item['plan']['id']))
        def matches(item):
            day, count = item['plan']['data']['planned_date'], item['contacts']['counts']
            return ((selected['range'] != 'past' or day < today.isoformat())
                and (selected['start'] is None or day >= selected['start'])
                and (selected['end'] is None or day <= selected['end'])
                and (selected['state'] == 'all' or item['plan']['state'] == selected['state'])
                and (state == 'all' or (state == 'current' and count['current'] > 0)
                     or (state == 'historical_only' and count['current'] == 0 and count['historical'] > 0)
                     or (state == 'none' and count['current'] + count['historical'] == 0)))
        matched = [item for item in items if matches(item)]
        return {'schema': SCHEMA, 'as_of_date': today.isoformat(), 'timezone': 'Asia/Shanghai', 'read_at': now.isoformat(),
                'filters': selected, 'page': page, 'page_size': size, 'total': len(matched),
                'items': matched[(page - 1) * size:page * size], 'snapshot': snapshot, 'limits': LIMITS.copy(),
                'writes_database': False}
