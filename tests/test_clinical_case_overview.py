"""CW-B10: real JWT, exact saved text and no business writes in a disposable DB."""
import copy
import hashlib
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from sqlalchemy import event
from sqlalchemy.exc import OperationalError
from test_manual_imaging_records import ImagingFixture, f, storage
import clinical_case_overview as overview

FIXTURE = json.loads((Path(__file__).parent / 'fixtures/clinical_case_overview_cw_b10_cases.json').read_text())


class OverviewFixture(ImagingFixture):
    def setUp(self):
        super().setUp()
        env = patch.dict(os.environ, {'VISIT_OVERVIEW_ENABLED': '1', 'VISIT_OVERVIEW_SYNTHETIC_ONLY': '1'})
        env.start(); self.addCleanup(env.stop)
        self.overview_url = f'/api/cases/{self.cid}/visit-overview'
        response = self.client.put(f'/api/cases/{self.cid}', headers=self.owner_headers, json=FIXTURE['case'])
        self.assertEqual(response.status_code, 200, response.text)

    def change_case(self, **fields):
        response = self.client.put(f'/api/cases/{self.cid}', headers=self.owner_headers, json=fields)
        self.assertEqual(response.status_code, 200, response.text)

    def overview(self):
        response = self.client.get(self.overview_url, headers=self.owner_headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers['cache-control'], 'private, no-store')
        return response.json()

    def both_reports(self):
        self.meta = {**self.meta, 'kind': 'dr'}
        image_source, _, image = self.save_image()
        self.meta = {**self.meta, 'kind': 'lab'}
        from build_attachment_cw_b6_fixtures import pdf
        lab_source, _, _ = self.attach('lab.pdf', 'application/pdf', pdf())
        result = self.lab_commit(self.lab_review(self.lab_body(lab_source)))
        self.assertEqual(result.status_code, 200, result.text)
        return image_source, image, lab_source, result.json()['report']

    def business(self):
        with f.db.engine.connect() as connection:
            tables = {table.name: [list(map(str, row)) for row in connection.execute(table.select().order_by(*table.primary_key.columns))]
                      for table in (f.models.Case.__table__, f.models.DiagnosticReport.__table__, f.models.Observation.__table__, f.models.ImagingStudy.__table__, f.models.AuditLog.__table__)}
        files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(self.temp.name).iterdir() if p.is_file() and p.name != '.cw-b6.lock'}
        return tables, files


