"""Read-only CW-B21 path gate; execute historical gates on their frozen commits."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BASE = "a6ad9166b19984f535eed39ecd5c22a7a47b4369"
TREE = "1ea8dc856e567c128753b340060e282b67988a94"
ALLOWED = set(['backend/clinical_followup_contact_documents.py', 'backend/clinical_docs_api.py', 'frontend/src/followupContactDocuments.js', 'frontend/src/components/ClinicalDocFollowupContactSelection.jsx', 'frontend/src/components/ClinicalDocReview.jsx', 'frontend/src/pages/CaseDetail.jsx', 'frontend/tests/followup-contact-documents.test.jsx', 'frontend/tests/case-detail-followup-contact-documents.test.jsx', 'frontend/tests/run-consult-update-review.mjs', 'tests/test_clinical_followup_contact_documents.py', 'tests/test_clinical_followup_contact_document_concurrency.py', 'tests/test_clinical_followup_contact_document_isolation.py', 'tests/acceptance/clinical_followup_contact_document_checks.cjs', 'tests/acceptance/postgres_checks.py', 'tests/acceptance/fixture.py', 'tests/fixtures/clinical_followup_contact_documents_cw_b21_cases.json', '.github/workflows/consult-browser-postgres.yml', 'scripts/validate_clinical_followup_contact_documents_cw_b21.py', 'docs/clinical_docs/CLINICAL_FOLLOWUP_CONTACT_DOCUMENTS_CW_B21.md', 'docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md'])


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main():
    subprocess.check_call(["git", "merge-base", "--is-ancestor", BASE, "HEAD"], cwd=ROOT)
    assert git("rev-parse", BASE + "^{tree}") == TREE
    changed = set(git("diff", "--name-only", BASE).splitlines()) | set(git("ls-files", "--others", "--exclude-standard").splitlines())
    assert len(ALLOWED) == 20 and 0 < len(changed) <= 20 and changed <= ALLOWED, sorted(changed - ALLOWED)
    assert all((ROOT / path).is_file() for path in changed)
    with tempfile.TemporaryDirectory(prefix="cwb21-frozen-") as temporary:
        frozen = str(Path(temporary) / "cw20")
        subprocess.check_call(["git", "worktree", "add", "--detach", "--quiet", frozen, BASE], cwd=ROOT)
        try:
            historical = json.loads(subprocess.check_output([sys.executable, "-B", "scripts/validate_clinical_followup_contact_overview_cw_b20.py"], cwd=frozen, text=True))
        finally:
            subprocess.check_call(["git", "worktree", "remove", frozen], cwd=ROOT)
    assert historical["status"] == "PASS"
    workflow = (ROOT / ".github/workflows/consult-browser-postgres.yml").read_text()
    previous = git("show", BASE + ":.github/workflows/consult-browser-postgres.yml")
    for line in previous.splitlines():
        if any(token in line for token in ("python tests/", "node tests/", "npm --prefix", "retention-days:")):
            assert line in workflow, line
    marker = "      - name: Package and verify complete evidence in bounded parts"
    assert workflow[workflow.index(marker):].strip() == previous[previous.index(marker):].strip()
    for marker in ("cwb20-scope.json", "cwb21-scope.json", "test_clinical_followup_contact_documents.py", "test_clinical_followup_contact_document_concurrency.py", "test_clinical_followup_contact_document_isolation.py", "clinical_followup_contact_document_checks.cjs", "cwb21-doc-samples"):
        assert marker in workflow, marker
    previous_runner = git("show", BASE + ":frontend/tests/run-consult-update-review.mjs")
    addition = "  names.push('followup-contact-documents', 'case-detail-followup-contact-documents');\n"
    runner = (ROOT / "frontend/tests/run-consult-update-review.mjs").read_text()
    assert runner.count(addition) == 1 and runner.replace(addition, "").strip() == previous_runner
    previous_index = git("show", BASE + ":docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md")
    index = (ROOT / "docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md").read_text()
    assert index.startswith(previous_index) and "CW-B21" in index and "Snake Depth V2" in index
    print(json.dumps({"status": "PASS", "baseline": BASE, "baseline_tree": TREE, "changed": sorted(changed), "allowed": sorted(ALLOWED), "frozen_cwb20": historical, "external_calls": 0}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
