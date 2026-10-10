"""CW-B25 approved eleven-path increment; prior scopes run on their frozen commits."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BASE = '414f7216074415543fb8f7d158f79c19ac874e20'
TREE = '626d810ed3c59e04a55a5bb14a215c4f3a8dc0cf'
ALLOWED = {
    'frontend/src/components/ClinicalLabTable.css',
    'frontend/src/components/CaseLabResults.jsx',
    'frontend/src/components/CaseLabRangeReview.jsx',
    'frontend/src/components/ClinicalDocLabSelection.jsx',
    'frontend/src/pages/CaseDetail.jsx',
    'tests/fixtures/clinical_lab_readability_cw_b25_cases.json',
    'tests/acceptance/clinical_lab_readability_checks.cjs',
    'scripts/validate_clinical_lab_readability_cw_b25.py',
    'docs/clinical_docs/CLINICAL_LAB_READABILITY_CW_B25.md',
    '.github/workflows/consult-browser-postgres.yml',
    'docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md',
}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def main():
    subprocess.check_call(['git', 'merge-base', '--is-ancestor', BASE, 'HEAD'], cwd=ROOT)
    assert git('rev-parse', BASE+'^{tree}') == TREE
    changed = set(git('diff', '--name-only', BASE).splitlines()) | set(git('ls-files', '--others', '--exclude-standard').splitlines())
    assert len(ALLOWED) == 11 and changed == ALLOWED, sorted(changed ^ ALLOWED)
    assert all((ROOT/p).is_file() and not (ROOT/p).is_symlink() for p in changed)
    with tempfile.TemporaryDirectory(prefix='cwb25-frozen-') as temporary:
        frozen = str(Path(temporary)/'cw24')
        subprocess.check_call(['git', 'worktree', 'add', '--detach', '--quiet', frozen, BASE], cwd=ROOT)
        try:
            historical = json.loads(subprocess.check_output([sys.executable, '-B', 'scripts/validate_clinical_visit_journey_cw_b24.py'], cwd=frozen, text=True))
        finally:
            subprocess.check_call(['git', 'worktree', 'remove', frozen], cwd=ROOT)
    assert historical['status'] == 'PASS'
    workflow = (ROOT/'.github/workflows/consult-browser-postgres.yml').read_text()
    previous = git('show', BASE+':.github/workflows/consult-browser-postgres.yml')
    for line in previous.splitlines():
        if any(token in line for token in ('python tests/', 'node tests/', 'npm --prefix', 'retention-days:', 'pdftotext', 'PDF lost literal')):
            assert line in workflow, 'Removed historical gate: '+line
    marker = '      - name: Package and verify complete evidence in bounded parts'
    assert workflow[workflow.index(marker):].strip() == previous[previous.index(marker):].strip()
    assert '    timeout-minutes: 30' in workflow
    for token in ('cwb25-scope.json', 'frozen_cwb24', 'clinical_lab_readability_checks.cjs'):
        assert token in workflow, token
    index = 'docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md'
    assert (ROOT/index).read_text().startswith(git('show', BASE+':'+index))
    assert 'CW-B25' in (ROOT/index).read_text() and 'Snake Depth V2' in (ROOT/index).read_text()
    print(json.dumps({'status':'PASS', 'baseline':BASE, 'baseline_tree':TREE,
                      'allowed':sorted(ALLOWED), 'changed':sorted(changed),
                      'frozen_cwb24':historical, 'external_business_calls':0}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
