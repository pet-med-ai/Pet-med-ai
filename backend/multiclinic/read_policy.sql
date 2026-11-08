-- Apply only to an isolated/migrated target with all old web/worker processes stopped.
-- Run as the database/role administrator, never as the web application.
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='pmai_scope_acl') THEN
    CREATE ROLE pmai_scope_acl NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='pmai_scope_reader') THEN
    CREATE ROLE pmai_scope_reader NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='pmai_scope_runtime') THEN
    CREATE ROLE pmai_scope_runtime LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT;
  END IF;
  IF EXISTS (SELECT FROM pg_roles WHERE rolname IN ('pmai_scope_acl','pmai_scope_reader','pmai_scope_runtime')
      AND (rolsuper OR rolbypassrls OR rolcreaterole OR rolcreatedb OR rolreplication OR rolinherit))
     OR EXISTS (SELECT FROM pg_auth_members a JOIN pg_roles r ON r.oid=a.member
                WHERE r.rolname IN ('pmai_scope_acl','pmai_scope_reader','pmai_scope_runtime')) THEN
    RAISE EXCEPTION 'Scope roles must be unprivileged and have no role memberships';
  END IF;
END $$;

CREATE SCHEMA IF NOT EXISTS pmai_scope;
REVOKE ALL ON SCHEMA pmai_scope FROM PUBLIC;
GRANT USAGE ON SCHEMA public, pmai_scope TO pmai_scope_acl, pmai_scope_reader, pmai_scope_runtime;
GRANT SELECT (id,status,principal_kind,token_version) ON public.users TO pmai_scope_acl;
GRANT SELECT ON public.auth_sessions, public.organizations, public.clinics,
    public.org_memberships, public.role_bindings, public.case_access_grants TO pmai_scope_acl;
GRANT SELECT ON public.cases TO pmai_scope_reader;
-- Runtime receives no base clinical-table privilege, including legacy case child tables.
GRANT SELECT (id,email,hashed_password,status,principal_kind,token_version) ON public.users TO pmai_scope_runtime;
GRANT SELECT, INSERT ON public.auth_sessions TO pmai_scope_runtime;
GRANT UPDATE (revoked_at) ON public.auth_sessions TO pmai_scope_runtime;

CREATE OR REPLACE FUNCTION pmai_scope.actor_id() RETURNS integer
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
  SELECT u.id FROM public.users u JOIN public.auth_sessions s ON s.user_id=u.id
  WHERE u.id=NULLIF(current_setting('pmai.actor_id',true),'')::integer
    AND s.id=NULLIF(current_setting('pmai.session_id',true),'')::uuid
    AND u.status='active' AND u.principal_kind='human'
    AND s.token_version=u.token_version AND s.revoked_at IS NULL AND s.expires_at>statement_timestamp()
$$;
ALTER FUNCTION pmai_scope.actor_id() OWNER TO pmai_scope_acl;

CREATE OR REPLACE FUNCTION pmai_scope.case_allowed(o uuid,c uuid,i integer,owner_id integer,visibility text,projection text)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT o=NULLIF(current_setting('pmai.org_id',true),'')::uuid
    AND c=NULLIF(current_setting('pmai.clinic_id',true),'')::uuid
    AND projection IN ('clinical','demographics')
    AND EXISTS (
      SELECT FROM public.org_memberships m
      JOIN public.organizations org ON org.id=m.org_id AND org.status='active' AND org.policy_version=1
      JOIN public.clinics clinic ON clinic.org_id=org.id AND clinic.id=c AND clinic.status='active'
      WHERE m.org_id=o AND m.user_id=pmai_scope.actor_id() AND m.status='active'
      AND (
        EXISTS (SELECT FROM public.case_access_grants g WHERE g.org_id=o AND g.clinic_id=c AND g.case_id=i
          AND g.grantee_membership_id=m.id AND g.permission='clinical.read' AND g.revoked_at IS NULL
          AND g.expires_at>statement_timestamp())
        OR ((visibility='clinic' OR owner_id=m.user_id) AND EXISTS (
          SELECT FROM public.role_bindings b WHERE b.org_id=o AND b.membership_id=m.id AND b.clinic_id=c
          AND b.scope_kind='clinic' AND b.revoked_at IS NULL AND b.valid_from<=statement_timestamp()
          AND (b.valid_until IS NULL OR b.valid_until>statement_timestamp())
          AND (b.role_code IN ('veterinarian','clinical_assistant','clinical_auditor')
               OR (projection='demographics' AND b.role_code='frontdesk'))
        ))
      )
    )
$$;
ALTER FUNCTION pmai_scope.case_allowed(uuid,uuid,integer,integer,text,text) OWNER TO pmai_scope_acl;

