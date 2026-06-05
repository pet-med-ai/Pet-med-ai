#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
MIGRATIONS = BACKEND / "migrations" / "versions"

REQUIRED_FILES = [
    ROOT / "docs" / "ops" / "RELEASE_UPGRADE_RUNBOOK.md",
    ROOT / "docs" / "ops" / "RELEASE_CHECKLIST.csv",
    ROOT / "docs" / "ops" / "ROLLBACK_CHECKLIST.csv",
    ROOT / "docs" / "ops" / "RENDER_DEPLOYMENT_VERIFICATION.md",
    ROOT / "docs" / "ops" / "ALEMBIC_RELEASE_GUARDRAILS.md",
    ROOT / "docs" / "ops" / "RELEASE_TEMPLATE.md",
    ROOT / "render.yaml",
    ROOT / "scripts" / "smoke_petmed.sh",
]

EXPECTED_RENDER_MARKERS = [
    "pet-med-ai-backend",
    "pet-med-ai-frontend-static",
    "VITE_API_BASE",
    "https://pet-med-ai-backend.onrender.com",
]

FORBIDDEN_STARTUP_SCHEMA_MARKERS = [
    "Base.metadata.create_all(bind=engine)",
    "ensure_consult_session_columns()",
    "ensure_case_extra_columns()",
]


def fail(message: str) -> int:
    print(f"FAIL {message}", file=sys.stderr)
    return 1


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def find_revision_id(path: Path) -> str:
    text = read_text(path)
    tree = ast.parse(text)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "revision":
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        return node.value.value
    raise ValueError(f"revision not found in {path}")


def validate_migration_revisions() -> int:
    if not MIGRATIONS.exists():
        return fail("missing backend/migrations/versions")

    revisions = {}
    errors = []
    for path in sorted(MIGRATIONS.glob("*.py")):
        if path.name == "__init__.py":
            continue
        try:
            revision = find_revision_id(path)
        except Exception as exc:
            errors.append(f"{path.relative_to(ROOT)}: cannot read revision: {exc}")
            continue

        if len(revision) > 32:
            errors.append(
                f"{path.relative_to(ROOT)} revision id too long ({len(revision)} > 32): {revision}"
            )
        if revision in revisions:
            errors.append(
                f"duplicate revision id {revision}: {path.relative_to(ROOT)} and {revisions[revision]}"
            )
        revisions[revision] = str(path.relative_to(ROOT))

    if errors:
        return fail("Alembic revision validation failed:\\n  " + "\\n  ".join(errors))
    return 0


def validate_render_yaml() -> int:
    path = ROOT / "render.yaml"
    if not path.exists():
        return fail("missing render.yaml")
    text = read_text(path)
    missing = [marker for marker in EXPECTED_RENDER_MARKERS if marker not in text]
    if missing:
        return fail("render.yaml missing expected markers: " + ", ".join(missing))
    return 0


def validate_docs() -> int:
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED_FILES if not path.exists()]
    if missing:
        return fail("missing release framework files: " + ", ".join(missing))

    runbook = read_text(ROOT / "docs" / "ops" / "RELEASE_UPGRADE_RUNBOOK.md")
    for marker in (
        "Do not reintroduce Base.metadata.create_all",
        "revision ids must be <=32 characters",
        "BASE_URL=https://pet-med-ai-backend.onrender.com bash scripts/smoke_petmed.sh",
        "git add <target files>",
    ):
        if marker not in runbook:
            return fail(f"release runbook missing marker: {marker}")

    guardrails = read_text(ROOT / "docs" / "ops" / "ALEMBIC_RELEASE_GUARDRAILS.md")
    for marker in ("<= 32 characters", "upgrade head", "stamp head"):
        if marker not in guardrails:
            return fail(f"Alembic guardrails missing marker: {marker}")

    return 0


def validate_main_no_startup_schema_mutation() -> int:
    main_path = BACKEND / "main.py"
    if not main_path.exists():
        return fail("missing backend/main.py")
    text = read_text(main_path)
    present = [marker for marker in FORBIDDEN_STARTUP_SCHEMA_MARKERS if marker in text]
    if present:
        return fail("startup schema mutation markers found in backend/main.py: " + ", ".join(present))
    return 0


def validate_smoke_includes_release_readiness() -> int:
    smoke = ROOT / "scripts" / "smoke_petmed.sh"
    if not smoke.exists():
        return fail("missing scripts/smoke_petmed.sh")
    text = read_text(smoke)
    if "validate_release_readiness.py" not in text:
        return fail("smoke script does not include validate_release_readiness.py")
    return 0


def main() -> int:
    checks = [
        validate_docs,
        validate_render_yaml,
        validate_migration_revisions,
        validate_main_no_startup_schema_mutation,
        validate_smoke_includes_release_readiness,
    ]

    for check in checks:
        rc = check()
        if rc:
            return rc

    print("OK release readiness: runbooks, Render markers, Alembic guardrails and smoke integration are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
