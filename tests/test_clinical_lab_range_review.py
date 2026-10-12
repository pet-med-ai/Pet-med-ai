"""CW-B11: real JWT, exact decimal matrix, source validation and no business writes."""
import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from sqlalchemy import event
from sqlalchemy.exc import OperationalError
from test_clinical_case_overview import OverviewFixture, f, storage
import clinical_lab_range_review as service
import manual_lab_results as lab

FIXTURE = json.loads((Path(__file__).parent / 'fixtures/clinical_lab_range_review_cw_b11_cases.json').read_text())


class RangeFixture(OverviewFixture):
    def setUp(self):
        super().setUp()
        env = patch.dict(os.environ, {'LAB_RANGE_REVIEW_ENABLED': '1', 'LAB_RANGE_REVIEW_SYNTHETIC_ONLY': '1'})
        env.start(); self.addCleanup(env.stop)
        self.meta = {**self.meta, 'kind': 'lab'}
        self.range_url = f'/api/cases/{self.cid}/lab-range-review'
        self.change_case(**FIXTURE['case'])

    def saved_range(self):
        source, _, _ = self.attach()
        body = self.lab_body(source); body['data'] = copy.deepcopy(FIXTURE['data'])
        result = self.lab_commit(self.lab_review(body))
        self.assertEqual(result.status_code, 200, result.text)
        return source, result.json()['report']

    def ranges(self):
        r = self.client.get(self.range_url, headers=self.owner_headers)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.headers['cache-control'], 'private, no-store')
        self.assertEqual(r.headers['x-pmai-writes-database'], 'false')
        return r.json()


