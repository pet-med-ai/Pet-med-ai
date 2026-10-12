"""CW-B17 opt-in saved-plan inventory; caller owns the case transaction."""
import os

from case_attachment_store import AttachmentError
import clinical_followup_plans as plans

SCHEMA = 'clinical-case-overview-cw-b17-v1'
STATES = ('planned', 'needs_review', 'superseded', 'withdrawn')


def enabled():
    return (os.getenv('FOLLOWUP_PLAN_OVERVIEW_ENABLED') == '1'
            and os.getenv('FOLLOWUP_PLAN_OVERVIEW_SYNTHETIC_ONLY') == '1'
            and os.getenv('ENVIRONMENT') in {'test', 'development'}
            and os.getenv('RENDER', '').lower() != 'true')


def group(db, case):
    """Never open a second session, write, clean up, or infer actual follow-up."""
    try:
        plans.ensure_enabled()
    except plans.PlanError as exc:
        if exc.code != 'followup_plans_disabled':
            raise
        return {'status': 'disabled', 'records': None, 'counts': None,
                'case': None, 'timezone': 'Asia/Shanghai'}
    try:
        records = [plans.public(row, meta, case) for row, meta in plans.records(db, case)]
    except plans.PlanError:
        raise AttachmentError('visit_overview_data_unreadable', 409) from None
    return {'status': 'available', 'records': records,
            'counts': {state: sum(row['state'] == state for row in records) for state in STATES},
            'case': plans.case_snapshot(case), 'timezone': 'Asia/Shanghai'}
