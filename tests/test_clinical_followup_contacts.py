"""Real JWT and disposable SQLite; raw expected facts independent of service formatting."""
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
from test_clinical_followup_plans import FollowupFixture, f, plans
import clinical_followup_contacts as contacts

FIXTURE = json.loads((Path(__file__).parent/'fixtures/clinical_followup_contacts_cw_b19_cases.json').read_text())


class ContactFixture(FollowupFixture):
    def setUp(self):
        super().setUp()
        flags=patch.dict(os.environ, FOLLOWUP_CONTACTS_ENABLED='1',FOLLOWUP_CONTACTS_SYNTHETIC_ONLY='1')
        flags.start();self.addCleanup(flags.stop)
        self.source=self.save(data=FIXTURE['plan'])
        self.contact_root=f'/api/cases/{self.cid}/followup-contacts'

    def contact(self,suffix='',body=None,expected=200,headers=None):
        r=self.client.request('GET' if body is None else 'POST',self.contact_root+suffix,
            headers=self.owner_headers if headers is None else headers,**({'json':body} if body is not None else {}))
        self.assertEqual(r.status_code,expected,r.text)
        self.assertEqual(r.headers['cache-control'],'private, no-store')
        return r.json()

    def contact_body(self,operation='create',row=None,data=None,source=None,reason=None):
        listing=self.contact()
        p=source or next(p for p in listing['plans'] if p['id']==(row['source']['id'] if row else self.source['id']))
        return {'request_id':uuid4().hex,'operation':operation,'contact_id':row['id'] if row else None,
            'expected_contact_token':row['token'] if row else '', 'source_plan_id':p['id'],'source_plan_version':p['version'],
            'expected_source_token':p['token'],'expected_case_token':listing['case_token'],'expected_state_token':listing['state_token'],
            'data':None if operation=='withdraw' else copy.deepcopy(data or FIXTURE['contact']),
            'reason':reason if reason is not None else ('' if operation=='create' else FIXTURE['correction_reason'])}

    def contact_review(self,body=None):
        body=body or self.contact_body()
        return {**body,'preview_token':self.contact('/preview',body)['preview_token'],'reviewed':True}

    def contact_save(self,operation='create',row=None,data=None,**kw):
        return self.contact('/confirm',self.contact_review(self.contact_body(operation,row,data,**kw)))['record']


