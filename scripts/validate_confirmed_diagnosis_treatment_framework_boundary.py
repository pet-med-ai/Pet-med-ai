#!/usr/bin/env python3
# Python 3.9-safe validator for Confirmed Diagnosis Treatment Framework Boundary V1.
# Stdlib only. Run from anywhere inside the repository.

from __future__ import print_function

import csv
from pathlib import Path

STAGE = "Confirmed Diagnosis Treatment Framework Boundary V1"
ROOT = Path(__file__).resolve().parents[1]

TARGETS = [
    "docs/clinical_data/CONFIRMED_DIAGNOSIS_TREATMENT_FRAMEWORK_BOUNDARY_V1.md",
    "docs/clinical_data/CONFIRMED_DIAGNOSIS_TREATMENT_FRAMEWORK_BOUNDARY_CHECKLIST_V1.csv",
    "docs/clinical_data/CONFIRMED_DIAGNOSIS_TREATMENT_FRAMEWORK_BOUNDARY_GO_NO_GO_V1.csv",
    "scripts/validate_confirmed_diagnosis_treatment_framework_boundary.py",
    "scripts/ci_static_checks.sh",
    "scripts/smoke_petmed.sh",
]

DANGEROUS_FLAGS = [
    "ENABLE_EMR_REAL_IMPORT",
    "ENABLE_EMR_IMPORT_CASE_UPDATE",
    "ENABLE_EMR_ATTACHMENT_DOWNLOAD",
    "ENABLE_PREVENTIVE_AUTO_DELIVERY",
    "ENABLE_PREVENTIVE_SMS_DELIVERY",
    "ENABLE_PREVENTIVE_WECHAT_DELIVERY",
    "ENABLE_PREVENTIVE_EMAIL_DELIVERY",
    "ENABLE_PRESCRIPTION_STRUCTURED_WRITE",
    "ENABLE_DEVICE_REAL_INGEST",
    "ENABLE_BILLING_REAL_WRITE",
]

REQUIRED_MARKERS = [
    "Confirmed Diagnosis Treatment Framework Boundary V1",
    "documentation + validator only",
    "no backend endpoint",
    "no API endpoint",
    "no database migration",
    "no database write",
    "no Case.treatment write",
    "no prescription write",
    "no frontend rendering",
    "clinician-confirmed diagnosis",
    "The system must not confirm, infer, finalize, or upgrade a diagnosis.",
    "422 confirmed diagnosis by clinician is required",
    "confirmed_diagnosis_label",
    "confirmed_by",
    "confirmation_source",
    "ai_generated",
    "\"writes_database\": false",
    "\"creates_prescription\": false",
    "\"writes_prescription\": false",
    "\"writes_case_treatment\": false",
    "\"returns_drug_dose\": false",
    "\"returns_drug_route\": false",
    "\"returns_drug_frequency\": false",
    "\"not_client_facing\": true",
    "\"requires_human_review\": true",
    "\"clinician_signoff_required\": true",
    "Forbidden scanner patterns",
    "database_revision=0009_diag_data",
    "alembic_head=0009_diag_data",
    "schema_ok=true",
    "migration_errors=[]",
    "writes_database=false",
    "exposes_database_url=false",
    "dangerous_feature_flags_disabled=true",
    "decision=GO_TO_CONFIRMED_DIAGNOSIS_TREATMENT_FRAMEWORK_DRAFT_V1",
]

ALLOWED_OUTPUT_FIELDS = [
    "treatment_goals",
    "care_priority_hint",
    "supportive_care_categories",
    "monitoring_parameters",
    "recheck_plan_categories",
    "contraindication_checks",
    "hospitalization_or_referral_triggers",
    "procedure_or_surgery_review_points",
    "nutrition_and_environment_support_points",
    "client_communication_topics_for_clinician_review",
    "medication_class_review_needed",
    "quality_gate",
    "safety",
]