-- FORCE makes table-owner execution obey RLS too. Superusers are not a runtime option.
ALTER TABLE public.cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cases FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS pmai_scope_case_read ON public.cases;
CREATE POLICY pmai_scope_case_read ON public.cases FOR SELECT TO pmai_scope_reader
 USING (deleted_at IS NULL AND pmai_scope.case_allowed(org_id,clinic_id,id,owner_id,visibility,'demographics'));

CREATE OR REPLACE VIEW pmai_scope.demographic_cases WITH (security_barrier=true) AS
 SELECT org_id,clinic_id,id,patient_name,species,sex,age_info,breed,weight,coat_color,owner_name,owner_phone,
        row_version,visibility
 FROM public.cases WHERE deleted_at IS NULL
   AND pmai_scope.case_allowed(org_id,clinic_id,id,owner_id,visibility,'demographics');
ALTER VIEW pmai_scope.demographic_cases OWNER TO pmai_scope_reader;
CREATE OR REPLACE VIEW pmai_scope.clinical_cases WITH (security_barrier=true) AS
 SELECT org_id,clinic_id,id,patient_name,species,sex,age_info,breed,weight,coat_color,owner_name,owner_phone,
        row_version,visibility,chief_complaint,history,exam_findings,analysis,treatment,prognosis
 FROM public.cases WHERE deleted_at IS NULL
   AND pmai_scope.case_allowed(org_id,clinic_id,id,owner_id,visibility,'clinical');
ALTER VIEW pmai_scope.clinical_cases OWNER TO pmai_scope_reader;

CREATE OR REPLACE FUNCTION pmai_scope.available_clinics()
 RETURNS TABLE(org_id uuid,org_name text,clinic_id uuid,clinic_name text,permissions text[])
 LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT o.id,o.name::text,c.id,c.name::text,
   array_remove(ARRAY[
     CASE WHEN bool_or(b.role_code IN ('veterinarian','clinical_assistant','clinical_auditor')) OR bool_or(g.id IS NOT NULL)
       THEN 'clinical.read' END,
     CASE WHEN bool_or(b.role_code IN ('veterinarian','clinical_assistant','clinical_auditor','frontdesk')) OR bool_or(g.id IS NOT NULL)
       THEN 'patient.demographics.read' END
   ],NULL)
 FROM public.org_memberships m
 JOIN public.organizations o ON o.id=m.org_id AND o.status='active' AND o.policy_version=1
 JOIN public.clinics c ON c.org_id=o.id AND c.status='active'
 LEFT JOIN public.role_bindings b ON b.org_id=o.id AND b.membership_id=m.id AND b.clinic_id=c.id
   AND b.scope_kind='clinic' AND b.revoked_at IS NULL AND b.valid_from<=statement_timestamp()
   AND (b.valid_until IS NULL OR b.valid_until>statement_timestamp())
 LEFT JOIN public.case_access_grants g ON g.org_id=o.id AND g.clinic_id=c.id AND g.grantee_membership_id=m.id
   AND g.revoked_at IS NULL AND g.expires_at>statement_timestamp() AND g.permission='clinical.read'
 WHERE m.user_id=pmai_scope.actor_id() AND m.status='active'
 GROUP BY o.id,c.id HAVING bool_or(b.role_code IN ('veterinarian','clinical_assistant','clinical_auditor','frontdesk'))
   OR bool_or(g.id IS NOT NULL)
$$;
ALTER FUNCTION pmai_scope.available_clinics() OWNER TO pmai_scope_acl;

REVOKE ALL ON ALL FUNCTIONS IN SCHEMA pmai_scope FROM PUBLIC;
GRANT EXECUTE ON FUNCTION pmai_scope.actor_id(),pmai_scope.available_clinics() TO pmai_scope_runtime;
GRANT EXECUTE ON FUNCTION pmai_scope.case_allowed(uuid,uuid,integer,integer,text,text) TO pmai_scope_reader,pmai_scope_runtime;
GRANT SELECT ON pmai_scope.clinical_cases,pmai_scope.demographic_cases TO pmai_scope_runtime;

CREATE OR REPLACE FUNCTION pmai_scope.reject_audit_mutation() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog AS $$ BEGIN
 RAISE EXCEPTION 'Access audit is append-only'; END $$;
REVOKE ALL ON FUNCTION pmai_scope.reject_audit_mutation() FROM PUBLIC;
DROP TRIGGER IF EXISTS access_audit_append_only ON public.access_audit_events;
CREATE TRIGGER access_audit_append_only BEFORE UPDATE OR DELETE OR TRUNCATE ON public.access_audit_events
 FOR EACH STATEMENT EXECUTE FUNCTION pmai_scope.reject_audit_mutation();
