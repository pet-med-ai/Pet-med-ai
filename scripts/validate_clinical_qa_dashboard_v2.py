#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import ast
import importlib.util
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

AUDIT_LOG_ALLOWED_FIELDS = (
    "log_id",
    "case_id",
    "event_type",
    "source",
    "created_at",
)
AUDIT_LOG_FORBIDDEN_FIELDS = (
    "note",
    "metadata",
    "metadata_json",
    "patient_token",
    "clinician_id",
    "request_id",
)

REQUIRED_FILES = [
    "backend/clinical_qa_dashboard.py",
    "backend/diagnostic_data_api.py",
    "docs/clinical_data/CLINICAL_QA_DASHBOARD_V2.md",
    "docs/clinical_data/CLINICAL_QA_DASHBOARD_CHECKLIST_V2.csv",
    "docs/clinical_data/CLINICAL_QA_DASHBOARD_GO_NO_GO_V2.csv",
    "scripts/validate_clinical_qa_dashboard_v2.py",
    "scripts/ci_static_checks.sh",
    "scripts/smoke_petmed.sh",
]

REQUIRED_SNIPPETS = {
    "backend/clinical_qa_dashboard.py": [
        'CLINICAL_QA_DASHBOARD_MODE = "clinical_qa_dashboard_v2"',
        '"writes_database": False',
        '"updates_diagnostic_report": False',
        '"updates_observation": False',
        '"updates_imaging_study": False',
        '"writes_ai_summary": False',
        '"writes_audit_log": False',
        '"persists_reasoning_trace": False',
        '"generates_final_diagnosis": False',
        '"creates_treatment_plan": False',
        '"writes_prescription": False',
        '"returns_drug_dose": False',
        '"requires_human_review": True',
        '"clinician_signoff_required": True',
        '"not_client_facing": True',
        "build_clinical_qa_dashboard",
        "qa_queue",
        "diagnostic_summary_audit_log_count",
    ],
    "backend/diagnostic_data_api.py": [
        "# --- Clinical QA Dashboard V2 endpoint: start ---",
        '@router.get("/clinical-qa-dashboard/v2/summary"',
        "build_clinical_qa_dashboard",
        "clinical_qa_dashboard_v2_summary",
        "Case.owner_id == owner_id",
        "case = _owned_case_or_404(db, int(case_id), user)",
        "DiagnosticReport.case_id.in_(case_ids)",
        "Observation.case_id.in_(case_ids)",
        "ImagingStudy.case_id.in_(case_ids)",
        "AuditLog.case_id.in_(case_ids)",
        '"audit_logs": dashboard_payload["audit_logs"]',
        '"owner_scoped": True',
        "# --- Clinical QA Dashboard V2 endpoint: end ---",
    ],
    "docs/clinical_data/CLINICAL_QA_DASHBOARD_V2.md": [
        "Clinical QA Dashboard V2",
        "GET /api/diagnostic-data/clinical-qa-dashboard/v2/summary",
        "writes_database=false",
        "not_client_facing=true",
        "GO_TO_OPS_DASHBOARD_CLINICAL_CORE_V2",
    ],
}

FORBIDDEN_ENDPOINT_SNIPPETS = [
    "db.add(",
    "db.commit(",
    "db.delete(",
    "AuditLog(",
    "Case(",
    "DiagnosticReport(",
    "Observation(",
    "ImagingStudy(",
    "OpenAI(",
    "requests.post(",
    "httpx.post(",
    "pydicom",
    "pynetdicom",
    "dicomweb",
]


def fail(message: str) -> None:
    print("VALIDATOR=FAIL")
    print(message)
    raise SystemExit(1)


def read(rel: str) -> str:
    path = ROOT / rel
    if not path.exists():
        fail("missing required file: %s" % rel)
    if path.suffix == ".py":
        py_compile.compile(str(path), doraise=True)
    return path.read_text(encoding="utf-8")


