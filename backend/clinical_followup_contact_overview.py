"""CW-B20 saved contact inventory; the caller owns the whole case transaction."""
import os

from case_attachment_store import AttachmentError
import clinical_followup_contacts as contacts

SCHEMA = 'clinical-case-overview-cw-b20-v1'
STATES = ('recorded', 'superseded', 'withdrawn')


def enabled():
    return (os.getenv('FOLLOWUP_CONTACT_OVERVIEW_ENABLED') == '1'
            and os.getenv('FOLLOWUP_CONTACT_OVERVIEW_SYNTHETIC_ONLY') == '1'
            and os.getenv('ENVIRONMENT') in {'test', 'development'}
            and os.getenv('RENDER', '').lower() != 'true')


def group(db, case, plan_group):
    """Use the already verified plans; never open another session or repair data."""
    try:
        contacts.ensure_enabled()
    except contacts.Error as exc:
        if exc.code not in {'followup_contacts_disabled', 'followup_plans_disabled'}:
            raise
        return {'status': 'disabled', 'records': None, 'counts': None,
                'case': None, 'timezone': 'Asia/Shanghai'}
    if plan_group['status'] != 'available':
        raise AttachmentError('visit_overview_data_unreadable', 409)
    sources = plan_group['records']
    try:
        records = [contacts.public(row, meta, sources)
                   for row, meta in contacts.records(db, case, sources)]
    except contacts.Error:
        raise AttachmentError('visit_overview_data_unreadable', 409) from None
    return {'status': 'available', 'records': records,
            'counts': {state: sum(row['state'] == state for row in records) for state in STATES},
            'case': contacts.plans.case_snapshot(case), 'timezone': 'Asia/Shanghai'}
