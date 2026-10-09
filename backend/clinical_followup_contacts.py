"""CW-B19: clinician-recorded contacts, never a claim of completed clinical review."""
from datetime import datetime, timezone
import json
import os
import re

from sqlalchemy import func, or_
from models import FollowUp, AuditLog
import clinical_followup_plans as plans

SCHEMA = 'clinical-followup-contacts-cw-b19-v1'
SOURCE = 'clinical-followup-contacts-cw-b19'
PREFIX = 'cw-b19-'
RECORDED, SUPERSEDED, WITHDRAWN = (PREFIX + s for s in ('recorded', 'superseded', 'withdrawn'))
MAX_VERSIONS = 50
METHODS = {'phone', 'wechat', 'in_person', 'other'}
OUTCOMES = {'reached', 'not_reached', 'declined', 'other'}
DATA_FIELDS = {'occurred_at', 'method', 'outcome', 'note', 'next_action'}
SOURCE_FIELDS = ('id', 'root_id', 'version', 'data', 'case_snapshot', 'reviewed_by', 'reviewed_at')
META_FIELDS = {'schema', 'root_id', 'version', 'source', 'data', 'case_snapshot', 'recorded_by',
               'recorded_at', 'reason', 'withdrawal'}
BODY_FIELDS = {'request_id', 'operation', 'contact_id', 'expected_contact_token', 'source_plan_id',
               'source_plan_version', 'expected_source_token', 'expected_case_token', 'expected_state_token', 'data', 'reason'}
Error = plans.PlanError


def ensure_enabled():
    if (os.getenv('FOLLOWUP_CONTACTS_ENABLED') != '1' or os.getenv('FOLLOWUP_CONTACTS_SYNTHETIC_ONLY') != '1'
            or os.getenv('ENVIRONMENT') not in {'test', 'development'} or os.getenv('RENDER', '').lower() == 'true'):
        raise Error('followup_contacts_disabled', 503)
    plans.ensure_enabled()


def namespace(status, channel):
    return or_(func.coalesce(status, '').startswith(PREFIX), func.coalesce(channel, '') == SOURCE)


def contact_time(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}\+08:00', value):
        raise Error('contact_invalid_time', 422)
    try:
        return datetime.fromisoformat(value).astimezone(timezone.utc).replace(tzinfo=None)
    except (ValueError, OverflowError):
        raise Error('contact_invalid_time', 422) from None


def validate_data(value, incoming=False):
    if not isinstance(value, dict) or set(value) != DATA_FIELDS:
        raise Error('contact_invalid_fields', 422)
    when = contact_time(value['occurred_at'])
    if incoming and when > datetime.now(timezone.utc).replace(tzinfo=None, second=0, microsecond=0):
        raise Error('contact_future_time', 422)
    if not isinstance(value['method'], str) or value['method'] not in METHODS or not isinstance(value['outcome'], str) or value['outcome'] not in OUTCOMES:
        raise Error('contact_invalid_choice', 422)
    plans.literal(value['note'], 2000, True)
    plans.literal(value['next_action'], 1000)
    return value


def frozen_source(plan):
    return {key: plan[key] for key in SOURCE_FIELDS}


def valid_case(snapshot, cid):
    return (isinstance(snapshot, dict) and set(snapshot) == {'id', 'owner_id', *plans.FIELDS}
            and plans.positive(snapshot['id']) and snapshot['id'] == cid and plans.positive(snapshot['owner_id'])
            and all(snapshot[k] is None or isinstance(snapshot[k], str) for k in plans.FIELDS))


def immutable_hash(meta):
    return plans.digest({k: v for k, v in meta.items() if k != 'withdrawal'})


def ledger_id(uid, cid, rid):
    if not isinstance(rid, str) or not plans.REQUEST.fullmatch(rid):
        raise Error('contact_invalid_request', 422)
    return plans.digest([SOURCE, str(uid), cid, rid])


