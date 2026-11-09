-- Administrator-only, after read_policy.sql and mc02. No service is enabled here.
DO $$ BEGIN
 IF NOT EXISTS(SELECT FROM pg_roles WHERE rolname='pmai_treatment_runtime') THEN
  CREATE ROLE pmai_treatment_runtime LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT NOCREATEDB NOCREATEROLE NOREPLICATION;
 END IF;
 IF EXISTS(SELECT FROM pg_roles WHERE rolname='pmai_treatment_runtime' AND
   (rolsuper OR rolbypassrls OR rolinherit OR rolcreatedb OR rolcreaterole OR rolreplication)) OR
   EXISTS(SELECT FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname='pmai_treatment_runtime')) THEN
  RAISE EXCEPTION 'Treatment runtime must be unprivileged with no memberships'; END IF;
END $$;
CREATE SCHEMA IF NOT EXISTS pmai_treatment;
REVOKE ALL ON SCHEMA pmai_treatment FROM PUBLIC;
GRANT USAGE ON SCHEMA public,pmai_scope,pmai_treatment TO pmai_treatment_runtime,pmai_scope_acl;
GRANT SELECT(id,email,hashed_password,status,principal_kind,token_version) ON users TO pmai_treatment_runtime;
GRANT SELECT,INSERT ON auth_sessions TO pmai_treatment_runtime;
GRANT UPDATE(revoked_at) ON auth_sessions TO pmai_treatment_runtime;
GRANT SELECT ON pmai_scope.clinical_cases,pmai_scope.demographic_cases TO pmai_treatment_runtime;
GRANT EXECUTE ON FUNCTION pmai_scope.actor_id(),pmai_scope.available_clinics(),pmai_scope.case_allowed(uuid,uuid,integer,integer,text,text) TO pmai_treatment_runtime;
-- Trusted NOLOGIN function owner; callers never receive base clinical SELECT/UPDATE.
GRANT SELECT,UPDATE ON cases,organizations,org_memberships TO pmai_scope_acl;
GRANT UPDATE(id) ON users,auth_sessions TO pmai_scope_acl;
GRANT SELECT ON clinician_profiles,patients,diagnostic_reports,observations,imaging_studies,consult_sessions,followups,audit_log TO pmai_scope_acl;
DROP POLICY IF EXISTS treatment_acl ON cases;
CREATE POLICY treatment_acl ON cases TO pmai_scope_acl USING(true) WITH CHECK(true);
CREATE OR REPLACE FUNCTION pmai_treatment.allowed(o uuid,c uuid,i integer,writing boolean,signing boolean)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS(SELECT FROM public.cases k WHERE k.org_id=o AND k.clinic_id=c AND k.id=i AND k.deleted_at IS NULL
  AND pmai_scope.case_allowed(o,c,i,k.owner_id,k.visibility,'clinical')
  AND (NOT writing OR EXISTS(SELECT FROM public.org_memberships m JOIN public.role_bindings b ON b.org_id=m.org_id AND b.membership_id=m.id
    WHERE m.org_id=o AND m.user_id=pmai_scope.actor_id() AND m.status='active'
    AND (k.visibility='clinic' OR k.owner_id=m.user_id) AND b.clinic_id=c AND b.scope_kind='clinic'
    AND b.revoked_at IS NULL AND b.valid_from<=statement_timestamp() AND (b.valid_until IS NULL OR b.valid_until>statement_timestamp())
    AND (b.role_code='veterinarian' OR (NOT signing AND b.role_code='clinical_assistant'))
    AND (NOT signing OR EXISTS(SELECT FROM public.clinician_profiles p WHERE p.org_id=o AND p.membership_id=m.id AND p.status='active')))))
$$;
ALTER FUNCTION pmai_treatment.allowed(uuid,uuid,integer,boolean,boolean) OWNER TO pmai_scope_acl;
CREATE OR REPLACE FUNCTION pmai_treatment.reviewer_valid(o uuid,c uuid,a integer,snapshot jsonb)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS(SELECT FROM public.org_memberships m JOIN public.clinician_profiles p ON p.org_id=m.org_id AND p.membership_id=m.id
   JOIN public.users u ON u.id=m.user_id JOIN public.role_bindings b ON b.org_id=m.org_id AND b.membership_id=m.id
   WHERE m.org_id=o AND m.user_id=a AND m.status='active' AND p.status='active' AND to_jsonb(p)=snapshot
   AND u.status='active' AND u.principal_kind='human' AND b.clinic_id=c AND b.scope_kind='clinic' AND b.role_code='veterinarian'
   AND b.revoked_at IS NULL AND b.valid_from<=statement_timestamp() AND (b.valid_until IS NULL OR b.valid_until>statement_timestamp()))
