#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import importlib.util
import json
import py_compile
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "backend/exotics_knowledge_coverage_gap_review.py",
    "docs/clinical_data/EXOTICS_KNOWLEDGE_COVERAGE_GAP_REVIEW_V1.md",
    "docs/clinical_data/EXOTICS_KNOWLEDGE_COVERAGE_MATRIX_V1.csv",
    "docs/clinical_data/EXOTICS_KNOWLEDGE_COVERAGE_GAP_REVIEW_CHECKLIST_V1.csv",
    "docs/clinical_data/EXOTICS_KNOWLEDGE_COVERAGE_GAP_REVIEW_GO_NO_GO_V1.csv",
    "scripts/validate_exotics_knowledge_coverage_gap_review.py",
]

REQUIRED_SNIPPETS = {
    "backend/exotics_knowledge_coverage_gap_review.py": [
        "EXOTICS_KNOWLEDGE_COVERAGE_GAP_REVIEW_MODE = \"exotics_knowledge_coverage_gap_review_v1\"",
        "EXPECTED_COVERAGE_ROWS",
        "build_exotics_knowledge_coverage_gap_review",
        "write_coverage_matrix_csv",
        '"writes_database": False',
        '"returns_drug_dose": False',
        '"creates_treatment_plan": False',
        '"writes_prescription": False',
        '"requires_human_review": True',
        '"clinician_signoff_required": True',
        "GO_TO_EXOTICS_RABBIT_DEEPENING_V1",
    ],
    "docs/clinical_data/EXOTICS_KNOWLEDGE_COVERAGE_GAP_REVIEW_V1.md": [
        "Exotics Knowledge Coverage Gap Review V1",
        "triage_scaffold_not_comprehensive_clinical_kb",
        "EXOTICS_KNOWLEDGE_COVERAGE_MATRIX_V1.csv",
        "no DB write",
        "no drug dose",
        "GO_TO_EXOTICS_RABBIT_DEEPENING_V1",
    ],
}

PROHIBITED_MODULE_SNIPPETS = [
    "db.add(",
    "db.commit(",
    "db.delete(",
    "requests.post(",
    "httpx.post(",
    "OpenAI(",
    "create_prescription(",
    "write_prescription(",
    "create_treatment_plan(",
]


def fail(message: str) -> None:
    print("VALIDATOR=FAIL")
    print(message)
    raise SystemExit(1)


def read(rel: str) -> str:
    path = ROOT / rel
    if not path.exists():
        fail("missing required file: %s" % rel)
    return path.read_text(encoding="utf-8")