def records(db, case, sources):
    """Validate all bounded records and their audit receipts; no silent filtering/repair."""
    rows = db.query(FollowUp).filter(FollowUp.case_id == case.id, namespace(FollowUp.status, FollowUp.channel)).order_by(FollowUp.id).limit(MAX_VERSIONS + 1).all()
    audits = db.query(AuditLog).filter_by(case_id=case.id, source=SOURCE).order_by(AuditLog.log_id).limit(MAX_VERSIONS * 2 + 1).all()
    try:
        if len(rows) > MAX_VERSIONS or len(audits) > MAX_VERSIONS * 2: raise ValueError('Limit')
        parsed, roots, by_id = [], {}, {}
        for row in rows:
            meta = json.loads(row.note)
            if not isinstance(meta, dict) or set(meta) != META_FIELDS or meta['schema'] != SCHEMA: raise ValueError('Schema')
            if row.case_id != case.id or row.channel != SOURCE or row.status not in {RECORDED, SUPERSEDED, WITHDRAWN} or row.done_at is not None: raise ValueError('Namespace')
            if not plans.positive(meta['root_id']) or not plans.positive(meta['version']) or meta['version'] > MAX_VERSIONS: raise ValueError('Version')
            validate_data(meta['data']); plans.literal(meta['reason'], 500, meta['version'] > 1)
            if not valid_case(meta['case_snapshot'], case.id): raise ValueError('Case')
            if (meta['recorded_by'] != str(meta['case_snapshot']['owner_id']) or row.owner != meta['recorded_by']
                    or plans.timestamp(meta['recorded_at']) != row.created_at): raise ValueError('Attribution')
            source = meta['source']
            if not isinstance(source, dict) or set(source) != set(SOURCE_FIELDS) or not plans.positive(source['id']): raise ValueError('Source')
            current = next((p for p in sources if p['id'] == source['id']), None)
            if current is None or source != frozen_source(current): raise ValueError('Source content')
            if row.due_date != plans.due_date(source['data']['planned_date']): raise ValueError('Due date')
            withdrawal = meta['withdrawal']
            if row.status == WITHDRAWN:
                if not isinstance(withdrawal, dict) or set(withdrawal) != {'reason', 'by', 'at'}: raise ValueError('Withdrawal')
                plans.literal(withdrawal['reason'], 500, True)
                if not isinstance(withdrawal['by'], str) or not re.fullmatch(r'[1-9][0-9]*', withdrawal['by']): raise ValueError('Withdrawal account')
                if plans.timestamp(withdrawal['at']) != row.updated_at: raise ValueError('Withdrawal time')
            elif withdrawal is not None: raise ValueError('Unexpected withdrawal')
            roots.setdefault(meta['root_id'], []).append((row, meta))
            parsed.append((row, meta)); by_id[row.id] = (row, meta)
        for root, versions in roots.items():
            if versions[0][0].id != root: raise ValueError('Root')
            for i, (row, meta) in enumerate(versions):
                if meta['version'] != i + 1 or meta['source'] != versions[0][1]['source']: raise ValueError('Chain source/version')
                if (row.status == SUPERSEDED) != (i < len(versions) - 1): raise ValueError('Chain lifecycle')
        events = {}
        for audit in audits:
            info = audit.extra_data
            if not isinstance(info, dict) or set(info) != {'schema', 'fingerprint', 'record_id', 'version', 'operation', 'content_hash'}: raise ValueError('Audit')
            if info['schema'] != SCHEMA or not isinstance(info['fingerprint'], str) or not plans.HASH.fullmatch(info['fingerprint']): raise ValueError('Fingerprint')
            if not plans.positive(info['record_id']) or not plans.positive(info['version']) or info['record_id'] not in by_id: raise ValueError('Orphan audit')
            row, meta = by_id[info['record_id']]
            op = info['operation']
            if op not in {'create', 'correct', 'withdraw'} or info['version'] != meta['version'] or info['content_hash'] != immutable_hash(meta): raise ValueError('Audit content')
            if audit.log_id != ledger_id(audit.clinician_id, case.id, audit.request_id) or audit.event_type != 'followup_contact_' + op or audit.action_taken != op: raise ValueError('Receipt binding')
            if op == 'withdraw':
                if meta['withdrawal'] is None or audit.clinician_id != meta['withdrawal']['by'] or audit.note != meta['withdrawal']['reason'] or audit.created_at != plans.timestamp(meta['withdrawal']['at']): raise ValueError('Withdrawal audit')
            elif (op != ('create' if meta['version'] == 1 else 'correct') or audit.clinician_id != meta['recorded_by']
                  or audit.note != meta['reason'] or audit.created_at != row.created_at): raise ValueError('Creation audit')
            events.setdefault(row.id, []).append(op)
        for row, meta in parsed:
            expected = ['create' if meta['version'] == 1 else 'correct'] + (['withdraw'] if row.status == WITHDRAWN else [])
            if sorted(events.get(row.id, [])) != sorted(expected): raise ValueError('Missing/duplicate receipt')
        return parsed
    except (ValueError, TypeError, KeyError, AttributeError, Error, OverflowError):
        raise Error('contact_invalid_saved_data') from None


