# Pet-Med-AI Future Development Outline V1

## Purpose

This document freezes the next development outline for Pet-Med-AI after the clinical diagnostic data loop and the current exotics knowledge / source-review safety chain.

Pet-Med-AI remains a clinician-facing veterinary clinical workflow system. The main line is not reminders, simple CRUD, or commercial packaging. The main line is:

```text
structured intake
species knowledge
history merge
case accumulation
lab / imaging / device data
DiagnosticReport / Observation / ImagingStudy
AI abnormal summary
diagnostic assistance
treatment boundary
drug dose safety
clinical documents
hospital operations loop
```

Commercial operations, preventive reminders, front-desk manual contact, and Ops dashboards are support layers.

## Current production hard gate

Every later stage must preserve:

```text
database_revision=0009_diag_data
alembic_head=0009_diag_data
schema_ok=true
migration_errors=[]
writes_database=false
exposes_database_url=false
```

The required check is:

```bash
curl -sS https://pet-med-ai-backend.onrender.com/api/system/version | python3 -m json.tool
```

Dangerous feature flags must remain disabled unless a later stage has its own risk review, dry-run, controlled pilot, rollback evidence, and Go / No-Go approval.

```text
ENABLE_EMR_REAL_IMPORT=false
ENABLE_EMR_IMPORT_CASE_UPDATE=false
ENABLE_EMR_ATTACHMENT_DOWNLOAD=false
ENABLE_PREVENTIVE_AUTO_DELIVERY=false
ENABLE_PREVENTIVE_SMS_DELIVERY=false
ENABLE_PREVENTIVE_WECHAT_DELIVERY=false
ENABLE_PREVENTIVE_EMAIL_DELIVERY=false
ENABLE_PRESCRIPTION_STRUCTURED_WRITE=false
ENABLE_DEVICE_REAL_INGEST=false
ENABLE_BILLING_REAL_WRITE=false
```

## Permanent engineering discipline

```text
Do not run git add .
Do not commit .env files.
Do not commit app.db or other local database files.
Do not commit Downloads apply scripts.
Do not commit backend/app.
Do not commit backend/ai_engine.
Do not commit frontend/src/components.
Do not commit frontend/package-lock.json unless explicitly scoped.
Do not enable real EMR / lab / DICOM / device integrations.
Do not write prescriptions.
Do not output drug dose values.
Do not output route or frequency.
Do not release client-facing AI diagnosis.
```

## Stage template

Every stage should include:

```text
docs/<domain>/<STAGE_NAME>_V1.md or _V2.md
docs/<domain>/<STAGE_NAME>_CHECKLIST_V*.csv
docs/<domain>/<STAGE_NAME>_GO_NO_GO_V*.csv
backend/<feature>.py or frontend/<feature>.jsx when needed
scripts/validate_<stage>.py
scripts/ci_static_checks.sh hook
scripts/smoke_petmed.sh hook
```

Every stage should run:

```bash
git diff --check
python3 scripts/validate_<stage>.py
bash scripts/ci_static_checks.sh
```

Frontend stages should also run:

```bash
cd frontend
npm run build
```

Production stages should run:

```bash
KEEP_TMP=1 \
BASE_URL=https://pet-med-ai-backend.onrender.com \
FRONTEND_URL=https://pet-med-ai-frontend-static.onrender.com \
bash scripts/smoke_petmed.sh
```

## A. Immediate exotics source-review safety chain

The latest completed decision points are:

```text
Exotics Drug Dose Source Review Source Registry V1
Exotics Drug Dose Source Review Source Collection Protocol V1
Exotics Drug Dose Source Review Source Collection Execution Readiness V1
Exotics Drug Dose Source Review Source Collection Execution Controlled Pilot V1
Exotics Drug Dose Source Review Source Collection Controlled Pilot Report V1
Exotics Drug Dose Source Review Source Collection Governance Go/No-Go V1
Exotics Drug Dose Source Review Metadata-only Collection Workspace V1
Exotics Drug Dose Source Review Metadata-only Collection Workspace Validation V1
Exotics Drug Dose Source Review Metadata-only Collection Workspace Validation Report V1
Exotics Drug Dose Source Review Metadata-only Collection Workspace Governance Signoff V1
Exotics Drug Dose Source Review Metadata-only Collection Workspace Governance Signoff Record V1
```

### A1. Metadata-only Collection Workspace Governance Signoff Record Validation V1

Goal:

```text
Validate governance signoff record completeness.
Confirm species_group x review_domain coverage.
Confirm NO_GO_TO_COLLECTION_EXECUTION remains true.
Confirm no numeric dose / route / frequency / usable medication instruction fields.
```

Suggested files:

