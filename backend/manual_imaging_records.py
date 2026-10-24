"""CW-B9 source-bound, clinician-entered imaging records. No image interpretation."""
from copy import deepcopy
from datetime import datetime, timezone
import os
from sqlalchemy import inspect, or_
from models import ImagingStudy, AuditLog
from case_attachment_store import Store, AttachmentError, digest, ensure_enabled as attachments_enabled
import case_attachment_service as attachments
from manual_lab_results import IDENTITY_FIELDS, identity

SOURCE = 'manual-imaging-cw-b9'
SCHEMA = 'manual-imaging-cw-b9-v1'
MAX_REPORTS, MAX_VERSIONS = 20, 20
TEXT_LIMITS = {'title': 150, 'modality': 20, 'body_part': 100, 'taken_at': 40, 'institution': 150,
               'findings': 5000, 'impression': 5000, 'limitations': 1000, 'note': 1000, 'position': 255}
CHECKS = {'checked_findings', 'checked_impression'}


def ensure_enabled():
    attachments_enabled()
    if os.getenv('MANUAL_IMAGING_ENABLED') != '1' or os.getenv('MANUAL_IMAGING_SYNTHETIC_ONLY') != '1':
        raise AttachmentError('manual_imaging_disabled', 503)


def legacy_only(column):
    return or_(column.is_(None), column != SOURCE)


def is_manual(row):
    return row.source_type == SOURCE or (row.extra_data or {}).get('schema') == SCHEMA


def text(value, limit, required=False):
    if not isinstance(value, str) or len(value) > limit or any(
        not (c in '\t\r\n' or '\x20' <= c <= '\ud7ff' or '\ue000' <= c <= '\ufffd' or '\U00010000' <= c <= '\U0010ffff') for c in value
    ): raise AttachmentError('invalid_manual_imaging_text', 422)
    if required and not value.strip(): raise AttachmentError('manual_imaging_required_field', 422)
    return value


def taken_at(value):
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if result.tzinfo is None or result.utcoffset() is None: raise ValueError()
        return result.astimezone(timezone.utc).replace(tzinfo=None)
    except (ValueError, OverflowError): raise AttachmentError('invalid_manual_imaging_date', 422) from None


def validate(data):
    if not isinstance(data, dict) or set(data) != set(TEXT_LIMITS) | CHECKS:
        raise AttachmentError('invalid_manual_imaging_payload', 422)
    if any(data[k] is not True for k in CHECKS): raise AttachmentError('manual_imaging_check_sections', 422)
    result = {k: text(data[k], limit, k in {'title', 'body_part', 'taken_at', 'position'}) for k, limit in TEXT_LIMITS.items()}
    if result['modality'] not in {'dr', 'ultrasound'}: raise AttachmentError('invalid_manual_imaging_modality', 422)
    taken_at(result['taken_at'])
    if not (result['findings'].strip() or result['impression'].strip()):
        raise AttachmentError('manual_imaging_report_empty', 422)
    return {**result, **{k: True for k in CHECKS}}


def reports(db, cid):
    return db.query(ImagingStudy).filter_by(case_id=cid, source_type=SOURCE).order_by(ImagingStudy.id).all()


def report_token(row):
    return digest({'id': row.id, 'status': row.review_status, 'data': row.extra_data})


def _source(store, case, aid):
    item = attachments.find(case, aid, active=True)
    if item['metadata']['kind'] not in {'dr', 'ultrasound'}: raise AttachmentError('manual_imaging_source_not_imaging', 409)
    store.verified(item)
    return item


def effective(store, case, row):
    if row.review_status != 'confirmed': return row.review_status
    meta = row.extra_data
    if meta['identity'] != identity(case): return 'needs_review'
    try: item = _source(store, case, row.attachment_ref)
    except (AttachmentError, OSError): return 'source_unavailable'
    return 'confirmed' if digest(attachments.public(item)) == meta['source_digest'] else 'needs_review'


