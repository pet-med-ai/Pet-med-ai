"""CW-B10: source-verified saved-record inventory. No clinical interpretation or writes."""
from datetime import datetime, timezone
import os
import re

from models import DiagnosticReport, ImagingStudy
from case_attachment_store import Store, AttachmentError, digest, ensure_enabled as attachments_enabled
import case_attachment_service as attachments
import manual_lab_results as lab
import manual_imaging_records as imaging
import clinical_followup_plan_overview as followup

SCHEMA = 'clinical-case-overview-cw-b10-v1'
FIELDS = {'chief_complaint': '主诉', 'history': '病史', 'exam_findings': '查体记录',
          'analysis': '评估内容', 'treatment': '诊疗计划', 'prognosis': '预后与补充说明'}
TARGETS = ['edit', 'attachments', 'lab', 'imaging', 'outpatient', 'owner_summary']
STATES = {'confirmed', 'needs_review', 'source_unavailable', 'superseded', 'withdrawn'}
HEX = re.compile(r'[a-f0-9]{64}\Z')


def ensure_enabled():
    attachments_enabled()
    if os.getenv('VISIT_OVERVIEW_ENABLED') != '1' or os.getenv('VISIT_OVERVIEW_SYNTHETIC_ONLY') != '1':
        raise AttachmentError('visit_overview_disabled', 503)


def require(condition):
    if not condition:
        raise AttachmentError('visit_overview_data_unreadable', 409)


def text_state(value):
    if value is None or (isinstance(value, str) and not value.strip()):
        return 'missing'
    return 'recorded' if isinstance(value, str) else 'unknown'


def original_shape(item):
    require(isinstance(item, dict))
    require(all(isinstance(item.get(k), str) for k in ('id', 'name', 'sha256', 'mime', 'state')))
    require(bool(HEX.fullmatch(item['id'])) and bool(HEX.fullmatch(item['sha256'])))
    require(type(item.get('size')) is int and item['size'] > 0)
    require(item['state'] in {'active', 'withdrawn'})
    attachments.metadata(item.get('metadata'))


def originals(store, case):
    rows, legacy = [], 0
    for item in case.attachments or []:
        if not attachments.known(item):
            legacy += 1
            continue
        original_shape(item)
        # CW-B6 stores public metadata inside the authenticated Case; staging owner
        # fields are not retained. Reject conflicting fields if a future item has them.
        require('case_id' not in item or item['case_id'] == case.id)
        require('owner' not in item or item['owner'] == case.owner_id)
        require(item.get('confirmed_by') is not None and bool(item.get('confirmed_at')))
        require(not any(row['id'] == item['id'] for row in rows))
        state = item['state']
        if state == 'active':
            try:
                store.verified(item)
            except (AttachmentError, OSError):
                state = 'source_unavailable'
        rows.append({**attachments.public(item), 'state': state, 'stored_state': item['state'], 'target': 'attachments'})
    return {'status': 'available', 'records': rows, 'legacy_count': legacy,
            'counts': {key: sum(row['state'] == key for row in rows)
                       for key in ('active', 'source_unavailable', 'withdrawn')}}


