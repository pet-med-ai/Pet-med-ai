"""Read-only scope gate; historical CW-B18 executes on its frozen actual commit."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BASE = "73ba51e664241bac2b664d10d8eaf242b991a0e5"
TREE = "ceb4e6aca1dc7d929dbbde6a0d423471f3d4738e"
ALLOWED = set(['backend/clinical_followup_contacts.py', 'backend/clinical_followup_contacts_api.py', 'backend/main.py', 'backend/clinical_followup_plans.py', 'frontend/src/followupContacts.js', 'frontend/src/components/CaseFollowupContacts.jsx', 'frontend/src/pages/CaseDetail.jsx', 'frontend/tests/followup-contacts.test.jsx', 'frontend/tests/case-detail-followup-contacts.test.jsx', 'frontend/tests/run-consult-update-review.mjs', 'frontend/tests/check-route-chunks.mjs', 'tests/test_clinical_followup_contacts.py', 'tests/test_clinical_followup_contact_concurrency.py', 'tests/test_clinical_followup_contact_isolation.py', 'tests/acceptance/clinical_followup_contact_checks.cjs', 'tests/acceptance/postgres_checks.py', 'tests/acceptance/fixture.py', 'tests/fixtures/clinical_followup_contacts_cw_b19_cases.json', '.github/workflows/consult-browser-postgres.yml', 'scripts/validate_clinical_followup_contacts_cw_b19.py', 'docs/clinical_docs/CLINICAL_FOLLOWUP_CONTACTS_CW_B19.md', 'docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md'])


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main():
    subprocess.check_call(["git", "merge-base", "--is-ancestor", BASE, "HEAD"], cwd=ROOT)
    assert git("rev-parse", BASE + "^{tree}") == TREE
    changed = set(git("diff", "--name-only", BASE).splitlines()) | set(git("ls-files", "--others", "--exclude-standard").splitlines())
    assert len(ALLOWED) == 22 and 0 < len(changed) <= 22 and changed <= ALLOWED, sorted(changed - ALLOWED)
    assert all((ROOT / path).is_file() for path in changed)
    with tempfile.TemporaryDirectory(prefix="cwb19-frozen-") as temporary:
        frozen = str(Path(temporary) / "cw18")
        subprocess.check_call(["git", "worktree", "add", "--detach", "--quiet", frozen, BASE], cwd=ROOT)
        try:
            historical = json.loads(subprocess.check_output([sys.executable, "-B", "scripts/validate_clinical_followup_plan_queue_cw_b18.py"], cwd=frozen, text=True))
        finally:
            subprocess.check_call(["git", "worktree", "remove", frozen], cwd=ROOT)
    assert historical["status"] == "PASS"
    workflow = (ROOT / ".github/workflows/consult-browser-postgres.yml").read_text()
    for marker in ("cwb17-scope.json", "test_clinical_followup_plan_overview.py", "test_clinical_followup_plan_overview_concurrency.py", "clinical_followup_plan_overview_checks.cjs", "test_clinical_followup_plan_owner_documents.py", "test_clinical_followup_plan_owner_document_concurrency.py", "clinical_followup_plan_owner_document_checks.cjs", "cwb16-scope.json", "test_clinical_followup_plan_documents.py", "test_clinical_followup_plan_document_concurrency.py", "clinical_followup_plan_document_checks.cjs", "cwb14-scope.json", "clinical_followup_plan_checks.cjs", "test_clinical_followup_plans.py", "test_clinical_followup_plan_concurrency.py", "cwb13-scope.json", "clinical_lab_comparison_document_checks.cjs", "test_clinical_lab_comparison_document_concurrency.py", "cwb12-scope.json", "clinical_lab_comparison_checks.cjs", "test_clinical_lab_comparison_concurrency.py", "cwb11-scope.json", "clinical_lab_range_review_checks.cjs", "test_clinical_lab_range_review_concurrency.py", "cwb10-scope.json", "clinical_case_overview_checks.cjs", "test_clinical_case_overview_concurrency.py", "m7-scope.json", "outpatient-identity-scope.json", "b1-scope.json", "b2-scope.json", "b3-scope.json", "b4-scope.json", "cwb5-scope.json", "cwb6-scope.json", "cwb7-scope.json", "cwb8-scope.json", "cwb9-scope.json", "manual_imaging_checks.cjs", "test_manual_imaging_concurrency.py", "test_manual_imaging_documents.py", "manual_lab_document_checks.cjs", "test_manual_lab_document_concurrency.py", "npm --prefix frontend audit", "manual_lab_checks.cjs", "test_manual_lab_result_concurrency.py"):
        assert marker in workflow, marker
    index = (ROOT / "docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md").read_text()
    for marker in ("Snake Depth V2", "CW-B7", "CW-B8", "CW-B9", "CW-B10", "CW-B11", "CW-B12", "CW-B13", "CW-B14", "CW-B16", "CW-B17", "草稿候选", "CI 通过", "已合并", "已上线", "医生验收"):
        assert marker in index, marker
    assert 'retention-days: 14' in workflow and 'Verify each part size/SHA256' in workflow
    registration = '\nfrom clinical_followup_contacts_api import router as followup_contacts_router\napp.include_router(followup_contacts_router)'
    main_source = (ROOT / 'backend/main.py').read_text()
    assert main_source.count(registration) == 1
    assert main_source.replace(registration, '').strip() == git('show', BASE + ':backend/main.py')
    source = (ROOT / 'backend/clinical_followup_plans.py').read_text()
    extension = "~or_(namespace(status, channel), func.coalesce(status, '').startswith('cw-b19-'),\n                func.coalesce(channel, '') == 'clinical-followup-contacts-cw-b19')"
    assert source.count(extension) == 1
    assert source.replace(extension, '~namespace(status, channel)').strip() == git('show', BASE + ':backend/clinical_followup_plans.py')
    for marker in ('cwb18-scope.json', 'test_clinical_followup_plan_queue.py', 'test_clinical_followup_plan_queue_concurrency.py', 'clinical_followup_plan_queue_checks.cjs'):
        assert marker in workflow, marker
    assert 'FollowupPlanQueue' in (ROOT / 'frontend/tests/check-route-chunks.mjs').read_text()
    for marker in ('cwb19-scope.json', 'test_clinical_followup_contacts.py', 'test_clinical_followup_contact_concurrency.py', 'test_clinical_followup_contact_isolation.py', 'clinical_followup_contact_checks.cjs'):
        assert marker in workflow, marker
    assert 'CaseFollowupContacts' in (ROOT / 'frontend/tests/check-route-chunks.mjs').read_text()
    previous = git('show', BASE + ':.github/workflows/consult-browser-postgres.yml')
    # Keep every historical execution and exact evidence packaging/upload tail.
    for line in previous.splitlines():
        if any(token in line for token in ('python tests/', 'node tests/', 'npm --prefix', 'retention-days:')):
            assert line in workflow, line
    marker = '      - name: Package and verify complete evidence in bounded parts'
    assert marker in previous and workflow[workflow.index(marker):].strip() == previous[previous.index(marker):].strip()

    print(json.dumps({"status":"PASS", "baseline":BASE, "baseline_tree":TREE, "changed":sorted(changed), "allowed":sorted(ALLOWED), "frozen_cwb18":historical, "external_calls":0}, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
