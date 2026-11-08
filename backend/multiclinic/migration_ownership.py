"""Scope tables currently use explicit SQL, not the legacy ORM metadata.

Keep autogeneration from interpreting that deliberate omission as DROP TABLE.
Their changes must be explicit forward migrations and PostgreSQL integration tests.
"""

TABLES = frozenset(
    {
        "organizations",
        "clinics",
        "org_memberships",
        "role_bindings",
        "patients",
        "case_access_grants",
        "auth_sessions",
        "access_audit_events",
        "migration_batches",
    }
)
COLUMNS = {
    "users": {"status", "principal_kind", "token_version"},
    "cases": {
        "org_id",
        "clinic_id",
        "patient_id",
        "visibility",
        "row_version",
        "clinical_epoch",
    },
}
CONSTRAINTS = frozenset(
    {
        "fk_case_clinic_scope",
        "fk_case_patient_scope",
        "uq_case_scope",
        "ck_case_scope_pair",
        "ck_case_visibility",
        "ix_cases_scope_id",
        "ck_user_active_status",
        "ck_user_principal_kind",
        "ck_user_token_version",
    }
)


def include_object(obj, name, type_, reflected, compare_to):
    if reflected and compare_to is None:
        if type_ == "table" and (
            name in TABLES or getattr(obj, "schema", None) == "pmai_scope"
        ):
            return False
        if type_ == "column" and name in COLUMNS.get(obj.table.name, set()):
            return False
        if name in CONSTRAINTS:
            return False
    return True
