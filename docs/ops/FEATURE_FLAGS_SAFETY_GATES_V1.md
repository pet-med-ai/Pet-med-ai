# Pet-Med-AI Feature Flag / Safety Gate V1

## Purpose

This stage adds runtime safety gates for high-risk Pet-Med-AI features.

The goal is not to enable real writes. The goal is to make high-risk capabilities explicitly disabled by default so future code cannot accidentally execute dangerous workflows after deployment.

## Endpoint

```txt
GET /api/system/feature-flags
```

This endpoint is read-only and exposes boolean flag state only.

## Default policy

All dangerous flags default to false.

```txt
ENABLE_EMR_REAL_IMPORT=false
ENABLE_EMR_IMPORT_CASE_UPDATE=false
ENABLE_EMR_ATTACHMENT_DOWNLOAD=false
ENABLE_PRESCRIPTION_STRUCTURED_WRITE=false
ENABLE_DEVICE_REAL_INGEST=false
ENABLE_BILLING_REAL_WRITE=false
ENABLE_KB_PRODUCTION_PATCH=false
ENABLE_CASE_DELETE_IMPORT=false
```

## Flag meaning

### ENABLE_EMR_REAL_IMPORT

Allows a future real EMR import execution path to run.

Default:

```txt
false
```

This must remain false until create-only pilot implementation, rollback rehearsal, clinical signoff, and smoke gates are complete.

### ENABLE_EMR_IMPORT_CASE_UPDATE

Allows EMR import to update existing Case records.

Default:

```txt
false
```

V1 import policy is create-only. Updates are too risky until a separate overwrite policy exists.

### ENABLE_EMR_ATTACHMENT_DOWNLOAD

Allows downloading external EMR attachment URLs.

Default:

```txt
false
```

Attachment ingestion requires storage, malware, PHI, size, timeout, retry, and rollback controls.

### ENABLE_PRESCRIPTION_STRUCTURED_WRITE

Allows structured prescription or medication order writes.

Default:

```txt
false
```

Medication order writes need separate clinical safety review.

### ENABLE_DEVICE_REAL_INGEST

Allows real hospital device ingest.

Default:

```txt
false
```

Device data must stay in mock/dry-run until each vendor interface is validated.

### ENABLE_BILLING_REAL_WRITE

Allows billing / invoice writes.

Default:

```txt
false
```

Financial writes require reconciliation and rollback policy.

### ENABLE_KB_PRODUCTION_PATCH

Allows production knowledge-base patch promotion.

Default:

```txt
false
```

Clinical KB patches require schema validation and clinician review.

### ENABLE_CASE_DELETE_IMPORT

Allows imported data to delete Case records.

Default:

```txt
false
```

This should remain disabled indefinitely unless a separate legal and clinical deletion workflow exists.

## Response markers

Expected safe response:

```txt
message=system_feature_flags
all_dangerous_features_disabled=true
writes_database=false
exposes_secret_values=false
flags.ENABLE_EMR_REAL_IMPORT.enabled=false
flags.ENABLE_EMR_IMPORT_CASE_UPDATE.enabled=false
flags.ENABLE_EMR_ATTACHMENT_DOWNLOAD.enabled=false
```

## Safety boundary

This stage does not:

```txt
write database
change schema
enable real import
create Case
update Case
download attachments
write prescriptions
write billing rows
change frontend
```

## How future code should use this

Future high-risk endpoints should call:

```python
from feature_flags import assert_feature_enabled

assert_feature_enabled("ENABLE_EMR_REAL_IMPORT")
```

A disabled flag should return HTTP 403 and stop the workflow before any write occurs.

## Completion criteria

```txt
1. backend/feature_flags.py exists.
2. backend/main.py includes feature_flags_router.
3. GET /api/system/feature-flags returns 200.
4. Dangerous flags default false.
5. Response includes writes_database=false.
6. Response does not expose secrets.
7. Smoke checks the endpoint.
```
