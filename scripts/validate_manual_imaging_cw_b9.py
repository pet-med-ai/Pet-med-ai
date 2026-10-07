"""Read-only scope gate; historical CW-B8 executes on its frozen actual commit."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BASE = "cdd80aa02eb23522557eb225f788ebcecef4f272"
TREE = "3a45b7e5e85e110d2e550e8231dc9eb7234634ff"
ALLOWED = set(['backend/manual_imaging_records.py', 'backend/manual_imaging_records_api.py', 'backend/manual_imaging_documents.py', 'backend/main.py', 'backend/case_attachment_service.py', 'backend/diagnostic_data_api.py', 'backend/clinical_docs_api.py', 'backend/manual_lab_documents.py', 'backend/kpi_api.py', 'frontend/src/pages/CaseDetail.jsx', 'frontend/src/components/CaseImagingRecords.jsx', 'frontend/src/manualImagingRecords.js', 'frontend/src/components/ClinicalDocReview.jsx', 'frontend/src/components/ClinicalDocImagingSelection.jsx', 'frontend/src/manualImagingDocuments.js', 'frontend/tests/manual-imaging-records.test.jsx', 'frontend/tests/manual-imaging-documents.test.jsx', 'frontend/tests/case-detail-documents.test.jsx', 'frontend/tests/run-consult-update-review.mjs', 'tests/test_manual_imaging_records.py', 'tests/test_manual_imaging_concurrency.py', 'tests/test_manual_imaging_documents.py', 'tests/acceptance/manual_imaging_checks.cjs', 'tests/acceptance/postgres_checks.py', 'tests/acceptance/fixture.py', 'tests/fixtures/manual_imaging_cw_b9_cases.json', '.github/workflows/consult-browser-postgres.yml', 'scripts/validate_manual_imaging_cw_b9.py', 'docs/clinical_docs/MANUAL_IMAGING_CW_B9.md', 'docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md'])


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main():
    subprocess.check_call(["git", "merge-base", "--is-ancestor", BASE, "HEAD"], cwd=ROOT)
    assert git("rev-parse", BASE + "^{tree}") == TREE
    changed = set(git("diff", "--name-only", BASE).splitlines()) | set(git("ls-files", "--others", "--exclude-standard").splitlines())
    assert len(ALLOWED) == 30 and 0 < len(changed) <= 30 and changed <= ALLOWED, sorted(changed - ALLOWED)
    assert all((ROOT / path).is_file() for path in changed)
    with tempfile.TemporaryDirectory(prefix="cwb9-frozen-") as temporary:
        frozen = str(Path(temporary) / "cw8")
        subprocess.check_call(["git", "worktree", "add", "--detach", "--quiet", frozen, BASE], cwd=ROOT)
        try:
            historical = json.loads(subprocess.check_output([sys.executable, "-B", "scripts/validate_manual_lab_documents_cw_b8.py"], cwd=frozen, text=True))
        finally:
            subprocess.check_call(["git", "worktree", "remove", frozen], cwd=ROOT)
    assert historical["status"] == "PASS"
    workflow = (ROOT / ".github/workflows/consult-browser-postgres.yml").read_text()
    for marker in ("m7-scope.json", "outpatient-identity-scope.json", "b1-scope.json", "b2-scope.json", "b3-scope.json", "b4-scope.json", "cwb5-scope.json", "cwb6-scope.json", "cwb7-scope.json", "cwb8-scope.json", "cwb9-scope.json", "manual_imaging_checks.cjs", "test_manual_imaging_concurrency.py", "test_manual_imaging_documents.py", "manual_lab_document_checks.cjs", "test_manual_lab_document_concurrency.py", "npm --prefix frontend audit", "manual_lab_checks.cjs", "test_manual_lab_result_concurrency.py"):
        assert marker in workflow, marker
    index = (ROOT / "docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md").read_text()
    for marker in ("Snake Depth V2", "CW-B7", "CW-B8", "CW-B9", "草稿候选", "CI 通过", "已合并", "已上线", "医生验收"):
        assert marker in index, marker
    print(json.dumps({"status":"PASS", "baseline":BASE, "baseline_tree":TREE, "changed":sorted(changed), "allowed":sorted(ALLOWED), "frozen_cwb8":historical, "external_calls":0}, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
