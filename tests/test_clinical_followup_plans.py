"""Real JWT + disposable SQLite; independent literal/date/KPI expectations."""
import copy
from datetime import datetime
import json
import os
from pathlib import Path
import time
import unittest
from unittest.mock import patch
from uuid import uuid4
from sqlalchemy import event
from sqlalchemy.exc import OperationalError
import test_consult_update_preview as f
import clinical_followup_plans as plans

FIXTURE = json.loads((Path(__file__).parent / 'fixtures/clinical_followup_plans_cw_b14_cases.json').read_text())


class FollowupFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        f.ConsultUpdatePreviewTests.setUpClass.__func__(cls)
        f.db.Base.metadata.create_all(f.db.engine, tables=[f.models.FollowUp.__table__, f.models.AuditLog.__table__])

    @classmethod
    def tearDownClass(cls):
        f.ConsultUpdatePreviewTests.tearDownClass.__func__(cls)

    def setUp(self):
        f.ConsultUpdatePreviewTests.setUp(self)
        flags = patch.dict(os.environ, {'FOLLOWUP_PLANS_ENABLED':'1', 'FOLLOWUP_PLANS_SYNTHETIC_ONLY':'1'})
        flags.start(); self.addCleanup(flags.stop)
        self.root = f'/api/cases/{self.cid}/followup-plan'

    def request(self, suffix='', body=None, expected=200, headers=None):
        result = self.client.request('GET' if body is None else 'POST', self.root + suffix,
            headers=self.owner_headers if headers is None else headers, **({'json':body} if body is not None else {}))
        self.assertEqual(result.status_code, expected, result.text)
        if expected != 401 and expected != 422: self.assertEqual(result.headers['cache-control'], 'private, no-store')
        return result.json()

    def body(self, operation='create', row=None, data=None, reason=None, listing=None):
        listing = listing or self.request()
        return {'request_id':uuid4().hex, 'operation':operation, 'plan_id':row['id'] if row else None,
                'expected_plan_token':row['token'] if row else '', 'expected_case_token':listing['case_token'],
                'expected_state_token':listing['state_token'], 'data':None if operation=='withdraw' else copy.deepcopy(data or FIXTURE['plan']),
                'reason':reason if reason is not None else ('' if operation=='create' else FIXTURE['correction_reason'])}

    def reviewed(self, body=None):
        body = body or self.body()
        return {**body, 'preview_token':self.request('/preview',body)['preview_token'], 'reviewed':True}

    def save(self, operation='create', row=None, data=None, reason=None):
        return self.request('/confirm', self.reviewed(self.body(operation,row,data,reason)))['plan']

    def business(self):
        with f.db.SessionLocal() as db:
            return {table.__tablename__:[{col.key:getattr(row,col.key) for col in table.__table__.columns}
                for row in db.query(table).filter_by(case_id=self.cid).order_by(table.id if table is f.models.FollowUp else table.log_id).all()]
                for table in [f.models.FollowUp,f.models.AuditLog]}

    def case(self):
        with f.db.SessionLocal() as db:
            row=db.get(f.models.Case,self.cid)
            return {col.key:getattr(row,col.key) for col in row.__table__.columns}

    change_case = f.ConsultUpdatePreviewTests.change_case


