#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.exotic_intake_templates import load_intake_index, load_intake_templates  # noqa: E402


def main() -> int:
    index = load_intake_index()
    templates = load_intake_templates()
    expected = set(index.get("templates") or [])
    actual = set(templates.keys())
    if expected != actual:
        raise SystemExit(f"intake templates mismatch: expected={sorted(expected)}, actual={sorted(actual)}")

    for key, template in templates.items():
        sections = template.get("sections") or []
        question_count = sum(len(section.get("questions") or []) for section in sections)
        red_flags = len(template.get("red_flag_prompts") or [])
        required = sum(
            1
            for section in sections
            for question in (section.get("questions") or [])
            if question.get("required")
        )
        print(
            f"OK intake {key}: "
            f"sections={len(sections)}, questions={question_count}, required={required}, red_flags={red_flags}"
        )

    print(f"ALL EXOTIC STRUCTURED INTAKE TEMPLATES VALID: {index.get('version')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
