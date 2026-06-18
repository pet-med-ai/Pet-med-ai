# Commercial V1 D1-D7 Daily Pilot Operations Evidence V1

## 1. Document Status

- project: Pet-Med-AI
- phase: Commercial V1 Post-Go
- evidence_stage: Commercial V1 D1-D7 Daily Pilot Operations Evidence
- created_at: 2026-06-18
- status: D1_D7_DAILY_OPERATIONS_EVIDENCE_IN_PROGRESS
- prerequisite: Commercial V1 D0 Pilot Start Evidence completed
- D0 decision: GO_CONTINUE_D1
- scope: first clinic supervised pilot operation window
- production_backend: https://pet-med-ai-backend.onrender.com
- production_frontend: https://pet-med-ai-frontend-static.onrender.com

---

## 2. Product Direction Guardrail

Pet-Med-AI is a clinical AI assistance and clinical data system for real veterinary hospital workflows.

The long-term clinical mainline remains:

```text
structured intake
species knowledge base
history merge
case persistence
lab / imaging / device data ingest
DiagnosticReport / Observation / ImagingStudy
AI abnormality summary
diagnostic assistance
treatment recommendation
drug dosing safety
clinical document output
hospital operations loop
```

Commercial V1 daily pilot operations are a safety and adoption layer. They do not replace the clinical core roadmap.

---

## 3. D1-D7 Scope

Allowed during D1-D7:

- one pilot clinic only
- named pilot users only
- supervised AI consultation
- supervised dynamic consultation
- supervised case save / detail / edit checks
- supervised Clinical Docs Word export check
- preventive reminder review
- manual front-desk queue check
- opt-out handling check
- daily incident review
- daily health / version / feature flag / smoke evidence

Not allowed during D1-D7:

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
- structured prescription real write
- invoice / billing real write
- multi-clinic rollout

---

## 4. Required Daily Gates

Every day from D1 through D7 must record:

```text
healthz OK
system version OK
database_revision=0008_auto_delivery
alembic_head=0008_auto_delivery
schema_ok=true
feature flags OK
all dangerous flags disabled
online smoke PASS
open_p0_count recorded
open_p1_count recorded
daily decision recorded
owner signoff recorded
```

Required dangerous feature flags:

```text
ENABLE_EMR_REAL_IMPORT=false
ENABLE_EMR_IMPORT_CASE_UPDATE=false
ENABLE_EMR_ATTACHMENT_DOWNLOAD=false
ENABLE_PREVENTIVE_AUTO_DELIVERY=false
ENABLE_PREVENTIVE_SMS_DELIVERY=false
ENABLE_PREVENTIVE_WECHAT_DELIVERY=false
ENABLE_PREVENTIVE_EMAIL_DELIVERY=false
```

---

## 5. Daily Workflow Evidence

Each day should record supervised outcomes for:

```text
ai_consult_ok
dynamic_consult_ok
case_save_ok
case_detail_ok
case_edit_ok
word_export_ok
preventive_reminder_ok
manual_queue_ok
opt_out_ok
```

Evidence must stay de-identified. Do not commit real client names, phone numbers, addresses, medical record numbers, or PHI to repo evidence.

Recommended placeholders:

```text
pilot_clinic=FIRST_CLINIC_PILOT_001
pilot_users=release_owner,clinical_ops_user_01,frontdesk_user_01
```

---

## 6. Daily Pause Criteria

Pause clinic-facing pilot use immediately if any of these occur:

```text
schema_ok=false
database_revision != 0008_auto_delivery
database_revision != alembic_head
dangerous feature flag enabled
online smoke fails
cross-user data access
secret leakage
PHI / customer data committed into repo evidence
automatic outbound message sent
EMR real write occurs
device / DICOM / lab real ingest occurs without controlled pilot approval
structured prescription real write occurs
billing / invoice real write occurs
```

---

## 7. Daily Decisions

Allowed daily decisions:

```text
GO_CONTINUE_NEXT_DAY
GO_WITH_MONITORING
NO_GO_PAUSE_PILOT
GO_COMPLETE_D7
```

Expected no-incident daily decision:

```text
D1-D6: GO_CONTINUE_NEXT_DAY
D7: GO_COMPLETE_D7
```

If any P0 is open:

```text
decision=NO_GO_PAUSE_PILOT
```

---

## 8. Evidence Files

Daily evidence is recorded in:

