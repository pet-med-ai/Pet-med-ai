# Diagnostic Data Model Gap Review V1

## 1. Document Status

- project: Pet-Med-AI
- stage: Diagnostic Data Model Gap Review V1
- status: DOCS_VALIDATION
- previous_stage: Clinical Core Roadmap Refresh V1
- previous_decision: GO_TO_DIAGNOSTIC_DATA_MODEL_GAP_REVIEW_V1
- next_recommended_stage: DiagnosticReport / Observation / ImagingStudy Design V1

---

## 2. Purpose

This stage reviews the clinical data model gap before any database migration or runtime implementation.

Pet-Med-AI is returning from Commercial V1 post-go operations to the clinical core roadmap.

The immediate clinical objective is to define the gap for:

```text
DiagnosticReport
Observation
ImagingStudy
```

These objects are required before safe lab result ingestion, imaging metadata ingestion, device data ingestion, AI abnormal summaries, and clinical diagnostic assistance.

---

## 3. Scope

In scope:

- current diagnostic-data capability review
- DiagnosticReport field candidate review
- Observation field candidate review
- ImagingStudy field candidate review
- Case relationship review
- source metadata review
- status / review workflow review
- unit / reference range / abnormal flag review
- attachment / external reference review
- migration risk register
- validator and smoke coverage plan
- next-stage recommendation

Out of scope:

- no Alembic migration
- no new database table
- no backend runtime API implementation
- no frontend runtime UI implementation
- no real EMR import
- no EMR case update
- no EMR attachment download
- no real device ingest
- no DICOM real ingest
- no lab equipment real ingest
- no structured prescription write
- no invoice / billing real write

---

## 4. Current Foundation

Commercial V1 has established:

- AI consultation
- dynamic consultation
- structured consultation
- case save / detail / edit
- Clinical Docs Word export
- EMR webhook dry-run
- webhook inbox dry-run receipt persistence
- EMR to Case mapping dry-run
- feature flag safety gates
- online smoke
- D0-D7 pilot evidence
- weekly review close decision

Existing dry-run / operational models provide useful safety patterns, but they do not replace the clinical diagnostic data model.

---

## 5. Identified Gaps

### 5.1 DiagnosticReport gaps

Pet-Med-AI needs a durable report-level object for lab panels, imaging reports, device reports and imported diagnostic summaries.

Key missing areas:

- case relationship
- report category
- source type
- source system identifier
- report status
- report title
- report text
- ordering clinician
- reviewing clinician
- reviewed timestamp
- attachment references
- external report identifiers
- abnormal summary
- AI summary review status
- audit metadata

### 5.2 Observation gaps

Pet-Med-AI needs a structured observation object for individual lab values, measurements and device readings.

Key missing areas:

- parent DiagnosticReport relationship
- case relationship
- observation code
- display name
- value
- value type
- unit
- reference range low / high
- abnormal flag
- interpretation
- specimen type
- collected timestamp
- source metadata
- review status

### 5.3 ImagingStudy gaps

Pet-Med-AI needs an imaging study object for imaging metadata and report linkage.

Key missing areas:

- case relationship
- modality
- body region
- study date
- accession number
- study instance UID or safe external reference
- report text
- radiologist / clinician review fields
- attachment or external viewer reference
- AI imaging summary status
- abnormal flag
- source system
- audit metadata

---

## 6. Relationship Direction

Proposed relationship direction for next design stage:

```text
Case
 ├── DiagnosticReport
 │    └── Observation
 └── ImagingStudy
```

DiagnosticReport can represent:

- lab report
- device report
- imported EMR diagnostic report
- other structured diagnostic summary

Observation should belong to a DiagnosticReport and also be queryable by Case.

ImagingStudy should belong to Case and may also attach a report text or link to future ImagingReport style data.

---

## 7. Status and Review Direction

Candidate statuses:

```text
draft
received
review_pending
reviewed
final
amended
voided
```

Clinical safety rule:

```text
AI-generated abnormal summaries must not become final clinical interpretation without clinician review.
```

---

## 8. Source Type Direction

Candidate source types:

```text
manual
emr_dry_run
emr_import
lab_device_dry_run
lab_device
imaging_gateway_dry_run
imaging_gateway
device_gateway_dry_run
device_gateway
```

Commercial V1 does not permit real import or real device ingestion. The next implementation stages must start with dry-run and read-only preview.

---

## 9. AI Abnormal Summary Dependency

AI Lab Abnormal Summary V1 and AI Imaging Report Summary V1 require this diagnostic data model first.

AI summary must be staged as:

```text
raw diagnostic data
↓
structured report / observation / imaging metadata
↓
read-only case display
↓
AI abnormal summary draft
↓
clinician review
↓
case note or document output
```

---

## 10. Migration Risk

No migration should be created during this gap review.

Risks to resolve before migration:

- field naming stability
- unit representation
- reference range representation
- abnormal flag semantics
- source system identifier format
- attachment storage policy
- PHI handling
- audit requirements
- rollback plan
- read-only smoke coverage

---

## 11. Next Stage Recommendation

Recommended next stage:

```text
DiagnosticReport / Observation / ImagingStudy Design V1
```

Expected decision after this gap review:

```text
decision=GO_TO_DIAGNOSTIC_REPORT_OBSERVATION_IMAGINGSTUDY_DESIGN_V1
```