def load_module():
    path = ROOT / "backend" / "clinical_qa_dashboard.py"
    spec = importlib.util.spec_from_file_location("clinical_qa_dashboard", str(path))
    if spec is None or spec.loader is None:
        fail("unable to load clinical_qa_dashboard module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _string_constant(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Str):  # pragma: no cover - compatibility form
        return node.s
    return None


def _dict_value_for_key(node, key):
    if not isinstance(node, ast.Dict):
        return None
    for item_key, item_value in zip(node.keys, node.values):
        if _string_constant(item_key) == key:
            return item_value
    return None


def _subscript_key(node):
    if not isinstance(node, ast.Subscript):
        return None
    slice_node = node.slice
    if isinstance(slice_node, ast.Index):  # pragma: no cover - Python < 3.9 AST
        slice_node = slice_node.value
    return _string_constant(slice_node)


def assert_audit_readback_contract() -> None:
    api_path = ROOT / "backend" / "diagnostic_data_api.py"
    api_text = read("backend/diagnostic_data_api.py")
    start = "# --- Clinical QA Dashboard V2 endpoint: start ---"
    end = "# --- Clinical QA Dashboard V2 endpoint: end ---"
    if api_text.count(start) != 1 or api_text.count(end) != 1:
        fail("Clinical QA Dashboard V2 endpoint markers must occur exactly once")
    endpoint_text = api_text.split(start, 1)[1].split(end, 1)[0]

    owner_scope_tokens = (
        "case = _owned_case_or_404(db, int(case_id), user)",
        "Case.owner_id == owner_id",
        "case_ids = [int(item.id) for item in case_rows]",
        "AuditLog.case_id.in_(case_ids)",
        '"owner_scoped": True',
    )
    for token in owner_scope_tokens:
        if token not in endpoint_text:
            fail("owner-scoped audit readback token missing: %s" % token)

    helper_tokens = (
        'if not case or int(getattr(case, "owner_id", -1)) != _user_id(user):',
        'raise HTTPException(status_code=404, detail="Case not found")',
    )
    for token in helper_tokens:
        if token not in api_text:
            fail("cross-user 404 helper token missing: %s" % token)

    tree = ast.parse(api_text, filename=str(api_path))
    functions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "get_clinical_qa_dashboard_v2_summary"
    ]
    if len(functions) != 1:
        fail("expected exactly one get_clinical_qa_dashboard_v2_summary function")
    function = functions[0]

    payload_dicts = []
    for node in ast.walk(function):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Dict):
            continue
        if any(isinstance(target, ast.Name) and target.id == "dashboard_payload" for target in node.targets):
            payload_dicts.append(node.value)
    if len(payload_dicts) != 1:
        fail("expected exactly one dashboard_payload dictionary")

    audit_value = _dict_value_for_key(payload_dicts[0], "audit_logs")
    if not isinstance(audit_value, ast.ListComp) or not isinstance(audit_value.elt, ast.Dict):
        fail("dashboard_payload.audit_logs must be a sanitized list comprehension")
    audit_fields = tuple(_string_constant(key) for key in audit_value.elt.keys)
    if audit_fields != AUDIT_LOG_ALLOWED_FIELDS:
        fail(
            "audit_logs field whitelist mismatch: expected %r, got %r"
            % (AUDIT_LOG_ALLOWED_FIELDS, audit_fields)
        )
    forbidden = set(AUDIT_LOG_FORBIDDEN_FIELDS).intersection(audit_fields)
    if forbidden:
        fail("sensitive audit_logs fields exposed: %s" % ", ".join(sorted(forbidden)))

    response_dicts = []
    for node in ast.walk(function):
        if not isinstance(node, ast.Return) or not isinstance(node.value, ast.Dict):
            continue
        if _dict_value_for_key(node.value, "message") is not None:
            response_dicts.append(node.value)
    if len(response_dicts) != 1:
        fail("expected exactly one Clinical QA endpoint response dictionary")
    response = response_dicts[0]
    response_audit = _dict_value_for_key(response, "audit_logs")
    if not (
        isinstance(response_audit, ast.Subscript)
        and isinstance(response_audit.value, ast.Name)
        and response_audit.value.id == "dashboard_payload"
        and _subscript_key(response_audit) == "audit_logs"
    ):
        fail('response must expose only dashboard_payload["audit_logs"]')

    spread_indexes = [
        index
        for index, (key, value) in enumerate(zip(response.keys, response.values))
        if key is None and isinstance(value, ast.Name) and value.id == "dashboard"
    ]
    audit_indexes = [
        index
        for index, key in enumerate(response.keys)
        if _string_constant(key) == "audit_logs"
    ]
    if len(spread_indexes) != 1 or len(audit_indexes) != 1 or audit_indexes[0] <= spread_indexes[0]:
        fail("sanitized audit_logs must follow **dashboard in the endpoint response")

    if any(token in endpoint_text for token in FORBIDDEN_ENDPOINT_SNIPPETS):
        fail("Clinical QA audit readback endpoint is no longer read-only")


