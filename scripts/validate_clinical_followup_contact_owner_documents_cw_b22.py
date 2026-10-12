"""Read-only CW-B22 path gate; execute historical gates on their frozen commits."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BASE = "7793ec36df0b79b1c82a770a8b5276d7739c3303"
TREE = "d83122335230f8b767053de4fca0e837dfc39514"
ALLOWED = set(['backend/clinical_followup_contact_documents.py', 'backend/clinical_docs_api.py', 'frontend/src/followupContactDocuments.js', 'frontend/src/components/ClinicalDocFollowupContactSelection.jsx', 'frontend/src/components/ClinicalDocReview.jsx', 'frontend/tests/followup-contact-owner-documents.test.jsx', 'frontend/tests/case-detail-followup-contact-owner-documents.test.jsx', 'frontend/tests/followup-contact-documents.test.jsx', 'frontend/tests/run-consult-update-review.mjs', 'tests/test_clinical_followup_contact_owner_documents.py', 'tests/test_clinical_followup_contact_owner_document_concurrency.py', 'tests/test_clinical_followup_contact_owner_document_isolation.py', 'tests/test_clinical_followup_contact_documents.py', 'tests/acceptance/clinical_followup_contact_owner_document_checks.cjs', 'tests/acceptance/clinical_followup_contact_document_checks.cjs', 'tests/acceptance/postgres_checks.py', 'tests/acceptance/fixture.py', 'tests/fixtures/clinical_followup_contact_owner_documents_cw_b22_cases.json', '.github/workflows/consult-browser-postgres.yml', 'scripts/validate_clinical_followup_contact_owner_documents_cw_b22.py', 'docs/clinical_docs/CLINICAL_FOLLOWUP_CONTACT_OWNER_DOCUMENTS_CW_B22.md', 'docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md'])


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main():
    subprocess.check_call(["git", "merge-base", "--is-ancestor", BASE, "HEAD"], cwd=ROOT)
    assert git("rev-parse", BASE + "^{tree}") == TREE
    changed = set(git("diff", "--name-only", BASE).splitlines()) | set(git("ls-files", "--others", "--exclude-standard").splitlines())
    assert len(ALLOWED) == 22 and 0 < len(changed) <= 22 and changed <= ALLOWED, sorted(changed - ALLOWED)
    assert all((ROOT / path).is_file() for path in changed)
    with tempfile.TemporaryDirectory(prefix="cwb22-frozen-") as temporary:
        frozen = str(Path(temporary) / "cw21")
        subprocess.check_call(["git", "worktree", "add", "--detach", "--quiet", frozen, BASE], cwd=ROOT)
        try:
            historical = json.loads(subprocess.check_output([sys.executable, "-B", "scripts/validate_clinical_followup_contact_documents_cw_b21.py"], cwd=frozen, text=True))
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
    for marker in ("cwb21-scope.json", "cwb22-scope.json", "test_clinical_followup_contact_owner_documents.py", "test_clinical_followup_contact_owner_document_concurrency.py", "test_clinical_followup_contact_owner_document_isolation.py", "clinical_followup_contact_owner_document_checks.cjs", "cwb22-doc-samples"):
        assert marker in workflow, marker
    assert '    timeout-minutes: 30' in workflow
    # Only the three explicitly approved CW-B21 template expectations may change.
    changes = {
      'tests/test_clinical_followup_contact_documents.py': (
        "for template in ('owner_visit_summary_zh','admission_hospitalization_record_bilingual','discharge_summary_bilingual'):",
        "self.assertEqual(self.document(choice,template_id='owner_visit_summary_zh').status_code,503)\n        self.assertEqual(self.document(None,template_id='owner_visit_summary_zh').status_code,422)\n        for template in ('admission_hospitalization_record_bilingual','discharge_summary_bilingual'):"),
      'tests/acceptance/clinical_followup_contact_document_checks.cjs': (
        "await expect(button(doc,'选择人工随访记录附节')).toHaveCount(0);",
        "await expect(button(doc,'选择人工随访记录附节')).toBeVisible();await expect(appendix).toHaveCount(0);await expect(whole).not.toBeChecked();"),
    }
    for path, (old, new) in changes.items():
        previous_test = git('show', BASE + ':' + path)
        assert previous_test.count(old) == 1
        assert (ROOT/path).read_text().strip() == previous_test.replace(old, new)
    path = 'frontend/tests/followup-contact-documents.test.jsx'
    previous_test = git('show', BASE + ':' + path)
    prefix = previous_test[:previous_test.index("test('owner template never offers contact selection'")]
    current_test = (ROOT/path).read_text()
    assert current_test.startswith(prefix) and current_test[len(prefix):].count('test(') == 1
    assert "assert(button('选择人工随访记录附节'))" in current_test[len(prefix):]
    assert "assert(!requests.some(c=>c.url.endsWith('/followup-contacts')))" in current_test[len(prefix):]
    previous_runner = git("show", BASE + ":frontend/tests/run-consult-update-review.mjs")
    addition = "  names.push('followup-contact-owner-documents', 'case-detail-followup-contact-owner-documents');\n"
    runner = (ROOT / "frontend/tests/run-consult-update-review.mjs").read_text()
    assert runner.count(addition) == 1 and runner.replace(addition, "").strip() == previous_runner
    previous_index = git("show", BASE + ":docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md")
    index = (ROOT / "docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md").read_text()
    assert index.startswith(previous_index) and "CW-B22" in index and "Snake Depth V2" in index
    print(json.dumps({"status": "PASS", "baseline": BASE, "baseline_tree": TREE, "changed": sorted(changed), "allowed": sorted(ALLOWED), "frozen_cwb21": historical, "external_calls": 0}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
