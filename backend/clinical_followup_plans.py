"""CW-B14 clinician-entered plans, isolated from completed-contact KPIs."""
from contextlib import contextmanager
from datetime import date, datetime, time, timezone
import hashlib
import json
import os
import re
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, text
from db import SessionLocal
from models import Case, FollowUp, AuditLog

SCHEMA = 'clinical-followup-plans-cw-b14-v1'
SOURCE = 'clinical-followup-plans-cw-b14'
PREFIX = 'cw-b14-'
PLANNED, SUPERSEDED, WITHDRAWN = (PREFIX + s for s in ('planned', 'superseded', 'withdrawn'))
MAX_VERSIONS = 50
LOCAL = ZoneInfo('Asia/Shanghai')
HASH = re.compile(r'[a-f0-9]{64}\Z')
REQUEST = re.compile(r'[a-f0-9]{32}\Z')
FIELDS = ('patient_name', 'species', 'sex', 'age_info', 'breed', 'weight', 'coat_color',
          'owner_name', 'owner_phone', 'chief_complaint', 'history', 'exam_findings',
          'analysis', 'treatment', 'prognosis')
DATA_FIELDS = {'planned_date', 'purpose', 'items', 'return_conditions', 'note'}
META_FIELDS = {'schema', 'root_id', 'version', 'data', 'case_snapshot', 'reviewed_by',
               'reviewed_at', 'reason', 'withdrawal'}


class PlanError(Exception):
    def __init__(self, code, status=409):
        self.code, self.status = code, status
        super().__init__(code)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def ensure_enabled():
    if (os.getenv('FOLLOWUP_PLANS_ENABLED') != '1' or os.getenv('FOLLOWUP_PLANS_SYNTHETIC_ONLY') != '1'
            or os.getenv('ENVIRONMENT') not in {'test', 'development'} or os.getenv('RENDER', '').lower() == 'true'):
        raise PlanError('followup_plans_disabled', 503)


def namespace(status, channel):
    # channel is a source discriminator, never a claim that contact occurred.
    return or_(func.coalesce(status, '').startswith(PREFIX), func.coalesce(channel, '') == SOURCE)


def legacy_only(status, channel):
    return ~or_(namespace(status, channel), func.coalesce(status, '').startswith('cw-b19-'),
                func.coalesce(channel, '') == 'clinical-followup-contacts-cw-b19')


def today():
    return datetime.now(timezone.utc).astimezone(LOCAL).date().isoformat()


def literal(value, maximum, required=False):
    if (not isinstance(value, str) or len(value) > maximum or (required and not value.strip())
            or any(not (c in '\t\r\n' or 32 <= ord(c) <= 0xd7ff or 0xe000 <= ord(c) <= 0xfffd
                        or 0x10000 <= ord(c) <= 0x10ffff) or 127 <= ord(c) < 160 for c in value)):
        raise PlanError('followup_invalid_text', 422)
    return value


def due_date(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value):
        raise PlanError('followup_invalid_date', 422)
    try:
        parsed = date.fromisoformat(value)
        return datetime.combine(parsed, time.min, LOCAL).astimezone(timezone.utc).replace(tzinfo=None)
    except (ValueError, OverflowError):
        raise PlanError('followup_invalid_date', 422) from None


def validate_data(value):
    if not isinstance(value, dict) or set(value) != DATA_FIELDS:
        raise PlanError('followup_invalid_fields', 422)
    due_date(value['planned_date'])
    for key in ('purpose', 'return_conditions', 'note'):
        literal(value[key], 1000, key == 'purpose')
    if not isinstance(value['items'], list) or not 1 <= len(value['items']) <= 10:
        raise PlanError('followup_item_limit', 422)
    for item in value['items']: literal(item, 300, True)
    return value


def positive(value):
    return type(value) is int and 0 < value <= 2**53 - 1


def case_snapshot(case):
    return {'id': case.id, 'owner_id': case.owner_id, **{key: getattr(case, key) for key in FIELDS}}