def public(store, case, row):
    meta = row.extra_data
    return {'id': row.id, 'root_id': meta['root_id'], 'version': meta['version'], 'state': effective(store, case, row),
            'stored_state': row.review_status, 'token': report_token(row), 'attachment_id': row.attachment_ref,
            'data': meta['data'], 'source': meta['source_snapshot'], 'identity': meta['identity'],
            'reason': meta.get('reason', ''), 'reviewed_by': row.reviewed_by, 'reviewed_at': str(row.reviewed_at),
            'invalidated_reason': meta.get('invalidated_reason', '')}


def listing(uid, cid):
    ensure_enabled(); store = Store()
    with store.locked(), attachments.transaction(uid, cid) as (db, case):
        return {**attachments.case_view(case), 'reports': [public(store, case, row) for row in reports(db, cid)],
                'sources': [attachments.public(a) for a in case.attachments or [] if attachments.known(a)
                            and a.get('state') == 'active' and a.get('metadata', {}).get('kind') in {'dr', 'ultrasound'}],
                'limits': {'reports': MAX_REPORTS, 'versions': MAX_VERSIONS}}


def document_reports(store, db, case, ids):
    rows = reports(db, case.id); latest = {}
    for row in rows: latest[row.extra_data['root_id']] = row
    result = []
    for rid in ids:
        row = next((r for r in rows if r.id == rid), None)
        if row is None: raise AttachmentError('manual_imaging_not_found', 404)
        if latest.get(row.extra_data['root_id']) is not row or effective(store, case, row) != 'confirmed':
            raise AttachmentError('manual_imaging_document_stale', 409)
        if validate(row.extra_data['data']) != row.extra_data['data']:
            raise AttachmentError('manual_imaging_document_stale', 409)
        result.append(deepcopy(public(store, case, row)))
    return result


def _get(db, case, rid):
    row = db.query(ImagingStudy).filter_by(id=rid, case_id=case.id, source_type=SOURCE).first()
    if row is None: raise AttachmentError('manual_imaging_not_found', 404)
    return row


def _preview(store, db, case, uid, body):
    if body['expected_case_token'] != attachments.case_token(case): raise AttachmentError('case_changed_review_again')
    attachments.request_id(body['request_id']); operation = body['operation']; old = None
    if operation != 'create':
        old = _get(db, case, body['report_id'])
        if report_token(old) != body['expected_report_token'] or old.review_status in {'superseded', 'withdrawn'}:
            raise AttachmentError('manual_imaging_version_changed')
        if old.attachment_ref != body['attachment_id']: raise AttachmentError('manual_imaging_source_changed')
        text(body['reason'], 500, True)
    elif body['report_id'] is not None or body['expected_report_token']:
        raise AttachmentError('invalid_manual_imaging_create', 422)
    rows = reports(db, case.id)
    if operation == 'withdraw':
        if body['data'] is not None: raise AttachmentError('invalid_manual_imaging_withdraw', 422)
        data = None; source = old.extra_data['source_snapshot']
    else:
        data = validate(body['data']); source = attachments.public(_source(store, case, body['attachment_id']))
        if source['metadata']['kind'] != data['modality']: raise AttachmentError('manual_imaging_modality_mismatch', 422)
        if operation == 'create':
            if any(r.attachment_ref == body['attachment_id'] for r in rows): raise AttachmentError('manual_imaging_report_exists')
            if sum(r.review_status not in {'superseded', 'withdrawn'} for r in rows) >= MAX_REPORTS:
                raise AttachmentError('manual_imaging_report_limit', 422)
        else:
            if old.extra_data['version'] >= MAX_VERSIONS: raise AttachmentError('manual_imaging_version_limit', 422)
            if any(r.extra_data['root_id'] == old.extra_data['root_id'] and r.id > old.id for r in rows):
                raise AttachmentError('manual_imaging_version_changed')
    state = {'case': attachments.case_view(case), 'identity': identity(case), 'source': source,
             'before': public(store, case, old) if old else None, 'data': data, 'operation': operation, 'reason': body['reason']}
    return {**state, 'preview_token': digest({'body': body, 'owner': uid, 'state': state})}


