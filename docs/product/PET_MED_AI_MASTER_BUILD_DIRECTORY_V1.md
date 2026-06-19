# Pet-Med-AI Master Build Directory V1

## 1. Product Identity

Pet-Med-AI is a veterinary hospital AI-assisted clinical workflow and clinical data platform.

The product direction is:

```text
consultation -> structured history -> case -> diagnostic data -> AI clinical assistance -> treatment safety -> documentation -> hospital operations
```

## 2. Build Directory

### A. AI Consultation and Session System

Completed / built:

- AI consultation API
- dynamic consultation
- consultation session persistence
- history session recovery
- consultation saved as case
- continued consultation updates case
- user isolation
- history pagination and filters

To build:

- SOAP mapping
- structured answer persistence
- clinical question quality scoring
- clinician review trace
- specialty consultation templates

### B. Species Knowledge Base

Completed / built:

- exotic foundation
- exotic JSON rule library
- dog / cat JSON rule library
- smoke checks for species knowledge rules

To build:

- knowledge-base admin UI
- rule versioning
- clinical review workflow
- differential diagnosis rules
- diagnostic test recommendation rules
- treatment support rules
- drug dose knowledge base

### C. Structured Consultation Templates

Completed / built:

- exotic structured intake V1 / V2 / V3
- dog / cat structured intake V1 / V2 / V3
- pre-save history merge preview
- structured intake record model foundation

To build:

- structured intake answers table
- specialty templates
- versioned templates
- structured answer analytics
- template-driven differential diagnosis

### D. Case System and Clinical Data Hub

Completed / built:

- case save
- case list / detail / edit
- case updates
- case isolation
- Clinical Docs Word export

To build:

- SOAP/POMR case structure
- problem list
- diagnosis fields
- treatment plan fields
- diagnostic data attachments
- case timeline
- revision history

### E. Diagnostic Data Model

Current status:

- design direction established
- DiagnosticReport / Observation / ImagingStudy identified as core next objects

To build:

- DiagnosticReport model
- Observation model
- ImagingStudy model
- Alembic migration plan
- read-only preview API
- case relationship
- unit / reference range / abnormal flag logic
- review status workflow

### F. Lab / Imaging / Device Integration

Completed / built as dry-run foundation:

- EMR webhook dry-run
- webhook inbox persistence
- EMR to Case mapping dry-run
- EMR import batch planning
- EMR execution dry-run
- feature flag protected high-risk gates

To build:

- Integration API V1
- Local Device Gateway V1
- Lab Result Ingest Dry-run V1
- Imaging / DICOM Ingest Dry-run V1
- lab parser fixtures
- imaging metadata parser fixtures
- review queue
- case detail diagnostic display

Blocked until separate risk review:

- EMR real import
- EMR case update
- attachment download
- device real ingest
- DICOM real ingest
- lab equipment real ingest

### G. AI Clinical Reasoning

Completed / built:

- dynamic questioning
- risk level output
- species rule paths
- basic inspection suggestions
- basic treatment suggestions
- AI review audit foundation

To build:

- AI Lab Abnormal Summary V1
- AI Imaging Report Summary V1
- differential diagnosis assistant
- test recommendation ranking
- treatment recommendation boundary
- clinician feedback loop
- regression evaluation set

### H. Treatment and Drug Dose Safety

Current foundation:

- basic treatment suggestions
- structured prescription write disabled by feature gate
- physician final responsibility established in legal pack

To build:

- Treatment Recommendation Boundary V1
- Drug Dose Safety Framework V1
- Drug Dose Knowledge Base V1
- dose unit conversion tests
- species-specific dose rules
- contraindication rules
- renal / hepatic / age / weight adjustments
- clinician-confirmed prescription draft only

Blocked:

- automatic prescription
- real structured prescription write
- customer-facing unreviewed treatment advice

### I. Clinical Documentation

Completed / built:

- Word template spec
- DOCX assets
- render-preview
- DOCX render API
- Case detail export UI
- document hash
- DOCX smoke coverage

To build:

- outpatient note
- surgery record
- anesthesia record
- lab / imaging summary document
- consent forms
- PDF conversion implementation
- document archive and audit

### J. Preventive Care and Manual Operations

Completed / built:

- preventive care rules
- rule engine dry-run
- in-app reminders
- manual notification queue
- opt-out handling
- ops dashboard
- automated delivery dry-run / template registry / risk review

Allowed in Commercial V1:

- in-app reminders
- manual queue
- opt-out handling
- read-only ops dashboard

Blocked in Commercial V1:

- real SMS
- real WeChat
- real email
- provider credentials
- background worker auto-delivery

### K. Commercial Launch, Ops, Security

Completed / built:

- Render backend
- Render static frontend
- Render PostgreSQL
- healthz
- system version
- feature flags
- CI static checks
- smoke
- launch readiness
- feature scope lock
- ops runbook
- access review
- monitoring plan
- backup / restore drill
- legal / consent pack
- final Go / No-Go
- D0-D7 post-go evidence
- first clinic weekly review

To build:

- controlled rollout gate
- multi-clinic tenant review
- support escalation process
- post-pilot metrics review

## 3. Immediate Priority

```text
Diagnostic Data Model Gap Review V1
```
