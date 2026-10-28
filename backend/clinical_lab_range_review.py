"""CW-B11: decimal comparison of validated saved manual results. No diagnosis or writes."""
from datetime import datetime, timezone
from decimal import Decimal
import os

from case_attachment_store import Store, AttachmentError, digest
import case_attachment_service as attachments
import clinical_case_overview as inventory
import manual_lab_results as lab

SCHEMA = 'clinical-lab-range-review-cw-b11-v1'
RULES = 'saved-decimal-closed-bounds-separate-v1'
COMPARABLE = {'below', 'between', 'above'}
UNABLE = {'reference_incomplete', 'comparison', 'text', 'not_tested', 'not_provided'}


def ensure_enabled():
    lab.ensure_enabled()
    if os.getenv('LAB_RANGE_REVIEW_ENABLED') != '1' or os.getenv('LAB_RANGE_REVIEW_SYNTHETIC_ONLY') != '1':
        raise AttachmentError('lab_range_review_disabled', 503)


def compare(item):
    """Only call after validate(input_data(saved)) == saved; never parse free text."""
    kind = item['result_type']
    state = kind
    if kind == 'number':
        low, high = item['reference_low_decimal'], item['reference_high_decimal']
        if low is None or high is None:
            state = 'reference_incomplete'
        else:
            value, low, high = Decimal(item['decimal']), Decimal(low), Decimal(high)
            state = ('boundary' if value in (low, high) else
                     'below' if value < low else 'above' if value > high else 'between')
    flag = item['flag']
    flag_state = 'not_provided' if flag == '' else 'uninterpreted'
    if flag in {'H', 'L'}:
        flag_state = ('agrees' if (flag == 'H' and state == 'above') or (flag == 'L' and state == 'below')
                      else 'conflict') if state in COMPARABLE else 'not_assessed'
    return {'state': state, 'flag_state': flag_state}


def assemble(store, db, case):
    """The caller holds both original-file and case locks until the snapshot is complete."""
    sources = inventory.originals(store, case)
    group = inventory.report_group(store, db, case, lab, {s['id']: s for s in sources['records']})
    inventory.require(group['status'] == 'available')
    rows = {row.id: row for row in lab.reports(db, case.id)}
    reports, excluded = [], []
    for summary in group['records']:
        row = rows[summary['id']]
        source = summary['source']
        inventory.require('owner' not in source or source['owner'] == case.owner_id)
        inventory.require('case_id' not in source or source['case_id'] == case.id)
        report = {**summary, 'token': lab.report_token(row), 'report': row.metadata_json['data']['report']}
        if summary['state'] != 'confirmed':
            excluded.append(report)
            continue
        report['items'] = [{**item, 'index': i + 1, 'comparison': compare(item)}
                           for i, item in enumerate(row.metadata_json['data']['items'])]
        reports.append(report)
    items = [item for report in reports for item in report['items']]
    identity = {key: getattr(case, key) for key in (*lab.IDENTITY_FIELDS, 'owner_phone', 'age_info', 'weight')}
    inventory.require(all(v is None or isinstance(v, str) for v in identity.values()))
    return {'schema': SCHEMA, 'rules': RULES, 'case_id': case.id, 'identity': identity,
            'reports': reports, 'excluded': excluded, 'legacy_count': group['legacy_count'],
            'counts': {'reports': len(reports), 'items': len(items),
                       'out_of_range': sum(i['comparison']['state'] in {'below', 'above'} for i in items),
                       'unable': sum(i['comparison']['state'] in UNABLE for i in items),
                       'boundary': sum(i['comparison']['state'] == 'boundary' for i in items),
                       'flag_conflicts': sum(i['comparison']['flag_state'] == 'conflict' for i in items)},
            'read_only': True, 'writes_database': False, 'includes_unsaved_drafts': False}


def review(uid, cid):
    ensure_enabled()
    store = Store()
    with store.locked(), attachments.transaction(uid, cid) as (db, case):
        result = assemble(store, db, case)
        result['snapshot'] = digest(result)
        result['read_at'] = datetime.now(timezone.utc).isoformat()
        return result
