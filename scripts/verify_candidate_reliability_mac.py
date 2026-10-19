"""Targeted, synthetic Mac checks. A passing script is not Safari/Word acceptance."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
import sys

import run_clinical_doctor_trial_cw_b26 as trial

BACKEND = (
    'test_clinical_followup_plans.py', 'test_clinical_followup_plan_concurrency.py',
    'test_clinical_followup_plan_queue.py', 'test_clinical_followup_plan_queue_concurrency.py',
    'test_clinical_followup_contacts.py', 'test_clinical_followup_contact_concurrency.py',
    'test_clinical_followup_contact_queue.py', 'test_clinical_followup_contact_queue_concurrency.py',
    'test_clinical_doctor_trial.py',
)
FRONTEND = (
    'case-detail-documents', 'case-edit-review', 'followup-plan', 'followup-contacts',
    'case-detail-followup-plan-documents', 'case-detail-followup-contact-owner-documents',
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expect-head', required=True, help='Exact candidate commit; never changes the checkout')
    parser.add_argument('--out', required=True, type=Path, help='New evidence directory outside the repository')
    args = parser.parse_args()
    if sys.platform != 'darwin':
        parser.error('Mac evidence requires execution on macOS; this host is not macOS.')
    if not re.fullmatch('[a-f0-9]{40}', args.expect_head):
        parser.error('Expected a full commit SHA')
    node, identity = trial.preflight(args.expect_head)
    if not identity['clean']:
        parser.error('Candidate checkout is not clean; preserve changes and use an independent clean worktree.')
    output = args.out.expanduser().resolve()
    if output == trial.ROOT or trial.ROOT in output.parents or not output.parent.is_dir():
        parser.error('Evidence must be in a new directory outside the checkout, with an existing parent.')
    output.mkdir(mode=0o700, exist_ok=False)
    receipt = {'schema': 'candidate-reliability-mac-v1', 'status': 'RUNNING',
               'started_at': datetime.now(timezone.utc).isoformat(), **identity,
               'tree': trial.git('rev-parse', 'HEAD^{tree}').decode().strip(),
               'platform': sys.platform, 'macos': platform.mac_ver()[0], 'machine': platform.machine(),
               'python': platform.python_version(), 'tests': [],
               'safari_manual': 'PENDING', 'word_manual': 'PENDING',
               'acceptance': 'NOT_CLOSED', 'production_access': False}
    commands = [(name, [sys.executable, '-B', str(trial.ROOT / 'tests' / name)]) for name in BACKEND]
    commands.append(('frontend-targeted', [node, str(trial.ROOT / 'frontend/tests/run-consult-update-review.mjs'), *FRONTEND]))
    try:
        for name, command in commands:
            log = output / (name + '.log')
            print('CHECK ' + name, flush=True)
            with log.open('x', encoding='utf-8') as stream:
                result = subprocess.run(command, cwd=trial.ROOT, env=trial.clean_environment(),
                                        stdout=stream, stderr=subprocess.STDOUT, timeout=300)
            receipt['tests'].append({'name': name, 'exit_code': result.returncode,
                                     'log': log.name, 'sha256': hashlib.sha256(log.read_bytes()).hexdigest()})
            if result.returncode:
                receipt['status'] = 'FAILED';break
        else:
            if trial.source_identity() != identity:
                raise RuntimeError('Candidate changed during checks')
            receipt['status'] = 'AUTOMATED_CHECKS_PASSED_GUI_PENDING'
    except (Exception, KeyboardInterrupt) as error:
        receipt['status'] = 'FAILED'
        receipt['error_type'] = type(error).__name__
    finally:
        receipt['finished_at'] = datetime.now(timezone.utc).isoformat()
        trial.write_private(output / 'receipt.json', receipt)
        print('RECEIPT ' + str(output / 'receipt.json'), flush=True)
        print(receipt['status'], flush=True)
    return 0 if receipt['status'] == 'AUTOMATED_CHECKS_PASSED_GUI_PENDING' else 1


if __name__ == '__main__':
    raise SystemExit(main())
