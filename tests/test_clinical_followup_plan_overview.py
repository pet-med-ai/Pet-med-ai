"""CW-B17 real JWT, strict saved provenance, compatibility and no business writes."""
import copy
import json
import os
from pathlib import Path
import time
import unittest
from unittest.mock import patch
from sqlalchemy import event
from sqlalchemy.exc import OperationalError
from test_clinical_followup_plan_documents import PlanDocumentFixture, f, storage
import clinical_case_overview as overview
import clinical_followup_plan_overview as extension

FIXTURE = json.loads((Path(__file__).parent / 'fixtures/clinical_followup_plan_overview_cw_b17_cases.json').read_text())
FLAGS = {'VISIT_OVERVIEW_ENABLED': '1', 'VISIT_OVERVIEW_SYNTHETIC_ONLY': '1',
         'FOLLOWUP_PLAN_OVERVIEW_ENABLED': '1', 'FOLLOWUP_PLAN_OVERVIEW_SYNTHETIC_ONLY': '1'}


class PlanOverviewFixture(PlanDocumentFixture):
    def setUp(self):
        super().setUp()
        flags = patch.dict(os.environ, FLAGS); flags.start(); self.addCleanup(flags.stop)
        self.change_case(**FIXTURE['case'])
        self.overview_url = f'/api/cases/{self.cid}/visit-overview'

    def save_plan(self, operation='create', row=None, data=None):
        return super().save_plan(operation, row, FIXTURE['plan'] if data is None else data)

    def overview(self, expected=200, **kw):
        r = self.client.get(self.overview_url, headers=self.owner_headers,
                            params={'include_followup_plan': 'true'}, **kw)
        self.assertEqual(r.status_code, expected, r.text)
        self.assertEqual(r.headers['cache-control'], 'private, no-store')
        self.assertEqual(r.headers['x-pmai-writes-database'], 'false')
        return r.json()

    def mixed_sources(self):
        sources, labs = self.save_pair()
        self.meta = {**self.meta, 'kind': 'dr'}
        image_source, _, image = self.save_image()
        return sources, labs, image_source, image