def load_module():
    path = ROOT / "backend" / "exotics_knowledge_coverage_gap_review.py"
    spec = importlib.util.spec_from_file_location("exotics_knowledge_coverage_gap_review", str(path))
    if spec is None or spec.loader is None:
        fail("unable to load exotics coverage module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def assert_files_and_snippets() -> None:
    for rel in REQUIRED_FILES:
        path = ROOT / rel
        if not path.exists():
            fail("missing required file: %s" % rel)
        if path.suffix == ".py":
            py_compile.compile(str(path), doraise=True)

    for rel, snippets in REQUIRED_SNIPPETS.items():
        text = read(rel)
        for snippet in snippets:
            if snippet not in text:
                fail("missing snippet in %s: %s" % (rel, snippet))

    module_text = read("backend/exotics_knowledge_coverage_gap_review.py")
    for snippet in PROHIBITED_MODULE_SNIPPETS:
        if snippet in module_text:
            fail("prohibited snippet in exotics coverage review module: %s" % snippet)


def assert_existing_exotics_validators() -> None:
    for script in (
        "scripts/validate_exotic_kb.py",
        "scripts/validate_exotic_intake_templates.py",
    ):
        if not (ROOT / script).exists():
            fail("missing existing exotics validator: %s" % script)
        result = subprocess.run(
            [sys.executable, script],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if result.returncode != 0:
            print(result.stdout)
            fail("existing exotics validator failed: %s" % script)


def assert_module_behavior() -> None:
    module = load_module()
    report = module.build_exotics_knowledge_coverage_gap_review(ROOT)
    if report.get("mode") != "exotics_knowledge_coverage_gap_review_v1":
        fail("mode mismatch")
    if report.get("writes_database") is not False:
        fail("coverage review must not write database")
    if report.get("returns_drug_dose") is not False:
        fail("coverage review must not return drug dose")
    if report.get("creates_treatment_plan") is not False:
        fail("coverage review must not create treatment plan")
    if report.get("writes_prescription") is not False:
        fail("coverage review must not write prescription")
    if report.get("requires_human_review") is not True:
        fail("requires_human_review must be true")
    if report.get("clinician_signoff_required") is not True:
        fail("clinician_signoff_required must be true")
    if report.get("decision") != "GO_TO_EXOTICS_RABBIT_DEEPENING_V1":
        fail("next decision mismatch")

    current_rule_keys = set(report.get("current_rule_keys") or [])
    for key in ("rabbit", "bird", "reptile", "ferret", "rodent"):
        if key not in current_rule_keys:
            fail("current exotics KB missing rule key: %s" % key)

    rows = report.get("coverage_matrix") or []
    if len(rows) < 15:
        fail("coverage matrix must include at least 15 taxa rows")
    taxa = {row.get("species_or_taxon") for row in rows if isinstance(row, dict)}
    for taxon in ("rabbit", "bird_general", "reptile_general", "ferret", "guinea_pig", "hedgehog", "sugar_glider", "tarantula_scorpion_invertebrate"):
        if taxon not in taxa:
            fail("coverage matrix missing taxon: %s" % taxon)

    gap_summary = report.get("gap_summary") or {}
    if gap_summary.get("is_comprehensive") is not False:
        fail("gap summary must explicitly mark KB as not comprehensive")
    if not gap_summary.get("source_review_not_started"):
        fail("source review gaps must be listed")
    if not gap_summary.get("drug_dose_source_review_not_started"):
        fail("drug dose source review gaps must be listed")
    if report.get("quality_gate", {}).get("status") != "PASS":
        fail("quality_gate.status must be PASS")

    print(json.dumps({
        "mode": report.get("mode"),
        "current_rule_keys": sorted(current_rule_keys),
        "coverage_rows": len(rows),
        "decision": report.get("decision"),
    }, ensure_ascii=False))


def assert_matrix_csv() -> None:
    path = ROOT / "docs" / "clinical_data" / "EXOTICS_KNOWLEDGE_COVERAGE_MATRIX_V1.csv"
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) < 15:
        fail("coverage matrix CSV must have at least 15 rows")
    required_columns = [
        "species_group",
        "species_or_taxon",
        "current_rule",
        "coverage_status",
        "covered_presentations",
        "critical_gaps",
        "priority",
        "next_stage",
        "drug_dose_status",
        "source_review_status",
    ]
    for column in required_columns:
        if column not in (rows[0].keys() if rows else []):
            fail("coverage matrix CSV missing column: %s" % column)
    taxa = {row.get("species_or_taxon") for row in rows}
    if "rabbit" not in taxa or "bird_general" not in taxa or "fish_general" not in taxa:
        fail("coverage matrix CSV missing expected taxa")
    for row in rows:
        if row.get("drug_dose_status") != "not_reviewed_not_enabled":
            fail("drug dose must remain not reviewed/not enabled for row: %s" % row.get("species_or_taxon"))
        if row.get("source_review_status") != "required_not_started":
            fail("source review must be required_not_started for row: %s" % row.get("species_or_taxon"))


def assert_ci_and_smoke_hooks() -> None:
    ci = read("scripts/ci_static_checks.sh")
    smoke = read("scripts/smoke_petmed.sh")
    if "Exotics Knowledge Coverage Gap Review V1 static checks" not in ci:
        fail("ci_static_checks missing Exotics Knowledge Coverage Gap Review V1 block")
    if "python3 scripts/validate_exotics_knowledge_coverage_gap_review.py" not in ci:
        fail("ci_static_checks missing exotics coverage validator command")
    if "Exotics Knowledge Coverage Gap Review V1 smoke" not in smoke:
        fail("smoke missing Exotics Knowledge Coverage Gap Review V1 block")
    if "validate_exotics_knowledge_coverage_gap_review.py" not in smoke:
        fail("smoke missing exotics coverage validator command")


def main() -> None:
    assert_files_and_snippets()
    assert_existing_exotics_validators()
    assert_module_behavior()
    assert_matrix_csv()
    assert_ci_and_smoke_hooks()
    print("VALIDATOR=PASS Exotics Knowledge Coverage Gap Review V1")


if __name__ == "__main__":
    main()