def assert_files_and_snippets() -> None:
    for rel in REQUIRED_FILES:
        read(rel)
    for rel, snippets in REQUIRED_SNIPPETS.items():
        text = read(rel)
        for snippet in snippets:
            if snippet not in text:
                fail("missing snippet in %s: %s" % (rel, snippet))

    api_text = read("backend/diagnostic_data_api.py")
    if api_text.count("/clinical-qa-dashboard/v2/summary") != 1:
        fail("expected exactly one Clinical QA Dashboard V2 endpoint")
    block = api_text.split("# --- Clinical QA Dashboard V2 endpoint: start ---", 1)[1].split("# --- Clinical QA Dashboard V2 endpoint: end ---", 1)[0]
    for snippet in FORBIDDEN_ENDPOINT_SNIPPETS:
        if snippet in block:
            fail("forbidden snippet in Clinical QA Dashboard V2 endpoint: %s" % snippet)


def assert_module_behavior() -> None:
    module = load_module()
    payload = {
        "cases": [{"case_id": 1}],
        "diagnostic_reports": [
            {"report_id": 10, "case_id": 1, "status": "reviewed", "ai_summary_status": "persisted", "has_ai_summary": True},
            {"report_id": 11, "case_id": 1, "status": "draft", "ai_summary_status": "not_generated", "has_ai_summary": False},
        ],
        "observations": [
            {"observation_id": 20, "case_id": 1, "abnormal_flag": "high", "review_status": "pending_clinician_review"},
            {"observation_id": 21, "case_id": 1, "abnormal_flag": "normal", "review_status": "reviewed"},
        ],
        "imaging_studies": [
            {"imaging_study_id": 30, "case_id": 1, "abnormal_flag": "abnormal", "review_status": "draft"},
        ],
        "audit_logs": [
            {"log_id": "log_1", "case_id": 1, "event_type": "diagnostic_summary_review", "source": "diagnostic_summary_audit_log_v1"},
        ],
    }
    result = module.build_clinical_qa_dashboard(payload, case_context={"case_id": 1})
    if result.get("mode") != "clinical_qa_dashboard_v2":
        fail("mode mismatch")
    for key in (
        "writes_database",
        "updates_diagnostic_report",
        "updates_observation",
        "updates_imaging_study",
        "writes_ai_summary",
        "writes_audit_log",
        "persists_reasoning_trace",
        "generates_final_diagnosis",
        "creates_treatment_plan",
        "writes_prescription",
        "returns_drug_dose",
    ):
        if result.get(key) is not False:
            fail("expected %s false" % key)
    if result.get("requires_human_review") is not True:
        fail("requires_human_review must be true")
    if result.get("clinician_signoff_required") is not True:
        fail("clinician_signoff_required must be true")
    if result.get("not_client_facing") is not True:
        fail("not_client_facing must be true")
    if result.get("quality_gate", {}).get("status") != "PASS":
        fail("quality_gate.status must PASS")
    if "audit_logs" in result:
        fail("dashboard builder must remain aggregate-only; endpoint owns audit readback exposure")
    metrics = result.get("metrics") or {}
    if metrics.get("diagnostic_reports_total") != 2:
        fail("diagnostic report metric mismatch")
    if metrics.get("observation_abnormal_flag_review_gap_count") != 1:
        fail("observation review gap metric mismatch")
    if metrics.get("imagingstudy_review_gap_count") != 1:
        fail("imaging review gap metric mismatch")
    if not isinstance(result.get("qa_queue"), list) or not result["qa_queue"]:
        fail("qa_queue should contain review gap items")


def assert_ci_and_smoke_hooks() -> None:
    ci = read("scripts/ci_static_checks.sh")
    smoke = read("scripts/smoke_petmed.sh")
    if "Clinical QA Dashboard V2 static checks" not in ci:
        fail("ci_static_checks missing Clinical QA Dashboard V2 block")
    if "python3 scripts/validate_clinical_qa_dashboard_v2.py" not in ci:
        fail("ci_static_checks missing validator command")
    if "Clinical QA Dashboard V2 smoke" not in smoke:
        fail("smoke missing Clinical QA Dashboard V2 block")
    if "clinical_qa_dashboard_v2_summary" not in smoke:
        fail("smoke missing endpoint assertion")


def main() -> None:
    assert_files_and_snippets()
    assert_audit_readback_contract()
    assert_module_behavior()
    assert_ci_and_smoke_hooks()
    print("AUDIT_READBACK_CONTRACT=PASS")
    print("AUDIT_LOG_FIELD_WHITELIST=log_id,case_id,event_type,source,created_at")
    print("VALIDATOR=PASS Clinical QA Dashboard V2")


if __name__ == "__main__":
    main()
