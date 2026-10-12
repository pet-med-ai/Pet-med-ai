"""Real JWT and SQL against isolated synthetic SQLite; no external business calls."""
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
import unittest
from unittest.mock import patch
from sqlalchemy import event
from sqlalchemy.exc import OperationalError
from test_clinical_followup_plans import FollowupFixture, f, plans
import clinical_followup_plan_queue as queue
import auth_jwt

FIXTURE = json.loads((Path(__file__).parent/'fixtures/clinical_followup_plan_queue_cw_b18_cases.json').read_text())


class Clock(datetime):
    @classmethod
    def now(cls, tz=None): return datetime(2028, 2, 29, 8, tzinfo=timezone.utc)


class QueueFixture(FollowupFixture):
    def setUp(self):
        # Only this process's disposable SQLite; retain authenticated synthetic accounts.
        with f.db.SessionLocal() as db:
            for model in (f.models.AuditLog, f.models.FollowUp, f.models.ConsultSession, f.models.Case): db.query(model).delete()
            db.commit()
        super().setUp()
        for manager in (patch.dict(os.environ, {'FOLLOWUP_PLAN_QUEUE_ENABLED':'1','FOLLOWUP_PLAN_QUEUE_SYNTHETIC_ONLY':'1'}), patch.object(queue, 'datetime', Clock)):
            manager.start(); self.addCleanup(manager.stop)

    def get_queue(self, params=None, expected=200, headers=None):
        response = self.client.get('/api/followup-plan-queue', params=params,
            headers=self.owner_headers if headers is None else headers)
        self.assertEqual(response.status_code, expected, response.text)
        self.assertEqual(response.headers['cache-control'], 'private, no-store')
        return response.json()

    def add_case(self, species='cat', owner=None, deleted=False):
        with f.db.SessionLocal() as db:
            row = f.models.Case(owner_id=owner or self.owner_id, **FIXTURE['cat_case' if species=='cat' else 'case'])
            if deleted: row.deleted_at = datetime(2028, 2, 29)
            db.add(row); db.commit(); return row.id

    def seed_plan(self, cid=None, data=None, count=1):
        # Exact CW-B14 rows for large read-only fixtures, independent of queue internals.
        cid = cid or self.cid
        with f.db.SessionLocal() as db:
            case = db.get(f.models.Case, cid); root = None; now = datetime(2028, 2, 29, 1)
            for version in range(1, count+1):
                row = f.models.FollowUp(case_id=cid, status=plans.PLANNED if version==count else plans.SUPERSEDED,
                    channel=plans.SOURCE, owner=str(case.owner_id), due_date=plans.due_date((data or FIXTURE['plan'])['planned_date']),
                    created_at=now, updated_at=now, done_at=None)
                db.add(row); db.flush(); root = root or row.id
                meta = {'schema':plans.SCHEMA,'root_id':root,'version':version,'data':copy.deepcopy(data or FIXTURE['plan']),
                    'case_snapshot':plans.case_snapshot(case),'reviewed_by':str(case.owner_id),'reviewed_at':now.replace(tzinfo=timezone.utc).isoformat(),
                    'reason':'' if version==1 else '合成版本更正','withdrawal':None}
                row.note=json.dumps(meta,ensure_ascii=False)
            db.commit(); return row.id

    def all_business(self):
        with f.db.SessionLocal() as db:
            return {model.__tablename__:[{c.key:getattr(row,c.key) for c in model.__table__.columns} for row in db.query(model).order_by(model.log_id if model is f.models.AuditLog else model.id)]
                for model in (f.models.Case,f.models.FollowUp,f.models.AuditLog,f.models.ConsultSession)}


