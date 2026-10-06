"""CW-B7 manual laboratory records. Exact source text; no interpretation or ingestion."""
from datetime import datetime
from decimal import Decimal, InvalidOperation
import os
import re
from sqlalchemy import inspect, or_
from models import Case, DiagnosticReport, Observation, AuditLog
from case_attachment_store import Store, AttachmentError, digest, ensure_enabled as attachments_enabled
import case_attachment_service as attachments

SOURCE = 'manual-lab-cw-b7'
SCHEMA = 'manual-lab-cw-b7-v1'
IDENTITY_FIELDS = ('patient_name', 'species', 'sex', 'breed', 'coat_color', 'owner_name')
MAX_ITEMS, MAX_REPORTS, MAX_VERSIONS = 100, 20, 20
REPORT_FIELDS = {'title', 'panel', 'specimen', 'collected_at', 'reported_at', 'laboratory', 'device', 'note'}
ROW_FIELDS = {'name', 'result_type', 'value', 'unit', 'reference', 'reference_low', 'reference_high', 'reference_unit', 'flag', 'position', 'checked'}
NUM = re.compile(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d{1,3})?\Z')


def ensure_enabled():
    attachments_enabled()
    if os.getenv('MANUAL_LAB_RESULTS_ENABLED') != '1' or os.getenv('MANUAL_LAB_RESULTS_SYNTHETIC_ONLY') != '1':
        raise AttachmentError('manual_lab_disabled', 503)


def legacy_only(column):
    return or_(column.is_(None), column != SOURCE)


def is_manual(row):
    return row.source_type == SOURCE or (row.metadata_json or {}).get('schema') == SCHEMA


def reject_legacy(row):
    if is_manual(row):
        raise AttachmentError('manual_lab_use_dedicated_review', 409)


def identity(case):
    return {key: getattr(case, key) for key in IDENTITY_FIELDS}


def text(value, limit=255, required=False):
    if not isinstance(value, str) or len(value) > limit or any(ord(c) < 32 and c not in '\n\r\t' for c in value):
        raise AttachmentError('invalid_manual_lab_text', 422)
    if required and not value.strip(): raise AttachmentError('manual_lab_required_field', 422)
    return value


def decimal_string(raw):
    if not NUM.fullmatch(raw) or len(raw) > 50:
        raise AttachmentError('invalid_manual_lab_number', 422)
    try:
        value = Decimal(raw)
        if not value.is_finite() or abs(value.adjusted()) > 100: raise InvalidOperation()
    except InvalidOperation:
        raise AttachmentError('invalid_manual_lab_number', 422) from None
    return str(value)


def validate(data):
    if not isinstance(data, dict) or set(data) != {'report', 'items'}: raise AttachmentError('invalid_manual_lab_payload', 422)
    report, rows = data['report'], data['items']
    if not isinstance(report, dict) or set(report) != REPORT_FIELDS: raise AttachmentError('invalid_manual_lab_report', 422)
    report = {k: text(v, 1000 if k == 'note' else 150, k == 'title') for k, v in report.items()}
    if report['panel'] not in {'cbc', 'chemistry', 'urine', 'mixed', 'other'}: raise AttachmentError('invalid_manual_lab_panel', 422)
    for key in ('collected_at', 'reported_at'):
        if report[key]:
            try:
                if datetime.fromisoformat(report[key].replace('Z', '+00:00')).tzinfo is None: raise ValueError()
            except ValueError: raise AttachmentError('invalid_manual_lab_date', 422) from None
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_ITEMS: raise AttachmentError('manual_lab_item_limit', 422)
    output = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != ROW_FIELDS or row['checked'] is not True:
            raise AttachmentError('manual_lab_check_every_item', 422)
        item = {k: text(v, 255, k in {'name', 'position'}) for k,v in row.items() if k != 'checked'}
        if len(item['unit']) > 50 or len(item['reference_unit']) > 50: raise AttachmentError('invalid_manual_lab_unit', 422)
        kind, raw = item['result_type'], item['value']
        parsed, comparator = None, None
        if kind == 'number': parsed = decimal_string(raw)
        elif kind == 'comparison':
            match = re.fullmatch(r'(<=|>=|<|>|≤|≥)\s*(.+)', raw)
            if not match: raise AttachmentError('invalid_manual_lab_number', 422)
            comparator, parsed = match[1], decimal_string(match[2])
        elif kind == 'text': text(raw, required=True)
        elif kind in {'not_tested', 'not_provided'}:
            if raw: raise AttachmentError('manual_lab_missing_value_conflict', 422)
        else: raise AttachmentError('invalid_manual_lab_result_type', 422)
        low = decimal_string(item['reference_low']) if item['reference_low'] else None
        high = decimal_string(item['reference_high']) if item['reference_high'] else None
        if low is not None or high is not None:
            if not item['reference'].strip(): raise AttachmentError('manual_lab_reference_original_required', 422)
            if not item['unit'].strip() or item['unit'] != item['reference_unit']: raise AttachmentError('manual_lab_reference_unit_conflict', 422)
            if low is not None and high is not None and Decimal(low) > Decimal(high): raise AttachmentError('manual_lab_reference_order', 422)
        output.append({**item, 'checked': True, 'decimal': parsed, 'comparator': comparator,
                       'reference_low_decimal': low, 'reference_high_decimal': high})
    return {'report': report, 'items': output}