```text
backend/exotics_drug_dose_source_review_metadata_only_collection_workspace_governance_signoff_record_validation.py
docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_RECORD_VALIDATION_V1.md
docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_RECORD_VALIDATION_MATRIX_V1.csv
docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_RECORD_VALIDATION_CHECKLIST_V1.csv
docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_RECORD_VALIDATION_GO_NO_GO_V1.csv
scripts/validate_exotics_drug_dose_source_review_metadata_only_collection_workspace_governance_signoff_record_validation.py
```

### A2. Governance Signoff Record Validation Report V1

Goal:

```text
Produce a report shell for governance signoff record validation.
No source collection results.
No dose data.
No executable medication instruction.
```

### A3. Metadata-only Source Collection Workspace Human Assignment V1

Goal:

```text
Define clinical owner / primary collector / second reviewer / copyright reviewer role shell.
Do not store personal identifiers beyond role placeholders.
Do not start collection execution.
```

### A4. Metadata-only Source Collection Workspace Access Control Review V1

Goal:

```text
Review access controls for the source collection workspace.
Block unreviewed source uploads.
Block copied full text.
Block numeric dose / route / frequency fields.
```

### A5. Metadata-only Source Collection Workspace Dry-run Fixture V1

Goal:

```text
Create synthetic source metadata fixture.
No copyrighted source text.
No numeric medication values.
No route or frequency.
No prescription direction.
```

### A6. Metadata-only Source Collection Dry-run Parser V1

Goal:

```text
Parse synthetic metadata fixture into preview rows.
No DB write.
No evidence-table values.
No dose fields.
```

### A7. Source Registry Population Readiness V1

Goal:

```text
Decide whether metadata-only source registry controlled population can be proposed.
Default decision should remain NO_GO unless copyright, access, reviewer, and blocker gates pass.
```

### A8. Source Registry Metadata-only Controlled Population V1

Risk: high.

Goal:

```text
Allow a small, metadata-only source registry population path only after explicit Go / No-Go.
Still no dose, route, frequency, prescription, treatment plan, or client-facing instruction.
```

### A9. Evidence Tables Metadata-only Population Readiness V1

Goal:

```text
Prepare evidence tables metadata-only population.
No usable medication instruction.
```

### A10. Evidence Tables Metadata-only Controlled Population V1

Goal:

```text
Associate reviewed source metadata with evidence table shells.
No numeric dose or route/frequency.
```

### A11. Source Conflict Review V1

Goal:

```text
Record qualitative source conflict notes.
Do not resolve to a dose.
Do not recommend a medication.
```

### A12. Exotics Medication Contraindication Themes V1

Goal:

```text
Build species-specific contraindication themes.
No dose values.
No treatment plan.
```

Examples:

```text
species_sensitivity_theme
renal_risk_theme
hepatic_risk_theme
GI_stasis_risk_theme
dehydration_risk_theme
sedation_anesthesia_risk_theme
```

### A13. Exotics Monitoring Themes V1

Goal:

```text
Build monitoring theme shell.
No prescription instructions.
```

Examples:

```text
hydration_monitoring
appetite_feces_monitoring
body_weight_monitoring
renal_monitoring
hepatic_monitoring
sedation_recovery_monitoring
respiratory_monitoring
```

### A14. Exotics Drug Dose Value Capture Readiness Review V1

Goal:

```text
Assess whether value capture could ever be proposed.
Default decision: NO_GO_TO_VALUE_CAPTURE.
```

Hard boundary:

```text
dose_output_enabled=false
prescription_engine=false
client_facing=false
```

## B. Exotics clinical knowledge depth roadmap

Current status:

```text
Rabbit Deepening V1 complete
Avian Deepening V1 complete
Reptile Split V1 complete
Small Mammal Split V1 complete
Ferret Deepening V1 complete
```

The current exotics knowledge remains triage scaffold, not comprehensive clinical knowledge.

### B1. Rabbit Clinical Depth V2

Focus:

```text
E. cuniculi
uterine adenocarcinoma risk
urolithiasis / sludge
pododermatitis staging
dental abscess
GI obstruction vs ileus differentiation
pain scoring
nutrition and hay intake context
```

### B2. Avian Clinical Depth V2

Focus:

```text
PBFD
PDD
aspergillosis
heavy metal exposure
hypovitaminosis A
hepatic lipidosis
egg binding risk stratification
crop stasis / sour crop patterns
air sac disease patterns
```

### B3. Turtle / Tortoise Depth V2

Focus:

```text
shell rot
respiratory disease
vitamin A deficiency
egg retention
water quality
basking / UVB deficiency
floating abnormality
trauma / dog bite
```

### B4. Lizard Depth V2

Focus:

```text
bearded dragon MBD
leopard gecko impaction
chameleon husbandry disease
egg binding
dysecdysis
oral disease
parasite burden
```

### B5. Snake Depth V2

Focus:

