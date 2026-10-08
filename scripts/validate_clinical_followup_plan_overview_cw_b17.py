"""Read-only scope gate; historical CW-B16 executes on its frozen actual commit."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BASE = "dde9b8c763e5c837b26b5f206240f31ead0cecfc"
TREE = "90fe32dc93a5dcc9018321a7f8b7d977fd034b66"
ALLOWED = set(['backend/clinical_followup_plan_overview.py', 'backend/clinical_case_overview.py', 'backend/clinical_case_overview_api.py', 'frontend/src/visitOverview.js', 'frontend/src/components/CaseVisitOverview.jsx', 'frontend/src/pages/CaseDetail.jsx', 'frontend/tests/followup-plan-overview.test.jsx', 'frontend/tests/case-detail-followup-plan-overview.test.jsx', 'frontend/tests/run-consult-update-review.mjs', 'tests/test_clinical_followup_plan_overview.py', 'tests/test_clinical_followup_plan_overview_concurrency.py', 'tests/acceptance/clinical_followup_plan_overview_checks.cjs', 'tests/acceptance/clinical_case_overview_checks.cjs', 'tests/acceptance/postgres_checks.py', 'tests/acceptance/fixture.py', 'tests/fixtures/clinical_followup_plan_overview_cw_b17_cases.json', '.github/workflows/consult-browser-postgres.yml', 'scripts/validate_clinical_followup_plan_overview_cw_b17.py', 'docs/clinical_docs/CLINICAL_FOLLOWUP_PLAN_OVERVIEW_CW_B17.md', 'docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md'])


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main():
    subprocess.check_call(["git", "merge-base", "--is-ancestor", BASE, "HEAD"], cwd=ROOT)
    assert git("rev-parse", BASE + "^{tree}") == TREE
    changed = set(git("diff", "--name-only", BASE).splitlines()) | set(git("ls-files", "--others", "--exclude-standard").splitlines())
    assert len(ALLOWED) == 20 and 0 < len(changed) <= 20 and changed <= ALLOWED, sorted(changed - ALLOWED)
    assert all((ROOT / path).is_file() for path in changed)
    with tempfile.TemporaryDirectory(prefix="cwb17-frozen-") as temporary:
        frozen = str(Path(temporary) / "cw16")
        subprocess.check_call(["git", "worktree", "add", "--detach", "--quiet", frozen, BASE], cwd=ROOT)
        try:
            historical = json.loads(subprocess.check_output([sys.executable, "-B", "scripts/validate_clinical_followup_plan_owner_documents_cw_b16.py"], cwd=frozen, text=True))
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
    assert (ROOT / 'backend/main.py').read_text().strip() == git('show', BASE + ':backend/main.py')
    print(json.dumps({"status":"PASS", "baseline":BASE, "baseline_tree":TREE, "changed":sorted(changed), "allowed":sorted(ALLOWED), "frozen_cwb16":historical, "external_calls":0}, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
