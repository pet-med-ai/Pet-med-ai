#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from preventive_care_rules import compute_preventive_care_reminders, load_preventive_care_rules  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Preventive Care Reminder Rule Engine dry-run V1")
    parser.add_argument("--input", required=True, help="Input JSON file with pet payload")
    parser.add_argument("--rules", default=str(ROOT / "docs" / "preventive_care" / "VACCINE_DEWORMING_RULES_V1.csv"))
    parser.add_argument("--as-of", default=None, help="YYYY-MM-DD; defaults to today")
    parser.add_argument("--out", default="", help="Optional output JSON file")
    parser.add_argument("--only-actionable", action="store_true", help="Exclude active/not-yet-near reminders")
    args = parser.parse_args()

    input_path = Path(args.input)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    rules = load_preventive_care_rules(Path(args.rules))

    pet = payload.get("pet") if isinstance(payload, dict) and "pet" in payload else payload
    as_of = args.as_of or (payload.get("as_of_date") if isinstance(payload, dict) else None)

    report = compute_preventive_care_reminders(
        pet,
        as_of=as_of,
        rules=rules,
        include_active=not args.only_actionable,
    )

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
