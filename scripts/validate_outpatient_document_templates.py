#!/usr/bin/env python3
"""Validate the M2 DOCX asset contract without importing or starting the app."""
import ast
import hashlib
import json
from pathlib import Path
import re
import zipfile
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
CASE_FIELDS = {
    'visit.case_id': 'id', 'visit.pet_name': 'patient_name', 'visit.species': 'species',
    'visit.age': 'age_info', 'visit.sex': 'sex', 'visit.weight': 'weight',
    'visit.complaint': 'chief_complaint', 'visit.history': 'history',
    'visit.exam': 'exam_findings', 'visit.assessment': 'analysis',
    'visit.plan': 'treatment', 'visit.notes': 'prognosis',
}
TEMPLATES = ('outpatient_record_zh', 'owner_visit_summary_zh')
KEYS = set(CASE_FIELDS) | {'visit.follow_up', 'export.account_id', 'timestamp', 'hash'}


def main():
    manifest = json.loads((ROOT / 'templates/clinical_docs/CLINICAL_DOCS_TEMPLATE_ASSETS_MANIFEST.json').read_text())
    entries = {item['template_id']: item for item in manifest['generated_assets']}
    assert len(entries) == len(manifest['generated_assets']), 'Duplicate template IDs'
    assert set(entries) == set(TEMPLATES) | {'admission_hospitalization_record_bilingual', 'discharge_summary_bilingual'}
    source = ast.parse((ROOT / 'backend/clinical_docs_api.py').read_text())
    mapping = next(ast.literal_eval(node.value) for node in source.body if isinstance(node, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == 'OUTPATIENT_CASE_FIELDS' for t in node.targets))
    assert mapping == CASE_FIELDS, 'Source fields must not reinterpret assessment as final diagnosis'
    for name in TEMPLATES:
        entry = entries[name]
        path = ROOT / f'templates/clinical_docs/{name}.docx'
        assert entry['path'] == str(path.relative_to(ROOT))
        assert entry['sha256'] == hashlib.sha256(path.read_bytes()).hexdigest(), name
        assert set(entry['required_placeholders']) == KEYS
        assert entry['case_field_mapping'] == CASE_FIELDS
        assert entry['signed'] is False and entry['account_source'] == 'authenticated_user_id'
        assert entry['follow_up_source'] == 'no_independent_field'
        with zipfile.ZipFile(path) as z:
            assert z.testzip() is None
            assert not any('vba' in p.lower() or '/embeddings/' in p for p in z.namelist())
            texts = []
            for member in z.namelist():
                if member.endswith('.rels'):
                    rels = ET.fromstring(z.read(member))
                    assert not any(r.attrib.get('TargetMode') == 'External' for r in rels), member
                if not (member.startswith('word/') and member.endswith('.xml')):
                    continue
                xml = ET.fromstring(z.read(member))
                for field in xml.iter(W+'fldSimple'):
                    assert field.get(W+'instr', '').strip() == 'PAGE', 'Unexpected active field'
                assert not list(xml.iter(W+'instrText')), 'Unexpected complex field'
                texts.extend(''.join(t.text or '' for t in p.iter(W+'t')) for p in xml.iter(W+'p'))
            text = '\n'.join(texts)
            assert set(re.findall(r'\{\{([^{}]+)\}\}', text)) == KEYS
            assert '草稿' in text and '待医生核对' in text and '尚未签署' in text
            for unsafe in ['{{final_dx}}', '{{clinician.name}}', '{{follow_up_plan}}', '{{stamp.image}}',
                           '电子章', 'Address TBD', '最终诊断', '医生签名']:
                assert unsafe not in text, unsafe
            body = ET.fromstring(z.read('word/document.xml'))
            for size in body.iter(W+'pgSz'):
                assert (int(size.get(W+'w')), int(size.get(W+'h'))) == (11906, 16838), 'Expected A4 portrait'
            assert not list(body.iter(W+'trHeight')), 'Fixed row height could truncate clinical text'
        print('PASS', name, 'literal fields, draft status, A4, hash and inactive DOCX package')
    print('PASS M2 template contract; legacy entries retained')


if __name__ == '__main__':
    main()
