"""CW-B12 real JWT, exact arithmetic, explicit selectors and no business writes."""
import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from sqlalchemy import event
from sqlalchemy.exc import OperationalError
from test_clinical_case_overview import OverviewFixture, f, storage
from build_attachment_cw_b6_fixtures import pdf
import clinical_lab_comparison as service
import manual_lab_results as lab

FIXTURE = json.loads((Path(__file__).parent / 'fixtures/clinical_lab_comparison_cw_b12_cases.json').read_text())


class ComparisonFixture(OverviewFixture):
    def setUp(self):
        super().setUp()
        env = patch.dict(os.environ, {'LAB_COMPARISON_ENABLED': '1', 'LAB_COMPARISON_SYNTHETIC_ONLY': '1', 'LAB_RANGE_REVIEW_ENABLED': '0'})
        env.start(); self.addCleanup(env.stop)
        self.meta = {**self.meta, 'kind': 'lab'}
        self.url = f'/api/cases/{self.cid}/lab-comparison'
        self.change_case(**FIXTURE['case'])

    def save_pair(self, same_source=False):
        sources, reports = [], []
        for i, data in enumerate(FIXTURE['reports']):
            source = sources[0] if same_source and i else self.attach(f'synthetic-{i}.pdf', 'application/pdf', pdf().replace(b'CW-B6', f'CW-B{i}'.encode()))[0]
            body = self.lab_body(source); body['data'] = copy.deepcopy(data)
            r = self.lab_commit(self.lab_review(body)); self.assertEqual(r.status_code, 200, r.text)
            sources.append(source); reports.append(r.json()['report'])
        return sources, reports

    def read_comparison(self):
        r = self.client.get(self.url, headers=self.owner_headers)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.headers['cache-control'], 'private, no-store')
        return r.json()

    def request_body(self, data=None, index=0, confirmed=True):
        data = data or self.read_comparison()
        return {'snapshot': data['snapshot'], 'a': service.selection(data['reports'][0], data['reports'][0]['items'][index]),
                'b': service.selection(data['reports'][1], data['reports'][1]['items'][index]), 'doctor_confirmed': confirmed}

    def preview(self, body=None, expected=200):
        r = self.client.post(self.url + '/preview', headers=self.owner_headers, json=body or self.request_body())
        self.assertEqual(r.status_code, expected, r.text)
        self.assertEqual(r.headers['cache-control'], 'private, no-store')
        self.assertEqual(r.headers['x-pmai-writes-database'], 'false')
        return r.json()