class PlanOverviewTests(PlanOverviewFixture):
    def test_original_plan_provenance_snapshot_and_no_sql_writes(self):
        self.mixed_sources(); row = self.save_plan(); before = self.all_business(); writes = []
        def capture(_c, _cur, sql, *_):
            if sql.lstrip().split()[0].upper() in {'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP'}: writes.append(sql)
        event.listen(f.db.engine, 'before_cursor_execute', capture)
        try:
            with patch.object(storage.Store, 'cleanup', side_effect=AssertionError('GET cannot clean files')), \
                 patch.object(extension.plans, 'transaction', side_effect=AssertionError('No nested session')):
                result = self.overview(); again = self.overview()
        finally:
            event.remove(f.db.engine, 'before_cursor_execute', capture)
        self.assertEqual(writes, []); self.assertEqual(self.all_business(), before)
        self.assertEqual(result['schema'], extension.SCHEMA)
        self.assertEqual(result['snapshot'], again['snapshot'])
        self.assertEqual(result['navigation_targets'], overview.TARGETS + ['followup'])
        group = result['groups']['followup']
        self.assertEqual(group['records'], [row]); self.assertEqual(row['data'], FIXTURE['plan'])
        self.assertEqual(group['timezone'], 'Asia/Shanghai')
        self.assertEqual(group['case'], self.plan_call()['case'])
        self.assertEqual(group['counts'], {'planned': 1, 'needs_review': 0, 'superseded': 0, 'withdrawn': 0})

    def test_opt_in_and_default_off_preserve_exact_legacy_payload_without_plan_reads(self):
        self.save_plan()
        legacy = self.client.get(self.overview_url, headers=self.owner_headers).json(); legacy.pop('read_at')
        with patch.object(extension.plans, 'records', side_effect=AssertionError('Must not query plans')):
            for params in ({}, {'include_followup_plan': 'false'}):
                r = self.client.get(self.overview_url, headers=self.owner_headers, params=params)
                self.assertEqual(r.status_code, 200); result = r.json(); result.pop('read_at')
                self.assertEqual(result, legacy)
            for flag in ('FOLLOWUP_PLAN_OVERVIEW_ENABLED', 'FOLLOWUP_PLAN_OVERVIEW_SYNTHETIC_ONLY'):
                for value in ('0', ''):
                    with patch.dict(os.environ, {flag: value}):
                        result = self.overview(); result.pop('read_at'); self.assertEqual(result, legacy)
        self.assertEqual(self.client.get(self.overview_url, headers=self.owner_headers,
                                        params={'include_followup_plan': 'unknown'}).status_code, 422)

    def test_disabled_empty_and_legacy_records_are_distinct(self):
        with f.db.SessionLocal() as db:
            db.add(f.models.FollowUp(case_id=self.cid, due_date=extension.plans.due_date('2026-01-01'),
                                    status='done', channel='telephone', owner='synthetic', note='old followup'))
            db.commit()
        before = self.all_business()
        group = self.overview()['groups']['followup']
        self.assertEqual(group['records'], []); self.assertEqual(sum(group['counts'].values()), 0)
        for flag in ('FOLLOWUP_PLANS_ENABLED', 'FOLLOWUP_PLANS_SYNTHETIC_ONLY'):
            with patch.dict(os.environ, {flag: '0'}), patch.object(extension.plans, 'records', side_effect=AssertionError('Disabled cannot read')):
                group = self.overview()['groups']['followup']
                self.assertEqual(group, {'status': 'disabled', 'records': None, 'counts': None, 'case': None, 'timezone': 'Asia/Shanghai'})
        self.assertEqual(self.all_business(), before)

    def test_state_changes_history_withdrawal_and_new_root_are_exact(self):
        first = self.save_plan(); initial = self.overview()
        self.change_case(history='医生更正的病例原文')
        result = self.overview(); self.assertNotEqual(result['snapshot'], initial['snapshot'])
        self.assertEqual(result['groups']['followup']['records'][0]['state'], 'needs_review')
        second = self.save_plan('correct', first, FIXTURE['corrected_plan'])
        result = self.overview()['groups']['followup']; self.assertEqual([r['state'] for r in result['records']], ['superseded', 'planned'])
        self.assertEqual(result['records'][0]['data'], FIXTURE['plan'])
        self.save_plan('withdraw', second)
        third = self.save_plan(data=FIXTURE['short_plan'])
        result = self.overview()['groups']['followup']
        self.assertEqual([r['state'] for r in result['records']], ['superseded', 'withdrawn', 'planned'])
        self.assertEqual(result['records'][2]['root_id'], third['id']); self.assertNotEqual(third['root_id'], first['root_id'])
        self.assertEqual(result['records'][1]['withdrawal']['reason'], ' 合成更正或撤销\n原文 ')
        self.assertEqual(result['counts'], {'planned': 1, 'needs_review': 0, 'superseded': 1, 'withdrawn': 1})

    def test_dog_cat_short_maximum_and_timezone_literal_dates(self):
        current = None
        for animal in ('case', 'cat_case'):
            self.change_case(**FIXTURE[animal])
            for key in ('short_plan', 'long_plan'):
                current = self.save_plan('correct' if current else 'create', current, FIXTURE[key])
                self.assertEqual(self.overview()['groups']['followup']['records'][-1]['data'], FIXTURE[key])
        for zone in ('UTC', 'Asia/Shanghai', 'America/Los_Angeles'):
            with patch.dict(os.environ, {'TZ': zone}):
                time.tzset()
                try:
                    for item in FIXTURE['date_cases']:
                        data = {**FIXTURE['short_plan'], 'planned_date': item['date']}
                        current = self.save_plan('correct', current, data)
                        self.assertEqual(self.overview()['groups']['followup']['records'][-1]['data']['planned_date'], item['date'])
                finally:
                    # The environment patch is restored before subsequent cases.
                    pass
        time.tzset()

    def test_fifty_versions_are_complete_and_excess_is_error_not_truncation(self):
        row = self.save_plan(data=FIXTURE['short_plan'])
        for _ in range(49): row = self.save_plan('correct', row, FIXTURE['short_plan'])
        result = self.overview()['groups']['followup']
        self.assertEqual(len(result['records']), 50); self.assertEqual(result['counts']['superseded'], 49)
        with f.db.SessionLocal() as db:
            source = db.get(f.models.FollowUp, row['id'])
            db.add(f.models.FollowUp(**{c.key: getattr(source, c.key) for c in source.__table__.columns if c.key != 'id'})); db.commit()
        self.assertEqual(self.overview(409)['detail'], 'visit_overview_data_unreadable')

    def test_corruption_is_never_an_empty_inventory(self):
        row = self.save_plan()
        with f.db.SessionLocal() as db:
            saved = db.get(f.models.FollowUp, row['id']); original = saved.note
        def wrong(meta, key, value): meta[key] = value; return meta
        variants = ['not json', 'null', json.dumps(wrong(json.loads(original), 'version', 2)),
                    json.dumps(wrong(json.loads(original), 'schema', 'unknown'))]
        meta = json.loads(original); meta['case_snapshot']['id'] = self.cid + 999; variants.append(json.dumps(meta))
        meta = json.loads(original); meta['data']['items'] = []; variants.append(json.dumps(meta))
        for note in variants:
            with f.db.SessionLocal() as db:
                db.get(f.models.FollowUp, row['id']).note = note; db.commit()
            before = self.all_business(); self.overview(409); self.assertEqual(before, self.all_business())
        with f.db.SessionLocal() as db:
            saved = db.get(f.models.FollowUp, row['id']); saved.note = original; saved.status = 'cw-b14-broken'; db.commit()
        self.overview(409)

    def test_real_auth_deleted_case_parent_gates_and_database_failure(self):
        self.save_plan()
        for headers, status in (({}, 401), (self.other_headers, 404)):
            r = self.client.get(self.overview_url, headers=headers, params={'include_followup_plan': True})
            self.assertEqual(r.status_code, status)
        for values in ({'VISIT_OVERVIEW_ENABLED': '0'}, {'CASE_ATTACHMENTS_ENABLED': '0'}, {'ENVIRONMENT': 'production'}, {'RENDER': 'true'}):
            with patch.dict(os.environ, values): self.overview(503)
        with patch.object(extension.plans, 'records', side_effect=OperationalError('synthetic', {}, Exception('offline'))):
            self.assertEqual(self.overview(503)['detail'], 'visit_overview_read_failed')
        second = self.client.post('/api/cases', headers=self.owner_headers, json=FIXTURE['cat_case']).json()['id']
        r = self.client.get(f'/api/cases/{second}/visit-overview', headers=self.owner_headers, params={'include_followup_plan': True})
        self.assertEqual(r.status_code, 200); self.assertEqual(r.json()['groups']['followup']['records'], [])
        self.assertEqual(self.client.delete(f'/api/cases/{self.cid}', headers=self.owner_headers).status_code, 204)
        self.overview(404)


if __name__ == '__main__': unittest.main(verbosity=2)