def public(row, meta, sources):
    source = next(p for p in sources if p['id'] == meta['source']['id'])
    return {'id': row.id, 'root_id': meta['root_id'], 'version': meta['version'], 'state': row.status.removeprefix(PREFIX),
            'token': plans.digest({'id': row.id, 'case_id': row.case_id, 'status': row.status, 'meta': meta, 'updated_at': str(row.updated_at)}),
            **{k: meta[k] for k in ('source', 'data', 'case_snapshot', 'recorded_by', 'recorded_at', 'reason', 'withdrawal')},
            'source_state': source['state']}


def listing_data(db, case):
    plan_list = plans.listing_data(db, case)
    sources = plan_list['plans']
    value = {'schema': SCHEMA, 'case_id': case.id, 'case': plans.case_snapshot(case),
             'as_of_date': plan_list['as_of_date'], 'timezone': 'Asia/Shanghai', 'plans': sources,
             'records': [public(r, m, sources) for r, m in records(db, case, sources)],
             'limits': {'versions': MAX_VERSIONS}, 'writes_database': False, 'case_token': plan_list['case_token']}
    value['state_token'] = plans.digest(value)
    return value


def listing(uid, cid):
    ensure_enabled()
    with plans.transaction(uid, cid) as (db, case): return listing_data(db, case)


def validate_request(body):
    if not isinstance(body, dict) or set(body) != BODY_FIELDS: raise Error('contact_invalid_fields', 422)
    ledger_id(1, 1, body['request_id'])
    if body['operation'] not in {'create', 'correct', 'withdraw'}: raise Error('contact_invalid_operation', 422)
    for key in ('expected_case_token', 'expected_state_token', 'expected_source_token'):
        if not isinstance(body[key], str) or not plans.HASH.fullmatch(body[key]): raise Error('contact_invalid_snapshot', 422)
    if not plans.positive(body['source_plan_id']) or not plans.positive(body['source_plan_version']): raise Error('contact_invalid_source', 422)
    plans.literal(body['reason'], 500, body['operation'] != 'create')
    if body['operation'] == 'create':
        if body['contact_id'] is not None or body['expected_contact_token'] != '' or body['reason'] != '': raise Error('contact_invalid_create', 422)
    elif not plans.positive(body['contact_id']) or not isinstance(body['expected_contact_token'], str) or not plans.HASH.fullmatch(body['expected_contact_token']):
        raise Error('contact_invalid_selection', 422)
    if body['operation'] == 'withdraw':
        if body['data'] is not None: raise Error('contact_invalid_withdraw', 422)
    else: validate_data(body['data'])


def build_preview(db, case, uid, body):
    validate_request(body)
    value = listing_data(db, case)
    if body['expected_case_token'] != value['case_token'] or body['expected_state_token'] != value['state_token']:
        raise Error('contact_changed_review_again')
    source = next((p for p in value['plans'] if p['id'] == body['source_plan_id'] and p['version'] == body['source_plan_version']), None)
    if source is None: raise Error('contact_source_not_found', 404)
    if source['token'] != body['expected_source_token']: raise Error('contact_source_changed')
    before = None
    if body['operation'] == 'create':
        if source['state'] != 'planned': raise Error('contact_source_not_current')
    else:
        before = next((r for r in value['records'] if r['id'] == body['contact_id']), None)
        if before is None: raise Error('contact_not_found', 404)
        if before['token'] != body['expected_contact_token'] or before['state'] != 'recorded': raise Error('contact_version_changed')
        if before['source'] != frozen_source(source): raise Error('contact_cannot_rebind_source')
    if body['operation'] != 'withdraw':
        validate_data(body['data'], incoming=True)
        if len(value['records']) >= MAX_VERSIONS: raise Error('contact_version_limit', 422)
    result = {'schema': SCHEMA, 'case_id': case.id, 'case': value['case'], 'as_of_date': value['as_of_date'],
              'timezone': value['timezone'], 'before': before, 'source': frozen_source(source), 'source_state': source['state'],
              'data': body['data'], 'operation': body['operation'], 'reason': body['reason'], 'request_id': body['request_id'],
              'writes_database': False, 'case_token': value['case_token'], 'state_token': value['state_token']}
    result['preview_token'] = plans.digest({'owner': uid, 'body': body, 'preview': result})
    return result


