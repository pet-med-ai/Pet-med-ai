ALTER TABLE organizations
 ADD COLUMN review_policy text NOT NULL DEFAULT 'self_allowed' CHECK(review_policy IN ('self_allowed','two_person')),
 ADD COLUMN required_signing_assurance text NOT NULL DEFAULT 'account_attestation' CHECK(required_signing_assurance IN ('account_attestation','certificate_signature')),
 ADD COLUMN signing_policy_version bigint NOT NULL DEFAULT 1 CHECK(signing_policy_version>0);
CREATE TABLE clinician_profiles (
 id uuid PRIMARY KEY, org_id uuid NOT NULL, membership_id uuid NOT NULL,
 display_name text NOT NULL CHECK(length(display_name)>0), credential_ref text NOT NULL CHECK(length(credential_ref)>0),
 status text NOT NULL CHECK(status IN ('active','revoked')), verified_by integer NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
 verified_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(org_id,membership_id) REFERENCES org_memberships(org_id,id) ON DELETE RESTRICT,
 UNIQUE(org_id,membership_id)
);
CREATE TABLE treatment_plans (
 id uuid PRIMARY KEY, org_id uuid NOT NULL, clinic_id uuid NOT NULL, case_id integer NOT NULL,
 head_revision_id uuid, active_signature_id uuid, lock_version bigint NOT NULL DEFAULT 1 CHECK(lock_version>0),
 archived_at timestamptz,
 UNIQUE(org_id,clinic_id,case_id), UNIQUE(org_id,clinic_id,case_id,id),
 FOREIGN KEY(org_id,clinic_id,case_id) REFERENCES cases(org_id,clinic_id,id) ON DELETE RESTRICT
);
CREATE TABLE command_receipts (
 id uuid PRIMARY KEY, org_id uuid NOT NULL, clinic_id uuid NOT NULL, case_id integer NOT NULL, plan_id uuid NOT NULL,
 actor_id integer NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
 operation text NOT NULL CHECK(operation IN ('draft.save','revision.freeze','review','sign','amend','revoke')),
 idempotency_key text NOT NULL CHECK(idempotency_key ~ '^[0-9a-f]{64}$'),
 request_hash text NOT NULL CHECK(request_hash ~ '^[0-9a-f]{64}$'),
 state text NOT NULL CHECK(state IN ('pending','committed','failed','cancelled')),
 attempt_version integer NOT NULL DEFAULT 1 CHECK(attempt_version>0), lease_until timestamptz,
 http_status integer, result jsonb, error_code text, created_at timestamptz NOT NULL DEFAULT now(), completed_at timestamptz,
 UNIQUE(org_id,actor_id,operation,idempotency_key), UNIQUE(org_id,clinic_id,case_id,plan_id,id),
 FOREIGN KEY(org_id,clinic_id,case_id,plan_id) REFERENCES treatment_plans(org_id,clinic_id,case_id,id) ON DELETE RESTRICT,
 CHECK((state='pending' AND completed_at IS NULL AND result IS NULL AND lease_until IS NOT NULL) OR
       (state<>'pending' AND completed_at IS NOT NULL AND http_status IS NOT NULL))
);
CREATE TABLE treatment_drafts (
 plan_id uuid PRIMARY KEY, org_id uuid NOT NULL, clinic_id uuid NOT NULL, case_id integer NOT NULL,
 base_revision_id uuid, amendment_of uuid, content jsonb NOT NULL,
 draft_version bigint NOT NULL CHECK(draft_version>0), created_by integer NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
 updated_by integer NOT NULL REFERENCES users(id) ON DELETE RESTRICT, updated_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(org_id,clinic_id,case_id,plan_id) REFERENCES treatment_plans(org_id,clinic_id,case_id,id) ON DELETE RESTRICT
);
CREATE TABLE treatment_revisions (
 id uuid PRIMARY KEY, org_id uuid NOT NULL, clinic_id uuid NOT NULL, case_id integer NOT NULL, plan_id uuid NOT NULL,
 revision_no integer NOT NULL CHECK(revision_no>0), draft_version bigint NOT NULL CHECK(draft_version>0), predecessor_id uuid, amendment_of uuid,
 schema_version text NOT NULL CHECK(schema_version='treatment-content-v1'), content jsonb NOT NULL, source_manifest jsonb NOT NULL,
 canonical_bytes bytea NOT NULL, content_sha256 text NOT NULL CHECK(content_sha256 ~ '^[0-9a-f]{64}$'),
 created_by integer NOT NULL REFERENCES users(id) ON DELETE RESTRICT, created_at timestamptz NOT NULL,
 origin text NOT NULL CHECK(origin IN ('clinical','legacy_import')),
 UNIQUE(plan_id,revision_no), UNIQUE(org_id,clinic_id,case_id,plan_id,id), UNIQUE(org_id,clinic_id,case_id,plan_id,id,content_sha256),
 FOREIGN KEY(org_id,clinic_id,case_id,plan_id) REFERENCES treatment_plans(org_id,clinic_id,case_id,id) ON DELETE RESTRICT,
 FOREIGN KEY(org_id,clinic_id,case_id,plan_id,predecessor_id) REFERENCES treatment_revisions(org_id,clinic_id,case_id,plan_id,id) ON DELETE RESTRICT,
 CHECK(encode(sha256(canonical_bytes),'hex')=content_sha256),
 CHECK(convert_from(canonical_bytes,'UTF8')::jsonb->'content'=content),
 CHECK(convert_from(canonical_bytes,'UTF8')::jsonb->'source_manifest'=source_manifest),
 CHECK(convert_from(canonical_bytes,'UTF8')::jsonb->>'revision_id'=id::text),
 CHECK(convert_from(canonical_bytes,'UTF8')::jsonb->>'plan_id'=plan_id::text),
 CHECK(convert_from(canonical_bytes,'UTF8')::jsonb->>'org_id'=org_id::text),
 CHECK(convert_from(canonical_bytes,'UTF8')::jsonb->>'clinic_id'=clinic_id::text),
 CHECK((convert_from(canonical_bytes,'UTF8')::jsonb->>'case_id')::integer=case_id),
 CHECK((convert_from(canonical_bytes,'UTF8')::jsonb->>'created_by')::integer=created_by),
 CHECK((convert_from(canonical_bytes,'UTF8')::jsonb->>'created_at')::timestamptz=created_at)
);
CREATE TABLE treatment_reviews (
 id uuid PRIMARY KEY, org_id uuid NOT NULL, clinic_id uuid NOT NULL, case_id integer NOT NULL, plan_id uuid NOT NULL,
 revision_id uuid NOT NULL UNIQUE, reviewed_hash text NOT NULL,
 decision text NOT NULL CHECK(decision IN ('approve','request_revision','reject')),
 reviewer_id integer NOT NULL REFERENCES users(id) ON DELETE RESTRICT, clinician_snapshot jsonb NOT NULL,
 review_mode text NOT NULL CHECK(review_mode IN ('self_allowed','two_person')), reason text NOT NULL, reviewed_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(org_id,clinic_id,case_id,plan_id,revision_id,id,reviewed_hash),
 FOREIGN KEY(org_id,clinic_id,case_id,plan_id,revision_id,reviewed_hash) REFERENCES treatment_revisions(org_id,clinic_id,case_id,plan_id,id,content_sha256) ON DELETE RESTRICT
);
CREATE TABLE signing_challenges (
 id uuid PRIMARY KEY, org_id uuid NOT NULL, clinic_id uuid NOT NULL, case_id integer NOT NULL, plan_id uuid NOT NULL,
 revision_id uuid NOT NULL, content_hash text NOT NULL, action text NOT NULL CHECK(action IN ('sign','revoke')),
 target_signature_id uuid, actor_id integer NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
 session_id uuid NOT NULL REFERENCES auth_sessions(id) ON DELETE RESTRICT,
 method text NOT NULL CHECK(method='password'), verified_at timestamptz NOT NULL DEFAULT now(), expires_at timestamptz NOT NULL,
 consumed_by_command uuid UNIQUE,
 FOREIGN KEY(org_id,clinic_id,case_id,plan_id,revision_id,content_hash) REFERENCES treatment_revisions(org_id,clinic_id,case_id,plan_id,id,content_sha256) ON DELETE RESTRICT,
 FOREIGN KEY(org_id,clinic_id,case_id,plan_id,consumed_by_command) REFERENCES command_receipts(org_id,clinic_id,case_id,plan_id,id) ON DELETE RESTRICT,
 CHECK(expires_at>verified_at AND expires_at<=verified_at+interval '5 minutes'),
 CHECK((action='sign' AND target_signature_id IS NULL) OR (action='revoke' AND target_signature_id IS NOT NULL))
);
CREATE TABLE clinical_audit_events (
 id uuid PRIMARY KEY, org_id uuid NOT NULL, clinic_id uuid NOT NULL, case_id integer NOT NULL, plan_id uuid NOT NULL,
 actor_id integer NOT NULL REFERENCES users(id) ON DELETE RESTRICT, session_id uuid NOT NULL REFERENCES auth_sessions(id) ON DELETE RESTRICT,
 action text NOT NULL, target_id uuid NOT NULL, command_id uuid NOT NULL,
 payload_sha256 text NOT NULL CHECK(payload_sha256 ~ '^[0-9a-f]{64}$'),
 policy_version bigint NOT NULL, actor_snapshot jsonb NOT NULL, reason text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(command_id,action,target_id), UNIQUE(org_id,clinic_id,case_id,plan_id,id),
 FOREIGN KEY(org_id,clinic_id,case_id,plan_id,command_id) REFERENCES command_receipts(org_id,clinic_id,case_id,plan_id,id) ON DELETE RESTRICT
);
CREATE TABLE treatment_signatures (
 id uuid PRIMARY KEY, org_id uuid NOT NULL, clinic_id uuid NOT NULL, case_id integer NOT NULL, plan_id uuid NOT NULL,
 revision_id uuid NOT NULL UNIQUE, review_id uuid NOT NULL, content_hash text NOT NULL,
 signer_id integer NOT NULL REFERENCES users(id) ON DELETE RESTRICT, clinician_snapshot jsonb NOT NULL,
 assurance text NOT NULL CHECK(assurance='account_attestation'), challenge_id uuid NOT NULL UNIQUE REFERENCES signing_challenges(id) ON DELETE RESTRICT,
 audit_event_id uuid NOT NULL UNIQUE, command_id uuid NOT NULL UNIQUE, signed_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(org_id,clinic_id,case_id,plan_id,id),
 FOREIGN KEY(org_id,clinic_id,case_id,plan_id,revision_id,review_id,content_hash) REFERENCES treatment_reviews(org_id,clinic_id,case_id,plan_id,revision_id,id,reviewed_hash) ON DELETE RESTRICT,
 FOREIGN KEY(org_id,clinic_id,case_id,plan_id,audit_event_id) REFERENCES clinical_audit_events(org_id,clinic_id,case_id,plan_id,id) ON DELETE RESTRICT,
 FOREIGN KEY(org_id,clinic_id,case_id,plan_id,command_id) REFERENCES command_receipts(org_id,clinic_id,case_id,plan_id,id) ON DELETE RESTRICT
);
CREATE TABLE treatment_events (
 id uuid PRIMARY KEY, org_id uuid NOT NULL, clinic_id uuid NOT NULL, case_id integer NOT NULL, plan_id uuid NOT NULL,
 signature_id uuid NOT NULL UNIQUE, event text NOT NULL CHECK(event IN ('revoked','superseded')), successor_signature_id uuid,
 reason text NOT NULL CHECK(length(reason)>0), actor_id integer NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
 command_id uuid NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(org_id,clinic_id,case_id,plan_id,signature_id) REFERENCES treatment_signatures(org_id,clinic_id,case_id,plan_id,id) ON DELETE RESTRICT,
 FOREIGN KEY(org_id,clinic_id,case_id,plan_id,successor_signature_id) REFERENCES treatment_signatures(org_id,clinic_id,case_id,plan_id,id) ON DELETE RESTRICT,
 FOREIGN KEY(org_id,clinic_id,case_id,plan_id,command_id) REFERENCES command_receipts(org_id,clinic_id,case_id,plan_id,id) ON DELETE RESTRICT,
 CHECK(signature_id IS DISTINCT FROM successor_signature_id),
 CHECK((event='revoked' AND successor_signature_id IS NULL) OR (event='superseded' AND successor_signature_id IS NOT NULL))
);
ALTER TABLE treatment_plans
 ADD FOREIGN KEY(org_id,clinic_id,case_id,id,head_revision_id) REFERENCES treatment_revisions(org_id,clinic_id,case_id,plan_id,id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
 ADD FOREIGN KEY(org_id,clinic_id,case_id,id,active_signature_id) REFERENCES treatment_signatures(org_id,clinic_id,case_id,plan_id,id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE treatment_drafts
 ADD FOREIGN KEY(org_id,clinic_id,case_id,plan_id,base_revision_id) REFERENCES treatment_revisions(org_id,clinic_id,case_id,plan_id,id) ON DELETE RESTRICT,
 ADD FOREIGN KEY(org_id,clinic_id,case_id,plan_id,amendment_of) REFERENCES treatment_signatures(org_id,clinic_id,case_id,plan_id,id) ON DELETE RESTRICT;
ALTER TABLE treatment_revisions ADD FOREIGN KEY(org_id,clinic_id,case_id,plan_id,amendment_of) REFERENCES treatment_signatures(org_id,clinic_id,case_id,plan_id,id) ON DELETE RESTRICT;
ALTER TABLE signing_challenges ADD FOREIGN KEY(org_id,clinic_id,case_id,plan_id,target_signature_id) REFERENCES treatment_signatures(org_id,clinic_id,case_id,plan_id,id) ON DELETE RESTRICT;
-- Immutable facts reject mutations even by the table owner. Runtime never gets TRUNCATE.
CREATE FUNCTION public.pmai_treatment_immutable() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN RAISE EXCEPTION 'Treatment history is append-only'; END $$;
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['treatment_revisions','treatment_reviews','treatment_signatures','treatment_events','clinical_audit_events'] LOOP
  EXECUTE format('CREATE TRIGGER immutable_history BEFORE UPDATE OR DELETE OR TRUNCATE ON %I FOR EACH STATEMENT EXECUTE FUNCTION public.pmai_treatment_immutable()',t);
 END LOOP;
END $$;
CREATE FUNCTION public.pmai_command_transition() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF OLD.state<>'pending' OR NEW.state='pending' OR
    (to_jsonb(NEW)-ARRAY['state','completed_at','http_status','result','error_code','lease_until']) IS DISTINCT FROM
    (to_jsonb(OLD)-ARRAY['state','completed_at','http_status','result','error_code','lease_until']) THEN
  RAISE EXCEPTION 'Invalid command transition';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER command_transition BEFORE UPDATE ON command_receipts FOR EACH ROW EXECUTE FUNCTION public.pmai_command_transition();
CREATE TRIGGER command_no_delete BEFORE DELETE OR TRUNCATE ON command_receipts FOR EACH STATEMENT EXECUTE FUNCTION public.pmai_treatment_immutable();
CREATE FUNCTION public.pmai_challenge_transition() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF OLD.consumed_by_command IS NOT NULL OR NEW.consumed_by_command IS NULL OR
    to_jsonb(NEW)-'consumed_by_command' IS DISTINCT FROM to_jsonb(OLD)-'consumed_by_command' THEN
  RAISE EXCEPTION 'Challenge can only be consumed once'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER challenge_transition BEFORE UPDATE ON signing_challenges FOR EACH ROW EXECUTE FUNCTION public.pmai_challenge_transition();
-- Any legacy clinical source mutation invalidates frozen reviews. Old writers must
-- still be stopped; triggers are a second line of protection, not worker routing.
CREATE FUNCTION public.pmai_case_epoch() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF (to_jsonb(NEW)-ARRAY['clinical_epoch','row_version','updated_at']) IS DISTINCT FROM
    (to_jsonb(OLD)-ARRAY['clinical_epoch','row_version','updated_at']) THEN
  NEW.clinical_epoch=OLD.clinical_epoch+1;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER treatment_source_epoch BEFORE UPDATE ON cases FOR EACH ROW EXECUTE FUNCTION public.pmai_case_epoch();
CREATE FUNCTION public.pmai_child_epoch() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF TG_OP<>'INSERT' THEN UPDATE public.cases SET clinical_epoch=clinical_epoch+1 WHERE id=OLD.case_id; END IF;
 IF TG_OP<>'DELETE' AND (TG_OP='INSERT' OR NEW.case_id IS DISTINCT FROM OLD.case_id) THEN
  UPDATE public.cases SET clinical_epoch=clinical_epoch+1 WHERE id=NEW.case_id;
 END IF;
 RETURN NULL;
END $$;
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['diagnostic_reports','observations','imaging_studies','consult_sessions','followups','audit_log'] LOOP
  EXECUTE format('CREATE TRIGGER treatment_source_epoch AFTER INSERT OR UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION public.pmai_child_epoch()',t);
 END LOOP;
END $$;
REVOKE ALL ON FUNCTION public.pmai_treatment_immutable(), public.pmai_command_transition(), public.pmai_challenge_transition(), public.pmai_case_epoch(),public.pmai_child_epoch() FROM PUBLIC;
CREATE FUNCTION public.pmai_patient_epoch() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF to_jsonb(NEW) IS DISTINCT FROM to_jsonb(OLD) THEN
  UPDATE public.cases SET clinical_epoch=clinical_epoch+1 WHERE org_id=OLD.org_id AND patient_id=OLD.id;
 END IF;
 RETURN NULL;
END $$;
CREATE TRIGGER treatment_patient_epoch AFTER UPDATE ON patients FOR EACH ROW EXECUTE FUNCTION public.pmai_patient_epoch();
CREATE FUNCTION public.pmai_signing_policy_epoch() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF NEW.review_policy IS DISTINCT FROM OLD.review_policy OR NEW.required_signing_assurance IS DISTINCT FROM OLD.required_signing_assurance THEN
  NEW.signing_policy_version=OLD.signing_policy_version+1;
 ELSIF NEW.signing_policy_version<OLD.signing_policy_version THEN
  RAISE EXCEPTION 'Signing policy version cannot decrease';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER treatment_policy_epoch BEFORE UPDATE ON organizations FOR EACH ROW EXECUTE FUNCTION public.pmai_signing_policy_epoch();
REVOKE ALL ON FUNCTION public.pmai_patient_epoch(),public.pmai_signing_policy_epoch() FROM PUBLIC;