$$;
ALTER FUNCTION pmai_treatment.reviewer_valid(uuid,uuid,integer,jsonb) OWNER TO pmai_scope_acl;
CREATE OR REPLACE FUNCTION pmai_treatment.context(o uuid,c uuid,i integer,locking boolean)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE k public.cases; org public.organizations; m public.org_memberships; profile jsonb; src jsonb;
BEGIN
 IF NOT pmai_treatment.allowed(o,c,i,false,false) THEN RETURN NULL; END IF;
 IF locking THEN
  SELECT * INTO org FROM public.organizations WHERE id=o FOR UPDATE;
  SELECT * INTO m FROM public.org_memberships WHERE org_id=o AND user_id=pmai_scope.actor_id() FOR UPDATE;
  SELECT * INTO k FROM public.cases WHERE org_id=o AND clinic_id=c AND id=i FOR UPDATE;
  PERFORM id FROM public.users WHERE id=m.user_id FOR SHARE;
  PERFORM id FROM public.auth_sessions WHERE id=NULLIF(current_setting('pmai.session_id',true),'')::uuid FOR SHARE;
 ELSE
  SELECT * INTO org FROM public.organizations WHERE id=o;
  SELECT * INTO m FROM public.org_memberships WHERE org_id=o AND user_id=pmai_scope.actor_id();
  SELECT * INTO k FROM public.cases WHERE org_id=o AND clinic_id=c AND id=i;
 END IF;
 IF NOT pmai_treatment.allowed(o,c,i,false,false) THEN RETURN NULL; END IF;
 SELECT to_jsonb(p) INTO profile FROM public.clinician_profiles p WHERE p.org_id=o AND p.membership_id=m.id AND p.status='active';
 src=jsonb_build_object('case',to_jsonb(k)-ARRAY['updated_at','row_version'],
  'policy',jsonb_build_object('version',org.signing_policy_version,'review_policy',org.review_policy,'required_assurance',org.required_signing_assurance),
  'patient',(SELECT to_jsonb(p) FROM public.patients p WHERE p.org_id=o AND p.id=k.patient_id),
  'diagnostic_reports',COALESCE((SELECT jsonb_agg(to_jsonb(x) ORDER BY x.id) FROM public.diagnostic_reports x WHERE x.case_id=i),'[]'),
  'observations',COALESCE((SELECT jsonb_agg(to_jsonb(x) ORDER BY x.id) FROM public.observations x WHERE x.case_id=i),'[]'),
  'imaging_studies',COALESCE((SELECT jsonb_agg(to_jsonb(x) ORDER BY x.id) FROM public.imaging_studies x WHERE x.case_id=i),'[]'),
  'consult_sessions',COALESCE((SELECT jsonb_agg(to_jsonb(x) ORDER BY x.id) FROM public.consult_sessions x WHERE x.case_id=i),'[]'),
  'followups',COALESCE((SELECT jsonb_agg(to_jsonb(x) ORDER BY x.id) FROM public.followups x WHERE x.case_id=i),'[]'),
  'legacy_audit',COALESCE((SELECT jsonb_agg(to_jsonb(x) ORDER BY x.log_id) FROM public.audit_log x WHERE x.case_id=i),'[]'));
 RETURN jsonb_build_object('actor_id',m.user_id,'profile',profile,'source',src,
   'can_edit',pmai_treatment.allowed(o,c,i,true,false),'can_sign',pmai_treatment.allowed(o,c,i,true,true));
