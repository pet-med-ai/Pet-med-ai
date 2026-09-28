"""M6 real authenticated routes on a fresh, network-denied SQLite database."""
from datetime import datetime
import unittest
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError
from test_consult_update_preview import main, db, models, feature_flags, TestClient, FIXTURE
import followups_api as follow
import kpi_api


class FollowUpPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert not main.app.dependency_overrides
        assert not feature_flags.dangerous_enabled_flags()
        db.Base.metadata.create_all(db.engine, tables=[models.User.__table__, models.Case.__table__,
                                                      models.FollowUp.__table__, models.AuditLog.__table__])
        cls.client = TestClient(main.app)
        for name in ('owner', 'other'):
            assert cls.client.post('/auth/signup', json={'email': name+'@example.com', 'password': 'synthetic-test-password'}).status_code == 200
            r = cls.client.post('/auth/login', data={'username': name+'@example.com', 'password': 'synthetic-test-password'})
            setattr(cls, name, {'Authorization': 'Bearer '+r.json()['access_token']})

    @classmethod
    def tearDownClass(cls):
        cls.client.close(); db.engine.dispose(); FIXTURE.cleanup()

    def setUp(self):
        r = self.client.post('/api/cases', headers=self.owner, json={'patient_name': 'M6合成犬', 'chief_complaint': '合成就诊'})
        self.assertEqual(r.status_code, 201, r.text)
        self.case_id = r.json()['id']
        self.base = f'/api/cases/{self.case_id}/follow-up'

    def get(self):
        r = self.client.get(self.base, headers=self.owner)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def request(self, action='create', due='2028-02-29', note='  医生原文：未见异常，不排除其他原因。🐾\r\n<literal> & {{literal}}\t  ', state=None):
        state = state or self.get()
        payload = {'action': action, 'expected_state_token': state['state_token'],
                   'due_date': None if action == 'cancel' else due, 'note': None if action == 'cancel' else note}
        r = self.client.post(self.base+'/preview', headers=self.owner, json=payload)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertFalse(r.json()['writes_database'])
        return {**payload, 'expected_preview_token': r.json()['preview_token'], 'request_id': uuid4().hex}

    def confirm(self, request, status=200):
        r = self.client.post(self.base+'/confirm', headers=self.owner, json=request)
        self.assertEqual(r.status_code, status, r.text)
        return r.json()

    def counts(self):
        with db.SessionLocal() as session:
            return (session.query(models.FollowUp).filter_by(case_id=self.case_id).count(),
                    session.query(models.AuditLog).filter_by(case_id=self.case_id).count())

    def test_review_is_readonly_and_confirm_reads_exact_original_date_and_text(self):
        before_case = self.client.get(f'/api/cases/{self.case_id}', headers=self.owner).json()
        request = self.request()
        self.assertEqual(self.counts(), (0, 0))
        result = self.confirm(request)
        state = self.get()
        self.assertTrue(state['can_write'])
        self.assertEqual(state['current']['note'], request['note'])
        self.assertEqual(state['current']['due_date'], request['due_date'])
        self.assertEqual(state['current']['due_at_stored'], '2028-02-29T00:00:00')
        self.assertEqual(state['current']['owner'], state['account_id'])
        self.assertEqual(result['receipt']['after_state_token'], state['state_token'])
        self.assertEqual(self.counts(), (1, 1))
        self.assertEqual(self.client.get(f'/api/cases/{self.case_id}', headers=self.owner).json(), before_case)

    def test_identical_request_replays_once_even_after_later_replacement(self):
        request = self.request(); first = self.confirm(request)
        replay = self.confirm(request)
        self.assertTrue(replay['replayed']); self.assertFalse(replay['writes_database'])
        self.assertEqual(replay['receipt'], first['receipt']); self.assertEqual(self.counts(), (1, 1))
        self.confirm(self.request('replace', note='更正后计划'))
        self.assertEqual(self.confirm(request)['receipt'], first['receipt'])
        self.assertEqual(self.counts(), (2, 2))
        self.assertEqual(self.get()['current']['note'], '更正后计划')

    def test_request_id_reuse_with_changed_payload_is_rejected(self):
        request = self.request(); self.confirm(request)
        self.confirm({**request, 'note': '另一内容'}, 409)
        self.assertEqual(self.counts(), (1, 1))

    def test_replacement_and_cancellation_preserve_old_rows_and_receipts(self):
        first = self.confirm(self.request())['receipt']['after']
        second = self.confirm(self.request('replace', due='2028-03-01', note='第二次原文'))['receipt']
        self.assertEqual(second['before']['id'], first['id'])
        self.assertEqual(second['cancelled']['note'], first['note'])
        state = self.get(); self.assertTrue(all(r['managed'] for r in state['items']))
        cancelled = self.confirm(self.request('cancel'))['receipt']
        self.assertIsNone(cancelled['after'])
        state = self.get()
        self.assertIsNone(state['current']); self.assertTrue(state['can_write'])
        self.assertEqual([r['status'] for r in state['items']], ['cancelled', 'cancelled'])
        self.assertEqual(self.counts(), (2, 3))
        self.confirm(self.request(note='撤销后的新计划'))
        self.assertEqual(self.counts(), (3, 4))

    def test_stale_collection_or_changed_preview_cannot_write(self):
        a, b = self.request(), self.request(note='另一标签页')
        self.confirm(a); self.confirm(b, 409)
        c = self.request('replace', note='新计划')
        self.confirm({**c, 'note': '确认时偷偷改字'}, 409)
        self.confirm({**c, 'expected_preview_token': '0'*64}, 409)
        self.assertEqual(self.counts(), (1, 1))

    def test_case_change_invalidates_review(self):
        request = self.request()
        self.assertEqual(self.client.put(f'/api/cases/{self.case_id}', headers=self.owner, json={'history': '医生补记'}).status_code, 200)
        self.confirm(request, 409); self.assertEqual(self.counts(), (0, 0))

    def test_anonymous_other_owner_and_deleted_case_cannot_read_or_write(self):
        request = self.request()
        for headers, expected in (({}, 401), (self.other, 404)):
            for method, url, payload in [('GET', self.base, None), ('POST', self.base+'/preview', {k:v for k,v in request.items() if k not in {'request_id','expected_preview_token'}}), ('POST', self.base+'/confirm', request), ('GET', self.base+'/receipts/'+request['request_id'], None)]:
                r = self.client.request(method, url, headers=headers, **({'json':payload} if payload else {}))
                self.assertEqual(r.status_code, expected, r.text)
        self.assertEqual(self.client.delete(f'/api/cases/{self.case_id}', headers=self.owner).status_code, 204)
        self.confirm(request, 404)
        self.assertEqual(self.client.get(self.base, headers=self.owner).status_code, 404)
        self.assertEqual(self.counts(), (0, 0))

    def test_invalid_dates_notes_control_characters_and_extra_identity_are_rejected(self):
        state = self.get(); template = {'action':'create', 'expected_state_token':state['state_token'], 'due_date':'2028-02-29', 'note':'原文'}
        for change in ({'due_date':'2027-02-29'}, {'due_date':'2028-02-29T00:00:00Z'}, {'due_date':123}, {'note':' \n'}, {'note':'bad\x01'}, {'note':'字'*8001}, {'owner':'someone'}, {'case_id':77}):
            r = self.client.post(self.base+'/preview', headers=self.owner, json={**template, **change})
            self.assertEqual(r.status_code, 422, r.text)
        self.assertEqual(self.counts(), (0, 0))

    def test_noop_wrong_action_and_cancellation_payload_are_rejected(self):
        self.confirm(self.request(note='same'))
        state = self.get()
        for payload, status in (({'action':'create','due_date':'2028-02-29','note':'new'},409), ({'action':'replace','due_date':'2028-02-29','note':'same'},400), ({'action':'cancel','due_date':'2028-02-29','note':None},422)):
            r = self.client.post(self.base+'/preview', headers=self.owner, json={**payload,'expected_state_token':state['state_token']})
            self.assertEqual(r.status_code, status, r.text)
        self.assertEqual(self.counts(), (1, 1))

    def test_unknown_legacy_timestamp_is_displayed_but_not_adopted_or_changed(self):
        with db.SessionLocal() as session:
            session.add(models.FollowUp(case_id=self.case_id, due_date=datetime(2028,2,29,13,45), note='旧时间原文', status='due'))
            session.commit()
        state = self.get(); self.assertFalse(state['can_write']); self.assertIsNone(state['current'])
        self.assertEqual(state['items'][0]['due_at_stored'], '2028-02-29T13:45:00')
        r = self.client.post(self.base+'/preview', headers=self.owner, json={'action':'create','due_date':'2028-03-01','note':'不应该覆盖','expected_state_token':state['state_token']})
        self.assertEqual(r.status_code, 409); self.assertEqual(self.counts(), (1, 0))

    def test_generic_audit_endpoint_cannot_forge_managed_plan(self):
        original = self.confirm(self.request())['receipt']
        with db.SessionLocal() as session:
            row = session.get(models.FollowUp, original['after']['id']); row.note = '直接改写'
            session.commit()
        forged = {**original, 'after':{**original['after'],'note':'直接改写'}}
        r = self.client.post('/api/audit-log', headers=self.owner, json={'request_id':original['request_id'],'clinician_id':original['account_id'], 'action_taken':'create','case_id':self.case_id,'event_type':follow.EVENT,'source':follow.SOURCE,'metadata':{'version':1,'receipt':forged}})
        self.assertEqual(r.status_code, 201, r.text)
        self.assertFalse(self.get()['can_write'])

    def test_audit_insert_failure_rolls_back_plan_and_cancellation(self):
        first = self.confirm(self.request())['receipt']['after']
        request = self.request('replace', note='失败的更正')
        def fail(conn, cursor, statement, *args):
            if statement.lower().startswith('insert into audit_log'):
                raise SQLAlchemyError('synthetic audit insert failure')
        event.listen(db.engine, 'before_cursor_execute', fail)
        try: self.confirm(request, 503)
        finally: event.remove(db.engine, 'before_cursor_execute', fail)
        self.assertEqual(self.counts(), (1, 1)); self.assertEqual(self.get()['current']['id'], first['id'])
        self.assertEqual(self.get()['current']['status'], 'due')

    def test_lost_commit_acknowledgement_is_recovered_by_get_and_replay(self):
        request = self.request(); original = db.SessionLocal.class_.commit
        def commit_then_disconnect(session):
            original(session)
            raise SQLAlchemyError('synthetic lost commit acknowledgement')
        with patch.object(db.SessionLocal.class_, 'commit', commit_then_disconnect):
            self.confirm(request, 503)
        receipt = self.client.get(self.base+'/receipts/'+request['request_id'], headers=self.owner).json()
        self.assertEqual(receipt['status'], 'committed'); self.assertFalse(receipt['writes_database'])
        self.assertTrue(self.confirm(request)['replayed']); self.assertEqual(self.counts(), (1, 1))

    def test_missing_receipt_is_not_reported_as_success(self):
        r = self.client.get(self.base+'/receipts/'+uuid4().hex, headers=self.owner)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['status'], 'not_found'); self.assertIsNone(r.json()['receipt'])
        self.assertEqual(self.counts(), (0, 0))

    def test_missing_table_does_not_masquerade_as_empty_plan_or_change_schema(self):
        models.FollowUp.__table__.drop(db.engine)
        try:
            r = self.client.get(self.base, headers=self.owner)
            self.assertEqual(r.status_code, 503, r.text)
            from sqlalchemy import inspect
            self.assertNotIn('followups', inspect(db.engine).get_table_names())
        finally: models.FollowUp.__table__.create(db.engine)

    def test_cancelled_plans_are_excluded_from_kpi_denominator_and_samples(self):
        self.confirm(self.request()); self.confirm(self.request('replace', note='当前复查说明'))
        with db.SessionLocal() as session:
            user = session.query(models.User).filter_by(email='owner@example.com').one()
            rows = kpi_api._owned_followups(session, user, datetime(2028,2,29), datetime(2028,3,1))
            these = [r for r in rows if r.case_id == self.case_id]
            self.assertEqual(len(these), 1); self.assertEqual(these[0].note, '当前复查说明')


if __name__ == '__main__':
    unittest.main(verbosity=2)