```text
regurgitation
dysecdysis
respiratory infection
mouth rot
scale rot
thermal burn
mites
refusal to feed
pre-shed context
```

### B6. Amphibian Depth V2

Focus:

```text
water quality
chytrid risk theme
skin lesions
bloat
toxicity / chemical exposure
temperature / humidity mismatch
axolotl-specific branch
```

### B7. Fish Depth V2

Focus:

```text
water quality triage
ammonia / nitrite / nitrate
oxygenation
gill disease
buoyancy issue
fin rot
parasite signs
tank outbreak pattern
```

### B8. Guinea Pig Depth V2

Focus:

```text
vitamin C deficiency
dental disease
urinary stone
ovarian cyst
pododermatitis
GI stasis
respiratory disease
pregnancy risk
```

### B9. Hamster Depth V2

Focus:

```text
wet-tail-like risk
cheek pouch disease
skin wounds
tumors
respiratory signs
hypothermia
hibernation-like state differentiation
```

### B10. Chinchilla Depth V2

Focus:

```text
dental disease
heat stress
GI stasis
fur slip
skin disease
dust bath history
diet fiber imbalance
```

### B11. Rat / Mouse Depth V2

Focus:

```text
respiratory disease
mammary tumor
skin lesions
head tilt
dental overgrowth
social group outbreak
geriatric disease
```

### B12. Hedgehog Depth V2

Focus:

```text
wobbly hedgehog syndrome theme
mites / skin
oral disease
mass / neoplasia
temperature / torpor
obesity
respiratory signs
```

### B13. Sugar Glider Depth V2

Focus:

```text
hind limb weakness
nutrition imbalance
self-mutilation
dehydration
pouch infection
stress / colony changes
trauma
```

## C. Exotics lab and imaging readiness roadmap

### C1. Exotics Lab Reference Range Source Review V1

Goal:

```text
Review reference range source requirements.
Do not enable interpretation.
Do not write Observation interpretation.
```

### C2. Exotics Observation Code Mapping V1

Goal:

```text
Map species-specific lab item names and Observation code readiness.
Mark missing reference range status.
```

### C3. Exotics Lab Abnormality Review Boundary V1

Goal:

```text
Only flag clinician review needs.
No disease interpretation.
No diagnosis.
```

### C4. Exotics Imaging Pattern Readiness V1

Goal:

```text
Prepare source review framework for imaging patterns.
No image interpretation engine.
No PACS access.
```

### C5. Exotics DiagnosticReport Merge Boundary V1

Goal:

```text
Merge exotics KB and diagnostic data readiness into clinician-only preview.
No final diagnosis.
No client-facing output.
```

## D. Diagnostic assistance roadmap

Already completed:

```text
Problem List V1
Differential Diagnosis Candidates V1
Diagnostic Reasoning Evidence Trace V1
Diagnostic Assistance Case Detail UI V1
Clinician Review Persistence V1
Diagnostic Summary Audit Log V1
DiagnosticReport AI Summary Persistence V1
Observation Abnormal Flag Review V1
ImagingStudy Review Workflow V1
Clinical Docs Diagnostic Data Merge V1
Clinical QA Dashboard V2
Ops Dashboard Clinical Core V2
```

### D1. Diagnostic Assistance Evidence Quality V1

Goal:

```text
Score evidence quality qualitatively.
No numeric probability.
No diagnosis.
```

### D2. Diagnostic Reasoning Conflict Detection V1

Goal:

```text
Detect conflicting lab / imaging / history evidence.
Do not adjudicate final diagnosis.
```

### D3. Diagnostic Follow-up Questions V1

Goal:

```text
Generate clinician review questions from evidence gaps.
No treatment plan.
```

### D4. Diagnostic Assistance Summary V2

Goal:

```text
Combine problem list, differential candidates, evidence trace, review status, and audit status into clinician-only summary.
Not client-facing.
```

### D5. Diagnostic Assistance Review Queue V1

Goal:

```text
Read-only queue of cases requiring diagnostic review.
No auto signoff.
```

## E. Clinical documents roadmap

### E1. Clinical Docs Diagnostic Data Merge V2

Goal:

```text
More precise diagnostic-data sections for clinical documents.
Group by lab, imaging, review status, and audit evidence.
```

### E2. Clinical Docs Exotics Context Merge V1

Goal:

```text
Merge exotics structured intake context into clinical documents.
No dose.
No prescription.
```

### E3. Clinical Docs Clinician-only Diagnostic Appendix V1

Goal:

```text
Create clinician-only appendix containing evidence trace and QA flags.
Not client-facing.
```

### E4. Client-facing Summary Boundary V1

Risk: high.

Goal:

```text
Define what can be shown to pet owners.
Block AI diagnosis, dose, prescription, and uncertain differential lists by default.
```