FORBIDDEN_SCANNER_TERMS = [
    "mg/kg",
    "ml/kg",
    "mcg/kg",
    "IU/kg",
    "q12h",
    "q24h",
    "BID",
    "SID",
    "TID",
    "QID",
    "PO",
    "IV",
    "IM",
    "SC",
    "SQ",
    "subcutaneous",
    "intravenous",
    "intramuscular",
    "oral",
    "per os",
    "dose",
    "dosage",
    "frequency",
    "route",
    "prescription",
    "rx",
    "refill",
]

UNSAFE_ENABLE_MARKERS = [
    "client-facing treatment output is allowed",
    "AI may confirm diagnosis",
    "AI can confirm diagnosis",
    "write Case.treatment",
    "write prescription",
    "creates prescription",
]
UNSAFE_ENABLE_MARKERS.extend([flag + "=true" for flag in DANGEROUS_FLAGS])

CSV_EXPECTED = {
    "docs/clinical_data/CONFIRMED_DIAGNOSIS_TREATMENT_FRAMEWORK_BOUNDARY_CHECKLIST_V1.csv": {
        "columns": ["item", "requirement", "status", "evidence", "owner", "notes"],
        "must_contain_items": [
            "stage_scope",
            "clinician_confirmed_diagnosis",
            "ai_does_not_confirm_diagnosis",
            "read_only_boundary",
            "output_contract",
            "blocks_prescription",
            "blocks_dose",
            "blocks_route_frequency",
            "not_client_facing",
            "feature_flags",
            "production_hard_gate",
            "next_stage",
        ],
    },
    "docs/clinical_data/CONFIRMED_DIAGNOSIS_TREATMENT_FRAMEWORK_BOUNDARY_GO_NO_GO_V1.csv": {
        "columns": ["gate", "required_state", "observed_state", "decision", "evidence"],
        "must_contain_items": [
            "validator",
            "ci_static_checks",
            "online_smoke",
            "clinician_confirmed_diagnosis",
            "ai_does_not_confirm_diagnosis",
            "read_only",
            "blocks_prescription",
            "blocks_dose",
            "blocks_route_frequency",
            "not_client_facing",
            "case_treatment",
            "production_revision",
            "production_alembic",
            "production_schema",
            "dangerous_feature_flags",
            "final_decision",
        ],
    },
}


def fail(message):
    print("FAIL: {0}".format(message))
    raise SystemExit(1)


def rel_path(path):
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_text(path):
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        fail("{0} is not valid UTF-8".format(rel_path(path)))


def require(condition, message):
    if not condition:
        fail(message)


def require_file(path_str):
    path = ROOT / path_str
    require(path.exists(), "missing required file: {0}".format(path_str))
    require(path.is_file(), "required path is not a file: {0}".format(path_str))
    text = read_text(path)
    require(text.endswith("\n"), "file must end with newline: {0}".format(path_str))
    return text


def validate_markdown():
    md_path = "docs/clinical_data/CONFIRMED_DIAGNOSIS_TREATMENT_FRAMEWORK_BOUNDARY_V1.md"
    text = require_file(md_path)

    for marker in REQUIRED_MARKERS:
        require(marker in text, "boundary doc missing marker: {0}".format(marker))

    for field in ALLOWED_OUTPUT_FIELDS:
        require(field in text, "boundary doc missing allowed output field: {0}".format(field))

    for term in FORBIDDEN_SCANNER_TERMS:
        require(term in text, "boundary doc missing forbidden scanner term: {0}".format(term))

    for flag in DANGEROUS_FLAGS:
        require(flag in text, "boundary doc missing dangerous feature flag: {0}".format(flag))

    lower_text = text.lower()
    require("no treatment framework persistence" in lower_text, "boundary doc must block treatment framework persistence")
    require("no client-facing treatment output" in lower_text, "boundary doc must block client-facing treatment output")
    require("not a treatment plan" in lower_text, "boundary doc must state preview is not a treatment plan")
    require("not a prescription" in lower_text, "boundary doc must state preview is not a prescription")

    for marker in UNSAFE_ENABLE_MARKERS:
        require(marker not in text, "unsafe positive marker found in boundary doc: {0}".format(marker))


