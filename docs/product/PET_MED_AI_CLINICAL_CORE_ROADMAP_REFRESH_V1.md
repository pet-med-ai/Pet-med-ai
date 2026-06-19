# Pet-Med-AI Clinical Core Roadmap Refresh V1

## 1. Purpose

This stage returns Pet-Med-AI from Commercial V1 post-go operations to the original clinical product roadmap.

Pet-Med-AI is a veterinary hospital AI-assisted clinical workflow and clinical data system. It is not only a reminder system, a simple case CRUD system, a commercial launch wrapper, or a generic AI chatbot.

Core clinical direction:

```text
structured consultation
species knowledge base
history merge
case record
lab / imaging / device data ingestion
DiagnosticReport / Observation / ImagingStudy
AI abnormal summary
diagnostic assistance
treatment recommendation
drug dose safety
clinical documentation
hospital operations loop
```

Commercial V1, preventive care reminders, manual front-desk queues and Ops Dashboard are operating support layers. They must not replace the clinical roadmap.

## 2. Previous Stage

Previous stage:

```text
First Clinic Pilot Weekly Review V1
decision=GO_CLOSE_D0_D7_OBSERVATION_WINDOW
next=CLINICAL_CORE_ROADMAP_REFRESH_V1
```

Commercial V1 D0-D7 proved that the deployed system can support a controlled first clinic pilot, but it did not prove readiness for real clinical data ingestion, real EMR writes, DICOM ingest, lab equipment ingest, structured prescriptions, or drug dose automation.

## 3. Clinical Core Principles

### Clinical safety first

AI assists doctors and does not replace doctors.

Doctor final responsibility remains mandatory.

High-risk clinical output must remain reviewed by a human clinician.

### Structured data before automation

Before real device, lab, imaging or EMR write flows, the system must first define and validate:

- DiagnosticReport
- Observation
- ImagingStudy
- source metadata
- review status
- abnormal flags
- units and reference ranges
- case linkage
- audit trail

### Dry-run before real integration

All clinical data ingestion must follow this sequence:

```text
docs + risk review
schema design
offline parser / dry-run
read-only preview
review queue
controlled pilot
rollback rehearsal
real integration decision
```

### No Commercial V1 boundary expansion

Clinical Core Refresh V1 does not enable:

- real automatic SMS sending
- real automatic WeChat sending
- real automatic email sending
- provider credentials
- background worker automatic delivery
- EMR real import
- EMR case update
- EMR attachment download
- device real ingest
- DICOM real ingest
- lab equipment real ingest
- structured prescription write
- invoice / billing real writes

## 4. Roadmap Tracks

### Track A: Structured Consultation and Clinical History

Current foundation:

- AI consultation
- dynamic consultation
- structured consultation templates
- saved consultation sessions
- save consultation as case
- update case after continued consultation
- user isolation

Next priorities:

- SOAP history mapping
- structured answer persistence
- specialty templates
- consultation quality scoring
- AI history summarization V2
- clinician review trace

### Track B: Species Knowledge Base

Current foundation:

- exotic knowledge base
- dog / cat knowledge base
- JSON rule libraries
- knowledge-base driven risk and tree path checks

Next priorities:

- knowledge-base admin UI
- versioned rule management
- clinician approval workflow
- differential diagnosis rules
- test recommendation rules
- treatment recommendation rules
- drug dose knowledge base

### Track C: Case as Clinical Data Hub

Current foundation:

- case list / detail / edit
- case save and update
- case export
- Clinical Docs Word export
- user isolation

Next priorities:

- SOAP / POMR case structure
- problem list
- diagnosis fields
- treatment plan fields
- case timeline
- diagnostic report attachment
- lab / imaging display
- audit timeline
- revision history

### Track D: Diagnostic Data Model

Next immediate priority.

Core objects:

- DiagnosticReport
- Observation
- ImagingStudy

Minimum design areas:

- relation to Case
- source type
- ordering clinician
- status: draft / reviewed / final / amended
- report text
- observation item values
- units
- reference ranges
- abnormal flags
- imaging metadata
- attachments / external references
- created_at / reviewed_at
- audit fields

### Track E: Integration API and Local Device Gateway

Target architecture:

```text
lab device / imaging system / EMR
↓
local gateway or adapter
↓
Pet-Med-AI Integration API dry-run
↓
read-only preview
↓
DiagnosticReport / Observation / ImagingStudy
↓
case detail display
↓
AI abnormal summary
```

Next priorities:

- Integration API V1 docs
- Local Device Gateway Architecture V1
- Lab Result Ingest Dry-run V1
- Imaging / DICOM Ingest Dry-run V1
- attachment safety policy
- PHI redaction and audit policy

### Track F: AI Clinical Reasoning Layer

Current foundation:

- dynamic questioning
- risk level output
- species knowledge base paths
- basic inspection and treatment suggestions
- AI review audit foundation

Next priorities:

- AI Lab Abnormal Summary V1
- AI Imaging Report Summary V1
- differential diagnosis assistant
- test recommendation ranking
- treatment recommendation boundary
- clinician accept / modify / reject feedback
- regression test set

### Track G: Treatment and Drug Dose Safety

This is high-risk clinical functionality and must be staged carefully.

Next priorities:

- Treatment Recommendation Boundary V1
- Drug Dose Safety Framework V1
- Drug Dose Knowledge Base V1
- species-specific dose rules
- contraindications
- renal / hepatic / age / weight adjustments
- unit conversion tests
- overdose / underdose warning rules
- clinician-confirmed prescription draft only

Not allowed in this stage:

- automatic prescription
- structured prescription write
- customer-facing treatment advice without clinician review

## 5. Next Stage Recommendation

The immediate next stage should be:

```text
Diagnostic Data Model Gap Review V1
```

Rationale:

Pet-Med-AI cannot safely build lab, imaging, device ingestion or AI abnormal summaries until the clinical data model is explicitly reviewed and locked.

Diagnostic Data Model Gap Review V1 should produce:

- current model inventory
- missing DiagnosticReport fields
- missing Observation fields
- missing ImagingStudy fields
- Case relationship design
- migration risk register
- read-only API plan
- dry-run sample fixtures
- validator requirements
- smoke coverage plan
