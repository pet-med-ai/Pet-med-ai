"""Read-only scope gate; historical CW-B17 executes on its frozen actual commit."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BASE = "9d425ca15ce1d34493f7415d1eb245b7182fcca0"
TREE = "7d97a1087deba6bf050a0c7cb7aee46d739c0556"
ALLOWED = set(['backend/clinical_followup_plan_queue.py', 'backend/clinical_followup_plan_queue_api.py', 'backend/main.py', 'backend/clinical_followup_plans.py', 'frontend/src/followupPlanQueue.js', 'frontend/src/pages/FollowupPlanQueue.jsx', 'frontend/src/App.jsx', 'frontend/src/pages/CaseDetail.jsx', 'frontend/tests/followup-plan-queue.test.jsx', 'frontend/tests/case-detail-followup-plan-queue.test.jsx', 'frontend/tests/deferred-pages.test.jsx', 'frontend/tests/run-consult-update-review.mjs', 'frontend/tests/check-route-chunks.mjs', 'tests/test_clinical_followup_plan_queue.py', 'tests/test_clinical_followup_plan_queue_concurrency.py', 'tests/acceptance/clinical_followup_plan_queue_checks.cjs', 'tests/acceptance/postgres_checks.py', 'tests/acceptance/fixture.py', 'tests/fixtures/clinical_followup_plan_queue_cw_b18_cases.json', '.github/workflows/consult-browser-postgres.yml', 'scripts/validate_clinical_followup_plan_queue_cw_b18.py', 'docs/clinical_docs/CLINICAL_FOLLOWUP_PLAN_QUEUE_CW_B18.md', 'docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md'])


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main():
    subprocess.check_call(["git", "merge-base", "--is-ancestor", BASE, "HEAD"], cwd=ROOT)
    assert git("rev-parse", BASE + "^{tree}") == TREE
    changed = set(git("diff", "--name-only", BASE).splitlines()) | set(git("ls-files", "--others", "--exclude-standard").splitlines())
    assert len(ALLOWED) == 23 and 0 < len(changed) <= 23 and changed <= ALLOWED, sorted(changed - ALLOWED)
    assert all((ROOT / path).is_file() for path in changed)
    with tempfile.TemporaryDirectory(prefix="cwb18-frozen-") as temporary:
        frozen = str(Path(temporary) / "cw17")
        subprocess.check_call(["git", "worktree", "add", "--detach", "--quiet", frozen, BASE], cwd=ROOT)
        try:
            historical = json.loads(subprocess.check_output([sys.executable, "-B", "scripts/validate_clinical_followup_plan_overview_cw_b17.py"], cwd=frozen, text=True))
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
    registration = '\nfrom clinical_followup_plan_queue_api import router as followup_plan_queue_router\napp.include_router(followup_plan_queue_router)'
    main_source = (ROOT / 'backend/main.py').read_text()
    assert main_source.count(registration) == 1
    assert main_source.replace(registration, '').strip() == git('show', BASE + ':backend/main.py')
    extraction = '    return validated_records(rows, case)\n\n\ndef validated_records(rows, case):\n    """Validate a complete, ID-ordered prefetched CW-B14 chain without I/O."""\n'
    source = (ROOT / 'backend/clinical_followup_plans.py').read_text()
    assert source.count(extraction) == 1
    assert source.replace(extraction, '').strip() == git('show', BASE + ':backend/clinical_followup_plans.py')
    for marker in ('cwb18-scope.json', 'test_clinical_followup_plan_queue.py', 'test_clinical_followup_plan_queue_concurrency.py', 'clinical_followup_plan_queue_checks.cjs'):
        assert marker in workflow, marker
    assert 'FollowupPlanQueue' in (ROOT / 'frontend/tests/check-route-chunks.mjs').read_text()
    print(json.dumps({"status":"PASS", "baseline":BASE, "baseline_tree":TREE, "changed":sorted(changed), "allowed":sorted(ALLOWED), "frozen_cwb17":historical, "external_calls":0}, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
