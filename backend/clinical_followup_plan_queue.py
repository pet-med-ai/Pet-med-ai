"""CW-B18: bounded, account-owned follow-up plans in one read-only snapshot."""
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
import os
import re

from sqlalchemy import exists, select, text
from db import SessionLocal
from models import Case, FollowUp
import clinical_followup_plans as plans

SCHEMA = 'clinical-followup-plan-queue-cw-b18-v1'
MAX_CASES, MAX_ROWS = 200, 10000
IDENTITY = ('patient_name', 'species', 'sex', 'age_info', 'breed', 'owner_name')
PARAMS = {'range', 'start', 'end', 'state', 'page', 'page_size', 'snapshot'}


def ensure_enabled():
    if (os.getenv('FOLLOWUP_PLAN_QUEUE_ENABLED') != '1'
            or os.getenv('FOLLOWUP_PLAN_QUEUE_SYNTHETIC_ONLY') != '1'
            or os.getenv('ENVIRONMENT') not in {'test', 'development'}
            or os.getenv('RENDER', '').lower() == 'true'):
        raise plans.PlanError('followup_plan_queue_disabled', 503)
    plans.ensure_enabled()


def calendar(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value):
        raise plans.PlanError('followup_queue_invalid_date', 422)
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise plans.PlanError('followup_queue_invalid_date', 422) from None


def integer(value, maximum):
    if not isinstance(value, str) or not re.fullmatch(r'[1-9][0-9]{0,6}', value) or int(value) > maximum:
        raise plans.PlanError('followup_queue_invalid_page', 422)
    return int(value)


def filters(params, today):
    if set(params) - PARAMS: raise plans.PlanError('followup_queue_invalid_parameters', 422)
    mode, state = params.get('range', 'today'), params.get('state', 'all')
    if mode not in {'today', 'next7', 'past', 'custom', 'all'} or state not in {'all', 'planned', 'needs_review'}:
        raise plans.PlanError('followup_queue_invalid_filter', 422)
    if mode == 'custom':
        start, end = calendar(params.get('start')), calendar(params.get('end'))
        if start > end: raise plans.PlanError('followup_queue_invalid_date_range', 422)
    else:
        if 'start' in params or 'end' in params: raise plans.PlanError('followup_queue_invalid_filter', 422)
        start = today if mode in {'today', 'next7'} else None
        end = (min(today + timedelta(days=min(6, (date.max-today).days)), date.max) if mode == 'next7'
               else today if mode == 'today' else today-timedelta(days=1) if mode == 'past' and today > date.min else None)
    page = integer(params.get('page', '1'), 1000000)
    size = integer(params.get('page_size', '20'), 50)
    snapshot = params.get('snapshot')
    if snapshot is not None and (not isinstance(snapshot, str) or not plans.HASH.fullmatch(snapshot)):
        raise plans.PlanError('followup_queue_invalid_snapshot', 422)
    if page > 1 and snapshot is None: raise plans.PlanError('followup_queue_snapshot_required', 422)
    return {'range': mode, 'start': start.isoformat() if start else None,
            'end': end.isoformat() if end else None, 'state': state}, page, size, snapshot


@contextmanager
def read_transaction():
    # A fresh session isolates this transaction from the JWT account lookup.
    with SessionLocal() as db:
        dialect = db.get_bind().dialect.name
        if dialect == 'postgresql':
            db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
            db.execute(text('SET TRANSACTION READ ONLY'))
        elif dialect == 'sqlite':
            # Explicit BEGIN is required: sqlite legacy mode doesn't begin on SELECT.
            db.execute(text('BEGIN'))
        else:
            raise plans.PlanError('followup_queue_database_unsupported', 503)
        yield db
        # Session close rolls back this read-only transaction; never commits.


def owned_cases(db, uid):
    has_plan = exists(select(FollowUp.id).where(FollowUp.case_id == Case.id,
                                               plans.namespace(FollowUp.status, FollowUp.channel)))
    return db.query(Case).filter(Case.owner_id == uid, Case.deleted_at.is_(None), has_plan).order_by(Case.id).limit(MAX_CASES+1).all()


def prefetched_rows(db, cases):
    return db.query(FollowUp).filter(FollowUp.case_id.in_([case.id for case in cases]),
        plans.namespace(FollowUp.status, FollowUp.channel)).order_by(FollowUp.id).limit(MAX_ROWS+1).all()


def listing(uid, params):
    ensure_enabled()
    now = datetime.now(timezone.utc)
    today = now.astimezone(plans.LOCAL).date()
    selected, page, size, expected = filters(params, today)
    with read_transaction() as db:
        cases = owned_cases(db, uid)
        if len(cases) > MAX_CASES: raise plans.PlanError('followup_queue_scale_limit', 409)
        rows = prefetched_rows(db, cases) if cases else []
        if len(rows) > MAX_ROWS: raise plans.PlanError('followup_queue_scale_limit', 409)
        by_case = {case.id: [] for case in cases}
        for row in rows: by_case[row.case_id].append(row)
        items, fingerprint = [], []
        for case in cases:
            parsed = plans.validated_records(by_case[case.id], case)
            public = [plans.public(row, meta, case) for row, meta in parsed]
            fingerprint.append({'case': plans.case_snapshot(case), 'plans': [p['token'] for p in public]})
            for plan in public:
                if plan['stored_state'] != 'planned': continue
                items.append({'case': {'id': case.id, **{key: getattr(case, key) for key in IDENTITY}},
                    'plan': {key: plan[key] for key in ('id', 'root_id', 'version', 'state', 'data', 'reviewed_by', 'reviewed_at', 'reason')}})
        snapshot = plans.digest({'schema': SCHEMA, 'owner': uid, 'date': today.isoformat(),
            'filters': selected, 'page_size': size, 'records': fingerprint})
        if expected is not None and expected != snapshot: raise plans.PlanError('followup_queue_snapshot_changed', 409)
        items.sort(key=lambda item: (item['plan']['data']['planned_date'], item['case']['id'], item['plan']['id']))
        def matches(item):
            day = item['plan']['data']['planned_date']
            return ((selected['range'] != 'past' or day < today.isoformat())
                    and (selected['start'] is None or day >= selected['start'])
                    and (selected['end'] is None or day <= selected['end'])
                    and (selected['state'] == 'all' or item['plan']['state'] == selected['state']))
        matched = [item for item in items if matches(item)]
        return {'schema': SCHEMA, 'as_of_date': today.isoformat(), 'timezone': 'Asia/Shanghai',
            'read_at': now.isoformat(), 'filters': selected, 'page': page, 'page_size': size,
            'total': len(matched), 'items': matched[(page-1)*size:page*size], 'snapshot': snapshot,
            'limits': {'cases': MAX_CASES, 'versions': MAX_ROWS, 'per_case': plans.MAX_VERSIONS},
            'writes_database': False}
