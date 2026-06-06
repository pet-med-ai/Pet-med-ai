#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "docs" / "ops" / "RELEASE_RECORD_TEMPLATE.md"
OUT_DIR = ROOT / "docs" / "ops" / "releases"


def slugify(value: str) -> str:
    raw = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    while "--" in raw:
        raw = raw.replace("--", "-")
    return raw.strip("-") or "release"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a Pet-Med-AI release record from template.")
    parser.add_argument("--name", required=True, help="Short release name, e.g. ops-dashboard-v1")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="YYYY-MM-DD")
    parser.add_argument("--risk-class", default="docs-only")
    parser.add_argument("--owner", default="")
    args = parser.parse_args()

    if not TEMPLATE.exists():
        raise SystemExit("missing docs/ops/RELEASE_RECORD_TEMPLATE.md")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    target = OUT_DIR / f"{args.date}_{slugify(args.name)}.md"
    if target.exists():
        raise SystemExit(f"release record already exists: {target.relative_to(ROOT)}")

    text = TEMPLATE.read_text(encoding="utf-8")
    text = text.replace("Release ID:", f"Release ID: {slugify(args.name)}")
    text = text.replace("Date:", f"Date: {args.date}")
    text = text.replace("Owner:", f"Owner: {args.owner}")
    text = text.replace("Risk class:", f"Risk class: {args.risk_class}")

    target.write_text(text, encoding="utf-8")
    print(target.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
