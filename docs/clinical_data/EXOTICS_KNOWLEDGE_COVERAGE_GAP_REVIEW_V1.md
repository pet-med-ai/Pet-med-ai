# Exotics Knowledge Coverage Gap Review V1

## Purpose

This stage formalizes the gap review for the existing Pet-Med-AI exotics knowledge base.

The current exotics module is useful as a triage scaffold, but it is not yet a comprehensive exotic-animal clinical knowledge base. This review produces a coverage matrix and the Go / No-Go boundary for the next exotics deepening phases.

## Current repository assets reviewed

```text
backend/exotic_knowledge.py
backend/exotic_intake_templates.py
knowledge-base/exotics/index.json
knowledge-base/exotics/rabbit.json
knowledge-base/exotics/bird.json
knowledge-base/exotics/reptile.json
knowledge-base/exotics/ferret.json
knowledge-base/exotics/rodent.json
knowledge-base/exotics/intake/index.json
scripts/validate_exotic_kb.py
scripts/validate_exotic_intake_templates.py
```

## Current level

```text
current_level=triage_scaffold_not_comprehensive_clinical_kb
```

The current KB can help with:

- species/group routing
- red-flag triage
- broad differential direction labels
- initial check categories
- structured intake prompts

It is not yet sufficient for:

- species-level clinical decision support
- diagnostic report interpretation
- lab reference interpretation
- imaging abnormal-pattern interpretation
- treatment plans
- medication or dose output
- client-facing diagnosis

## Coverage groups currently present

```text
rabbit
bird
reptile
ferret
rodent
```

## Major gaps found

### Rabbit

Current rabbit coverage is clinically useful for triage, especially anorexia, reduced feces, abdominal distension, dental signs, respiratory distress, and head tilt.

Gaps:

- E. cuniculi not expanded
- uterine disease / reproductive disease not expanded
- urolithiasis not expanded
- pododermatitis not expanded
- dental imaging workflow not expanded
- rabbit lab interpretation not present
- source review not present
- drug dose source review not present

### Avian

Current bird coverage catches respiratory distress, ruffled feathers, egg-binding risk, regurgitation, appetite loss, and collapse.

Gaps:

- parrot / passerine / pigeon / raptor / poultry / waterfowl not split
- PBFD, PDD, aspergillosis, heavy metal toxicosis, nutritional disease not expanded
- avian lab interpretation not present
- low-stress handling workflow not formalized
- source review not present
- drug dose source review not present

### Reptile / Amphibian / Fish

Current reptile coverage is useful for husbandry, UVB, temperature, humidity, metabolic bone disease, dysecdysis, respiratory distress, vent prolapse, and neurologic red flags.

Gaps:

- turtle / tortoise / lizard / snake / amphibian / fish are not separated
- water quality for aquatic species is inadequate
- species-specific temperature, humidity, UVB, diet and enclosure parameters are not present
- reptile lab and imaging interpretation is not present
- amphibian and fish should not remain under a generic reptile rule long term

### Ferret

Current ferret coverage handles hypoglycemia-like weakness, drooling, foreign body risk, vomiting, respiratory distress, and urinary/systemic red flags.

Gaps:

- insulinoma not expanded
- adrenal disease not expanded
- ECE not expanded
- lymphoma not expanded
- vaccine reaction / cardiopulmonary risk not expanded
- source review not present
- drug dose source review not present

### Small mammals currently grouped under rodent

Current rodent coverage helps with dental signs, anorexia, fecal changes, diarrhea, respiratory distress, skin/trauma and weight loss.

Gaps:

- guinea pig needs a dedicated rule
- hamster needs a dedicated rule
- chinchilla needs a dedicated rule
- rat/mouse need a dedicated rule
- hedgehog and sugar glider are mapped under rodent-like handling but need taxonomy and clinical mapping review
- antibiotic safety and species-specific drug-risk review are not present

## Coverage matrix artifact

The matrix is recorded in:

```text
docs/clinical_data/EXOTICS_KNOWLEDGE_COVERAGE_MATRIX_V1.csv
```

Required columns:

```text
species_group
species_or_taxon
current_rule
coverage_status
covered_presentations
critical_gaps
priority
next_stage
drug_dose_status
source_review_status
```

## Safety boundary

This stage is a review-only stage.

Allowed:

```text
read exotics JSON KB
read exotics intake template JSON
build coverage matrix
identify gaps
prioritize next exotics stages
```

Forbidden:

```text
no DB write
no Case write
no DiagnosticReport write
no Observation write
no ImagingStudy write
no ai_summary write
no abnormal_summary write
no audit log write
no final diagnosis
no diagnostic conclusion
no treatment plan
no prescription
no drug dose
no drug route
no drug frequency
no client-facing output
no external AI/provider call
no real EMR/lab/DICOM/device ingest
```

## Validation

```bash
python3 scripts/validate_exotic_kb.py
python3 scripts/validate_exotic_intake_templates.py
python3 scripts/validate_exotics_knowledge_coverage_gap_review.py
bash scripts/ci_static_checks.sh
```

## Go / No-Go

GO only if:

```text
validator=PASS
ci_static_checks=PASS
coverage_matrix_present=true
source_review_status=required_not_started clearly marked
drug_dose_status=not_reviewed_not_enabled clearly marked
no DB write
no drug dose
no treatment plan
```

## Decision

```text
Exotics Knowledge Coverage Gap Review V1：完成 only after validator PASS, CI PASS, and no production safety gate regression.
decision=GO_TO_EXOTICS_RABBIT_DEEPENING_V1
```