```text
docs/ops/COMMERCIAL_V1_D1_D7_DAILY_PILOT_CHECKLIST.csv
docs/ops/COMMERCIAL_V1_D1_D7_DAILY_OPERATIONS_LOG_TEMPLATE.csv
docs/ops/COMMERCIAL_V1_D1_D7_DAILY_INCIDENT_LOG.csv
docs/ops/COMMERCIAL_V1_D1_D7_DAILY_SIGNOFF.csv
```

Validator:

```text
scripts/validate_commercial_v1_d1_d7_daily_pilot_ops.py
```

---

## 9. Completion Criteria

Commercial V1 D1-D7 Daily Pilot Operations Evidence can be marked complete only when:

- D1 through D7 daily logs exist
- each day has healthz evidence
- each day has system version evidence
- each day has feature flags evidence
- each day has online smoke evidence
- each day has workflow evidence
- each day has incident counts
- each day has daily decision
- each day has owner signoff
- validator PASS
- CI static checks PASS
- no open P0/P1 blocking issue remains

Target completion state:

```text
Commercial V1 D1-D7 Daily Pilot Operations Evidence：完成
Next: First Clinic Weekly Pilot Review / Controlled Rollout Gate
```
---

## D1 Daily Operating Evidence

- date: 2026-06-18
- pilot_clinic: FIRST_CLINIC_PILOT_001
- pilot_users: release_owner,clinical_ops_user_01,frontdesk_user_01
- healthz_ok: true
- database_revision: 0008_auto_delivery
- alembic_head: 0008_auto_delivery
- schema_ok: true
- dangerous_flags_disabled: true
- ci_static_pass: true
- online_smoke_pass: true
- supervised_workflow_ok: true
- open_p0_count: 0
- open_p1_count: 0
- decision: GO_CONTINUE_NEXT_DAY
- release_owner: release_owner
- security_owner: security_owner
- clinical_ops_owner: clinical_ops_owner
- notes: D1 supervised operations completed with de-identified evidence; no PHI in repo.

D1 evidence is de-identified. No real client name, phone number, medical record number, secret, database URL, or PHI is committed in repo evidence.
---

## D2 Daily Operating Evidence

- date: 2026-06-18
- pilot_clinic: FIRST_CLINIC_PILOT_001
- pilot_users: release_owner,clinical_ops_user_01,frontdesk_user_01
- healthz_ok: true
- database_revision: 0008_auto_delivery
- alembic_head: 0008_auto_delivery
- schema_ok: true
- dangerous_flags_disabled: true
- ci_static_pass: true
- online_smoke_pass: true
- supervised_workflow_ok: true
- open_p0_count: 0
- open_p1_count: 0
- decision: GO_CONTINUE_NEXT_DAY
- release_owner: release_owner
- security_owner: security_owner
- clinical_ops_owner: clinical_ops_owner
- notes: D2 supervised operations completed with de-identified evidence; no PHI in repo.

D2 evidence is de-identified. No real client name, phone number, medical record number, secret, database URL, or PHI is committed in repo evidence.


<!-- D3_REAL_OPERATING_EVIDENCE_START -->
## D3 Real Daily Operating Evidence

- date: 2026-06-18
- pilot_clinic: FIRST_CLINIC_PILOT_001
- pilot_users: release_owner,clinical_ops_user_01,frontdesk_user_01
- base_url: https://pet-med-ai-backend.onrender.com
- frontend_url: https://pet-med-ai-frontend-static.onrender.com
- git_commit: 47cd6ad
- healthz_ok: true
- ci_static_pass: true
- online_smoke_pass: true
- schema_ok: true
- database_revision: 0008_auto_delivery
- alembic_head: 0008_auto_delivery
- dangerous_flags_disabled: true
- ai_consult_ok: true
- dynamic_consult_ok: true
- case_save_ok: true
- case_detail_ok: true
- case_edit_ok: true
- word_export_ok: true
- preventive_reminder_ok: true
- manual_queue_ok: true
- opt_out_ok: true
- open_p0_count: 0
- open_p1_count: 0
- decision: GO_CONTINUE_NEXT_DAY
- release_owner: release_owner
- security_owner: security_owner
- clinical_ops_owner: clinical_ops_owner
- smoke_log_status: not_provided
- notes: D3 supervised daily pilot operations evidence; no PHI stored in repo evidence.

<!-- D3_REAL_OPERATING_EVIDENCE_END -->
