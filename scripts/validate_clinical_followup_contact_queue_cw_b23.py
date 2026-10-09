"""Read-only CW-B23 exact-path and frozen historical acceptance gate."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BASE = '21a2afaa100807842dd42a4967e24b771e362d12'
TREE = 'f0bba24b08585d856b1122e1a514b23832a3eacc'
ALLOWED = set(["backend/clinical_followup_contact_queue.py","frontend/src/followupContactQueue.js","frontend/src/components/FollowupContactQueueSummary.jsx","frontend/tests/followup-contact-queue.test.jsx","frontend/tests/case-detail-followup-contact-queue.test.jsx","tests/test_clinical_followup_contact_queue.py","tests/test_clinical_followup_contact_queue_concurrency.py","tests/test_clinical_followup_contact_queue_isolation.py","tests/acceptance/clinical_followup_contact_queue_checks.cjs","tests/fixtures/clinical_followup_contact_queue_cw_b23_cases.json","scripts/validate_clinical_followup_contact_queue_cw_b23.py","docs/clinical_docs/CLINICAL_FOLLOWUP_CONTACT_QUEUE_CW_B23.md","backend/clinical_followup_plan_queue_api.py","backend/clinical_followup_contacts.py","frontend/src/pages/FollowupPlanQueue.jsx","frontend/src/pages/CaseDetail.jsx","frontend/tests/run-consult-update-review.mjs","tests/acceptance/postgres_checks.py","tests/acceptance/fixture.py",".github/workflows/consult-browser-postgres.yml","docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md"])


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def main():
    subprocess.check_call(['git', 'merge-base', '--is-ancestor', BASE, 'HEAD'], cwd=ROOT)
    assert git('rev-parse', BASE+'^{tree}') == TREE
    changed = set(git('diff', '--name-only', BASE).splitlines()) | set(git('ls-files', '--others', '--exclude-standard').splitlines())
    assert len(ALLOWED) == 21 and 0 < len(changed) <= 21 and changed <= ALLOWED, sorted(changed-ALLOWED)
    assert all((ROOT/path).is_file() for path in changed)
    with tempfile.TemporaryDirectory(prefix='cwb23-frozen-') as temporary:
        frozen = str(Path(temporary)/'cw22')
        subprocess.check_call(['git', 'worktree', 'add', '--detach', '--quiet', frozen, BASE], cwd=ROOT)
        try:
            historical = json.loads(subprocess.check_output([sys.executable, '-B', 'scripts/validate_clinical_followup_contact_owner_documents_cw_b22.py'], cwd=frozen, text=True))
        finally:
            subprocess.check_call(['git', 'worktree', 'remove', frozen], cwd=ROOT)
    assert historical['status'] == 'PASS'
    workflow = (ROOT/'.github/workflows/consult-browser-postgres.yml').read_text()
    previous = git('show', BASE+':.github/workflows/consult-browser-postgres.yml')
    for line in previous.splitlines():
        if any(token in line for token in ('python tests/', 'node tests/', 'npm --prefix', 'retention-days:')):
            assert line in workflow, line
    marker = '      - name: Package and verify complete evidence in bounded parts'
    assert workflow[workflow.index(marker):].strip() == previous[previous.index(marker):].strip()
    assert '    timeout-minutes: 30' in workflow
    for token in ('cwb23-scope.json','frozen_cwb22','test_clinical_followup_contact_queue.py','test_clinical_followup_contact_queue_concurrency.py','test_clinical_followup_contact_queue_isolation.py','clinical_followup_contact_queue_checks.cjs'):
        assert token in workflow, token
    path = 'backend/clinical_followup_contacts.py'
    before = git('show', BASE+':'+path)
    anchor = '    try:\n        if len(rows) > MAX_VERSIONS'
    assert before.count(anchor) == 1
    expected = before.replace(anchor, '    return validated_records(rows, audits, case, sources)\n\n\ndef validated_records(rows, audits, case, sources):\n    """The same bounded chain/receipt rules for case reads and prefetched queue rows."""\n'+anchor)
    expected = expected.replace('        for audit in audits:\n', "        for audit in audits:\n            if audit.case_id != case.id or audit.source != SOURCE: raise ValueError('Audit case/source')\n")
    assert (ROOT/path).read_text().strip() == expected, 'Only pure validator extraction and prefetched group guard allowed'
    path = 'frontend/tests/run-consult-update-review.mjs'
    addition = "  names.push('followup-contact-queue', 'case-detail-followup-contact-queue');\n"
    current = (ROOT/path).read_text()
    assert current.count(addition) == 1 and current.replace(addition,'').strip() == git('show',BASE+':'+path)
    path = 'docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md'
    assert (ROOT/path).read_text().startswith(git('show',BASE+':'+path))
    assert 'CW-B23' in (ROOT/path).read_text() and 'Snake Depth V2' in (ROOT/path).read_text()
    print(json.dumps({'status':'PASS','baseline':BASE,'baseline_tree':TREE,'changed':sorted(changed),'allowed':sorted(ALLOWED),'frozen_cwb22':historical,'external_calls':0}, ensure_ascii=False, indent=2))


if __name__ == '__main__':main()
