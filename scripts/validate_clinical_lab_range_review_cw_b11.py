"""Read-only scope gate; historical CW-B10 executes on its frozen actual commit."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BASE = "af6eee5860dceaa2d3f0fea3e9f352fa248f2368"
TREE = "6343e306e45fcae5087512d7d16173368eef3c61"
ALLOWED = set(['backend/clinical_lab_range_review.py', 'backend/clinical_lab_range_review_api.py', 'backend/main.py', 'frontend/src/components/CaseLabRangeReview.jsx', 'frontend/src/labRangeReview.js', 'frontend/src/pages/CaseDetail.jsx', 'frontend/src/components/CaseLabResults.jsx', 'frontend/tests/lab-range-review.test.jsx', 'frontend/tests/case-detail-lab-range-review.test.jsx', 'frontend/tests/run-consult-update-review.mjs', 'tests/test_clinical_lab_range_review.py', 'tests/test_clinical_lab_range_review_concurrency.py', 'tests/acceptance/clinical_lab_range_review_checks.cjs', 'tests/acceptance/postgres_checks.py', 'tests/acceptance/fixture.py', 'tests/fixtures/clinical_lab_range_review_cw_b11_cases.json', '.github/workflows/consult-browser-postgres.yml', 'scripts/validate_clinical_lab_range_review_cw_b11.py', 'docs/clinical_docs/CLINICAL_LAB_RANGE_REVIEW_CW_B11.md', 'docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md'])


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main():
    subprocess.check_call(["git", "merge-base", "--is-ancestor", BASE, "HEAD"], cwd=ROOT)
    assert git("rev-parse", BASE + "^{tree}") == TREE
    changed = set(git("diff", "--name-only", BASE).splitlines()) | set(git("ls-files", "--others", "--exclude-standard").splitlines())
    assert len(ALLOWED) == 20 and 0 < len(changed) <= 20 and changed <= ALLOWED, sorted(changed - ALLOWED)
    assert all((ROOT / path).is_file() for path in changed)
    with tempfile.TemporaryDirectory(prefix="cwb11-frozen-") as temporary:
        frozen = str(Path(temporary) / "cw10")
        subprocess.check_call(["git", "worktree", "add", "--detach", "--quiet", frozen, BASE], cwd=ROOT)
        try:
            historical = json.loads(subprocess.check_output([sys.executable, "-B", "scripts/validate_clinical_case_overview_cw_b10.py"], cwd=frozen, text=True))
        finally:
            subprocess.check_call(["git", "worktree", "remove", frozen], cwd=ROOT)
    assert historical["status"] == "PASS"
    workflow = (ROOT / ".github/workflows/consult-browser-postgres.yml").read_text()
    for marker in ("cwb11-scope.json", "clinical_lab_range_review_checks.cjs", "test_clinical_lab_range_review_concurrency.py", "cwb10-scope.json", "clinical_case_overview_checks.cjs", "test_clinical_case_overview_concurrency.py", "m7-scope.json", "outpatient-identity-scope.json", "b1-scope.json", "b2-scope.json", "b3-scope.json", "b4-scope.json", "cwb5-scope.json", "cwb6-scope.json", "cwb7-scope.json", "cwb8-scope.json", "cwb9-scope.json", "manual_imaging_checks.cjs", "test_manual_imaging_concurrency.py", "test_manual_imaging_documents.py", "manual_lab_document_checks.cjs", "test_manual_lab_document_concurrency.py", "npm --prefix frontend audit", "manual_lab_checks.cjs", "test_manual_lab_result_concurrency.py"):
        assert marker in workflow, marker
    index = (ROOT / "docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md").read_text()
    for marker in ("Snake Depth V2", "CW-B7", "CW-B8", "CW-B9", "CW-B10", "CW-B11", "草稿候选", "CI 通过", "已合并", "已上线", "医生验收"):
        assert marker in index, marker
    print(json.dumps({"status":"PASS", "baseline":BASE, "baseline_tree":TREE, "changed":sorted(changed), "allowed":sorted(ALLOWED), "frozen_cwb10":historical, "external_calls":0}, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