## F. Data ingestion roadmap

### F1. Lab Result Parser Expansion V2

Goal:

```text
Expand dry-run lab parser coverage.
No real LIS.
```

### F2. Imaging Metadata Parser Expansion V2

Goal:

```text
Expand dry-run imaging metadata parser.
No PACS.
No DICOM download.
```

### F3. Device / Vitals Dry-run Fixture Parser V1

Goal:

```text
Dry-run fixture parser for vitals and device outputs.
No real device gateway.
```

### F4. Lab Result Real Ingest Readiness Review V1

Goal:

```text
Readiness review only.
No real lab ingest.
```

### F5. DICOM / PACS Readiness Review V1

Goal:

```text
Readiness review only.
No PACS query.
No attachment download.
```

### F6. Device Real Ingest Readiness Review V1

Goal:

```text
Readiness review only.
No real device ingest.
```

### F7. EMR Real Import Controlled Pilot V1

Risk: high.

Requirements:

```text
dry-run preview
read-only rehearsal
clinical approval
rollback evidence
feature flag default false
```

## G. Frontend UI roadmap

### G1. Case Detail Diagnostic Assistance UI V2

Goal:

```text
Improve problem list, differential candidates, evidence trace, review signoff, and audit log display.
```

### G2. Clinician Review Persistence UI V1

Goal:

```text
Doctor review controls for DiagnosticReport / Observation / ImagingStudy.
Require explicit confirmation.
```

### G3. Diagnostic Summary Audit Log UI V1

Goal:

```text
Append-only audit log viewer.
No update / delete.
```

### G4. Exotics Module Visibility UI V1

Goal:

```text
Make exotics module visible in the product.
Show species coverage and scaffold status.
```

### G5. Exotics Structured Intake UI V2

Goal:

```text
Improve species-specific structured intake forms.
```

### G6. Ops Dashboard Exotics Coverage V1

Goal:

```text
Show exotics KB coverage, source-review status, and NO-GO dose status in Ops Dashboard.
```

## H. Ops, QA, and audit roadmap

### H1. Clinical QA Dashboard V3

Goal:

```text
Add species coverage, exotics coverage, review backlog, audit coverage, and diagnostic completeness.
```

### H2. Ops Dashboard Clinical Core V3

Goal:

```text
Unify clinical QA, exotics QA, and diagnostic data gates in Ops.
```

### H3. Audit Log Search / Filter V1

Goal:

```text
Search append-only audit logs by case, report, event_type, clinician_id.
```

### H4. Clinical Safety Incident Review V1

Goal:

```text
Record potential safety events for review.
No automatic action.
```

## I. Commercial deployment support roadmap

### I1. Clinic Pilot Clinical Workflow V2

Goal:

```text
Formalize clinic pilot workflow from intake to QA dashboard.
```

### I2. Staff Training Pack V1

Goal:

```text
Train clinician, front desk, and ops staff on boundaries.
```

### I3. Clinic Pilot Go / No-Go V2

Goal:

```text
Decide whether broader clinic pilot can proceed.
```

## J. Long-term high-risk prescription and dose roadmap

These stages must not be rushed.

### J1. Drug Dose Clinician-only Draft Policy V1

Goal:

```text
Define whether clinician-only drafts can ever exist.
Default NO-GO.
```

### J2. Prescription Draft Data Model Risk Review V1

Goal:

```text
Risk review before any prescription draft schema.
No table creation.
No prescription write.
```

### J3. Prescription Draft API Dry-run V1

Goal:

```text
Dry-run preview only.
No persistence.
No client-facing output.
```

### J4. Client-facing Dose Output Boundary V1

Goal:

```text
Define why client-facing dose output remains disabled by default.
```

## Recommended next sequence

```text
1. Exotics Drug Dose Source Review Metadata-only Collection Workspace Governance Signoff Record Validation V1
2. Exotics Drug Dose Source Review Metadata-only Collection Workspace Governance Signoff Record Validation Report V1
3. Exotics Module Visibility / Documentation V1
4. Exotics Structured Intake UI V2
5. Ops Dashboard Exotics Coverage V1
6. Exotics Lab Reference Range Source Review V1
7. Exotics Imaging Pattern Readiness V1
8. Lab Result Parser Expansion V2
9. Imaging Metadata Parser Expansion V2
10. Device / Vitals Dry-run Fixture Parser V1
11. Diagnostic Assistance Evidence Quality V1
12. Diagnostic Reasoning Conflict Detection V1
13. Clinician Review Persistence UI V1
14. Audit Log Search / Filter V1
```

## Decision

```text
Pet-Med-AI Future Development Outline V1: complete only after validator PASS, CI PASS, smoke PASS, and production schema gate remains 0009_diag_data.
decision=GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_RECORD_VALIDATION_V1
```
