"""CW-B20 authenticated inventory, literal provenance and read-only compatibility."""
import copy
from datetime import datetime
import json
import os
from pathlib import Path
import time
import unittest
from unittest.mock import patch
from sqlalchemy import event
from sqlalchemy.exc import OperationalError
from test_clinical_followup_plan_overview import PlanOverviewFixture, f, storage
from test_clinical_followup_contacts import ContactFixture, contacts
import clinical_followup_contact_overview as extension
import clinical_case_overview as service

FIXTURE = json.loads((Path(__file__).parent / 'fixtures/clinical_followup_contact_overview_cw_b20_cases.json').read_text())
PARAMS = {'include_followup_plan': 'true', 'include_followup_contacts': 'true'}
FLAGS = {'FOLLOWUP_CONTACT_OVERVIEW_ENABLED': '1', 'FOLLOWUP_CONTACT_OVERVIEW_SYNTHETIC_ONLY': '1',
         'FOLLOWUP_CONTACTS_ENABLED': '1', 'FOLLOWUP_CONTACTS_SYNTHETIC_ONLY': '1'}


class ContactOverviewFixture(PlanOverviewFixture):
    contact = ContactFixture.contact
    contact_body = ContactFixture.contact_body
    contact_review = ContactFixture.contact_review
    contact_save = ContactFixture.contact_save

    def setUp(self):
        super().setUp()
        flags = patch.dict(os.environ, FLAGS); flags.start(); self.addCleanup(flags.stop)
        self.change_case(**FIXTURE['case'])
        self.source = self.save_plan(data=FIXTURE['plan'])
        self.contact_root = f'/api/cases/{self.cid}/followup-contacts'

    def inventory(self, expected=200, params=None, headers=None, url=None):
        r = self.client.get(url or self.overview_url, params=PARAMS if params is None else params,
                            headers=self.owner_headers if headers is None else headers)
        self.assertEqual(r.status_code, expected, r.text)
        self.assertEqual(r.headers['cache-control'], 'private, no-store')
        self.assertEqual(r.headers['x-pmai-writes-database'], 'false')
        return r.json()

    def saved_inventory(self, **kw):
        value = self.inventory(**kw); value.pop('read_at', None); return value