END $$;
ALTER FUNCTION pmai_treatment.context(uuid,uuid,integer,boolean) OWNER TO pmai_scope_acl;
DO $$ DECLARE t text; clinical boolean; BEGIN
 FOREACH t IN ARRAY ARRAY['treatment_plans','treatment_drafts','treatment_revisions','treatment_reviews','treatment_signatures','treatment_events','clinical_audit_events','command_receipts','signing_challenges'] LOOP
  EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY',t);
  EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY',t);
  EXECUTE format('DROP POLICY IF EXISTS treatment_read ON %I',t);
  EXECUTE format('DROP POLICY IF EXISTS treatment_insert ON %I',t);
  EXECUTE format('DROP POLICY IF EXISTS treatment_update ON %I',t);
  clinical=t IN ('treatment_reviews','treatment_signatures','treatment_events','signing_challenges');
  EXECUTE format('CREATE POLICY treatment_read ON %I FOR SELECT TO pmai_treatment_runtime USING (pmai_treatment.allowed(org_id,clinic_id,case_id,false,false)%s)',t,
    CASE WHEN t IN ('command_receipts','signing_challenges') THEN ' AND actor_id=pmai_scope.actor_id()' ELSE '' END);
  EXECUTE format('CREATE POLICY treatment_insert ON %I FOR INSERT TO pmai_treatment_runtime WITH CHECK (pmai_treatment.allowed(org_id,clinic_id,case_id,true,%L)%s)',t,clinical,
    CASE WHEN t IN ('command_receipts','signing_challenges','clinical_audit_events','treatment_events') THEN ' AND actor_id=pmai_scope.actor_id()'
         WHEN t='treatment_reviews' THEN ' AND reviewer_id=pmai_scope.actor_id()'
         WHEN t='treatment_signatures' THEN ' AND signer_id=pmai_scope.actor_id()'
         WHEN t='treatment_revisions' THEN ' AND created_by=pmai_scope.actor_id() AND origin=''clinical'''
         WHEN t='treatment_drafts' THEN ' AND updated_by=pmai_scope.actor_id() AND created_by=pmai_scope.actor_id()' ELSE '' END);
  IF t IN ('treatment_plans','treatment_drafts','command_receipts','signing_challenges') THEN
   EXECUTE format('CREATE POLICY treatment_update ON %I FOR UPDATE TO pmai_treatment_runtime USING (pmai_treatment.allowed(org_id,clinic_id,case_id,true,%L)%s) WITH CHECK (pmai_treatment.allowed(org_id,clinic_id,case_id,true,%L)%s)',t,clinical,
    CASE WHEN t IN ('command_receipts','signing_challenges') THEN ' AND actor_id=pmai_scope.actor_id()' ELSE '' END,clinical,
    CASE WHEN t IN ('command_receipts','signing_challenges') THEN ' AND actor_id=pmai_scope.actor_id()'
         WHEN t='treatment_drafts' THEN ' AND updated_by=pmai_scope.actor_id()' ELSE '' END);
   EXECUTE format('GRANT UPDATE ON %I TO pmai_treatment_runtime',t);
  END IF;
  EXECUTE format('GRANT SELECT,INSERT ON %I TO pmai_treatment_runtime',t);
 END LOOP;
END $$;
-- Defense against accidental service-side bindings/ordering errors, including SQL
-- writes under the runtime role. Cross-scope bindings also have composite FKs.
CREATE OR REPLACE FUNCTION pmai_treatment.signature_guard() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE ctx jsonb; rev public.treatment_revisions; review public.treatment_reviews; ch public.signing_challenges; cmd public.command_receipts; audit public.clinical_audit_events;
BEGIN
 ctx=pmai_treatment.context(NEW.org_id,NEW.clinic_id,NEW.case_id,true);
 SELECT * INTO rev FROM public.treatment_revisions WHERE id=NEW.revision_id;
 SELECT * INTO review FROM public.treatment_reviews WHERE id=NEW.review_id;
 SELECT * INTO ch FROM public.signing_challenges WHERE id=NEW.challenge_id FOR UPDATE;
 SELECT * INTO cmd FROM public.command_receipts WHERE id=NEW.command_id;
 SELECT * INTO audit FROM public.clinical_audit_events WHERE id=NEW.audit_event_id;
 IF ctx IS NULL OR NOT (ctx->>'can_sign')::boolean OR
    (ctx->'source'->'policy'->>'required_assurance')<>'account_attestation' OR
    NOT EXISTS(SELECT FROM public.treatment_plans WHERE id=NEW.plan_id AND head_revision_id=NEW.revision_id) OR
    NOT EXISTS(SELECT FROM public.treatment_drafts WHERE plan_id=NEW.plan_id AND draft_version=rev.draft_version) OR
    rev.origin<>'clinical' OR rev.source_manifest IS DISTINCT FROM ctx->'source' OR review.decision<>'approve' OR
    NOT pmai_treatment.reviewer_valid(NEW.org_id,NEW.clinic_id,review.reviewer_id,review.clinician_snapshot) OR
    review.review_mode IS DISTINCT FROM ctx->'source'->'policy'->>'review_policy' OR
    (review.review_mode='two_person' AND review.reviewer_id=NEW.signer_id) OR
    NEW.signer_id IS DISTINCT FROM pmai_scope.actor_id() OR NEW.clinician_snapshot IS DISTINCT FROM ctx->'profile' OR
    ch.id IS NULL OR ch.action<>'sign' OR ch.revision_id<>NEW.revision_id OR ch.content_hash<>NEW.content_hash OR
    ch.actor_id<>NEW.signer_id OR ch.session_id<>NULLIF(current_setting('pmai.session_id',true),'')::uuid OR
    ch.consumed_by_command IS DISTINCT FROM NEW.command_id OR ch.expires_at<=clock_timestamp() OR
    cmd.id IS NULL OR cmd.state<>'pending' OR cmd.operation<>'sign' OR cmd.actor_id<>NEW.signer_id OR cmd.lease_until<=clock_timestamp() OR
    audit.id IS NULL OR audit.actor_id<>NEW.signer_id OR audit.action<>'sign' OR audit.target_id<>NEW.id OR
    audit.command_id<>NEW.command_id OR audit.payload_sha256<>NEW.content_hash THEN
  RAISE EXCEPTION 'Invalid signature binding'; END IF;
 RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS signature_guard ON treatment_signatures;