class ContactTests(ContactFixture):
    def test_lifecycle_raw_source_case_idempotency_and_relogin(self):
        before=self.case();source=self.request();request=self.contact_review()
        first=self.contact('/confirm',request)['record'];self.assertEqual(first['data'],FIXTURE['contact'])
        self.assertEqual(first['source'],contacts.frozen_source(self.source))
        written=self.business();replay=self.contact('/confirm',request)
        self.assertFalse(replay['writes_database']);self.assertEqual(self.business(),written)
        self.contact('/confirm',{**request,'data':{**request['data'],'note':'changed'}},409)
        second=self.contact_save('correct',first,FIXTURE['corrected'])
        self.assertEqual((second['root_id'],second['version']),(first['id'],2))
        last=self.contact_save('withdraw',second,reason=FIXTURE['withdrawal_reason'])
        self.assertEqual(last['withdrawal']['reason'],FIXTURE['withdrawal_reason'])
        third=self.contact_save();self.assertEqual((third['root_id'],third['version']),(third['id'],1))
        f.db.engine.dispose()
        token=self.client.post('/auth/login',data={'username':'owner@example.com','password':'synthetic-test-password'}).json()['access_token']
        listed=self.contact(headers={'Authorization':'Bearer '+token})
        self.assertEqual([r['state'] for r in listed['records']],['superseded','withdrawn','recorded'])
        self.assertEqual([r['data'] for r in listed['records']],[FIXTURE['contact'],FIXTURE['corrected'],FIXTURE['contact']])
        self.assertEqual(self.case(),before);self.assertEqual(self.request(),source)
        self.assertEqual(self.contact('/requests/'+request['request_id'])['record']['id'],first['id'])
        rows=[r for r in self.business()['followups'] if r['channel']==contacts.SOURCE]
        self.assertTrue(all(r['done_at'] is None for r in rows))
        self.assertEqual(contacts.contact_time(FIXTURE['contact']['occurred_at']).isoformat(),FIXTURE['expected_utc'])

    def test_get_preview_status_no_writes_and_permission_errors_private(self):
        before=self.business();sql=[]
        def capture(_c,_cur,statement,*_):
            if statement.lstrip().split()[0].upper() in {'INSERT','UPDATE','DELETE','CREATE','ALTER','DROP'}:sql.append(statement)
        event.listen(f.db.engine,'before_cursor_execute',capture)
        try:
            self.contact();self.contact_review();self.contact('/requests/'+uuid4().hex)
        finally:event.remove(f.db.engine,'before_cursor_execute',capture)
        self.assertEqual(sql,[]);self.assertEqual(self.business(),before)
        self.contact(headers={},expected=401);self.contact(headers=self.other_headers,expected=404)
        self.contact(headers={'Authorization':'Bearer invalid'},expected=401)
        for flag in ['FOLLOWUP_CONTACTS_ENABLED','FOLLOWUP_CONTACTS_SYNTHETIC_ONLY','FOLLOWUP_PLANS_ENABLED']:
            with patch.dict(os.environ,{flag:'0'}):self.contact(expected=503)
        for values in [{'ENVIRONMENT':'production'},{'RENDER':'true'}]:
            with patch.dict(os.environ,values):self.contact(expected=503)
        with f.db.SessionLocal() as db:
            db.get(f.models.Case,self.cid).deleted_at=datetime.utcnow();db.commit()
        self.contact(expected=404)
        with f.db.SessionLocal() as db:
            db.get(f.models.Case,self.cid).deleted_at=None;db.commit()
        self.assertEqual(self.contact()['records'],[])

    def test_strict_calendar_choices_lengths_unicode_and_explicit_boolean(self):
        base=self.contact_body();before=self.business()
        for v in FIXTURE['invalid_times']+['9999-12-31T12:00+08:00']:
            self.contact('/preview',{**base,'data':{**base['data'],'occurred_at':v}},422)
        for change in [{'note':' '},{'note':'x'*2001},{'note':'\x00'},{'note':'\ud800'},{'next_action':'x'*1001},{'method':[]},{'method':'sms'},{'outcome':'completed'},{'extra':1}]:
            self.contact('/preview',{**base,'data':{**base['data'],**change}},422)
        for change in [{'source_plan_id':True},{'source_plan_version':51},{'contact_id':'1'},{'extra':1}]:self.contact('/preview',{**base,**change},422)
        request=self.contact_review(base)
        for value in [False,1,'true',None]:self.contact('/confirm',{**request,'reviewed':value},422)
        missing=dict(request);del missing['reviewed'];self.contact('/confirm',missing,422)
        self.assertEqual(before,self.business())
        boundary={**FIXTURE['contact'],'note':'🐾'*2000,'next_action':'é'*1000}
        self.assertEqual(self.contact_save(data=boundary)['data'],boundary)
        for method in sorted(contacts.METHODS):
            for outcome in sorted(contacts.OUTCOMES):self.contact('/preview',self.contact_body(data={**FIXTURE['contact'],'method':method,'outcome':outcome}))

    def test_timezone_and_cross_day_conversion_independent_of_process_zone(self):
        for zone in ['UTC','America/Los_Angeles','Asia/Tokyo']:
            with patch.dict(os.environ,TZ=zone):
                time.tzset();self.assertEqual(contacts.contact_time(FIXTURE['contact']['occurred_at']).isoformat(),FIXTURE['expected_utc'])
                self.assertEqual(contacts.contact_time('2024-03-01T00:15+08:00').isoformat(),'2024-02-29T16:15:00')
        time.tzset()

    def test_plan_changes_preserve_historical_source_and_allow_correction_not_rebinding(self):
        first=self.contact_save();pending=self.contact_review()
        updated=self.save('correct',self.source,data={**FIXTURE['plan'],'purpose':'新版合成计划'})
        self.contact('/confirm',pending,409)
        historical=self.contact()['records'][0];self.assertEqual(historical['source_state'],'superseded')
        self.assertEqual(historical['source'],first['source'])
        self.contact('/preview',self.contact_body(source=self.source),409)
        self.contact('/preview',self.contact_body('correct',historical,source=updated),409)
        changed=self.contact_save('correct',historical,FIXTURE['corrected']);self.assertEqual(changed['source'],first['source'])
        self.source=updated;current=self.contact_save();self.save('withdraw',updated)
        current=self.contact()['records'][-1];self.assertEqual(current['source_state'],'withdrawn')
        self.contact_save('correct',current,FIXTURE['corrected'])
        self.contact('/preview',self.contact_body(),409)

    def test_body_identity_source_target_changes_and_foreign_source(self):
        first=self.contact_save()
        for key in plans.FIELDS:
            pending=self.contact_review(self.contact_body('correct',self.contact()['records'][-1]))
            self.change_case(**{key:'后续 '+key});self.contact('/confirm',pending,409)
        self.contact('/preview',self.contact_body(),409)
        current=self.contact()['records'][0];self.assertEqual(current['source_state'],'needs_review')
        self.contact_save('correct',current)
        for change in [{'source_plan_id':2**50},{'source_plan_version':49}]:self.contact('/preview',{**self.contact_body(),**change},404)
        self.assertEqual(self.contact()['records'][0]['source'],first['source'])

    def test_cap_preserves_history_and_allows_withdrawal(self):
        row=self.contact_save()
        for _ in range(2,51):row=self.contact_save('correct',row)
        self.assertEqual(len(self.contact()['records']),50)
        self.contact('/preview',self.contact_body('correct',row),422)
        self.contact('/preview',self.contact_body(),422)
        self.contact_save('withdraw',row);self.assertEqual(len(self.contact()['records']),50)
        with f.db.SessionLocal() as db:
            db.add(f.models.FollowUp(case_id=self.cid,status=contacts.RECORDED,channel=contacts.SOURCE,due_date=datetime(2024,2,29),note='broken'));db.commit()
        self.contact(expected=409)

    def test_corruption_and_missing_audit_never_imply_empty_or_not_committed(self):
        request=self.contact_review();row=self.contact('/confirm',request)['record'];original=self.business()
        contact_row=next(r for r in original['followups'] if r['id']==row['id']);meta=json.loads(contact_row['note'])
        variants=[{'status':'cw-b19-broken'},{'channel':'wrong'},{'note':'broken'},{'done_at':datetime(2024,3,1)}, {'due_date':datetime(2020,1,1)}]
        variants += [{'note':json.dumps({**meta,**x})} for x in [{'root_id':999},{'version':True},{'recorded_by':'wrong'},{'source':{**meta['source'],'version':2}},{'data':{**meta['data'],'note':'tampered'}}]]
        for change in variants:
            with f.db.SessionLocal() as db:
                stored=db.get(f.models.FollowUp,row['id'])
                for key,value in {**contact_row,**change}.items():setattr(stored,key,value)
                db.commit()
            before=self.business();self.contact(expected=409);self.contact('/requests/'+uuid4().hex,expected=409);self.assertEqual(before,self.business())
        with f.db.SessionLocal() as db:
            stored=db.get(f.models.FollowUp,row['id'])
            for key,value in contact_row.items():setattr(stored,key,value)
            db.query(f.models.AuditLog).filter_by(source=contacts.SOURCE).delete();db.commit()
        self.contact(expected=409);self.contact('/requests/'+request['request_id'],expected=409)


if __name__=='__main__':unittest.main(verbosity=2)
