# Exotics Rabbit Deepening V1

## Purpose

This stage deepens the rabbit branch of the exotics knowledge base.

It converts the rabbit coverage from a minimal triage scaffold into a broader rabbit-specific triage and history-capture layer covering:

- gastrointestinal stasis / obstruction directions
- dental and oral pain directions
- respiratory red flags
- urinary / renal / reproductive review prompts
- neurologic / head tilt review prompts
- pododermatitis / skin and husbandry review prompts
- emergency systemic status prompts

## Scope

Allowed:

- update `knowledge-base/exotics/rabbit.json`
- update `knowledge-base/exotics/intake/rabbit.json`
- add read-only coverage helper
- add docs, checklist, validator and smoke/CI hooks
- keep all existing exotics validators green

Not allowed:

- final diagnosis
- diagnostic conclusion
- treatment plan
- prescription
- drug dose
- drug route or frequency
- client-facing output
- database writes
- external AI or provider calls
- real EMR / lab / DICOM / device ingest

## Clinical boundary

This is not a complete rabbit medicine knowledge base.

Current level:

```text
rabbit_deepened_triage_scaffold_not_comprehensive_clinical_kb
```

Source review remains required before any treatment-level or dose-level output.

```text
source_review_status=required_not_started
drug_dose_status=not_reviewed_not_enabled
requires_human_review=true
clinician_signoff_required=true
```

## Files

```text
knowledge-base/exotics/rabbit.json
knowledge-base/exotics/intake/rabbit.json
backend/exotics_rabbit_deepening.py
docs/clinical_data/EXOTICS_RABBIT_DEEPENING_V1.md
docs/clinical_data/EXOTICS_RABBIT_DEEPENING_CHECKLIST_V1.csv
docs/clinical_data/EXOTICS_RABBIT_DEEPENING_GO_NO_GO_V1.csv
scripts/validate_exotics_rabbit_deepening.py
scripts/ci_static_checks.sh
scripts/smoke_petmed.sh
```

## Validation

```bash
python3 scripts/validate_exotic_kb.py
python3 scripts/validate_exotic_intake_templates.py
python3 scripts/validate_exotics_rabbit_deepening.py
bash scripts/ci_static_checks.sh
```

## Go / No-Go

GO only if:

```text
validator=PASS
ci_static_checks=PASS
online_smoke=ALL_PASS
rabbit coverage domains present
rabbit intake deepened
no DB write
no final diagnosis
no treatment plan
no prescription
no drug dose
requires_human_review=true
decision=GO_TO_EXOTICS_AVIAN_DEEPENING_V1
```