CREATE TRIGGER signature_guard BEFORE INSERT ON treatment_signatures FOR EACH ROW EXECUTE FUNCTION pmai_treatment.signature_guard();
CREATE OR REPLACE FUNCTION pmai_treatment.active_guard() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF EXISTS(SELECT FROM public.treatment_plans p JOIN public.treatment_events e ON e.signature_id=p.active_signature_id
           WHERE p.id=COALESCE(to_jsonb(NEW)->>'plan_id',to_jsonb(NEW)->>'id')::uuid) THEN
  RAISE EXCEPTION 'Active signature has terminal event'; END IF;
 IF EXISTS(SELECT FROM public.treatment_signatures s JOIN public.treatment_plans p ON p.id=s.plan_id
   LEFT JOIN public.treatment_events e ON e.signature_id=s.id
   WHERE p.id=COALESCE(to_jsonb(NEW)->>'plan_id',to_jsonb(NEW)->>'id')::uuid
     AND e.id IS NULL AND p.active_signature_id IS DISTINCT FROM s.id) THEN
  RAISE EXCEPTION 'Effective signature must be the active signature'; END IF;
 RETURN NULL;
END $$;
DROP TRIGGER IF EXISTS active_guard ON treatment_plans;
CREATE CONSTRAINT TRIGGER active_guard AFTER INSERT OR UPDATE ON treatment_plans DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pmai_treatment.active_guard();
DROP TRIGGER IF EXISTS active_guard ON treatment_events;
CREATE CONSTRAINT TRIGGER active_guard AFTER INSERT ON treatment_events DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pmai_treatment.active_guard();
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA pmai_treatment FROM PUBLIC;
GRANT EXECUTE ON FUNCTION pmai_treatment.allowed(uuid,uuid,integer,boolean,boolean),pmai_treatment.context(uuid,uuid,integer,boolean) TO pmai_treatment_runtime;

GRANT EXECUTE ON FUNCTION pmai_treatment.reviewer_valid(uuid,uuid,integer,jsonb) TO pmai_treatment_runtime;
CREATE OR REPLACE FUNCTION pmai_treatment.review_guard() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE ctx jsonb; rev public.treatment_revisions;
BEGIN
 ctx=pmai_treatment.context(NEW.org_id,NEW.clinic_id,NEW.case_id,true);
 SELECT * INTO rev FROM public.treatment_revisions WHERE id=NEW.revision_id;
 IF ctx IS NULL OR NOT (ctx->>'can_sign')::boolean OR NEW.reviewer_id IS DISTINCT FROM pmai_scope.actor_id() OR
  NEW.clinician_snapshot IS DISTINCT FROM ctx->'profile' OR NEW.review_mode IS DISTINCT FROM ctx->'source'->'policy'->>'review_policy' OR
  rev.id IS NULL OR NOT EXISTS(SELECT FROM public.treatment_drafts WHERE plan_id=NEW.plan_id AND draft_version=rev.draft_version) OR
    rev.origin<>'clinical' OR rev.source_manifest IS DISTINCT FROM ctx->'source' OR
  NOT EXISTS(SELECT FROM public.treatment_plans WHERE id=NEW.plan_id AND head_revision_id=NEW.revision_id) THEN
  RAISE EXCEPTION 'Invalid clinical review binding'; END IF;
 RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS review_guard ON treatment_reviews;
