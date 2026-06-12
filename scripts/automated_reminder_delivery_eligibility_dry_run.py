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

from automated_reminder_delivery_eligibility import (  # noqa: E402
    evaluate_delivery_eligibility,
    evaluate_delivery_scenarios,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Automated Reminder Delivery Eligibility Engine dry-run V1")
    parser.add_argument("--input", required=True, help="Input JSON scenario file")
    parser.add_argument("--out", default="", help="Optional output JSON file")
    parser.add_argument("--single", action="store_true", help="Treat input as one payload instead of scenario bundle")
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    report = evaluate_delivery_eligibility(payload) if args.single else evaluate_delivery_scenarios(payload)

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