def report_group(store, db, case, module, source_rows):
    target = 'lab' if module is lab else 'imaging'
    try:
        module.ensure_enabled()
    except AttachmentError as exc:
        if exc.code != ('manual_lab_disabled' if module is lab else 'manual_imaging_disabled'):
            raise
        return {'status': 'disabled', 'records': None, 'counts': None, 'legacy_count': None}
    model = DiagnosticReport if module is lab else ImagingStudy
    all_rows = db.query(model).filter_by(case_id=case.id).order_by(model.id).all()
    groups, legacy = {}, 0
    for row in all_rows:
        meta = row.metadata_json if module is lab else row.extra_data
        if row.source_type != module.SOURCE:
            require(not isinstance(meta, dict) or meta.get('schema') != module.SCHEMA)
            legacy += 1
            continue
        require(isinstance(meta, dict) and meta.get('schema') == module.SCHEMA)
        require(type(meta.get('root_id')) is int and meta['root_id'] > 0)
        require(type(meta.get('version')) is int and 1 <= meta['version'] <= module.MAX_VERSIONS)
        require(isinstance(meta.get('identity'), dict) and set(meta['identity']) == set(lab.IDENTITY_FIELDS))
        require(all(v is None or isinstance(v, str) for v in meta['identity'].values()))
        require(row.reviewed_by is not None and row.reviewed_at is not None)
        stored = row.status if module is lab else row.review_status
        require(stored in {'confirmed', 'needs_review', 'superseded', 'withdrawn'})
        source = meta.get('source_snapshot')
        original_shape(source)
        require(source['id'] == row.attachment_ref and digest(source) == meta.get('source_digest'))
        data = meta.get('data')
        validated = module.validate(lab.input_data(data) if module is lab else data)
        require(validated == data)
        require(source['metadata']['kind'] == ('lab' if module is lab else data['modality']))
        title = data['report']['title'] if module is lab else data['title']
        current_source = source_rows.get(row.attachment_ref)
        source_state = current_source['state'] if current_source else 'source_unavailable'
        state = stored
        if stored not in {'superseded', 'withdrawn'}:
            state = 'source_unavailable' if source_state != 'active' else module.effective(store, case, row)
        require(state in STATES)
        summary = {'id': row.id, 'root_id': meta['root_id'], 'version': meta['version'],
                   'state': state, 'stored_state': stored, 'title': title, 'attachment_id': row.attachment_ref,
                   'source': source, 'source_state': source_state, 'reviewed_by': str(row.reviewed_by),
                   'reviewed_at': str(row.reviewed_at), 'reason': meta.get('reason', ''),
                   'invalidated_reason': meta.get('invalidated_reason', ''), 'target': target}
        require(all(isinstance(summary[k], str) for k in ('reason', 'invalidated_reason')))
        groups.setdefault(meta['root_id'], []).append(summary)
    records, seen_sources = [], set()
    for root, versions in groups.items():
        require(versions[0]['id'] == root)
        require([r['version'] for r in versions] == list(range(1, len(versions) + 1)))
        require(all(r['state'] == 'superseded' for r in versions[:-1]))
        require(versions[-1]['state'] != 'superseded')
        aid = versions[0]['attachment_id']
        require(all(r['attachment_id'] == aid for r in versions) and aid not in seen_sources)
        seen_sources.add(aid)
        records.extend(versions)
    return {'status': 'available', 'records': records, 'legacy_count': legacy,
            'counts': {state: sum(r['state'] == state for r in records) for state in sorted(STATES)}}


def assemble(store, db, case):
    """Caller owns Store lock and the case transaction through complete assembly."""
    fields = [{'key': key, 'label': label, 'state': text_state(getattr(case, key)),
               'value': getattr(case, key) if text_state(getattr(case, key)) != 'unknown' else None, 'target': 'edit'}
              for key, label in FIELDS.items()]
    sources = originals(store, case)
    source_rows = {r['id']: r for r in sources['records']}
    groups = {'attachments': sources, 'lab': report_group(store, db, case, lab, source_rows),
              'imaging': report_group(store, db, case, imaging, source_rows)}
    notices = []
    for field in fields:
        if field['state'] != 'recorded':
            notices.append({'code': 'field_' + field['state'], 'label': field['label'] +
                            ('尚未填写' if field['state'] == 'missing' else '结构无法确认'), 'target': 'edit'})
    for key, group in groups.items():
        if group['status'] == 'disabled':
            notices.append({'code': 'module_disabled', 'label': ('检验' if key == 'lab' else '影像') + '模块未启用，不能判断记录有无', 'target': key})
            continue
        if group['legacy_count']:
            notices.append({'code': 'legacy_records', 'label': f'有 {group["legacy_count"]} 条旧式资料需回原入口核对', 'target': key})
        for row in group['records']:
            if row['state'] in {'needs_review', 'source_unavailable'}:
                notices.append({'code': row['state'], 'label': (row.get('title') or row['name']) +
                                ('需重新核对' if row['state'] == 'needs_review' else '来源不可用'), 'target': key})
    for source in sources['records']:
        target = {'lab': 'lab', 'dr': 'imaging', 'ultrasound': 'imaging'}.get(source['metadata']['kind'])
        if source['state'] != 'active' or not target or groups[target]['status'] != 'available':
            continue
        if not any(r['attachment_id'] == source['id'] for r in groups[target]['records']):
            notices.append({'code': 'source_without_record', 'label': source['metadata']['title'] + '尚无对应人工记录', 'target': target})
    identity = {key: getattr(case, key) for key in (*lab.IDENTITY_FIELDS, 'owner_phone', 'age_info', 'weight')}
    require(all(v is None or isinstance(v, str) for v in identity.values()))
    return {'schema': SCHEMA, 'case_id': case.id, 'identity': identity, 'fields': fields,
            'groups': groups, 'notices': notices, 'navigation_targets': TARGETS,
            'read_only': True, 'writes_database': False, 'includes_unsaved_drafts': False}


def overview(uid, cid, include_followup_plan=False):
    ensure_enabled()
    store = Store()
    with store.locked(), attachments.transaction(uid, cid) as (db, case):
        result = assemble(store, db, case)
        if include_followup_plan and followup.enabled():
            result['schema'] = followup.SCHEMA
            result['navigation_targets'] = [*TARGETS, 'followup']
            result['groups']['followup'] = followup.group(db, case)
        result['snapshot'] = digest(result)
        result['read_at'] = datetime.now(timezone.utc).isoformat()
        return result