CREATE TRIGGER review_guard BEFORE INSERT ON treatment_reviews FOR EACH ROW EXECUTE FUNCTION pmai_treatment.review_guard();
CREATE OR REPLACE FUNCTION pmai_treatment.event_guard() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE ctx jsonb; cmd public.command_receipts; old_signature public.treatment_signatures;
BEGIN
 ctx=pmai_treatment.context(NEW.org_id,NEW.clinic_id,NEW.case_id,true);
 SELECT * INTO cmd FROM public.command_receipts WHERE id=NEW.command_id;
 SELECT * INTO old_signature FROM public.treatment_signatures WHERE id=NEW.signature_id;
 IF ctx IS NULL OR NOT (ctx->>'can_sign')::boolean OR NEW.actor_id IS DISTINCT FROM pmai_scope.actor_id() OR
  cmd.id IS NULL OR cmd.actor_id<>NEW.actor_id OR cmd.state<>'pending' OR cmd.lease_until<=clock_timestamp() OR
  NOT EXISTS(SELECT FROM public.treatment_plans WHERE id=NEW.plan_id AND active_signature_id=NEW.signature_id) THEN
  RAISE EXCEPTION 'Invalid terminal event binding'; END IF;
 IF NEW.event='superseded' THEN
  IF cmd.operation<>'sign' OR NOT EXISTS(SELECT FROM public.treatment_signatures s JOIN public.treatment_revisions r ON r.id=s.revision_id
    WHERE s.id=NEW.successor_signature_id AND s.command_id=NEW.command_id AND r.amendment_of=NEW.signature_id) THEN
   RAISE EXCEPTION 'Invalid superseding signature'; END IF;
 ELSE
  IF cmd.operation<>'revoke' OR NOT EXISTS(SELECT FROM public.signing_challenges c
     WHERE c.consumed_by_command=NEW.command_id AND c.action='revoke' AND c.target_signature_id=NEW.signature_id
      AND c.revision_id=old_signature.revision_id AND c.content_hash=old_signature.content_hash AND c.actor_id=NEW.actor_id
      AND c.session_id=NULLIF(current_setting('pmai.session_id',true),'')::uuid AND c.expires_at>clock_timestamp())
    OR NOT EXISTS(SELECT FROM public.clinical_audit_events a WHERE a.command_id=NEW.command_id AND a.action='revoke' AND a.target_id=NEW.id AND a.actor_id=NEW.actor_id) THEN
   RAISE EXCEPTION 'Revocation requires a fresh action-bound challenge and audit'; END IF;
 END IF;
 RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS event_guard ON treatment_events;
CREATE TRIGGER event_guard BEFORE INSERT ON treatment_events FOR EACH ROW EXECUTE FUNCTION pmai_treatment.event_guard();
-- Commit-time proof that every signature/event finished its atomic command.
CREATE OR REPLACE FUNCTION pmai_treatment.committed_fact() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF NOT EXISTS(SELECT FROM public.command_receipts WHERE id=NEW.command_id AND state='committed' AND actor_id=COALESCE(to_jsonb(NEW)->>'signer_id',to_jsonb(NEW)->>'actor_id')::integer) THEN
  RAISE EXCEPTION 'Clinical fact has no committed command'; END IF;
 RETURN NULL;
END $$;
DROP TRIGGER IF EXISTS committed_fact ON treatment_signatures;
CREATE CONSTRAINT TRIGGER committed_fact AFTER INSERT ON treatment_signatures DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pmai_treatment.committed_fact();
DROP TRIGGER IF EXISTS committed_fact ON treatment_events;
CREATE CONSTRAINT TRIGGER committed_fact AFTER INSERT ON treatment_events DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pmai_treatment.committed_fact();
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA pmai_treatment FROM PUBLIC;

DROP TRIGGER IF EXISTS active_guard ON treatment_signatures;
CREATE CONSTRAINT TRIGGER active_guard AFTER INSERT ON treatment_signatures DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pmai_treatment.active_guard();