class RangeTests(RangeFixture):
    def test_full_decimal_matrix_and_original_text_exactly_preserved(self):
        source, saved = self.saved_range(); result = self.ranges()
        self.assertEqual(result['schema'], service.SCHEMA); self.assertEqual(result['rules'], service.RULES)
        self.assertEqual(result['counts'], FIXTURE['review']['counts'])
        row = result['reports'][0]
        self.assertEqual(row['report'], FIXTURE['data']['report'])
        self.assertEqual(row['token'], saved['token']); self.assertEqual(row['source']['sha256'], source['sha256'])
        self.assertEqual([r['comparison'] for r in row['items']], FIXTURE['expected'])
        self.assertEqual([r['index'] for r in row['items']], list(range(1, len(row['items']) + 1)))
        self.assertEqual(lab.input_data({'report': row['report'], 'items': row['items']}), FIXTURE['data'])
        self.assertFalse(result['writes_database']); self.assertFalse(result['includes_unsaved_drafts'])
        self.assertEqual(result['snapshot'], self.ranges()['snapshot'])
        f.db.engine.dispose(); self.assertEqual(result['snapshot'], self.ranges()['snapshot'])

    def test_read_only_no_sql_writes_audit_cleanup_or_file_mutation(self):
        self.saved_range(); stale = Path(self.temp.name) / ('e' * 64 + '.tmp'); stale.write_bytes(b'expired synthetic draft'); os.utime(stale, (0, 0))
        before = self.business(); statements = []
        def capture(_c, _cursor, sql, *_):
            if sql.lstrip().split()[0].upper() in {'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER'}: statements.append(sql)
        event.listen(f.db.engine, 'before_cursor_execute', capture)
        try:
            with patch.object(storage.Store, 'cleanup', side_effect=AssertionError('No GET cleanup')): self.ranges()
        finally: event.remove(f.db.engine, 'before_cursor_execute', capture)
        self.assertEqual(statements, []); self.assertEqual(before, self.business())

    def test_real_jwt_other_owner_soft_delete_default_and_environment_gates(self):
        self.assertEqual(self.client.get(self.range_url).status_code, 401)
        self.assertEqual(self.client.get(self.range_url, headers=self.other_headers).status_code, 404)
        for changes in ({'LAB_RANGE_REVIEW_ENABLED': ''}, {'LAB_RANGE_REVIEW_SYNTHETIC_ONLY': ''}, {'MANUAL_LAB_RESULTS_ENABLED': '0'}, {'CASE_ATTACHMENTS_ENABLED': '0'}, {'ENVIRONMENT': 'production'}, {'RENDER': 'true'}):
            with patch.dict(os.environ, changes): self.assertEqual(self.client.get(self.range_url, headers=self.owner_headers).status_code, 503)
        self.client.delete(f'/api/cases/{self.cid}', headers=self.owner_headers)
        self.assertEqual(self.client.get(self.range_url, headers=self.owner_headers).status_code, 404)

    def test_latest_only_withdrawal_and_navigation_tokens(self):
        _, old = self.saved_range(); body = self.lab_body(old=old, operation='correct'); body['data']['items'][0]['value'] = '1.500'
        new = self.lab_commit(self.lab_review(body)).json()['report']
        result = self.ranges()
        self.assertEqual([(r['id'], r['version']) for r in result['reports']], [(new['id'], 2)])
        self.assertEqual([r['state'] for r in result['excluded']], ['superseded']); self.assertNotIn('items', result['excluded'][0])
        self.assertNotEqual(result['excluded'][0]['token'], old['token'])
        self.assertEqual(result['reports'][0]['items'][0]['comparison']['state'], 'between')
        self.lab_commit(self.lab_review(self.lab_body(old=new, operation='withdraw')))
        later = self.ranges(); self.assertEqual(later['reports'], []); self.assertEqual(later['counts']['items'], 0)
        self.assertEqual([r['state'] for r in later['excluded']], ['superseded', 'withdrawn'])

    def test_source_metadata_and_identity_change_excludes_report(self):
        source, _ = self.saved_range()
        self.meta = {**self.meta, 'title': '合成来源更正'}; self.commit(self.reviewed(self.body(source, 'update')))
        self.assertEqual(self.ranges()['excluded'][0]['state'], 'needs_review')
        self.change_case(owner_name='身份已更正'); self.assertEqual(self.ranges()['reports'], [])

    def test_missing_corrupt_withdrawn_sources_never_compare(self):
        source, _ = self.saved_range(); path = storage.Store().path(source['id'], '.blob'); original = path.read_bytes()
        path.write_bytes(b'corrupt'); self.assertEqual(self.ranges()['excluded'][0]['state'], 'source_unavailable')
        path.unlink(); self.assertEqual(self.ranges()['reports'], [])
        path.write_bytes(original); self.assertEqual(len(self.ranges()['reports']), 1)
        self.commit(self.reviewed(self.body(source, 'withdraw'))); self.assertEqual(self.ranges()['excluded'][0]['state'], 'source_unavailable')

    def test_malformed_saved_structure_decimal_units_and_version_fail_closed(self):
        _, saved = self.saved_range()
        with f.db.SessionLocal() as db: original = copy.deepcopy(db.get(f.models.DiagnosticReport, saved['id']).metadata_json)
        variants = [{**original, **delta} for delta in ({'schema': 'unknown'}, {'version': 2}, {'root_id': 9999}, {'identity': {}}, {'source_digest': '0'*64}, {'data': {}})]
        for key, value in [('decimal', 'NaN'), ('decimal', '0.5'), ('reference_unit', 'mg/dL'), ('reference_low_decimal', 'bad'), ('value', 'not a number'), ('checked', False), ('result_type', 'unknown')]:
            bad = copy.deepcopy(original); bad['data']['items'][0][key] = value; variants.append(bad)
        for variant in variants:
            with f.db.SessionLocal() as db: db.get(f.models.DiagnosticReport, saved['id']).metadata_json = variant; db.commit()
            r = self.client.get(self.range_url, headers=self.owner_headers)
            self.assertEqual(r.status_code, 409, r.text); self.assertEqual(r.json(), {'detail': 'lab_range_review_data_unreadable'})

    def test_cross_owner_original_metadata_and_unknown_case_structure_fail(self):
        self.saved_range()
        with f.db.SessionLocal() as db:
            case = db.get(f.models.Case, self.cid); original = copy.deepcopy(case.attachments)
        for value in ([{**original[0], 'owner': str(self.owner_id) + "-other"}], [{**original[0], 'case_id': self.cid + 100}], {'unknown': []}):
            with f.db.SessionLocal() as db: db.get(f.models.Case, self.cid).attachments = value; db.commit()
            self.assertEqual(self.client.get(self.range_url, headers=self.owner_headers).status_code, 409)

    def test_legacy_and_empty_are_separate_from_current_comparisons(self):
        self.assertEqual(self.ranges()['counts']['items'], 0)
        with f.db.SessionLocal() as db:
            db.add(f.models.DiagnosticReport(case_id=self.cid, source_type='legacy', status='confirmed', report_type='lab')); db.commit()
        result = self.ranges(); self.assertEqual(result['legacy_count'], 1); self.assertEqual(result['reports'], [])

    def test_backend_failure_not_an_empty_success(self):
        with patch.object(service, 'assemble', side_effect=OperationalError('synthetic', {}, Exception('offline'))):
            r = self.client.get(self.range_url, headers=self.owner_headers)
        self.assertEqual(r.status_code, 503); self.assertEqual(r.json(), {'detail': 'lab_range_review_read_failed'})
        self.assertEqual(r.headers['cache-control'], 'private, no-store')


if __name__ == '__main__': unittest.main(verbosity=2)