def input_data(data):
    return {'report': data['report'], 'items': [{k: row[k] for k in ROW_FIELDS} for row in data['items']]}


def reports(db, cid):
    return db.query(DiagnosticReport).filter_by(case_id=cid, source_type=SOURCE).order_by(DiagnosticReport.id).all()


def report_token(row):
    return digest({'id': row.id, 'status': row.status, 'data': row.metadata_json})


def _source(store, case, aid):
    item = attachments.find(case, aid, active=True)
    if item['metadata']['kind'] != 'lab': raise AttachmentError('manual_lab_source_not_lab', 409)
    store.verified(item)
    return item


def effective(store, case, row):
    if row.status != 'confirmed': return row.status
    meta = row.metadata_json
    if meta['identity'] != identity(case): return 'needs_review'
    try: item = _source(store, case, row.attachment_ref)
    except (AttachmentError, OSError): return 'source_unavailable'
    return 'confirmed' if digest(attachments.public(item)) == meta['source_digest'] else 'needs_review'


def public(store, case, row):
    meta = row.metadata_json
    return {'id': row.id, 'root_id': meta['root_id'], 'version': meta['version'], 'state': effective(store, case, row),
            'stored_state': row.status, 'token': report_token(row), 'attachment_id': row.attachment_ref,
            'data': meta['data'], 'source': meta['source_snapshot'], 'identity': meta['identity'],
            'reason': meta.get('reason', ''), 'reviewed_by': row.reviewed_by, 'reviewed_at': str(row.reviewed_at),
            'invalidated_reason': meta.get('invalidated_reason', '')}


def _state(store, db, case):
    rows = reports(db, case.id)
    return {**attachments.case_view(case), 'reports': [public(store, case, row) for row in rows],
            'sources': [attachments.public(a) for a in case.attachments or [] if attachments.known(a) and a.get('state') == 'active' and a.get('metadata', {}).get('kind') == 'lab'],
            'limits': {'items': MAX_ITEMS, 'reports': MAX_REPORTS, 'versions': MAX_VERSIONS}}


def listing(uid, cid):
    ensure_enabled(); store = Store()
    with store.locked(), attachments.transaction(uid, cid) as (db, case): return _state(store, db, case)


def _get(db, case, rid):
    row = db.query(DiagnosticReport).filter_by(id=rid, case_id=case.id, source_type=SOURCE).first()
    if row is None: raise AttachmentError('manual_lab_not_found', 404)
    return row


def _preview(store, db, case, uid, body):
    if body['expected_case_token'] != attachments.case_token(case): raise AttachmentError('case_changed_review_again')
    attachments.request_id(body['request_id'])
    operation = body['operation']; old = None
    if operation != 'create':
        old = _get(db, case, body['report_id'])
        if report_token(old) != body['expected_report_token'] or old.status in {'superseded', 'withdrawn'}:
            raise AttachmentError('manual_lab_version_changed')
        if old.attachment_ref != body['attachment_id']: raise AttachmentError('manual_lab_source_changed')
        text(body['reason'], 500, True)
    elif body['report_id'] is not None or body['expected_report_token']:
        raise AttachmentError('invalid_manual_lab_create', 422)
    rows = reports(db, case.id)
    if operation == 'withdraw':
        if body['data'] is not None: raise AttachmentError('invalid_manual_lab_withdraw', 422)
        data = None; source = old.metadata_json['source_snapshot']
    else:
        data = validate(body['data']); source = attachments.public(_source(store, case, body['attachment_id']))
        if operation == 'create':
            if any(r.attachment_ref == body['attachment_id'] for r in rows): raise AttachmentError('manual_lab_report_exists')
            if sum(r.status not in {'superseded', 'withdrawn'} for r in rows) >= MAX_REPORTS: raise AttachmentError('manual_lab_report_limit', 422)
        else:
            if old.metadata_json['version'] >= MAX_VERSIONS: raise AttachmentError('manual_lab_version_limit', 422)
            if any(r.metadata_json['root_id'] == old.metadata_json['root_id'] and r.id > old.id for r in rows): raise AttachmentError('manual_lab_version_changed')
    state = {'case': attachments.case_view(case), 'identity': identity(case), 'source': source,
             'before': public(store, case, old) if old else None, 'data': data, 'operation': operation, 'reason': body['reason']}
    return {**state, 'preview_token': digest({'body': body, 'owner': uid, 'state': state})}


def preview(uid, cid, body):
    ensure_enabled(); store = Store()
    with store.locked(), attachments.transaction(uid, cid) as (db, case): return _preview(store, db, case, uid, body)


def ledger_id(uid, cid, request_id): return digest([SOURCE, str(uid), cid, attachments.request_id(request_id)])


