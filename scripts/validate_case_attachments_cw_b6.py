"""Read-only CW-B6 scope and historical-outline guard. No network or DB access."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = "bba87033eb7e392ded7e9d48652a1ac185b04058"
TREE = "f72860b116c474b356fc5f6d988dd71cdacdb12e"
ALLOWED = set(['backend/case_attachment_store.py', 'backend/case_attachment_service.py', 'backend/case_attachments_api.py', 'backend/main.py', 'frontend/src/pages/CaseDetail.jsx', 'frontend/src/components/CaseAttachments.jsx', 'frontend/src/caseAttachments.js', 'frontend/tests/case-attachments.test.jsx', 'frontend/tests/case-detail-documents.test.jsx', 'frontend/tests/run-consult-update-review.mjs', 'tests/test_case_attachment_store.py', 'tests/test_case_attachments.py', 'tests/test_case_attachment_concurrency.py', 'tests/acceptance/attachment_checks.cjs', 'tests/acceptance/postgres_checks.py', 'tests/fixtures/build_attachment_cw_b6_fixtures.py', 'scripts/verify_case_attachment_storage.py', '.github/workflows/consult-browser-postgres.yml', 'docs/clinical_docs/CASE_ATTACHMENTS_CW_B6.md', 'docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md', 'docs/product/PET_MED_AI_FUTURE_DEVELOPMENT_OUTLINE_V1.md', 'scripts/validate_case_attachments_cw_b6.py'])


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main():
    subprocess.check_call(["git", "merge-base", "--is-ancestor", BASE, "HEAD"], cwd=ROOT)
    assert git("rev-parse", BASE + "^{tree}") == TREE
    changed = set(git("diff", "--name-only", BASE).splitlines())
    changed |= set(git("ls-files", "--others", "--exclude-standard").splitlines())
    assert len(ALLOWED) == 22 and 0 < len(changed) <= 22 and changed <= ALLOWED, sorted(changed - ALLOWED)
    assert all((ROOT / p).is_file() for p in ALLOWED)
    outline = "docs/product/PET_MED_AI_FUTURE_DEVELOPMENT_OUTLINE_V1.md"
    old = subprocess.check_output(["git", "show", BASE + ":" + outline], cwd=ROOT, text=True)
    new = (ROOT / outline).read_text()
    addition = "\n## Companion-animal clinical workflow index (CW)\n\nThe parallel clinician workflow and five distinct delivery states are recorded in [PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md](PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md). Historical exotics B5 remains Snake Depth V2; original PRs, commits and budgets are unchanged. This link does not authorize merging, deployment or production data operations.\n"
    assert new == old.rstrip("\n") + "\n" + addition, "Historical outline must be preserved verbatim; only append CW index"
    workflow = (ROOT / ".github/workflows/consult-browser-postgres.yml").read_text()
    assert "b4, voice]" in workflow and BASE in workflow and TREE in workflow
    for marker in ("m7-scope.json", "outpatient-identity-scope.json", "b1-scope.json", "b2-scope.json", "b3-scope.json", "b4-scope.json", "cwb5-scope.json", "cwb6-scope.json", "npm --prefix frontend audit", "attachment_checks.cjs", "test_case_attachment_concurrency.py"):
        assert marker in workflow, marker
    index = (ROOT / "docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md").read_text()
    for marker in ("Snake Depth V2", "CW-B5", "CW-B6", "草稿候选", "CI 通过", "已合并", "已上线", "医生验收"):
        assert marker in index, marker
    print(json.dumps({"status":"PASS", "baseline":BASE, "baseline_tree":TREE, "changed":sorted(changed), "allowed":sorted(ALLOWED), "external_calls":0}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
