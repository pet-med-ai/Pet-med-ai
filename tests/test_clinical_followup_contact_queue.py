"""CW-B23 authenticated synthetic SQLite, literal expectations and bounded bulk reads."""
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4
from sqlalchemy import event
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.exc import OperationalError
from test_clinical_followup_contacts import ContactFixture, contacts, f, plans
from test_clinical_followup_plan_queue import QueueFixture, Clock
import clinical_followup_plan_queue as queue
import clinical_followup_contact_queue as service

FIXTURE = json.loads((Path(__file__).parent/'fixtures/clinical_followup_contact_queue_cw_b23_cases.json').read_text())


class ContactQueueFixture(ContactFixture):
    def setUp(self):
        with f.db.SessionLocal() as db:
            for model in (f.models.AuditLog, f.models.FollowUp, f.models.ConsultSession, f.models.Case): db.query(model).delete()
            db.commit()
        super().setUp()
        for manager in (patch.dict(os.environ, FOLLOWUP_PLAN_QUEUE_ENABLED='1', FOLLOWUP_PLAN_QUEUE_SYNTHETIC_ONLY='1',
                                 FOLLOWUP_CONTACT_QUEUE_ENABLED='1', FOLLOWUP_CONTACT_QUEUE_SYNTHETIC_ONLY='1'),
                        patch.object(queue, 'datetime', Clock)):
            manager.start(); self.addCleanup(manager.stop)

    add_case = QueueFixture.add_case
    seed_plan = QueueFixture.seed_plan

    def get_queue(self, params=None, expected=200, headers=None, included=True):
        values = {'range':'all', **({'include_followup_contacts':'true'} if included else {}), **(params or {})} if not isinstance(params,list) else params
        r=self.client.get('/api/followup-plan-queue',params=values,headers=self.owner_headers if headers is None else headers)
        self.assertEqual(r.status_code,expected,r.text); self.assertEqual(r.headers['cache-control'],'private, no-store')
        return r.json()

    def all_business(self):
        with f.db.SessionLocal() as db:
            return {m.__tablename__:[{p.key:getattr(r,p.key) for p in m.__mapper__.column_attrs}
                for r in db.query(m).order_by(m.log_id if m is f.models.AuditLog else m.id)]
                for m in (f.models.Case,f.models.FollowUp,f.models.AuditLog,f.models.ConsultSession)}

    def seed_contacts(self, cid=None, count=50, withdrawn=False):
        cid=cid or self.cid
        with f.db.SessionLocal() as db:
            case=db.get(f.models.Case,cid); source=next(p for p in plans.listing_data(db,case)['plans'] if p['stored_state']=='planned')
            now=datetime(2024,3,1); ids=[]
            for _ in range(count):
                row=f.models.FollowUp(case_id=cid,status=contacts.WITHDRAWN if withdrawn else contacts.RECORDED,channel=contacts.SOURCE,
                    owner=str(case.owner_id),due_date=plans.due_date(source['data']['planned_date']),created_at=now,updated_at=now,done_at=None)
                db.add(row);db.flush();ids.append(row.id)
                meta={'schema':contacts.SCHEMA,'root_id':row.id,'version':1,'data':copy.deepcopy(FIXTURE['contact']),
                    'case_snapshot':plans.case_snapshot(case),'source':contacts.frozen_source(source),'recorded_by':str(case.owner_id),
                    'recorded_at':now.replace(tzinfo=timezone.utc).isoformat(),'reason':'','withdrawal':
                    {'reason':'合成撤销','by':str(case.owner_id),'at':now.replace(tzinfo=timezone.utc).isoformat()} if withdrawn else None}
                row.note=json.dumps(meta,ensure_ascii=False)
                flag_modified(row, 'updated_at')
                for op in (['create','withdraw'] if withdrawn else ['create']):
                    rid=uuid4().hex
                    db.add(f.models.AuditLog(log_id=contacts.ledger_id(case.owner_id,cid,rid),request_id=rid,clinician_id=str(case.owner_id),
                        case_id=cid,source=contacts.SOURCE,event_type='followup_contact_'+op,action_taken=op,note='合成撤销' if op=='withdraw' else '',
                        created_at=now,extra_data={'schema':contacts.SCHEMA,'fingerprint':'a'*64,'record_id':row.id,'version':1,'operation':op,'content_hash':contacts.immutable_hash(meta)}))
            db.commit();return ids


