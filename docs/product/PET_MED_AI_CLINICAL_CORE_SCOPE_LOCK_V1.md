# Pet-Med-AI Clinical Core Scope Lock V1

## 1. Scope Purpose

This document locks the scope for Clinical Core Roadmap Refresh V1.

This stage is a roadmap and validation stage only.

It does not implement runtime clinical data ingestion or migrations.

## 2. In Scope

- clinical core roadmap refresh
- master build directory
- Commercial V1 to Clinical Core handoff
- clinical core scope lock
- next-stage matrix
- validator
- CI static check hook

## 3. Out of Scope

- backend runtime API changes
- frontend runtime UI changes
- database schema changes
- Alembic migrations
- real EMR import
- real EMR case update
- attachment download
- device real ingest
- lab equipment real ingest
- DICOM real ingest
- structured prescription write
- invoice / billing real writes
- real automatic SMS / WeChat / email
- provider credentials
- background worker automatic delivery

## 4. Safety Boundary

AI assists doctors and does not replace doctors.

Diagnostic and treatment suggestions must remain clinician-reviewed.

Drug dose safety requires a separate clinical review and controlled validation process.

## 5. Required Disabled Flags

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

## 6. Completion Decision

```text
decision=GO_TO_DIAGNOSTIC_DATA_MODEL_GAP_REVIEW_V1
```