def preview(uid, cid, body):
    ensure_enabled()
    with plans.transaction(uid, cid) as (db, case): return build_preview(db, case, uid, body)


def receipt(db, case, uid, rid, prior, fingerprint=None):
    value = listing_data(db, case)  # also validates every stored receipt, including this one
    if prior.source != SOURCE or prior.case_id != case.id or prior.clinician_id != str(uid) or prior.request_id != rid:
        raise Error('contact_invalid_saved_data')
    info = prior.extra_data
    if fingerprint is not None and fingerprint != info['fingerprint']: raise Error('contact_request_payload_changed')
    result = next((r for r in value['records'] if r['id'] == info['record_id'] and r['version'] == info['version']), None)
    if result is None: raise Error('contact_invalid_saved_data')
    return {'schema': SCHEMA, 'case_id': case.id, 'request_id': rid, 'state': 'committed',
            'operation': info['operation'], 'record': result, 'writes_database': False}


def append_audit(db, uid, cid, body, fingerprint, row, meta, now):
    db.add(AuditLog(log_id=ledger_id(uid, cid, body['request_id']), request_id=body['request_id'], clinician_id=str(uid),
        case_id=cid, source=SOURCE, event_type='followup_contact_' + body['operation'], action_taken=body['operation'],
        note=body['reason'], created_at=now, extra_data={'schema': SCHEMA, 'fingerprint': fingerprint,
        'record_id': row.id, 'version': meta['version'], 'operation': body['operation'], 'content_hash': immutable_hash(meta)}))


def commit(uid, cid, body, token):
    ensure_enabled(); validate_request(body)
    if not isinstance(token, str) or not plans.HASH.fullmatch(token): raise Error('contact_invalid_snapshot', 422)
    fingerprint = plans.digest({'body': body, 'preview_token': token})
    with plans.transaction(uid, cid) as (db, case):
        prior = db.get(AuditLog, ledger_id(uid, cid, body['request_id']))
        if prior: return receipt(db, case, uid, body['request_id'], prior, fingerprint)
        checked = build_preview(db, case, uid, body)
        if checked['preview_token'] != token: raise Error('contact_changed_review_again')
        old = db.get(FollowUp, body['contact_id']) if body['contact_id'] is not None else None
        now = datetime.now(timezone.utc); naive = now.replace(tzinfo=None)
        if body['operation'] == 'withdraw':
            row = old; meta = json.loads(row.note)
            meta['withdrawal'] = {'reason': body['reason'], 'by': str(uid), 'at': now.isoformat()}
            row.status = WITHDRAWN
        else:
            before = checked['before']
            if old: old.status = SUPERSEDED; old.updated_at = naive
            meta = {'schema': SCHEMA, 'root_id': before['root_id'] if before else None,
                    'version': before['version'] + 1 if before else 1, 'source': checked['source'], 'data': body['data'],
                    'case_snapshot': checked['case'], 'recorded_by': str(uid), 'recorded_at': now.isoformat(),
                    'reason': body['reason'], 'withdrawal': None}
            row = FollowUp(case_id=cid, due_date=plans.due_date(meta['source']['data']['planned_date']), done_at=None,
                           channel=SOURCE, owner=str(uid), status=RECORDED, created_at=naive, updated_at=naive)
            db.add(row); db.flush()
            if before is None: meta['root_id'] = row.id
        row.note = json.dumps(meta, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        row.updated_at = naive
        append_audit(db, uid, cid, body, fingerprint, row, meta, naive)
        db.flush()
        value = listing_data(db, case)
        result = {'schema': SCHEMA, 'case_id': cid, 'request_id': body['request_id'], 'state': 'committed',
                  'operation': body['operation'], 'record': next(r for r in value['records'] if r['id'] == row.id), 'writes_database': True}
        db.commit()
        return result


def status(uid, cid, rid):
    ensure_enabled()
    key = ledger_id(uid, cid, rid)
    with plans.transaction(uid, cid) as (db, case):
        prior = db.get(AuditLog, key)
        if prior: return receipt(db, case, uid, rid, prior)
        listing_data(db, case)
        return {'schema': SCHEMA, 'case_id': cid, 'request_id': rid, 'state': 'not_committed', 'writes_database': False}
