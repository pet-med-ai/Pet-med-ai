"""CW-B26 approved thirteen-path increment; prior scopes run on their frozen commits."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BASE = '3063eb61ac722bfa8900246ea8a7833c57beaaa6'
TREE = '3a4d19e4731959bad742cdd93dfb4ac6845c3f36'
ALLOWED = {
    'scripts/run_clinical_doctor_trial_cw_b26.py',
    'tests/acceptance/clinical_doctor_trial_runtime.py',
    'tests/fixtures/clinical_doctor_trial_cw_b26_cases.json',
    'frontend/src/components/ClinicalDoctorTrialGate.jsx',
    'frontend/tests/clinical-doctor-trial.test.jsx',
    'tests/test_clinical_doctor_trial.py',
    'tests/acceptance/clinical_doctor_trial_checks.cjs',
    'scripts/validate_clinical_doctor_trial_cw_b26.py',
    'docs/clinical_docs/CLINICAL_DOCTOR_TRIAL_CW_B26.md',
    'frontend/src/App.jsx',
    'frontend/tests/run-consult-update-review.mjs',
    '.github/workflows/consult-browser-postgres.yml',
    'docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md',
}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def main():
    subprocess.check_call(['git', 'merge-base', '--is-ancestor', BASE, 'HEAD'], cwd=ROOT)
    assert git('rev-parse', BASE+'^{tree}') == TREE
    changed = set(git('diff', '--name-only', BASE).splitlines()) | set(git('ls-files', '--others', '--exclude-standard').splitlines())
    assert len(ALLOWED) == 13 and changed == ALLOWED, sorted(changed ^ ALLOWED)
    assert all((ROOT/p).is_file() and not (ROOT/p).is_symlink() for p in changed)
    with tempfile.TemporaryDirectory(prefix='cwb26-frozen-') as temporary:
        frozen = str(Path(temporary)/'cw25')
        subprocess.check_call(['git', 'worktree', 'add', '--detach', '--quiet', frozen, BASE], cwd=ROOT)
        try:
            historical = json.loads(subprocess.check_output([sys.executable, '-B', 'scripts/validate_clinical_lab_readability_cw_b25.py'], cwd=frozen, text=True))
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
    for token in ('cwb26-scope.json', 'frozen_cwb25', 'clinical_doctor_trial_checks.cjs', 'test_clinical_doctor_trial.py'):
        assert token in workflow, token
    index = 'docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md'
    assert (ROOT/index).read_text().startswith(git('show', BASE+':'+index))
    assert 'CW-B26' in (ROOT/index).read_text() and 'Snake Depth V2' in (ROOT/index).read_text()
    print(json.dumps({'status':'PASS', 'baseline':BASE, 'baseline_tree':TREE,
                      'allowed':sorted(ALLOWED), 'changed':sorted(changed),
                      'frozen_cwb25':historical, 'external_business_calls':0}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