def preview(uid, cid, body):
    ensure_enabled(); store = Store()
    with store.locked(), attachments.transaction(uid, cid) as (db, case): return _preview(store, db, case, uid, body)


def ledger_id(uid, cid, request_id): return digest([SOURCE, str(uid), cid, attachments.request_id(request_id)])


def append_audit(db, uid, case, body, fingerprint, row, before):
    db.add(AuditLog(log_id=ledger_id(uid, case.id, body['request_id']), request_id=body['request_id'],
        clinician_id=str(uid), case_id=case.id, event_type='manual_imaging_' + body['operation'], action_taken=body['operation'],
        source=SOURCE, extra_data={'fingerprint': fingerprint, 'report_id': row.id,
        'before_id': before.id if before else None, 'reason': body['reason'], 'version': row.extra_data['version']}))


def commit(uid, cid, body, token):
    ensure_enabled(); store = Store(); fingerprint = digest({'body': body, 'token': token})
    with store.locked(), attachments.transaction(uid, cid) as (db, case):
        prior = db.get(AuditLog, ledger_id(uid, cid, body['request_id']))
        if prior:
            if prior.source != SOURCE or prior.extra_data['fingerprint'] != fingerprint: raise AttachmentError('request_payload_changed')
            return {'state': 'committed', 'report': public(store, case, _get(db, case, prior.extra_data['report_id']))}
        review = _preview(store, db, case, uid, body)
        if token != review['preview_token']: raise AttachmentError('review_changed')
        old = _get(db, case, body['report_id']) if body['report_id'] is not None else None
        now = datetime.utcnow()
        if body['operation'] == 'withdraw':
            row = old; row.review_status = 'withdrawn'
            row.extra_data = {**row.extra_data, 'reason': body['reason'], 'withdrawn_by': str(uid), 'withdrawn_at': now.isoformat()}
        else:
            if old: old.review_status = 'superseded'
            data = review['data']
            row = ImagingStudy(case_id=cid, modality=data['modality'], body_part=data['body_part'], taken_at=taken_at(data['taken_at']),
                source_type=SOURCE, source_system=data['institution'][:100], report_text=data['findings'],
                review_status='confirmed', reviewed_by=str(uid), reviewed_at=now, attachment_ref=body['attachment_id'],
                ai_summary_status='not_generated', extra_data={'schema': SCHEMA, 'data': data, 'identity': identity(case),
                'source_snapshot': review['source'], 'source_digest': digest(review['source']), 'reason': body['reason'],
                'version': old.extra_data['version'] + 1 if old else 1, 'root_id': old.extra_data['root_id'] if old else None})
            db.add(row); db.flush()
            if old is None: row.extra_data = {**row.extra_data, 'root_id': row.id}
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
    """Also invalidate while feature is off, within the caller's case transaction."""
    if os.getenv('ENVIRONMENT') not in {'test', 'development'} or os.getenv('RENDER', '').lower() == 'true': return
    if not inspect(db.connection()).has_table(ImagingStudy.__tablename__): return
    query = db.query(ImagingStudy).filter_by(case_id=case.id, source_type=SOURCE, review_status='confirmed')
    if attachment_id is not None: query = query.filter_by(attachment_ref=attachment_id)
    for row in query.all():
        row.review_status = 'needs_review'
        row.extra_data = {**row.extra_data, 'invalidated_reason': reason}
        event_id = digest([SOURCE, 'invalidate', row.id, row.extra_data['version'], reason])
        db.add(AuditLog(log_id=event_id, request_id=event_id[:32], clinician_id=str(case.owner_id), case_id=case.id,
                       event_type='manual_imaging_invalidate', source=SOURCE, action_taken='invalidate',
                       extra_data={'report_id': row.id, 'reason': reason}))


def invalidate_identity(db, case, changes):
    if any(k in changes and changes[k] != getattr(case, k) for k in IDENTITY_FIELDS):
        invalidate(db, case, reason='case_identity_changed')
