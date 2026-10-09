"""Read-only CW-B20 path gate; execute historical gates on their frozen commits."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BASE = "4f0dc07967df5a1bec69f23359b29dff5ff23ff7"
TREE = "d50b3b5f1512e4eb3b294819605e4140391ebf23"
ALLOWED = set(['backend/clinical_followup_contact_overview.py', 'backend/clinical_case_overview.py', 'backend/clinical_case_overview_api.py', 'frontend/src/visitOverview.js', 'frontend/src/components/CaseVisitOverview.jsx', 'frontend/src/components/CaseFollowupContacts.jsx', 'frontend/src/pages/CaseDetail.jsx', 'frontend/tests/followup-contact-overview.test.jsx', 'frontend/tests/case-detail-followup-contact-overview.test.jsx', 'frontend/tests/followup-plan-overview.test.jsx', 'frontend/tests/run-consult-update-review.mjs', 'tests/test_clinical_followup_contact_overview.py', 'tests/test_clinical_followup_contact_overview_concurrency.py', 'tests/test_clinical_followup_contact_overview_isolation.py', 'tests/acceptance/clinical_followup_contact_overview_checks.cjs', 'tests/acceptance/postgres_checks.py', 'tests/acceptance/fixture.py', 'tests/fixtures/clinical_followup_contact_overview_cw_b20_cases.json', '.github/workflows/consult-browser-postgres.yml', 'scripts/validate_clinical_followup_contact_overview_cw_b20.py', 'docs/clinical_docs/CLINICAL_FOLLOWUP_CONTACT_OVERVIEW_CW_B20.md', 'docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md'])


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main():
    subprocess.check_call(["git", "merge-base", "--is-ancestor", BASE, "HEAD"], cwd=ROOT)
    assert git("rev-parse", BASE + "^{tree}") == TREE
    changed = set(git("diff", "--name-only", BASE).splitlines()) | set(git("ls-files", "--others", "--exclude-standard").splitlines())
    assert len(ALLOWED) == 22 and 0 < len(changed) <= 22 and changed <= ALLOWED, sorted(changed - ALLOWED)
    assert all((ROOT / path).is_file() for path in changed)
    with tempfile.TemporaryDirectory(prefix="cwb20-frozen-") as temporary:
        frozen = str(Path(temporary) / "cw19")
        subprocess.check_call(["git", "worktree", "add", "--detach", "--quiet", frozen, BASE], cwd=ROOT)
        try:
            historical = json.loads(subprocess.check_output([sys.executable, "-B", "scripts/validate_clinical_followup_contacts_cw_b19.py"], cwd=frozen, text=True))
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
    for marker in ("cwb19-scope.json", "cwb20-scope.json", "test_clinical_followup_contact_overview.py", "test_clinical_followup_contact_overview_concurrency.py", "test_clinical_followup_contact_overview_isolation.py", "clinical_followup_contact_overview_checks.cjs"):
        assert marker in workflow, marker
    # The only permitted historical test change is the second explicit opt-in.
    old_test = git("show", BASE + ":frontend/tests/followup-plan-overview.test.jsx")
    assert old_test.count("{include_followup_plan:true}") == 1
    assert (ROOT / "frontend/tests/followup-plan-overview.test.jsx").read_text().strip() == old_test.replace("{include_followup_plan:true}", "{include_followup_plan:true,include_followup_contacts:true}")
    previous_runner = git("show", BASE + ":frontend/tests/run-consult-update-review.mjs")
    addition = "  names.push('followup-contact-overview', 'case-detail-followup-contact-overview');\n"
    runner = (ROOT / "frontend/tests/run-consult-update-review.mjs").read_text()
    assert runner.count(addition) == 1 and runner.replace(addition, "").strip() == previous_runner
    previous_index = git("show", BASE + ":docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md")
    index = (ROOT / "docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md").read_text()
    assert index.startswith(previous_index) and "CW-B20" in index and "Snake Depth V2" in index
    print(json.dumps({"status": "PASS", "baseline": BASE, "baseline_tree": TREE, "changed": sorted(changed), "allowed": sorted(ALLOWED), "frozen_cwb19": historical, "external_calls": 0}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
