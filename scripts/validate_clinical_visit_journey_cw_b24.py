"""CW-B24 exact approved scope and frozen CW-B23 acceptance chain."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BASE = '07a4c31bdbad3c0225641ab8faf23dc3357cf9eb'
TREE = '1cda1f540355752022580c81b86a27908244a9e3'
ALLOWED = set(['tests/acceptance/clinical_visit_journey_checks.cjs', 'tests/acceptance/clinical_visit_journey_readback.py', 'tests/acceptance/clinical_visit_journey_harness.cjs', 'tests/fixtures/clinical_visit_journey_cw_b24_cases.json', 'tests/test_clinical_visit_journey_evidence.py', 'scripts/validate_clinical_visit_journey_cw_b24.py', 'docs/clinical_docs/CLINICAL_VISIT_JOURNEY_CW_B24.md', 'docs/product/PET_MED_AI_FIRST_CLINIC_ACCEPTANCE_MATRIX_CW_B24.md', 'tests/acceptance/clinical_case_overview_checks.cjs', 'tests/acceptance/fixture.py', '.github/workflows/consult-browser-postgres.yml', 'docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md'])


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def main():
    subprocess.check_call(['git', 'merge-base', '--is-ancestor', BASE, 'HEAD'], cwd=ROOT)
    assert git('rev-parse', BASE+'^{tree}') == TREE
    changed = set(git('diff', '--name-only', BASE).splitlines()) | set(git('ls-files', '--others', '--exclude-standard').splitlines())
    assert len(ALLOWED) == 12 and 0 < len(changed) <= 12 and changed <= ALLOWED, sorted(changed-ALLOWED)
    assert all((ROOT/path).is_file() for path in changed)
    with tempfile.TemporaryDirectory(prefix='cwb24-frozen-') as temporary:
        frozen = str(Path(temporary)/'cw23')
        subprocess.check_call(['git', 'worktree', 'add', '--detach', '--quiet', frozen, BASE], cwd=ROOT)
        try:
            historical = json.loads(subprocess.check_output([sys.executable, '-B', 'scripts/validate_clinical_followup_contact_queue_cw_b23.py'], cwd=frozen, text=True))
        finally:
            subprocess.check_call(['git', 'worktree', 'remove', frozen], cwd=ROOT)
    assert historical['status'] == 'PASS'
    workflow = (ROOT/'.github/workflows/consult-browser-postgres.yml').read_text()
    previous = git('show', BASE+':.github/workflows/consult-browser-postgres.yml')
    for line in previous.splitlines():
        if any(token in line for token in ('python tests/', 'node tests/', 'npm --prefix', 'retention-days:')):
            assert line in workflow, line
    marker = '      - name: Package and verify complete evidence in bounded parts'
    assert workflow[workflow.index(marker):].strip() == previous[previous.index(marker):].strip()
    assert '    timeout-minutes: 30' in workflow
    for token in ('cwb24-scope.json', 'frozen_cwb23', 'test_clinical_visit_journey_evidence.py', 'clinical_visit_journey_checks.cjs', 'cwb24-independent-readback.json', 'cwb24-render-manifest.json'):
        assert token in workflow, token
    # Old clinical checks must survive unchanged. Only observed routing/teardown lines may differ.
    old = git('show', BASE+':tests/acceptance/clinical_case_overview_checks.cjs')
    new = (ROOT/'tests/acceptance/clinical_case_overview_checks.cjs').read_text()
    for line in old.splitlines():
        if any(token in line for token in ('assert.', 'expect(', 'passed.push(', 'sourceOp(', 'call(')):
            assert line in new, 'Removed historical clinical assertion: '+line
    index = 'docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md'
    assert (ROOT/index).read_text().startswith(git('show', BASE+':'+index))
    assert 'CW-B24' in (ROOT/index).read_text() and 'Snake Depth V2' in (ROOT/index).read_text()
    print(json.dumps({'status':'PASS','baseline':BASE,'baseline_tree':TREE,'changed':sorted(changed),
                      'allowed':sorted(ALLOWED),'frozen_cwb23':historical,'external_calls':0},ensure_ascii=False,indent=2))


if __name__ == '__main__':main()