@contextmanager
def transaction(uid, cid):
    # Fresh session: the JWT dependency may already have its own read transaction.
    with SessionLocal() as db:
        if db.get_bind().dialect.name == 'sqlite': db.execute(text('BEGIN IMMEDIATE'))
        case = db.query(Case).filter_by(id=cid, owner_id=uid).with_for_update().first()
        if case is None or case.deleted_at is not None: raise PlanError('case_not_found', 404)
        yield db, case


def timestamp(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None: raise ValueError('Missing timezone')
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def records(db, case):
    rows = db.query(FollowUp).filter(FollowUp.case_id == case.id, namespace(FollowUp.status, FollowUp.channel)).order_by(FollowUp.id).limit(MAX_VERSIONS + 1).all()
    return validated_records(rows, case)


def validated_records(rows, case):
    """Validate a complete, ID-ordered prefetched CW-B14 chain without I/O."""
    try:
        if len(rows) > MAX_VERSIONS: raise ValueError('Version limit')
        parsed, roots = [], {}
        for row in rows:
            meta = json.loads(row.note)
            if not isinstance(meta, dict) or set(meta) != META_FIELDS or meta['schema'] != SCHEMA: raise ValueError('Schema')
            if row.status not in {PLANNED, SUPERSEDED, WITHDRAWN} or row.channel != SOURCE or row.done_at is not None: raise ValueError('Lifecycle')
            if not positive(meta['root_id']) or not positive(meta['version']) or meta['version'] > MAX_VERSIONS: raise ValueError('Version')
            validate_data(meta['data']); literal(meta['reason'], 500, meta['version'] > 1)
            if row.due_date != due_date(meta['data']['planned_date']): raise ValueError('Date mismatch')
            snap = meta['case_snapshot']
            if (not isinstance(snap, dict) or set(snap) != {'id', 'owner_id', *FIELDS} or not positive(snap['id']) or snap['id'] != case.id
                    or not positive(snap['owner_id']) or any(snap[k] is not None and not isinstance(snap[k], str) for k in FIELDS)):
                raise ValueError('Case snapshot')
            if (not isinstance(meta['reviewed_by'], str) or meta['reviewed_by'] != str(snap['owner_id'])
                    or row.owner != meta['reviewed_by'] or timestamp(meta['reviewed_at']) != row.created_at): raise ValueError('Attribution')
            withdrawal = meta['withdrawal']
            if row.status == WITHDRAWN:
                if not isinstance(withdrawal, dict) or set(withdrawal) != {'reason', 'by', 'at'}: raise ValueError('Withdrawal')
                literal(withdrawal['reason'], 500, True)
                if not isinstance(withdrawal['by'], str) or not withdrawal['by'].isdigit() or int(withdrawal['by']) < 1: raise ValueError('Withdrawal account')
                if timestamp(withdrawal['at']) != row.updated_at: raise ValueError('Withdrawal time')
            elif withdrawal is not None: raise ValueError('Unexpected withdrawal')
            roots.setdefault(meta['root_id'], []).append((row, meta))
            parsed.append((row, meta))
        current = 0
        for root, versions in roots.items():
            if versions[0][0].id != root or [m['version'] for _, m in versions] != list(range(1, len(versions) + 1)): raise ValueError('Broken chain')
            if any(row.status != SUPERSEDED for row, _ in versions[:-1]) or versions[-1][0].status == SUPERSEDED: raise ValueError('Broken chain status')
            current += versions[-1][0].status == PLANNED
        if current > 1: raise ValueError('Multiple current plans')
        return parsed
    except (ValueError, TypeError, KeyError, AttributeError, PlanError, OverflowError):
        raise PlanError('followup_invalid_saved_data') from None


def public(row, meta, case):
    state = row.status.removeprefix(PREFIX)
    if state == 'planned' and meta['case_snapshot'] != case_snapshot(case): state = 'needs_review'
    token = digest({'id': row.id, 'case_id': row.case_id, 'status': row.status, 'meta': meta,
                    'due_date': row.due_date.isoformat(), 'updated_at': str(row.updated_at)})
    return {'id': row.id, 'root_id': meta['root_id'], 'version': meta['version'], 'state': state,
            'stored_state': row.status.removeprefix(PREFIX), 'token': token, 'data': meta['data'],
            'reviewed_by': meta['reviewed_by'], 'reviewed_at': meta['reviewed_at'], 'reason': meta['reason'],
            'withdrawal': meta['withdrawal'], 'case_snapshot': meta['case_snapshot']}


def listing_data(db, case):
    rows = records(db, case)
    value = {'schema': SCHEMA, 'case_id': case.id, 'case': case_snapshot(case), 'as_of_date': today(),
             'timezone': 'Asia/Shanghai', 'plans': [public(row, meta, case) for row, meta in rows],
             'limits': {'items': 10, 'versions': MAX_VERSIONS}, 'writes_database': False}
    value['case_token'] = digest(value['case'])
    value['state_token'] = digest(value)
    return value


def listing(uid, cid):
    ensure_enabled()
    with transaction(uid, cid) as (db, case): return listing_data(db, case)


def validate_request(body):
    keys = {'request_id', 'operation', 'plan_id', 'expected_plan_token', 'expected_case_token', 'expected_state_token', 'data', 'reason'}
    if not isinstance(body, dict) or set(body) != keys: raise PlanError('followup_invalid_fields', 422)
    if not isinstance(body['request_id'], str) or not REQUEST.fullmatch(body['request_id']): raise PlanError('followup_invalid_request', 422)
    if body['operation'] not in {'create', 'correct', 'withdraw'}: raise PlanError('followup_invalid_operation', 422)
    for key in ('expected_case_token', 'expected_state_token'):
        if not isinstance(body[key], str) or not HASH.fullmatch(body[key]): raise PlanError('followup_invalid_snapshot', 422)
    literal(body['reason'], 500, body['operation'] != 'create')
    if body['operation'] == 'create':
        if body['plan_id'] is not None or body['expected_plan_token'] != '' or body['reason'] != '': raise PlanError('followup_invalid_create', 422)
    elif not positive(body['plan_id']) or not isinstance(body['expected_plan_token'], str) or not HASH.fullmatch(body['expected_plan_token']):
        raise PlanError('followup_invalid_selection', 422)
    if body['operation'] == 'withdraw':
        if body['data'] is not None: raise PlanError('followup_invalid_withdraw', 422)
    else: validate_data(body['data'])


def build_preview(db, case, uid, body):
    validate_request(body)
    value = listing_data(db, case)
    before = None
    if body['operation'] != 'create':
        before = next((row for row in value['plans'] if row['id'] == body['plan_id']), None)
        if before is None: raise PlanError('followup_plan_not_found', 404)
    if body['expected_case_token'] != value['case_token'] or body['expected_state_token'] != value['state_token']:
        raise PlanError('followup_changed_review_again')
    if before:
        if before['token'] != body['expected_plan_token'] or before['stored_state'] != 'planned': raise PlanError('followup_version_changed')
    elif any(row['stored_state'] == 'planned' for row in value['plans']): raise PlanError('followup_current_plan_exists')
    if body['operation'] != 'withdraw' and len(value['plans']) >= MAX_VERSIONS: raise PlanError('followup_version_limit', 422)
    result = {'schema': SCHEMA, 'case_id': case.id, 'case': value['case'], 'as_of_date': value['as_of_date'],
              'timezone': value['timezone'], 'before': before, 'data': body['data'], 'operation': body['operation'],
              'reason': body['reason'], 'request_id': body['request_id'], 'writes_database': False,
              'case_token': value['case_token'], 'state_token': value['state_token']}
    result['preview_token'] = digest({'owner': uid, 'body': body, 'preview': result})
    return result


def preview(uid, cid, body):
    ensure_enabled()
    with transaction(uid, cid) as (db, case): return build_preview(db, case, uid, body)


def ledger_id(uid, cid, rid):
    if not isinstance(rid, str) or not REQUEST.fullmatch(rid): raise PlanError('followup_invalid_request', 422)
    return digest([SOURCE, str(uid), cid, rid])


def receipt(db, case, uid, rid, prior, fingerprint=None):
    try:
        meta = prior.extra_data
        if (prior.source != SOURCE or prior.case_id != case.id or prior.clinician_id != str(uid) or prior.request_id != rid
                or not isinstance(meta, dict) or set(meta) != {'schema', 'fingerprint', 'record_id', 'version', 'operation'}
                or meta['schema'] != SCHEMA or not HASH.fullmatch(meta['fingerprint'])
                or meta['operation'] not in {'create', 'correct', 'withdraw'} or not positive(meta['record_id']) or not positive(meta['version'])
                or prior.action_taken != meta['operation'] or prior.event_type != 'followup_plan_' + meta['operation']): raise ValueError('Receipt')
        if fingerprint is not None and meta['fingerprint'] != fingerprint: raise PlanError('followup_request_payload_changed')
        found = next(((row, m) for row, m in records(db, case) if row.id == meta['record_id'] and m['version'] == meta['version']), None)
        if found is None: raise ValueError('Receipt record')
        return {'schema': SCHEMA, 'case_id': case.id, 'request_id': rid, 'state': 'committed',
                'operation': meta['operation'], 'plan': public(*found, case), 'writes_database': False}
    except (ValueError, TypeError, KeyError, AttributeError):
        raise PlanError('followup_invalid_saved_data') from None


def append_audit(db, uid, cid, body, fingerprint, row, meta):
    db.add(AuditLog(log_id=ledger_id(uid, cid, body['request_id']), request_id=body['request_id'],
        clinician_id=str(uid), case_id=cid, source=SOURCE, event_type='followup_plan_' + body['operation'],
        action_taken=body['operation'], note=body['reason'], extra_data={'schema': SCHEMA, 'fingerprint': fingerprint,
        'record_id': row.id, 'version': meta['version'], 'operation': body['operation']}))


def commit(uid, cid, body, token):
    ensure_enabled(); validate_request(body)
    if not isinstance(token, str) or not HASH.fullmatch(token): raise PlanError('followup_invalid_snapshot', 422)
    fingerprint = digest({'body': body, 'preview_token': token})
    with transaction(uid, cid) as (db, case):
        prior = db.get(AuditLog, ledger_id(uid, cid, body['request_id']))
        if prior: return receipt(db, case, uid, body['request_id'], prior, fingerprint)
        checked = build_preview(db, case, uid, body)
        if checked['preview_token'] != token: raise PlanError('followup_changed_review_again')
        old = db.get(FollowUp, body['plan_id']) if body['plan_id'] is not None else None
        now = datetime.now(timezone.utc); naive = now.replace(tzinfo=None)
        if body['operation'] == 'withdraw':
            row = old; meta = json.loads(row.note)
            meta['withdrawal'] = {'reason': body['reason'], 'by': str(uid), 'at': now.isoformat()}
            row.status = WITHDRAWN
        else:
            before = checked['before']
            if old: old.status = SUPERSEDED; old.updated_at = naive
            meta = {'schema': SCHEMA, 'root_id': before['root_id'] if before else None,
                    'version': before['version'] + 1 if before else 1, 'data': body['data'],
                    'case_snapshot': checked['case'], 'reviewed_by': str(uid), 'reviewed_at': now.isoformat(),
                    'reason': body['reason'], 'withdrawal': None}
            row = FollowUp(case_id=cid, due_date=due_date(body['data']['planned_date']), done_at=None,
                           channel=SOURCE, owner=str(uid), status=PLANNED, created_at=naive, updated_at=naive)
            db.add(row); db.flush()
            if before is None: meta['root_id'] = row.id
        row.note = json.dumps(meta, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        row.updated_at = naive
        append_audit(db, uid, cid, body, fingerprint, row, meta)
        db.flush()
        # Validate the complete chain before committing both record and audit.
        records(db, case)
        result = {'schema': SCHEMA, 'case_id': cid, 'request_id': body['request_id'], 'state': 'committed',
                  'operation': body['operation'], 'plan': public(row, meta, case), 'writes_database': True}
        db.commit()
        return result


def status(uid, cid, rid):
    ensure_enabled()
    key = ledger_id(uid, cid, rid)
    with transaction(uid, cid) as (db, case):
        prior = db.get(AuditLog, key)
        if prior: return receipt(db, case, uid, rid, prior)
        # An unreadable chain is not evidence that a write did not happen.
        records(db, case)
        return {'schema': SCHEMA, 'case_id': cid, 'request_id': rid, 'state': 'not_committed', 'writes_database': False}