def append_audit(db, uid, case, body, fingerprint, row, before):
    db.add(AuditLog(log_id=ledger_id(uid, case.id, body['request_id']), request_id=body['request_id'],
        clinician_id=str(uid), case_id=case.id, event_type='manual_lab_' + body['operation'], action_taken=body['operation'],
        source=SOURCE, extra_data={'fingerprint': fingerprint, 'report_id': row.id,
        'before_id': before.id if before else None, 'reason': body['reason'], 'version': row.metadata_json['version']}))


def commit(uid, cid, body, token):
    ensure_enabled(); store = Store(); fingerprint = digest({'body': body, 'token': token})
    with store.locked(), attachments.transaction(uid, cid) as (db, case):
        prior = db.get(AuditLog, ledger_id(uid, cid, body['request_id']))
        if prior:
            if prior.source != SOURCE or prior.extra_data['fingerprint'] != fingerprint: raise AttachmentError('request_payload_changed')
            row = _get(db, case, prior.extra_data['report_id'])
            return {'state': 'committed', 'report': public(store, case, row)}
        review = _preview(store, db, case, uid, body)
        if token != review['preview_token']: raise AttachmentError('review_changed')
        old = _get(db, case, body['report_id']) if body['report_id'] is not None else None
        now = datetime.utcnow()
        if body['operation'] == 'withdraw':
            row = old; row.status = 'withdrawn'
            row.metadata_json = {**row.metadata_json, 'reason': body['reason'], 'withdrawn_by': str(uid), 'withdrawn_at': now.isoformat()}
            db.query(Observation).filter_by(diagnostic_report_id=row.id, source_type=SOURCE).update({'review_status': 'withdrawn'})
        else:
            if old:
                old.status = 'superseded'
                db.query(Observation).filter_by(diagnostic_report_id=old.id, source_type=SOURCE).update({'review_status': 'superseded'})
            data = review['data']; meta = data['report']
            row = DiagnosticReport(case_id=cid, report_type=meta['panel'], source_type=SOURCE, title=meta['title'],
                status='confirmed', reviewed_by=str(uid), reviewed_at=now, attachment_ref=body['attachment_id'],
                source_system=meta['laboratory'][:100], metadata_json={'schema': SCHEMA, 'data': data, 'identity': identity(case),
                'source_snapshot': review['source'], 'source_digest': digest(review['source']), 'reason': body['reason'],
                'version': old.metadata_json['version'] + 1 if old else 1, 'root_id': old.metadata_json['root_id'] if old else None})
            db.add(row); db.flush()
            if old is None: row.metadata_json = {**row.metadata_json, 'root_id': row.id}
            for pos, item in enumerate(data['items']):
                db.add(Observation(case_id=cid, diagnostic_report_id=row.id, display_name=item['name'], value_text=item['value'],
                    value_type=item['result_type'], unit=item['unit'], reference_text=item['reference'], source_type=SOURCE,
                    review_status='confirmed', specimen_type=meta['specimen'][:100],
                    metadata_json={'schema': SCHEMA, 'row': pos, 'original': item}))
        row.updated_at = now
        append_audit(db, uid, case, body, fingerprint, row, old)
        db.commit()
        return {'state': 'committed', 'report': public(store, case, row)}


def status(uid, cid, request_id):
    ensure_enabled(); store = Store()
    with store.locked(), attachments.transaction(uid, cid) as (db, case):
        prior = db.get(AuditLog, ledger_id(uid, cid, request_id))
        if prior is None: return {'state': 'not_committed'}
        if prior.source != SOURCE: raise AttachmentError('request_payload_changed')
        return {'state': 'committed', 'report': public(store, case, _get(db, case, prior.extra_data['report_id']))}


def invalidate(db, case, *, attachment_id=None, reason):
    """Inside caller's case transaction, including when the feature is switched off."""
    if os.getenv('ENVIRONMENT') not in {'test', 'development'} or os.getenv('RENDER', '').lower() == 'true': return
    if not inspect(db.connection()).has_table(DiagnosticReport.__tablename__): return
    query = db.query(DiagnosticReport).filter_by(case_id=case.id, source_type=SOURCE, status='confirmed')
    if attachment_id is not None: query = query.filter_by(attachment_ref=attachment_id)
    for row in query.all():
        row.status = 'needs_review'
        row.metadata_json = {**row.metadata_json, 'invalidated_reason': reason}
        db.query(Observation).filter_by(diagnostic_report_id=row.id, source_type=SOURCE).update({'review_status': 'needs_review'})
        event_id = digest([SOURCE, 'invalidate', row.id, row.metadata_json['version'], reason])
        db.add(AuditLog(log_id=event_id, request_id=event_id[:32],
            clinician_id=str(case.owner_id), case_id=case.id, event_type='manual_lab_invalidate', source=SOURCE,
            action_taken='invalidate', extra_data={'report_id': row.id, 'reason': reason}))


def invalidate_identity(db, case, changes):
    if any(k in changes and changes[k] != getattr(case, k) for k in IDENTITY_FIELDS):
        invalidate(db, case, reason='case_identity_changed')