class ContactQueueTests(ContactQueueFixture):
    def test_lifecycle_counts_exact_source_and_actual_time_order(self):
        old=self.contact_save(data={**FIXTURE['contact'],'occurred_at':'2024-02-28T23:59+08:00'})
        recent=self.contact_save(data=FIXTURE['long_contact'])
        corrected=self.contact_save('correct',old,{**old['data'],'note':'最近更正不是最近联系'})
        item=self.get_queue()['items'][0];self.assertEqual(item['contacts']['counts'],{'current':2,'historical':0})
        self.assertEqual(item['contacts']['latest']['current']['id'],recent['id'])
        self.assertEqual(item['contacts']['latest']['current']['data'],FIXTURE['long_contact'])
        latest=self.contact_save(data=FIXTURE['long_contact'])
        self.assertEqual(self.get_queue()['items'][0]['contacts']['latest']['current']['id'],latest['id'])
        self.source=self.save('correct',self.source,data=FIXTURE['corrected_plan'])
        item=self.get_queue({'contact_state':'historical_only'})['items'][0]
        self.assertEqual(item['contacts']['counts'],{'current':0,'historical':3})
        self.assertEqual(item['contacts']['latest']['historical']['source']['state'],'superseded')
        new=self.contact_save(data={**FIXTURE['contact'],'method':'other','outcome':'other'})
        self.assertEqual(self.get_queue({'contact_state':'current'})['total'],1)
        self.assertEqual(self.get_queue({'contact_state':'historical_only'})['total'],0)
        self.contact_save('withdraw',new)
        for row in (recent,latest,corrected):self.contact_save('withdraw',row)
        self.assertEqual(self.get_queue({'contact_state':'none'})['total'],1)
        self.assertEqual(self.get_queue()['items'][0]['contacts']['counts'],{'current':0,'historical':0})

    def test_minimal_identities_literal_history_replacement_and_no_completed_inference(self):
        row=self.contact_save()
        self.save('withdraw',self.source);self.source=self.save(data=FIXTURE['plan'])
        self.change_case(patient_name='更正后的身份',history='不应在清单传送的完整病例')
        item=self.get_queue()['items'][0];historical=item['contacts']['latest']['historical']
        self.assertEqual(historical['source']['state'],'withdrawn');self.assertEqual(historical['data'],row['data'])
        self.assertEqual(historical['source']['data'],row['source']['data'])
        self.assertNotEqual(item['case']['patient_name'],historical['case']['patient_name'])
        self.assertEqual(item['plan']['state'],'needs_review')
        body=json.dumps(item,ensure_ascii=False)
        for forbidden in ('owner_phone','case_snapshot','expected_state_token','不应在清单传送的完整病例'):self.assertNotIn(forbidden,body)
        self.assertEqual(self.get_queue({'state':'planned'})['total'],0)
        self.assertEqual(self.get_queue({'state':'needs_review'})['total'],1)
        for outcome in ('reached','not_reached','declined','other'):
            self.contact_save('correct',row,{**row['data'],'outcome':outcome})
            row=self.contact()['records'][-1]
            self.assertEqual(self.get_queue()['items'][0]['contacts']['latest']['historical']['data']['outcome'],outcome)
            self.assertEqual(self.request()['plans'][-1]['stored_state'],'planned')

    def test_auth_flags_parameters_and_default_isolation(self):
        self.contact_save();self.get_queue(headers={},expected=401);self.get_queue(headers={'Authorization':'Bearer invalid'},expected=401)
        with patch.object(service,'prefetched_contacts',side_effect=AssertionError('no contact read')):
            self.assertEqual(self.get_queue(included=False)['schema'],queue.SCHEMA)
            for flag in ['FOLLOWUP_CONTACT_QUEUE_ENABLED','FOLLOWUP_CONTACT_QUEUE_SYNTHETIC_ONLY','FOLLOWUP_CONTACTS_ENABLED',
                         'FOLLOWUP_CONTACTS_SYNTHETIC_ONLY','FOLLOWUP_PLAN_QUEUE_ENABLED','FOLLOWUP_PLAN_QUEUE_SYNTHETIC_ONLY','FOLLOWUP_PLANS_ENABLED','FOLLOWUP_PLANS_SYNTHETIC_ONLY']:
                with patch.dict(os.environ,{flag:'0'}):self.get_queue(expected=503)
            for flags in ({'ENVIRONMENT':'production'},{'RENDER':'true'}):
                with patch.dict(os.environ,flags):self.get_queue(expected=503)
        for params in ({'include_followup_contacts':'false'},{'include_followup_contacts':'1'},{'contact_state':'completed'},
                       {'owner_id':'2'},{'extra':'x'},{'page':'0'},{'page_size':'51'},{'snapshot':'bad'},
                       [('include_followup_contacts','true'),('include_followup_contacts','true')]):self.get_queue(params,422)
        self.get_queue({'contact_state':'all'},422,included=False)
        with patch.object(service,'prefetched_audits',side_effect=OperationalError('synthetic',{},Exception('offline'))):self.get_queue(expected=503)

    def test_multiple_accounts_deleted_cases_and_stable_paging(self):
        self.contact_save()
        for _ in range(22):self.seed_plan(self.add_case())
        with f.db.SessionLocal() as db:other=db.query(f.models.User).filter_by(email='other@example.com').one().id
        foreign=self.add_case(owner=other);self.seed_plan(foreign);self.seed_contacts(foreign,count=1)
        deleted=self.add_case(deleted=True);self.seed_plan(deleted);self.seed_contacts(deleted,count=1)
        first=self.get_queue();last=self.get_queue({'page':'2','snapshot':first['snapshot']})
        ids=[i['case']['id'] for i in first['items']+last['items']]
        self.assertEqual(len(ids),23);self.assertEqual(len(set(ids)),23);self.assertNotIn(foreign,ids);self.assertNotIn(deleted,ids)
        self.assertEqual(self.get_queue(headers=self.other_headers)['total'],1)
        self.get_queue({'page':'2'},422);self.get_queue({'page':'2','snapshot':first['snapshot'],'contact_state':'none'},409)
        self.get_queue({'page':'2','snapshot':first['snapshot'],'page_size':'1'},409)
        self.assertEqual(self.get_queue({'contact_state':'none'})['total'],22)
        token=self.client.post('/auth/login',data={'username':'owner@example.com','password':'synthetic-test-password'}).json()['access_token']
        self.assertEqual(self.get_queue(headers={'Authorization':'Bearer '+token})['snapshot'],first['snapshot'])

    def test_read_only_four_selects_scale_independent_and_all_audit_content_bound(self):
        self.contact_save()
        for count in (0,12):
            for _ in range(count):self.seed_contacts(self.seed_case(),count=2)
            sql=[];before=self.all_business()
            def capture(_c,_cur,s,*_):sql.append(s)
            event.listen(f.db.engine,'before_cursor_execute',capture)
            try:self.get_queue()
            finally:event.remove(f.db.engine,'before_cursor_execute',capture)
            self.assertEqual(before,self.all_business());self.assertEqual(sum(s.lstrip().upper().startswith('SELECT') for s in sql),5)
            self.assertFalse(any(s.lstrip().split()[0].upper() in {'INSERT','UPDATE','DELETE','ALTER','CREATE','DROP'} for s in sql))
        before=self.get_queue({'page_size':'1'})
        with f.db.SessionLocal() as db:
            audit=db.query(f.models.AuditLog).filter_by(case_id=self.cid,source=contacts.SOURCE).first();audit.model_version='audit metadata changed';db.commit()
        self.get_queue({'page':'2','page_size':'1','snapshot':before['snapshot']},409)

    def seed_case(self):
        cid=self.add_case();self.seed_plan(cid);return cid

    def test_bad_contact_and_receipts_fail_outside_filter_without_repair(self):
        row=self.contact_save()
        with f.db.SessionLocal() as db:
            original=db.get(f.models.FollowUp,row['id']).note
        for change in ({'schema':'wrong'},{'version':2},{'root_id':999999},{'source':{**json.loads(original)['source'],'id':999999}}):
            with f.db.SessionLocal() as db:db.get(f.models.FollowUp,row['id']).note=json.dumps({**json.loads(original),**change});db.commit()
            before=self.all_business();self.assertEqual(self.get_queue({'range':'today'},409)['detail'],'contact_invalid_saved_data');self.assertEqual(before,self.all_business())
        with f.db.SessionLocal() as db:
            db.get(f.models.FollowUp,row['id']).note=original
            audit=db.query(f.models.AuditLog).filter_by(case_id=self.cid,source=contacts.SOURCE).one();saved=copy.deepcopy(audit.extra_data);audit.extra_data={**saved,'content_hash':'b'*64};db.commit()
        self.get_queue(expected=409)
        with f.db.SessionLocal() as db:
            audit=db.query(f.models.AuditLog).filter_by(case_id=self.cid,source=contacts.SOURCE).one();audit.extra_data=saved;db.commit()
        self.assertEqual(self.get_queue()['total'],1)
        with f.db.SessionLocal() as db:db.query(f.models.AuditLog).filter_by(case_id=self.cid,source=contacts.SOURCE).delete();db.commit()
        self.get_queue(expected=409)

    def test_exact_limits_200_cases_10000_contacts_20000_audits_and_overflow(self):
        for i in range(200):
            cid=self.cid if i==0 else self.seed_case();self.seed_contacts(cid,withdrawn=True)
        r=self.get_queue({'page_size':'50'});self.assertEqual((r['total'],len(r['items'])),(200,50))
        self.assertTrue(all(i['contacts']['counts']=={'current':0,'historical':0} for i in r['items']))
        with f.db.SessionLocal() as db:
            row=f.models.AuditLog(log_id='z'*64,request_id='z'*32,clinician_id=str(self.owner_id),case_id=self.cid,source=contacts.SOURCE,action_taken='create');db.add(row);db.commit()
        self.assertEqual(self.get_queue(expected=409)['detail'],'followup_contact_queue_scale_limit')
        with f.db.SessionLocal() as db:db.query(f.models.AuditLog).filter_by(log_id='z'*64).delete();db.commit()
        self.seed_contacts(count=1);self.assertEqual(self.get_queue(expected=409)['detail'],'followup_contact_queue_scale_limit')
        self.seed_case();self.assertEqual(self.get_queue(expected=409)['detail'],'followup_queue_scale_limit')

    def test_per_case_caps_and_legacy_namespace(self):
        self.seed_contacts(withdrawn=True)
        with f.db.SessionLocal() as db:
            db.add(f.models.FollowUp(case_id=self.cid,status='done',channel='phone',note='legacy',due_date=datetime(2024,1,1)));db.commit()
        self.assertEqual(self.get_queue()['items'][0]['contacts']['counts']['current'],0)
        with f.db.SessionLocal() as db:
            db.add(f.models.AuditLog(log_id='z'*64,request_id='z'*32,clinician_id=str(self.owner_id),case_id=self.cid,source=contacts.SOURCE,action_taken='create'));db.commit()
        self.assertEqual(self.get_queue(expected=409)['detail'],'contact_invalid_saved_data')
        with f.db.SessionLocal() as db:db.query(f.models.AuditLog).filter_by(log_id='z'*64).delete();db.commit()
        self.seed_contacts(count=1);self.assertEqual(self.get_queue(expected=409)['detail'],'contact_invalid_saved_data')


if __name__=='__main__':unittest.main(verbosity=2)