class ContactOverviewTests(ContactOverviewFixture):
    def test_complete_originals_counts_provenance_and_no_business_sql_or_cleanup(self):
        self.mixed_sources()
        row = self.contact_save(data=FIXTURE['contact']); before = self.all_business(); writes = []
        def capture(_c, _cur, sql, *_):
            if sql.lstrip().split()[0].upper() in {'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP'}: writes.append(sql)
        event.listen(f.db.engine, 'before_cursor_execute', capture)
        try:
            with (patch.object(contacts.plans, 'transaction', side_effect=AssertionError('No nested session')),
                  patch.object(storage.Store, 'cleanup', side_effect=AssertionError('No GET cleanup'))):
                value = self.inventory(); again = self.inventory()
        finally:
            event.remove(f.db.engine, 'before_cursor_execute', capture)
        self.assertFalse(writes); self.assertEqual(before, self.all_business())
        self.assertEqual(value['schema'], extension.SCHEMA)
        self.assertEqual(value['snapshot'], again['snapshot'])
        self.assertEqual(value['navigation_targets'], service.TARGETS + ['followup', 'contacts'])
        group = value['groups']['contacts']
        self.assertEqual(group['records'], [row]); self.assertEqual(row['data'], FIXTURE['contact'])
        self.assertEqual(row['source']['data'], FIXTURE['plan'])
        self.assertEqual(group['case'], value['groups']['followup']['case'])
        self.assertEqual(group['counts'], {'recorded': 1, 'superseded': 0, 'withdrawn': 0})

    def test_unrequested_or_disabled_extension_keeps_both_old_payloads_exact(self):
        self.contact_save()
        old10 = self.saved_inventory(params={})
        old17 = self.saved_inventory(params={'include_followup_plan': True})
        with patch.object(contacts, 'records', side_effect=AssertionError('Must not read contacts')):
            self.assertEqual(self.saved_inventory(params={}), old10)
            self.assertEqual(self.saved_inventory(params={'include_followup_contacts': False}), old10)
            self.assertEqual(self.saved_inventory(params={'include_followup_plan': True, 'include_followup_contacts': False}), old17)
            for flag in ('FOLLOWUP_CONTACT_OVERVIEW_ENABLED', 'FOLLOWUP_CONTACT_OVERVIEW_SYNTHETIC_ONLY'):
                for value in ('0', ''):
                    with patch.dict(os.environ, {flag: value}): self.assertEqual(self.saved_inventory(), old17)
            for flag in ('FOLLOWUP_PLAN_OVERVIEW_ENABLED', 'FOLLOWUP_PLAN_OVERVIEW_SYNTHETIC_ONLY'):
                with patch.dict(os.environ, {flag: '0'}): self.assertEqual(self.saved_inventory(), old10)
        for env in ({'ENVIRONMENT': 'production'}, {'RENDER': 'true'}):
            with patch.dict(os.environ, env): self.assertFalse(extension.enabled())

    def test_private_auth_deleted_cases_and_query_errors(self):
        self.inventory(expected=401, headers={}); self.inventory(expected=401, headers={'Authorization': 'Bearer invalid'})
        self.inventory(expected=404, headers=self.other_headers)
        self.inventory(expected=404, url='/api/cases/999999/visit-overview')
        self.inventory(expected=422, url='/api/cases/not-a-number/visit-overview')
        for params in ({'include_followup_contacts': True}, {'include_followup_plan': False, 'include_followup_contacts': True},
                       {**PARAMS, 'include_followup_contacts': 'unknown'}, {**PARAMS, 'include_followup_plan': 'unknown'}):
            self.inventory(expected=422, params=params)
        with f.db.SessionLocal() as db:
            db.get(f.models.Case, self.cid).deleted_at = datetime.utcnow(); db.commit()
        self.inventory(expected=404)

    def test_disabled_empty_and_legacy_contacts_are_distinct(self):
        with f.db.SessionLocal() as db:
            db.add(f.models.FollowUp(case_id=self.cid, due_date=datetime(2024, 2, 29), status='done', channel='phone', note='合成旧随访'))
            db.commit()
        group = self.inventory()['groups']['contacts']
        self.assertEqual(group['records'], []); self.assertEqual(group['counts'], {'recorded': 0, 'superseded': 0, 'withdrawn': 0})
        for flag in ('FOLLOWUP_CONTACTS_ENABLED', 'FOLLOWUP_CONTACTS_SYNTHETIC_ONLY', 'FOLLOWUP_PLANS_ENABLED', 'FOLLOWUP_PLANS_SYNTHETIC_ONLY'):
            with patch.dict(os.environ, {flag: '0'}), patch.object(contacts, 'records', side_effect=AssertionError('Disabled must not read')):
                group = self.inventory()['groups']['contacts']
                self.assertEqual(group, {'status': 'disabled', 'records': None, 'counts': None, 'case': None, 'timezone': 'Asia/Shanghai'})

    def test_independent_contacts_versions_withdrawal_and_source_changes(self):
        first = self.contact_save(data=FIXTURE['contact']); second = self.contact_save(data=FIXTURE['corrected'])
        changed = self.contact_save('correct', first, FIXTURE['corrected'])
        self.contact_save('withdraw', changed, reason=FIXTURE['withdrawal_reason'])
        group = self.inventory()['groups']['contacts']
        self.assertEqual([r['state'] for r in group['records']], ['superseded', 'recorded', 'withdrawn'])
        self.assertEqual(group['counts'], {'recorded': 1, 'superseded': 1, 'withdrawn': 1})
        self.assertEqual(group['records'][0]['data'], FIXTURE['contact'])
        original = copy.deepcopy(first['source'])
        self.change_case(history='CW-B20 已更正病例原文')
        self.assertTrue(all(r['source_state'] == 'needs_review' for r in self.inventory()['groups']['contacts']['records']))
        self.source = self.save_plan('correct', self.source, FIXTURE['corrected_plan'])
        self.assertTrue(all(r['source_state'] == 'superseded' for r in self.inventory()['groups']['contacts']['records']))
        current = self.contact_save(data=FIXTURE['contact']); self.save_plan('withdraw', self.source)
        records = self.inventory()['groups']['contacts']['records']
        self.assertEqual(records[-1]['id'], current['id']); self.assertEqual(records[-1]['source_state'], 'withdrawn')
        self.assertEqual(records[0]['source'], original)
        self.assertEqual(records[1]['root_id'], second['id'])

    def test_fifty_versions_complete_and_fifty_first_fails_without_truncation(self):
        row = self.contact_save(data=FIXTURE['contact'])
        for _ in range(49): row = self.contact_save('correct', row, FIXTURE['corrected'])
        group = self.inventory()['groups']['contacts']
        self.assertEqual(len(group['records']), 50)
        self.assertEqual(group['counts'], {'recorded': 1, 'superseded': 49, 'withdrawn': 0})
        self.contact_save('withdraw', row)
        self.assertEqual(self.inventory()['groups']['contacts']['counts']['withdrawn'], 1)
        with f.db.SessionLocal() as db:
            db.add(f.models.FollowUp(case_id=self.cid, status=contacts.RECORDED, channel=contacts.SOURCE,
                                    due_date=datetime(2024, 2, 29), note='合成超限')); db.commit()
        before = self.all_business(); self.inventory(expected=409); self.assertEqual(before, self.all_business())

    def test_corrupt_namespace_chain_source_and_audit_fail_closed(self):
        row = self.contact_save()
        with f.db.SessionLocal() as db:
            stored = db.get(f.models.FollowUp, row['id'])
            original = {c.key: getattr(stored, c.key) for c in stored.__table__.columns}
        meta = json.loads(original['note'])
        variants = [{'status': 'cw-b19-broken'}, {'channel': 'bad'}, {'note': 'broken'}, {'done_at': datetime(2024, 3, 1)}]
        variants += [{'note': json.dumps({**meta, **change})} for change in (
            {'root_id': 999}, {'version': 3}, {'recorded_by': 'other'},
            {'source': {**meta['source'], 'version': 49}}, {'data': {**meta['data'], 'note': 'tampered'}})]
        for change in variants:
            with f.db.SessionLocal() as db:
                stored = db.get(f.models.FollowUp, row['id'])
                for key, value in {**original, **change}.items(): setattr(stored, key, value)
                db.commit()
            before = self.all_business(); self.inventory(expected=409); self.assertEqual(before, self.all_business())
            self.inventory(params={'include_followup_plan': True})
        with f.db.SessionLocal() as db:
            stored = db.get(f.models.FollowUp, row['id'])
            for key, value in original.items(): setattr(stored, key, value)
            db.query(f.models.AuditLog).filter_by(case_id=self.cid, source=contacts.SOURCE).delete(); db.commit()
        self.inventory(expected=409)

    def test_source_plan_damage_and_read_failure_are_explicit(self):
        self.contact_save(); before = self.all_business()
        for error, status in ((AttributeError('synthetic'), 409), (OSError('synthetic'), 503),
                              (OperationalError('synthetic', {}, Exception('offline')), 503)):
            with patch.object(extension, 'group', side_effect=error): self.inventory(expected=status)
        self.assertEqual(before, self.all_business())
        with f.db.SessionLocal() as db:
            db.get(f.models.FollowUp, self.source['id']).note = 'broken'; db.commit()
        self.inventory(expected=409)

    def test_dog_cat_short_long_unicode_and_timezones_preserve_literals(self):
        for kind in ('case', 'cat_case'):
            self.change_case(**FIXTURE[kind]); self.source = self.save_plan('correct', self.source, FIXTURE['plan'])
            for data in (FIXTURE['contact'], FIXTURE['long_contact']):
                row = self.contact_save(data=data)
                for zone in ('UTC', 'America/Los_Angeles', 'Asia/Shanghai'):
                    with patch.dict(os.environ, TZ=zone):
                        time.tzset(); records = self.inventory()['groups']['contacts']['records']
                        self.assertEqual(records[-1]['id'], row['id']); self.assertEqual(records[-1]['data'], data)
                        self.assertEqual(records[-1]['source']['data'], FIXTURE['plan'])
        time.tzset()


if __name__ == '__main__': unittest.main(verbosity=2)
