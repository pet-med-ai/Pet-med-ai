"""CW-B12: explicit same-case saved-item comparison. No persistence or clinical inference."""
from datetime import datetime, timezone
from decimal import Decimal, Inexact, Rounded, localcontext
import os
import re

from case_attachment_store import Store, AttachmentError, digest
import case_attachment_service as attachments
import clinical_lab_range_review as saved_results
import manual_lab_results as lab

SCHEMA = 'clinical-lab-comparison-cw-b12-v1'
RULES = 'explicit-same-case-exact-difference-v1'
HASH = re.compile(r'[a-f0-9]{64}\Z')
SELECTOR_FIELDS = {'id', 'version', 'token', 'index', 'position'}
CONDITIONS = ('panel', 'specimen', 'laboratory', 'device')
REFERENCES = ('reference', 'reference_low', 'reference_high', 'reference_unit')


def ensure_enabled():
    lab.ensure_enabled()
    if os.getenv('LAB_COMPARISON_ENABLED') != '1' or os.getenv('LAB_COMPARISON_SYNTHETIC_ONLY') != '1':
        raise AttachmentError('lab_comparison_disabled', 503)


def assemble(store, db, case):
    """Caller owns the original-file lock and case transaction, also during preview."""
    result = saved_results.assemble(store, db, case)
    result.update(schema=SCHEMA, rules=RULES)
    result['snapshot'] = digest(result)
    result['read_at'] = datetime.now(timezone.utc).isoformat()
    return result


def selection(row, item):
    return {key: row[key] for key in ('id', 'version', 'token')} | {key: item[key] for key in ('index', 'position')}


def validate_request(body):
    valid = isinstance(body, dict) and set(body) == {'snapshot', 'a', 'b', 'doctor_confirmed'}
    if valid:
        valid = isinstance(body['snapshot'], str) and HASH.fullmatch(body['snapshot']) and type(body['doctor_confirmed']) is bool
    if valid:
        for key in ('a', 'b'):
            value = body[key]
            valid = (isinstance(value, dict) and set(value) == SELECTOR_FIELDS
                     and all(type(value[k]) is int and 0 < value[k] <= 2**53 - 1 for k in ('id', 'version', 'index'))
                     and isinstance(value['token'], str) and HASH.fullmatch(value['token'])
                     and isinstance(value['position'], str) and 0 < len(value['position']) <= 255)
            if not valid: break
    if not valid: raise AttachmentError('lab_comparison_invalid_request', 422)


def selected(data, wanted):
    for row in data['reports']:
        if row['id'] != wanted['id']: continue
        for item in row['items']:
            if selection(row, item) == wanted: return row, item
    raise AttachmentError('lab_comparison_stale_selection', 409)


def difference(a, b):
    """B-A; the aligned integer coefficients plus one carry digit bound precision.

    Validated CW-B7 numbers are finite, <=50 source characters, |adjusted|<=100.
    Traps additionally fail closed if any future input rule defeats this bound.
    """
    left, right = Decimal(a), Decimal(b)
    exponent = min(left.as_tuple().exponent, right.as_tuple().exponent)
    width = max(len(v.as_tuple().digits) + v.as_tuple().exponent - exponent for v in (left, right))
    with localcontext() as context:
        context.prec = max(1, width + 1)
        context.traps[Inexact] = True
        context.traps[Rounded] = True
        value = right - left
        state = 'increase' if value > 0 else 'decrease' if value < 0 else 'same'
        # Fixed notation is bounded by saved input limits; never convert via float.
        return {'value': '0' if value == 0 else format(value, 'f'), 'state': state}


def compare(a, b, doctor_confirmed):
    ar, ai = a; br, bi = b
    reasons = []
    if ar['root_id'] == br['root_id']: reasons.append('same_report_root')
    if ar['source']['sha256'] == br['source']['sha256']: reasons.append('same_source')
    if ai['name'] != bi['name']: reasons.append('item_name_mismatch')
    if ai['result_type'] != 'number' or bi['result_type'] != 'number': reasons.append('non_numeric')
    if not ai['unit'].strip() or not bi['unit'].strip(): reasons.append('unit_missing')
    elif ai['unit'] != bi['unit']: reasons.append('unit_mismatch')
    for field in CONDITIONS:
        av, bv = ar['report'][field], br['report'][field]
        if not av.strip() or not bv.strip(): reasons.append(field + '_missing')
        elif av != bv: reasons.append(field + '_mismatch')
    dates = [row['report']['collected_at'] for row in (ar, br)]
    if not all(dates): reasons.append('collected_at_missing')
    else:
        # Saved structure and timezone validity were checked by assemble().
        at, bt = (datetime.fromisoformat(d.replace('Z', '+00:00')).astimezone(timezone.utc) for d in dates)
        if at == bt: reasons.append('collected_at_equal')
        elif at > bt: reasons.append('collected_at_reversed')
    if not doctor_confirmed: reasons.append('doctor_confirmation_required')
    delta = None if reasons else {**difference(ai['decimal'], bi['decimal']), 'unit': ai['unit']}
    return {'can_calculate': not reasons, 'reasons': reasons, 'delta': delta,
            'reference_changed': any(ai[key] != bi[key] for key in REFERENCES)}


def read(uid, cid):
    ensure_enabled()
    store = Store()
    with store.locked(), attachments.transaction(uid, cid) as (db, case):
        return assemble(store, db, case)


def preview(uid, cid, body):
    ensure_enabled()
    validate_request(body)
    store = Store()
    with store.locked(), attachments.transaction(uid, cid) as (db, case):
        data = assemble(store, db, case)
        if body['snapshot'] != data['snapshot']:
            raise AttachmentError('lab_comparison_stale_snapshot', 409)
        a, b = selected(data, body['a']), selected(data, body['b'])
        return {key: data[key] for key in ('schema', 'rules', 'case_id', 'snapshot', 'read_at',
                                         'read_only', 'writes_database', 'includes_unsaved_drafts')} | {
            'a': selection(*a), 'b': selection(*b), 'doctor_confirmed': body['doctor_confirmed'],
            **compare(a, b, body['doctor_confirmed'])}