class ComparisonTests(ComparisonFixture):
    def test_exact_saved_matrix_provenance_and_decimal_difference(self):
        sources, rows = self.save_pair(); saved = self.read_comparison()
        self.assertEqual(saved['schema'], service.SCHEMA); self.assertEqual(saved['rules'], service.RULES)
        for i, row in enumerate(saved['reports']):
            self.assertEqual(lab.input_data({'report': row['report'], 'items': row['items']}), FIXTURE['reports'][i])
            self.assertEqual(row['token'], rows[i]['token']); self.assertEqual(row['source']['sha256'], sources[i]['sha256'])
        for i, expected in enumerate(FIXTURE['expected_deltas']):
            result = self.preview(self.request_body(saved, i))
            self.assertEqual(result['delta']['value'], expected)
            self.assertEqual(result['delta']['state'], 'same' if expected == '0' else 'decrease' if expected[0] == '-' else 'increase')
            self.assertTrue(result['reference_changed']); self.assertTrue(result['can_calculate'])
        for i in range(7, 11):
            result = self.preview(self.request_body(saved, i)); self.assertIsNone(result['delta']); self.assertIn('non_numeric', result['reasons'])
        self.assertEqual(self.preview(self.request_body(saved, confirmed=False))['reasons'], ['doctor_confirmation_required'])
        f.db.engine.dispose(); self.assertEqual(self.read_comparison()['snapshot'], saved['snapshot'])

    def test_exact_conditions_no_normalization_no_override(self):
        a, b = copy.deepcopy(FIXTURE['review']['reports'])
        for field in ('panel', 'specimen', 'laboratory', 'device'):
            for value, suffix in [('', 'missing'), ('other' if field == 'panel' else a['report'][field] + ' ', 'mismatch')]:
                changed = copy.deepcopy(b); changed['report'][field] = value
                result = service.compare((a, a['items'][0]), (changed, changed['items'][0]), True)
                self.assertIn(field + '_' + suffix, result['reasons']); self.assertIsNone(result['delta'])
        for field, value, code in [('name', '零 ', 'item_name_mismatch'), ('unit', '', 'unit_missing'), ('unit', 'mmol/l', 'unit_mismatch')]:
            changed = {**b['items'][0], field: value}
            self.assertIn(code, service.compare((a, a['items'][0]), (b, changed), True)['reasons'])
        equal = copy.deepcopy(b); equal['items'][0].update({k: a['items'][0][k] for k in service.REFERENCES})
        self.assertFalse(service.compare((a, a['items'][0]), (equal, equal['items'][0]), True)['reference_changed'])

    def test_sampling_time_timezone_microseconds_missing_equal_and_reverse(self):
        a, b = copy.deepcopy(FIXTURE['review']['reports'])
        for at, bt, reason in [
            ('2026-10-07T00:01:00+08:00', '2026-10-06T16:02:00Z', None),
            ('2026-10-07T09:30:00.000001+08:00', '2026-10-07T01:30:00.000002Z', None),
            ('2026-10-07T09:30:00+08:00', '2026-10-07T01:30:00Z', 'collected_at_equal'),
            ('2026-10-07T09:30:00+08:00', '2026-10-07T01:29:59Z', 'collected_at_reversed'),
            ('', '2026-10-07T01:30:00Z', 'collected_at_missing')]:
            a['report']['collected_at'], b['report']['collected_at'] = at, bt
            result = service.compare((a, a['items'][0]), (b, b['items'][0]), True)
            self.assertEqual(result['reasons'], [reason] if reason else [])

    def test_read_and_post_are_readonly_without_cleanup_or_audit(self):
        self.save_pair(); body = self.request_body(); stale = Path(self.temp.name) / ('e' * 64 + '.tmp')
        stale.write_bytes(b'expired synthetic draft'); os.utime(stale, (0, 0))
        before = self.business(); statements = []
        def capture(_c, _cur, sql, *_):
            if sql.lstrip().split()[0].upper() in {'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER'}: statements.append(sql)
        event.listen(f.db.engine, 'before_cursor_execute', capture)
        try:
            with patch.object(storage.Store, 'cleanup', side_effect=AssertionError('No comparison cleanup')):
                self.read_comparison(); self.preview(body); self.preview({**body, 'doctor_confirmed': False})
        finally: event.remove(f.db.engine, 'before_cursor_execute', capture)
        self.assertEqual(statements, []); self.assertEqual(self.business(), before)

    def test_real_auth_case_isolation_soft_delete_and_default_environment_gates(self):
        self.save_pair(); body = self.request_body()
        for method, url, kwargs in [('get', self.url, {}), ('post', self.url + '/preview', {'json': body})]:
            self.assertEqual(getattr(self.client, method)(url, **kwargs).status_code, 401)
            self.assertEqual(getattr(self.client, method)(url, headers=self.other_headers, **kwargs).status_code, 404)
        for changes in ({'LAB_COMPARISON_ENABLED': ''}, {'LAB_COMPARISON_SYNTHETIC_ONLY': ''}, {'MANUAL_LAB_RESULTS_ENABLED': '0'}, {'CASE_ATTACHMENTS_ENABLED': '0'}, {'ENVIRONMENT': 'production'}, {'RENDER': 'true'}):
            with patch.dict(os.environ, changes):
                self.assertEqual(self.client.get(self.url, headers=self.owner_headers).status_code, 503); self.preview(body, 503)
        cid2 = self.client.post('/api/cases', headers=self.owner_headers, json=FIXTURE['case']).json()['id']
        self.assertEqual(self.client.post(f'/api/cases/{cid2}/lab-comparison/preview', headers=self.owner_headers, json=body).status_code, 409)
        self.client.delete(f'/api/cases/{self.cid}', headers=self.owner_headers)
        self.assertEqual(self.client.get(self.url, headers=self.owner_headers).status_code, 404); self.preview(body, 404)

    def test_exact_selector_snapshot_and_illegal_client_values(self):
        self.save_pair(); body = self.request_body()
        for changed in ({'snapshot': '0'*64}, {'a': {**body['a'], 'token': '0'*64}}, {'a': {**body['a'], 'version': 2}}, {'a': {**body['a'], 'index': 2}}, {'a': {**body['a'], 'position': 'different'}}, {'a': {**body['a'], 'id': body['b']['id']}}):
            self.preview({**body, **changed}, 409)
        for changed in ({'value': '99'}, {'doctor_confirmed': 1}, {'snapshot': 'bad'}, {'a': {**body['a'], 'id': True}}, {'a': {**body['a'], 'index': '1'}}, {'a': {**body['a'], 'value': '999'}}, {'a': None}):
            self.preview({**body, **changed}, 422)

    def test_same_root_and_same_original_cannot_be_two_samples(self):
        sources, _ = self.save_pair(); body = self.request_body()
        duplicate = self.lab_body(sources[0]); duplicate['data'] = copy.deepcopy(FIXTURE['reports'][1])
        r = self.client.post(self.labroot + '/preview', headers=self.owner_headers, json=duplicate)
        self.assertEqual(r.status_code, 409); self.assertEqual(r.json()['detail'], 'manual_lab_report_exists')
        a, b = copy.deepcopy(FIXTURE['review']['reports']); b['source']['sha256'] = a['source']['sha256']
        self.assertIn('same_source', service.compare((a, a['items'][0]), (b, b['items'][0]), True)['reasons'])
        reasons = self.preview({**body, 'b': body['a']})['reasons']
        self.assertIn('same_report_root', reasons); self.assertIn('collected_at_equal', reasons)

    def test_corrected_versions_excluded_and_old_selection_never_substituted(self):
        _, rows = self.save_pair(); before = self.read_comparison(); old = self.request_body(before)
        body = self.lab_body(old=rows[0], operation='correct'); body['data']['items'][0]['value'] = '1.500'
        new = self.lab_commit(self.lab_review(body)).json()['report']; data = self.read_comparison()
        self.assertEqual(len(data['reports']), 2); self.assertEqual(data['excluded'][0]['state'], 'superseded')
        self.assertNotIn('items', data['excluded'][0]); self.preview(old, 409)
        self.preview({**old, 'snapshot': data['snapshot']}, 409)
        self.lab_commit(self.lab_review(self.lab_body(old=new, operation='withdraw')))
        self.assertEqual([r['state'] for r in self.read_comparison()['excluded']], ['superseded', 'withdrawn'])

    def test_source_loss_metadata_and_identity_invalidate_before_preview(self):
        sources, _ = self.save_pair(); body = self.request_body()
        file = storage.Store().path(sources[0]['id'], '.blob'); original = file.read_bytes()
        for operation in ('corrupt', 'missing'):
            file.write_bytes(b'corrupt') if operation == 'corrupt' else file.unlink()
            data = self.read_comparison(); self.assertEqual(data['excluded'][0]['state'], 'source_unavailable'); self.preview(body, 409)
        file.write_bytes(original)
        self.meta = {**self.meta, 'title': '合成来源更正'}; self.commit(self.reviewed(self.body(sources[0], 'update')))
        self.assertEqual(self.read_comparison()['excluded'][0]['state'], 'needs_review'); self.preview(body, 409)
        self.change_case(owner_name='合成身份更正'); self.assertEqual(self.read_comparison()['reports'], [])

    def test_malformed_saved_data_is_failure_not_noncomparable(self):
        _, rows = self.save_pair(); body = self.request_body()
        with f.db.SessionLocal() as db: original = copy.deepcopy(db.get(f.models.DiagnosticReport, rows[0]['id']).metadata_json)
        variants = [{**original, **x} for x in ({'schema': 'unknown'}, {'version': 2}, {'root_id': 9999}, {'data': {}})]
        for field, value in [('decimal', 'NaN'), ('value', 'bad'), ('checked', False), ('reference_unit', 'bad')]:
            bad = copy.deepcopy(original); bad['data']['items'][0][field] = value
            if field == 'reference_unit': bad['data']['items'][0].update(reference_low='0', reference_low_decimal='0')
            variants.append(bad)
        for date in ('yesterday', '2026-10-07T01:30:00'):
            bad = copy.deepcopy(original); bad['data']['report']['collected_at'] = date; variants.append(bad)
        for bad in variants:
            with f.db.SessionLocal() as db: db.get(f.models.DiagnosticReport, rows[0]['id']).metadata_json = bad; db.commit()
            self.assertEqual(self.client.get(self.url, headers=self.owner_headers).status_code, 409); self.preview(body, 409)

    def test_legacy_empty_and_backend_failure_are_distinct(self):
        self.assertEqual(self.read_comparison()['reports'], [])
        with f.db.SessionLocal() as db:
            db.add(f.models.DiagnosticReport(case_id=self.cid, source_type='legacy', status='confirmed', report_type='lab')); db.commit()
        self.assertEqual(self.read_comparison()['legacy_count'], 1)
        with patch.object(service, 'assemble', side_effect=OperationalError('synthetic', {}, Exception('offline'))):
            self.assertEqual(self.client.get(self.url, headers=self.owner_headers).status_code, 503)


if __name__ == '__main__': unittest.main(verbosity=2)
