# Privacy / Data Handling SOP V1

> Template only. Must be reviewed and adapted by qualified local legal/professional counsel before use.

## Purpose

This SOP defines minimum data handling rules for Pet-Med-AI Commercial V1.

## Data minimization

Staff should avoid entering unnecessary personal information into free-text fields.

Do not enter unless necessary and approved:

```txt
human medical information
identity document numbers
financial account details
unrelated family information
passwords
tokens
API keys
DATABASE_URL
provider credentials
```

## Access limitation

Clinical data should be accessible only to authorized users who need it for:

```txt
clinical care
case documentation
front-desk manual contact workflow
preventive care workflow
support / incident response
release / backup / restore verification with sanitized evidence
```

## Owner-scoped data

Commercial V1 must preserve owner-scoped access for:

```txt
cases
consultation sessions
preventive care reminders
notification queue items
automated reminder delivery attempts
clinical document exports
audit records
```

User B must not access User A data by guessing IDs.

## Evidence and screenshots

Do not commit or share evidence containing:

```txt
client names
client phone numbers
pet owner personal data
raw clinical records
DATABASE_URL
JWT secret
provider token
Render secrets
GitHub secrets
database dump files
```

Use sanitized evidence:

```txt
PASS/FAIL
timestamps
git commit
schema_ok
database_revision
alembic_head
redacted resource IDs
duration
owner signoff
```

## Exports

Clinical document exports should be used only for legitimate clinical or clinic
operations purposes.

Before sharing exported documents:

```txt
confirm recipient
confirm case belongs to the clinic/user
confirm content was clinically reviewed
avoid sending through unapproved channels
```

## Incident triggers

Treat the following as incidents:

```txt
cross-user data visible
secret exposed
PHI/client data committed to repo
wrong client contacted
client contacted after opt-out
AI-generated advice sent without review
unexpected external message sent
EMR real import/write executed unexpectedly
```

## Retention / deletion

Retention and deletion rules must be confirmed by clinic policy and legal review.
Do not permanently delete clinical records solely based on informal requests
without review.

## Version

```txt
SOP version: Privacy / Data Handling SOP V1
Owner: security_owner
Review required before Final Go / No-Go V1
```
