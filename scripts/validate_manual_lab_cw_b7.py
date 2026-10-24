"""Read-only scope gate; historical CW-B6 executes on its frozen actual commit."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BASE = "b981aed400db46e2ebc40610bfab805871bc0a51"
TREE = "561ffbfb77270a16605c1403c1ec9d4ab9554f85"
ALLOWED = set(['backend/manual_lab_results.py', 'backend/manual_lab_results_api.py', 'backend/main.py', 'backend/case_attachment_service.py', 'backend/diagnostic_data_api.py', 'backend/clinical_docs_api.py', 'backend/audit_log_api.py', 'frontend/src/pages/CaseDetail.jsx', 'frontend/src/components/CaseLabResults.jsx', 'frontend/src/manualLabResults.js', 'frontend/src/components/CaseAttachments.jsx', 'frontend/tests/manual-lab-results.test.jsx', 'frontend/tests/case-detail-documents.test.jsx', 'frontend/tests/run-consult-update-review.mjs', 'tests/test_manual_lab_results.py', 'tests/test_manual_lab_result_concurrency.py', 'tests/test_clinical_doc_lifecycle.py', 'tests/acceptance/manual_lab_checks.cjs', 'tests/acceptance/postgres_checks.py', 'tests/fixtures/manual_lab_cw_b7_cases.json', '.github/workflows/consult-browser-postgres.yml', 'scripts/validate_manual_lab_cw_b7.py', 'docs/clinical_docs/MANUAL_LAB_RESULTS_CW_B7.md', 'docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md'])


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main():
    subprocess.check_call(["git", "merge-base", "--is-ancestor", BASE, "HEAD"], cwd=ROOT)
    assert git("rev-parse", BASE + "^{tree}") == TREE
    changed = set(git("diff", "--name-only", BASE).splitlines()) | set(git("ls-files", "--others", "--exclude-standard").splitlines())
    assert len(ALLOWED) == 24 and 0 < len(changed) <= 24 and changed <= ALLOWED, sorted(changed - ALLOWED)
    assert all((ROOT / path).is_file() for path in ALLOWED)
    with tempfile.TemporaryDirectory(prefix="cwb7-frozen-") as temporary:
        frozen = str(Path(temporary) / "cw6")
        subprocess.check_call(["git", "worktree", "add", "--detach", "--quiet", frozen, BASE], cwd=ROOT)
        try:
            historical = json.loads(subprocess.check_output([sys.executable, "-B", "scripts/validate_case_attachments_cw_b6.py"], cwd=frozen, text=True))
        finally:
            subprocess.check_call(["git", "worktree", "remove", frozen], cwd=ROOT)
    assert historical["status"] == "PASS"
    workflow = (ROOT / ".github/workflows/consult-browser-postgres.yml").read_text()
    for marker in ("m7-scope.json", "outpatient-identity-scope.json", "b1-scope.json", "b2-scope.json", "b3-scope.json", "b4-scope.json", "cwb5-scope.json", "cwb6-scope.json", "cwb7-scope.json", "npm --prefix frontend audit", "manual_lab_checks.cjs", "test_manual_lab_result_concurrency.py"):
        assert marker in workflow, marker
    index = (ROOT / "docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md").read_text()
    for marker in ("Snake Depth V2", "CW-B7", "草稿候选", "CI 通过", "已合并", "已上线", "医生验收"):
        assert marker in index, marker
    print(json.dumps({"status":"PASS", "baseline":BASE, "baseline_tree":TREE, "changed":sorted(changed), "allowed":sorted(ALLOWED), "frozen_cwb6":historical, "external_calls":0}, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