def validate_csv_file(path_str, spec):
    path = ROOT / path_str
    text = require_file(path_str)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        require(reader.fieldnames == spec["columns"], "unexpected CSV columns in {0}: {1}".format(path_str, reader.fieldnames))
        rows = list(reader)

    require(rows, "CSV has no rows: {0}".format(path_str))
    first_col = spec["columns"][0]
    row_keys = [row.get(first_col, "") for row in rows]

    for item in spec["must_contain_items"]:
        require(item in row_keys, "{0} missing required row: {1}".format(path_str, item))

    for row in rows:
        joined = " ".join([row.get(column, "") for column in spec["columns"]])
        require(("ENABLE_PRESCRIPTION_STRUCTURED_WRITE" + "=true") not in joined, "CSV must not enable structured prescription writes")
        require("client-facing treatment output is allowed" not in joined, "CSV must not allow client-facing treatment output")

    if "CHECKLIST" in path_str:
        for row in rows:
            require(row.get("status") == "PASS", "checklist row is not PASS: {0}".format(row.get("item")))

    if "GO_NO_GO" in path_str:
        decisions = set([row.get("decision", "") for row in rows])
        allowed = set(["GO", "GO_IF_PASS", "GO_IF_ALL_PASS"])
        require(decisions.issubset(allowed), "unexpected go/no-go decision values: {0}".format(sorted(decisions)))
        require("GO_IF_ALL_PASS" in decisions, "go/no-go file missing GO_IF_ALL_PASS final decision")
        require("TO_BE_VERIFIED_ONLINE" in text, "go/no-go must require online production verification")
        require("GO_AFTER_LOCAL_AND_ONLINE_PASS" in text, "go/no-go must avoid claiming completion before runtime smoke")


def validate_csvs():
    for path_str, spec in CSV_EXPECTED.items():
        validate_csv_file(path_str, spec)


def validate_scripts():
    validator_text = require_file("scripts/validate_confirmed_diagnosis_treatment_framework_boundary.py")
    ci_text = require_file("scripts/ci_static_checks.sh")
    smoke_text = require_file("scripts/smoke_petmed.sh")

    py310_match_token = "mat" + "ch "
    py310_union_token = "|" + " None"
    require("Python 3.9-safe" in validator_text, "validator must declare Python 3.9-safe")
    require(py310_match_token not in validator_text, "validator must not use Python 3.10 pattern syntax")
    require(py310_union_token not in validator_text, "validator must not use Python 3.10 union type syntax")
    require("git diff --check" in ci_text, "ci_static_checks.sh must run git diff --check")
    require("validate_confirmed_diagnosis_treatment_framework_boundary.py" in ci_text, "ci_static_checks.sh must run boundary validator")
    require("bash -n" in ci_text, "ci_static_checks.sh must run shell syntax checks")
    require("/api/system/version" in smoke_text, "smoke script must check system version")
    require("/api/system/feature-flags" in smoke_text, "smoke script must check feature flags")
    require("0009_diag_data" in smoke_text, "smoke script must verify 0009_diag_data")
    require("migration_errors" in smoke_text, "smoke script must verify migration_errors")
    require("writes_database" in smoke_text, "smoke script must verify writes_database")
    require("exposes_database_url" in smoke_text, "smoke script must verify exposes_database_url")

    for flag in DANGEROUS_FLAGS:
        require(flag in ci_text or flag in smoke_text, "scripts missing dangerous flag check: {0}".format(flag))


def validate_target_set():
    for path_str in TARGETS:
        require_file(path_str)


def main():
    print("Validating {0}".format(STAGE))
    validate_target_set()
    validate_markdown()
    validate_csvs()
    validate_scripts()
    print("PASS: {0}".format(STAGE))
    print("requires_clinician_confirmed_diagnosis=true")
    print("ai_does_not_confirm_diagnosis=true")
    print("blocks_prescription=true")
    print("blocks_dose=true")
    print("blocks_route_frequency=true")
    print("not_client_facing=true")
    print("read_only=true")
    print("requires_human_review=true")
    print("clinician_signoff_required=true")
    print("decision=GO_TO_CONFIRMED_DIAGNOSIS_TREATMENT_FRAMEWORK_DRAFT_V1")


if __name__ == "__main__":
    main()