class FollowupTests(FollowupFixture):
    def test_literal_dates_versions_withdrawal_idempotency_and_case_unchanged(self):
        before=self.case(); reviewed=self.reviewed(); first=self.request('/confirm',reviewed)
        self.assertTrue(first['writes_database']); self.assertEqual(first['plan']['data'],FIXTURE['plan'])
        snapshot=self.business(); replay=self.request('/confirm',reviewed)
        self.assertFalse(replay['writes_database']); self.assertEqual(replay['plan'],first['plan']); self.assertEqual(self.business(),snapshot)
        changed={**reviewed,'data':{**reviewed['data'],'note':'different'}}
        self.request('/confirm',changed,409)
        second=self.save('correct',first['plan'],FIXTURE['corrected_plan'])
        self.assertEqual((second['root_id'],second['version']),(first['plan']['id'],2))
        last=self.save('withdraw',second,reason=FIXTURE['withdrawal_reason'])
        self.assertEqual(last['data'],FIXTURE['corrected_plan']); self.assertEqual(last['withdrawal']['reason'],FIXTURE['withdrawal_reason'])
        f.db.engine.dispose()
        token=self.client.post('/auth/login',data={'username':'owner@example.com','password':'synthetic-test-password'}).json()['access_token']
        listing=self.request(headers={'Authorization':'Bearer '+token})
        self.assertEqual([p['state'] for p in listing['plans']],['superseded','withdrawn'])
        self.assertEqual([p['data'] for p in listing['plans']],[FIXTURE['plan'],FIXTURE['corrected_plan']])
        rows=self.business(); self.assertEqual(len(rows['audit_log']),3)
        self.assertEqual([r['due_date'].isoformat() for r in rows['followups']],[FIXTURE['expected_due_utc'],FIXTURE['corrected_due_utc']])
        self.assertTrue(all(r['done_at'] is None and r['channel']==plans.SOURCE for r in rows['followups']))
        self.assertEqual(self.case(),before)
        self.assertEqual(self.request('/requests/'+reviewed['request_id'])['plan']['id'],first['plan']['id'])
        new=self.save(); self.assertEqual((new['version'],new['root_id']),(1,new['id']))

    def test_get_preview_and_request_status_do_not_write_sql_or_audit(self):
        self.save(); before=self.business(); sql=[]
        def capture(_c,_cur,statement,*_):
            if statement.lstrip().split()[0].upper() in {'INSERT','UPDATE','DELETE','CREATE','ALTER','DROP'}:sql.append(statement)
        event.listen(f.db.engine,'before_cursor_execute',capture)
        try:
            row=self.request()['plans'][0]; self.reviewed(self.body('correct',row))
            self.request('/requests/'+uuid4().hex)
        finally:event.remove(f.db.engine,'before_cursor_execute',capture)
        self.assertEqual(sql,[]);self.assertEqual(self.business(),before)

    def test_auth_ownership_deleted_case_independent_gates_and_database_errors(self):
        body=self.reviewed()
        for suffix,value in [('',None),('/preview',self.body()),('/confirm',body),('/requests/'+body['request_id'],None)]:
            self.request(suffix,value,401,{});self.request(suffix,value,404,self.other_headers)
            for flags in [{'FOLLOWUP_PLANS_ENABLED':'0'},{'FOLLOWUP_PLANS_SYNTHETIC_ONLY':'0'},{'ENVIRONMENT':'production'},{'RENDER':'true'}]:
                with patch.dict(os.environ,flags):self.request(suffix,value,503)
        with patch.dict(os.environ,{'CASE_ATTACHMENTS_ENABLED':'0','MANUAL_LAB_RESULTS_ENABLED':'0'}):self.request('/confirm',body)
        with patch.object(plans,'records',side_effect=OperationalError('synthetic',{},Exception('offline'))):
            self.request(expected=503);self.request('/requests/'+uuid4().hex,expected=503)
        self.client.delete(f'/api/cases/{self.cid}',headers=self.owner_headers)
        self.request(expected=404);self.request('/confirm',body,404)

    def test_strict_fields_types_dates_lengths_controls_and_explicit_review(self):
        base=self.body();before=self.business()
        invalid=[{**base,'extra':1},{**base,'plan_id':True},{**base,'request_id':1},{**base,'data':[]},
                 {**base,'data':{**base['data'],'extra':1}},{**base,'data':{**base['data'],'purpose':1}}]
        for key,values in {'purpose':['',' \t','a'*1001,'x\x00','x\x7f','x\x85','x\ud800'], 'items':[[],['a']*11,[''],['a'*301]],
                           'note':['x'*1001], 'planned_date':FIXTURE['invalid_dates']}.items():
            invalid += [{**base,'data':{**base['data'],key:value}} for value in values]
        for value in invalid:
            # Surrogates cannot be UTF-8 JSON-encoded by httpx; send a legal JSON escape.
            if '\ud800' in str(value):
                r=self.client.post(self.root+'/preview',headers={**self.owner_headers,'Content-Type':'application/json'},content=json.dumps(value));self.assertEqual(r.status_code,422)
            else:self.request('/preview',value,422)
        reviewed=self.reviewed(base)
        for value in [False,1,'true',None]:self.request('/confirm',{**reviewed,'reviewed':value},422)
        missing=dict(reviewed);del missing['reviewed'];self.request('/confirm',missing,422)
        self.assertEqual(self.business(),before)
        boundary={**FIXTURE['plan'],'purpose':'🐾'*1000,'items':['é'*300]*10,'note':'x'*1000,'return_conditions':'y'*1000}
        self.assertEqual(self.save(data=boundary)['data'],boundary)

    def test_stale_body_identity_plan_version_foreign_plan_and_midnight(self):
        body=self.reviewed();self.change_case(history='后续正文')
        self.request('/confirm',body,409);row=self.save()
        for key in plans.FIELDS:
            snapshot=self.reviewed(self.body('correct',row))
            self.change_case(**{key:'后续 '+key})
            self.request('/confirm',snapshot,409)
            self.assertEqual(self.request()['plans'][0]['state'],'needs_review')
            row=self.request()['plans'][0]
        correct=self.reviewed(self.body('correct',row));withdraw=self.reviewed(self.body('withdraw',row))
        current=self.request('/confirm',correct)['plan'];self.request('/confirm',withdraw,409)
        foreign=self.body('withdraw',current);foreign['plan_id']=2**52;self.request('/preview',foreign,404)
        with patch.object(plans,'today',return_value='2026-10-08'):body=self.reviewed(self.body('withdraw',current))
        with patch.object(plans,'today',return_value='2026-10-09'):self.request('/confirm',body,409)

    def test_date_is_independent_of_machine_timezone_and_calendar_edges(self):
        for zone in ['UTC','America/Los_Angeles','Asia/Tokyo']:
            with patch.dict(os.environ,{'TZ':zone}):
                time.tzset();self.assertEqual(plans.due_date(FIXTURE['plan']['planned_date']).isoformat(),FIXTURE['expected_due_utc'])
        time.tzset()
        for value in ['2000-02-29','2026-01-31','2026-12-31','9999-12-31']:
            self.request('/preview',self.body(data={**FIXTURE['plan'],'planned_date':value}))

    def test_cap_keeps_all_history_and_allows_withdrawal(self):
        row=self.save()
        for number in range(2,51):row=self.save('correct',row,reason='版本 '+str(number))
        self.assertEqual(len(self.request()['plans']),50)
        self.request('/preview',self.body('correct',row),422)
        self.save('withdraw',row);self.request('/preview',self.body(),422)
        self.assertEqual(len(self.request()['plans']),50)

    def test_corrupt_row_chain_and_receipt_fail_closed_without_repairs(self):
        reviewed=self.reviewed();row=self.request('/confirm',reviewed)['plan'];original=self.business()
        variants=[{'status':'cw-b14-unknown'},{'channel':'other'},{'note':'not-json'}, {'due_date':datetime(2020,1,1)}, {'done_at':datetime(2024,3,1)}]
        meta=json.loads(original['followups'][0]['note'])
        variants += [{'note':json.dumps({**meta,**change})} for change in [{'version':2},{'root_id':9999},{'extra':True},{'reviewed_by':'other'},{'withdrawal':{}},{'data':{**meta['data'],'purpose':None}}]]
        for changes in variants:
            with f.db.SessionLocal() as db:
                stored=db.get(f.models.FollowUp,row['id'])
                for key,value in {**original['followups'][0],**changes}.items():setattr(stored,key,value)
                db.commit()
            before=self.business();self.request(expected=409);self.request('/requests/'+reviewed['request_id'],expected=409);self.assertEqual(self.business(),before)
        with f.db.SessionLocal() as db:
            stored=db.get(f.models.FollowUp,row['id'])
            for key,value in original['followups'][0].items():setattr(stored,key,value)
            audit=db.get(f.models.AuditLog,original['audit_log'][0]['log_id']);audit.extra_data={'schema':'broken'};db.commit()
        self.request('/requests/'+reviewed['request_id'],expected=409)

    def test_legacy_kpi_exactly_unchanged_by_all_plan_states_and_corruption(self):
        with f.db.SessionLocal() as db:
            for i,done in enumerate([datetime(2024,2,29,12),datetime(2024,3,2),None]):
                db.add(f.models.FollowUp(case_id=self.cid,due_date=datetime(2024,2,29),done_at=done,status='legacy-'+str(i),channel='phone',owner='legacy',note='旧自由文本 {{原文}}'))
            db.commit()
        url='/api/kpi/followups?start=2024-02-01&end=2024-03-31'
        def kpi():
            r=self.client.get(url,headers=self.owner_headers);self.assertEqual(r.status_code,200,r.text);return r.json()
        expected=kpi();actual=expected['metrics']['followup_compliance']
        for key,value in FIXTURE['legacy_kpi'].items():self.assertEqual(actual[key],value)
        before=self.business()['followups'];row=self.save();row=self.save('correct',row);self.save('withdraw',row)
        self.assertEqual(kpi(),expected)
        with f.db.SessionLocal() as db:
            for status,channel in [('cw-b14-unknown',''),('broken',plans.SOURCE),('cw-b14-',None)]:
                db.add(f.models.FollowUp(case_id=self.cid,due_date=datetime(2024,2,29),done_at=datetime(2024,2,29),status=status,channel=channel,note='broken'))
            db.commit()
        self.assertEqual(kpi(),expected);self.assertEqual(self.business()['followups'][:3],before)


if __name__=='__main__':unittest.main(verbosity=2)