class OverviewTests(OverviewFixture):
    def test_exact_saved_fields_missing_and_unknown_no_inference(self):
        data = self.overview()
        self.assertEqual(data['schema'], overview.SCHEMA)
        self.assertFalse(data['includes_unsaved_drafts']); self.assertFalse(data['writes_database'])
        self.assertEqual(data['identity']['owner_name'], FIXTURE['case']['owner_name'])
        for field in data['fields']:
            self.assertEqual(field['value'], FIXTURE['case'][field['key']])
            self.assertEqual(field['state'], 'missing' if field['key'] == 'prognosis' else 'recorded')
        self.assertEqual(overview.text_state({'unknown': []}), 'unknown')
        self.assertEqual(overview.text_state(' \n\t'), 'missing')
        self.assertNotIn('diagnosis', data)
        self.assertFalse(any(n['code'] == 'source_without_record' for n in data['notices']))
        self.assertEqual(data['snapshot'], self.overview()['snapshot'])
        long = ('未见异常，不代表排除病变。 < & {{literal}} 🐾\n' * 2000)
        self.change_case(history=long)
        later = self.overview()
        self.assertEqual(next(r['value'] for r in later['fields'] if r['key'] == 'history'), long)
        self.assertNotEqual(data['snapshot'], later['snapshot'])

    def test_read_has_no_sql_writes_cleanup_audit_or_original_changes(self):
        self.both_reports()
        # Even an expired, unreferenced temporary business file must survive a GET.
        stale = Path(self.temp.name) / ('f' * 64 + '.tmp'); stale.write_bytes(b'synthetic-pending')
        os.utime(stale, (0, 0))
        before = self.business(); writes = []
        def listener(_conn, _cursor, sql, *_):
            if sql.lstrip().split()[0].upper() in {'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER'}: writes.append(sql)
        event.listen(f.db.engine, 'before_cursor_execute', listener)
        try:
            with patch.object(storage.Store, 'cleanup', side_effect=AssertionError('GET must not clean up')):
                data = self.overview(); self.assertEqual(data['groups']['lab']['counts']['confirmed'], 1)
                self.assertEqual(data['groups']['imaging']['counts']['confirmed'], 1)
        finally: event.remove(f.db.engine, 'before_cursor_execute', listener)
        self.assertEqual(writes, []); self.assertEqual(self.business(), before)

    def test_real_auth_other_account_deleted_case_and_default_flags(self):
        self.assertEqual(self.client.get(self.overview_url).status_code, 401)
        self.assertEqual(self.client.get(self.overview_url, headers=self.other_headers).status_code, 404)
        for changes in ({'VISIT_OVERVIEW_ENABLED': '0'}, {'VISIT_OVERVIEW_SYNTHETIC_ONLY': '0'}, {'CASE_ATTACHMENTS_ENABLED': '0'}, {'ENVIRONMENT': 'production'}, {'RENDER': 'true'}):
            with patch.dict(os.environ, changes):
                self.assertEqual(self.client.get(self.overview_url, headers=self.owner_headers).status_code, 503)
        self.client.delete(f'/api/cases/{self.cid}', headers=self.owner_headers)
        self.assertEqual(self.client.get(self.overview_url, headers=self.owner_headers).status_code, 404)

    def test_current_versions_are_deduplicated_with_history_and_withdrawal(self):
        _, image, _, lab = self.both_reports()
        for old, body, review, commit, key in [(image, self.image_body, self.image_review, self.image_commit, 'imaging'), (lab, self.lab_body, self.lab_review, self.lab_commit, 'lab')]:
            request = review(body(old=old, operation='correct'))
            new = commit(request).json()['report']
            group = self.overview()['groups'][key]
            self.assertEqual(group['counts']['confirmed'], 1); self.assertEqual(group['counts']['superseded'], 1)
            self.assertEqual([r['state'] for r in group['records']], ['superseded', 'confirmed'])
            commit(review(body(old=new, operation='withdraw')))
            group = self.overview()['groups'][key]
            self.assertEqual(group['counts']['confirmed'], 0); self.assertEqual(group['counts']['withdrawn'], 1)
        before = self.overview(); f.db.engine.dispose()
        self.assertEqual(self.overview()['snapshot'], before['snapshot'])

    def test_sources_changed_missing_corrupt_withdrawn_and_identity(self):
        source, image, _, _ = self.both_reports()
        self.meta = {**source['metadata'], 'title': '合成原件已修改'}
        self.commit(self.reviewed(self.body(source, 'update')))
        self.assertEqual(self.overview()['groups']['imaging']['records'][0]['state'], 'needs_review')
        self.change_case(owner_name='更正合成宠主')
        self.assertEqual(self.overview()['groups']['lab']['records'][0]['state'], 'needs_review')
        path = storage.Store().path(source['id'], '.blob'); path.write_bytes(b'damaged')
        for missing in (False, True):
            if missing: path.unlink()
            data = self.overview()
            self.assertEqual(data['groups']['imaging']['records'][0]['state'], 'source_unavailable')
            self.assertEqual(data['groups']['attachments']['counts']['source_unavailable'], 1)
        self.commit(self.reviewed(self.body(source, 'withdraw')))
        data = self.overview()
        self.assertEqual(data['groups']['attachments']['counts']['withdrawn'], 1)
        self.assertEqual(data['groups']['imaging']['records'][0]['source_state'], 'withdrawn')

    def test_unlinked_source_legacy_and_disabled_are_not_missing_or_normal(self):
        self.attach()
        data = self.overview(); self.assertTrue(any(n['code'] == 'source_without_record' for n in data['notices']))
        with f.db.SessionLocal() as db:
            case = db.get(f.models.Case, self.cid); case.attachments = [*case.attachments, {'url': 'https://invalid.example/do-not-fetch'}]; db.commit()
        with patch.dict(os.environ, {'MANUAL_IMAGING_ENABLED': '0', 'MANUAL_LAB_RESULTS_ENABLED': '0'}):
            data = self.overview()
            for key in ('lab', 'imaging'):
                self.assertEqual(data['groups'][key], {'status': 'disabled', 'records': None, 'counts': None, 'legacy_count': None})
            self.assertEqual(data['groups']['attachments']['legacy_count'], 1)
            self.assertFalse(any(n['code'] == 'source_without_record' for n in data['notices']))

    def test_unknown_structure_and_version_damage_fail_closed(self):
        _, image, _, _ = self.both_reports()
        with f.db.SessionLocal() as db:
            row = db.get(f.models.ImagingStudy, image['id']); original = copy.deepcopy(row.extra_data)
        for patch_data in ({'schema': 'unknown'}, {'version': 2}, {'root_id': 99999}, {'source_digest': '0' * 64}, {'data': {}}, {'identity': []}):
            with f.db.SessionLocal() as db:
                row = db.get(f.models.ImagingStudy, image['id']); row.extra_data = {**original, **patch_data}; db.commit()
            response = self.client.get(self.overview_url, headers=self.owner_headers)
            self.assertEqual(response.status_code, 409, response.text)
            self.assertNotIn('groups', response.json())
        with f.db.SessionLocal() as db:
            db.get(f.models.Case, self.cid).attachments = {'unexpected': []}; db.commit()
        self.assertEqual(self.client.get(self.overview_url, headers=self.owner_headers).status_code, 409)

    def test_read_error_has_explicit_failure_no_cached_payload(self):
        self.overview()
        with patch.object(overview, 'assemble', side_effect=OperationalError('synthetic', {}, Exception('unavailable'))):
            response = self.client.get(self.overview_url, headers=self.owner_headers)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {'detail': 'visit_overview_read_failed'})
        self.assertEqual(response.headers['cache-control'], 'private, no-store')


if __name__ == '__main__': unittest.main(verbosity=2)