class QueueTests(QueueFixture):
    def test_dates_states_versions_literal_content_ownership_and_minimal_identity(self):
        row=self.save(data=FIXTURE['long_plan']); corrected=self.save('correct',row,data=FIXTURE['plan'])
        cat=self.add_case(); self.seed_plan(cat, {**FIXTURE['plan'],'planned_date':'2028-03-06'})
        past=self.add_case('dog'); self.seed_plan(past, {**FIXTURE['plan'],'planned_date':'2028-02-28'})
        with f.db.SessionLocal() as db:
            other=db.query(f.models.User).filter_by(email='other@example.com').one().id
        foreign=self.add_case(owner=other); self.seed_plan(foreign)
        deleted=self.add_case(deleted=True); self.seed_plan(deleted)
        own=self.get_queue(); self.assertEqual(own['total'],1); self.assertEqual(own['items'][0]['plan']['data'],FIXTURE['plan'])
        self.assertEqual(own['items'][0]['plan']['id'],corrected['id']); self.assertEqual(own['items'][0]['plan']['version'],2)
        self.assertNotIn('owner_phone',json.dumps(own));self.assertNotIn('history',json.dumps(own)); self.assertNotIn('case_snapshot',json.dumps(own))
        self.assertEqual(self.get_queue({'range':'next7'})['total'],2)
        self.assertEqual(self.get_queue({'range':'past'})['items'][0]['case']['id'],past)
        self.assertEqual(self.get_queue({'range':'all'})['total'],3)
        self.assertEqual(self.get_queue({'range':'custom','start':'2028-03-01','end':'2028-03-06'})['total'],1)
        self.change_case(history='合成资料变化')
        self.assertEqual(self.get_queue({'state':'needs_review'})['total'],1); self.assertEqual(self.get_queue({'state':'planned'})['total'],0)
        self.save('withdraw',self.request()['plans'][-1]); self.assertEqual(self.get_queue()['total'],0)
        new=self.save(data=FIXTURE['long_plan']); self.assertEqual(self.get_queue()['items'][0]['plan']['data'],FIXTURE['long_plan'])
        self.assertEqual(new['version'],1); self.assertEqual(self.get_queue(headers=self.other_headers)['items'][0]['case']['id'],foreign)

    def test_stable_sort_full_pages_exact_snapshot_and_fresh_relogin(self):
        for i in range(23): self.seed_plan(self.cid if i==0 else self.add_case('cat' if i%2 else 'dog'))
        first=self.get_queue({'page_size':'20'}); self.assertEqual((first['total'],len(first['items'])),(23,20))
        params={'page':'2','page_size':'20','snapshot':first['snapshot']}; last=self.get_queue(params)
        ids=[x['case']['id'] for x in first['items']+last['items']];self.assertEqual(ids,sorted(set(ids)));self.assertEqual(len(last['items']),3)
        self.assertEqual(self.get_queue({**params,'page':'3'})['items'],[])
        self.change_case(patient_name='合成更正身份');self.get_queue(params,409)
        self.get_queue({'page':'2'},422);self.get_queue({'page':'2','snapshot':'a'*64},409)
        token=self.client.post('/auth/login',data={'username':'owner@example.com','password':'synthetic-test-password'}).json()['access_token']
        self.assertEqual(self.get_queue(headers={'Authorization':'Bearer '+token})['total'],23)

    def test_auth_flags_unknown_duplicate_params_and_failed_reads_never_query_plans(self):
        self.seed_plan(); self.get_queue(expected=401,headers={})
        expired=auth_jwt.create_access_token('owner@example.com',minutes=-1)
        self.get_queue(expected=401,headers={'Authorization':'Bearer '+expired})
        with patch.object(queue,'owned_cases',side_effect=AssertionError('disabled must not query')):
            for flag in ({'FOLLOWUP_PLAN_QUEUE_ENABLED':'0'},{'FOLLOWUP_PLAN_QUEUE_SYNTHETIC_ONLY':'0'},{'FOLLOWUP_PLANS_ENABLED':'0'},{'FOLLOWUP_PLANS_SYNTHETIC_ONLY':'0'},{'ENVIRONMENT':'production'},{'RENDER':'true'}):
                with patch.dict(os.environ,flag): self.get_queue(expected=503)
        for params in ({'owner_id':'2'},[('range','today'),('range','all')],{'state':'done'},{'range':'overdue'},{'page':'0'},{'page':'01'},{'page':'1.0'},{'page':'true'},{'page':'1000001'},{'page_size':'51'},{'page_size':'0'},{'snapshot':'z'*64},{'start':'2028-02-29'}):self.get_queue(params,422)
        with patch.object(queue,'owned_cases',side_effect=OperationalError('synthetic',{},Exception('offline'))):self.get_queue(expected=503)

    def test_shanghai_calendar_leap_month_year_edges_independent_machine_timezone(self):
        for zone in ['UTC','America/Los_Angeles','Asia/Shanghai']:
            with patch.dict(os.environ,{'TZ':zone}):
                time.tzset();self.assertEqual(self.get_queue()['as_of_date'],'2028-02-29')
        time.tzset()
        for value in FIXTURE['invalid_dates']:
            self.get_queue({'range':'custom','start':value,'end':'9999-12-31'},422)
        self.get_queue({'range':'custom','start':'2028-03-01','end':'2028-02-29'},422)
        self.get_queue({'range':'custom','start':'0001-01-01','end':'9999-12-31'})
        for day in FIXTURE['date_edges']:
            self.seed_plan(self.add_case(),{**FIXTURE['plan'],'planned_date':day})
            self.assertEqual(self.get_queue({'range':'custom','start':day,'end':day})['total'],1)
        for instant,day,end in [('2026-12-31T16:00:00+00:00','2027-01-01','2027-01-07'),('2028-02-28T16:00:00+00:00','2028-02-29','2028-03-06'),('9999-12-30T16:00:00+00:00','9999-12-31','9999-12-31')]:
            class Boundary(datetime):
                @classmethod
                def now(cls,tz=None):return datetime.fromisoformat(instant)
            with patch.object(queue,'datetime',Boundary):
                r=self.get_queue({'range':'next7'});self.assertEqual(r['as_of_date'],day);self.assertEqual(r['filters']['end'],end)

    def test_read_only_fixed_selects_and_legacy_namespace_exclusion(self):
        self.seed_plan()
        with f.db.SessionLocal() as db:
            db.add(f.models.FollowUp(case_id=self.cid,status='done',channel='phone',note='legacy',due_date=datetime(2028,2,29)));db.commit()
        def check():
            before=self.all_business();sql=[]
            def capture(_c,_cur,s,*_):sql.append(s)
            event.listen(f.db.engine,'before_cursor_execute',capture)
            try:r=self.get_queue({'range':'all'})
            finally:event.remove(f.db.engine,'before_cursor_execute',capture)
            self.assertEqual(before,self.all_business());self.assertFalse(any(s.lstrip().split()[0].upper() in {'INSERT','UPDATE','DELETE','CREATE','DROP','ALTER'} for s in sql))
            return len([s for s in sql if s.lstrip().upper().startswith('SELECT')]),r
        a,_=check()
        for _ in range(49):self.seed_plan(self.add_case())
        b,result=check();self.assertEqual((a,b),(3,3));self.assertEqual(result['total'],50)
        self.get_queue({'range':'all','page_size':'50'})

    def test_all_chain_corruption_fails_even_outside_filter_and_without_repair(self):
        rid=self.seed_plan(count=2)
        with f.db.SessionLocal() as db:original={c.key:getattr(db.get(f.models.FollowUp,rid),c.key) for c in f.models.FollowUp.__table__.columns}
        meta=json.loads(original['note'])
        invalid=[{'note':'broken'},{'channel':'other'},{'status':'broken'},{'status':'cw-b14-broken'},{'done_at':datetime(2028,1,1)}, {'owner':'other'}, {'due_date':datetime(2027,1,1)}]
        invalid += [{'note':json.dumps({**meta,**change})} for change in [{'version':3},{'root_id':987654},{'withdrawal':{}},{'schema':'wrong'},{'case_snapshot':{**meta['case_snapshot'],'id':987654}},{'data':{**meta['data'],'items':[]}}]]
        for variant in invalid:
            with f.db.SessionLocal() as db:
                row=db.get(f.models.FollowUp,rid)
                for key,value in {**original,**variant}.items():setattr(row,key,value)
                db.commit()
            before=self.all_business();self.assertEqual(self.get_queue({'range':'past'},409)['detail'],'followup_invalid_saved_data');self.assertEqual(before,self.all_business())

    def test_exact_200_cases_10000_versions_and_excess_are_not_truncated(self):
        for i in range(200):self.seed_plan(self.cid if i==0 else self.add_case(),count=50)
        before=self.all_business();r=self.get_queue({'page_size':'50'});self.assertEqual((r['total'],len(r['items'])),(200,50));self.assertTrue(all(x['plan']['version']==50 for x in r['items']));self.assertEqual(before,self.all_business())
        with f.db.SessionLocal() as db:
            extra=f.models.FollowUp(case_id=self.cid,status='cw-b14-invalid',note='synthetic cap extra',due_date=datetime(2028,2,29));db.add(extra);db.commit();extra_id=extra.id
        before=self.all_business();self.assertEqual(self.get_queue(expected=409)['detail'],'followup_queue_scale_limit');self.assertEqual(before,self.all_business())
        with f.db.SessionLocal() as db:db.query(f.models.FollowUp).filter_by(id=extra_id).delete();db.commit()
        self.seed_plan(self.add_case());before=self.all_business();self.assertEqual(self.get_queue(expected=409)['detail'],'followup_queue_scale_limit');self.assertEqual(before,self.all_business())

    def test_per_case_51_version_chain_invalid_and_pure_validator_has_no_io(self):
        self.seed_plan(count=51);self.assertEqual(self.get_queue(expected=409)['detail'],'followup_invalid_saved_data')
        with f.db.SessionLocal() as db:
            case=db.get(f.models.Case,self.cid);rows=db.query(f.models.FollowUp).filter_by(case_id=self.cid).order_by(f.models.FollowUp.id).all()
            with patch.object(plans,'SessionLocal',side_effect=AssertionError('no I/O')):
                with self.assertRaises(plans.PlanError):plans.validated_records(rows,case)


if __name__=='__main__': unittest.main(verbosity=2)
