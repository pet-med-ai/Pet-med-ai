# Commercial V1 D0 Pilot Start Evidence V1

## 1. Document Status

- project: Pet-Med-AI
- phase: Commercial V1 Post-Go
- evidence_stage: Commercial V1 D0 Pilot Start Evidence
- date: 2026-06-17
- status: D0_EVIDENCE_IN_PROGRESS
- scope: first clinic supervised pilot start
- production_backend: https://pet-med-ai-backend.onrender.com
- production_frontend: https://pet-med-ai-frontend-static.onrender.com

## 2. Commercial V1 Boundary

D0 is a supervised first-clinic pilot start. It records launch-day operating evidence only.

Allowed:

- AI consultation
- dynamic consultation
- structured consultation
- case save, case detail, and case edit checks
- Clinical Docs Word export check
- preventive reminder review
- manual contact queue review
- opt-out handling check
- Ops, Release, and System read-only checks

Not allowed:

- real automatic SMS sending
- real automatic WeChat sending
- real automatic email sending
- provider credentials
- background worker automatic delivery
- EMR real import
- EMR case update
- device real integration
- DICOM real integration
- lab equipment real integration
- structured prescription write
- invoice or billing real writes

## 3. D0 Required Production State

Required:

- healthz: OK
- database_revision: 0008_auto_delivery
- alembic_head: 0008_auto_delivery
- schema_ok: true
- all dangerous feature flags disabled
- online smoke: PASS
- CI static checks: PASS

Dangerous flags must remain disabled:

- ENABLE_EMR_REAL_IMPORT=false
- ENABLE_EMR_IMPORT_CASE_UPDATE=false
- ENABLE_EMR_ATTACHMENT_DOWNLOAD=false
- ENABLE_PREVENTIVE_AUTO_DELIVERY=false
- ENABLE_PREVENTIVE_SMS_DELIVERY=false
- ENABLE_PREVENTIVE_WECHAT_DELIVERY=false
- ENABLE_PREVENTIVE_EMAIL_DELIVERY=false

## 4. D0 Evidence Commands

Run locally:

```bash
cd ~/Documents/Pet-med-ai
bash scripts/ci_static_checks.sh
```

Run against production:

```bash
curl -sS https://pet-med-ai-backend.onrender.com/healthz
curl -sS https://pet-med-ai-backend.onrender.com/api/system/version | python3 -m json.tool
curl -sS https://pet-med-ai-backend.onrender.com/api/system/feature-flags | python3 -m json.tool
BASE_URL=https://pet-med-ai-backend.onrender.com FRONTEND_URL=https://pet-med-ai-frontend-static.onrender.com bash scripts/smoke_petmed.sh
```

## 5. D0 Supervised Workflow Evidence

Record actual D0 results in:

- docs/ops/COMMERCIAL_V1_D0_PILOT_START_CHECKLIST.csv
- docs/ops/COMMERCIAL_V1_D0_PILOT_WORKFLOW_EVIDENCE_TEMPLATE.csv
- docs/ops/COMMERCIAL_V1_D0_PILOT_INCIDENT_SNAPSHOT.csv

## 6. D0 Immediate Pause Rule

Immediately pause clinic-facing use if any of the following occurs:

- schema_ok=false
- database_revision != 0008_auto_delivery
- database_revision != alembic_head
- dangerous feature flag enabled
- cross-user data access
- secret leakage
- PHI or customer data committed into repo evidence
- automatic outbound message sent
- EMR real write occurs
- online smoke fails

## 7. D0 Decision

Expected no-incident decision:

```text
open_p0_count=0
open_p1_count=0
decision=GO_CONTINUE_D1
```

If any P0 appears:

```text
decision=NO_GO_PAUSE_PILOT
```

## 8. Owner Signoff

- release_owner: TBD
- security_owner: TBD
- clinical_ops_owner: TBD
- final_decision: TBD

## 9. Completion Criteria

D0 Pilot Start Evidence can be marked complete only when:

- D0 health check evidence exists
- D0 system version evidence exists
- D0 feature flags evidence exists
- D0 online smoke evidence exists
- D0 pilot clinic and users are recorded
- D0 supervised AI consult is recorded
- D0 supervised case save is recorded
- D0 Word export check is recorded
- D0 manual queue check is recorded
- D0 incident snapshot exists
- D0 decision exists
- validator PASS
- CI static checks PASS
- online smoke PASS

Target status after completion:

```text
Commercial V1 D0 Pilot Start Evidence: complete
Next: Commercial V1 D1-D7 Daily Pilot Operations Evidence
```
