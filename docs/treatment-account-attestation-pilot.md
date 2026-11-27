# Treatment persistence and account-attestation pilot

This increment builds on PR #74 (`beff8743d6088b4da8d6ac3206f1d7c30790f2fc`).
It is opt-in and remains a draft delivery. It does not activate the historical
`0010` proposal or change the PR72 native-Safari acceptance candidate.

## Delivered behavior

A clinician can save a treatment draft, freeze the exact content and source
snapshot, review that revision, reauthenticate with the current account password,
and create an **account attestation**. The displayed label is
**已确认签署 · 院内账号确认**. This is not a certificate signature or a prescription
execution. No new AI, speech, device, messaging, charging, inventory, or certificate
provider call is made by this workflow.

Assistants can draft. Review/sign/revoke require an active veterinarian clinic
binding and an administrator-verified clinician profile. Organization administration
alone does not confer clinical permissions. Explicit cross-clinic `clinical.read`
grants remain read-only. Owner-private cases retain their existing restriction.
A `two_person` policy requires another eligible clinician to sign. A required
`certificate_signature` policy blocks this account-attestation implementation.

Every frozen revision retains exact UTF-8 canonical bytes, content hash, source
manifest, creator, version and time. No Unicode normalization, template expansion,
or whitespace trimming is applied to clinical text. A literal backslash-n remains
different from an actual newline. Clinician names are supplied by verified server
profiles, not free-text signature inputs.

Source snapshots cover the case (including attachments), mapped patient,
diagnostic reports, observations, imaging studies, consult sessions, followups,
and case-linked legacy audit entries. Case/child/patient changes advance the case
clinical epoch; the complete source snapshot is compared again at review/sign.
Organization signing-policy changes also invalidate the snapshot. This is the
coverage of this pilot; unported legacy routes and workers must remain stopped.
New AI/voice references and linked prescription/order IDs are rejected until their
scoped version stores are implemented.

## Data and invariants

| Table | Purpose and invariant |
| --- | --- |
| `clinician_profiles` | Explicitly verified org membership, display name, credential reference and status; no runtime write permission |
| `treatment_plans` | One plan per org/clinic/case, optimistic version, head revision and current signature |
| `treatment_drafts` | Mutable draft with version and amendment base; saving invalidates the prior frozen draft version |
| `treatment_revisions` | Immutable exact content, source manifest, canonical bytes/hash and source draft version |
| `treatment_reviews` | One immutable decision per frozen revision, bound clinician snapshot and content hash |
| `signing_challenges` | Five-minute password proof, bound to actor, session, scope, action, revision, hash and optional revoke target; single consumption |
| `treatment_signatures` | Immutable account attestation, approved review, challenge, audit event and command receipt |
| `treatment_events` | One terminal revoked/superseded event per signature; retains original signature |
| `clinical_audit_events` | Append-only clinical actions in the same domain transaction |
| `command_receipts` | Actor/scope/operation/key, request hash, lease and immutable terminal result |

Composite foreign keys prohibit cross-case/cross-clinic revision, review, signature,
challenge, event or audit bindings. Clinical history rejects UPDATE, DELETE and
TRUNCATE. RLS is enabled and forced on the nine scoped treatment tables. The new
`pmai_treatment_runtime` role has no legacy base clinical-table read/write privilege,
DDL, role memberships, or RLS bypass. Its treatment DML is constrained by RLS,
foreign keys and triggers. A NOLOGIN ACL role owns narrowly scoped source/context
functions with fixed search paths. Credentials for this role must never be used by
old workers.

The lock order is organization → membership → case → user/session validation locks
→ plan → command → challenge. Supported permission/profile/policy administration
also takes the organization lock. Signature, audit, optional supersession, active
pointer and committed receipt share one transaction. Unexpected failures roll back
all domain facts while preserving the separately reserved pending receipt.

Revocation retains the exact open draft and all signed history, clears its active
amendment target, and advances the draft version in that same transaction. Earlier
frozen approvals and challenges cannot sign it after revocation. A replacement
requires a new freeze, review and password confirmation; it never reactivates a
revoked signature.

Commands reserve a 60-second lease. They are never automatically re-executed with
a new key. Pending commands are queried or explicitly cancelled; late execution
must still find the same pending receipt and an unexpired lease. Cancellation
before request arrival creates a tombstone. Cancellation after commit returns the
committed result. A missing lookup returns `202 not_observed`, not “unsaved.” This
pilot has no autonomous lease-retry worker.

## Interfaces

All endpoints are under `/api/v2`. Let `C` be
`/organizations/{org_id}/clinics/{clinic_id}/cases/{case_id}`.

| Method and path | Input / result |
| --- | --- |
| `GET C/treatment` | Authorized aggregate, plan/draft ETags, source epoch and allowed actions |
| `PATCH C/treatment/draft` | Strict treatment-content-v1 payload; initial `If-None-Match: *`, then draft `If-Match` |
| `POST C/treatment/revisions` | Draft version + expected source epoch; freezes immutable content/source |
| `POST C/treatment/revisions/{id}/reviews` | approve/request_revision/reject plus reason; verified actor |
| `POST /auth/reauthenticate` | Current password + scope/revision/hash/action and optional revoke target; no password persistence |
| `POST C/treatment/revisions/{id}/signatures` | Review ID, exact content hash and session-bound challenge |
| `GET C/treatment/signatures/{id}` | Independent authorized readback of frozen bytes/content, audit and status |
| `POST C/treatment/amendments` | Current signature ID + reason; preserves old effective signature until replacement commits |
| `POST C/treatment/signatures/{id}/revocations` | Reason + new revoke-specific challenge; keeps historical content |
| `GET C/commands/{key}?operation=...` | Original actor's receipt; no retry or write |
| `POST C/commands/{key}/cancel` | Original operation/request hash + reason; cancel or return committed result |

Every business mutation needs a random 64-lowercase-hex `Idempotency-Key` and
`If-Match` (except the initial draft precondition). Operations are `draft.save`,
`revision.freeze`, `review`, `sign`, `amend`, `revoke`. The canonical request hash
contains actor, scope, operation, target, precondition and normalized business
payload; credentials are not included. Same key and request replays the receipt;
a changed request conflicts. The browser stores only the partitioned key,
operation and hash in sessionStorage, not raw clinical content or credentials.

Terminal command responses retain their actual HTTP status and a `state` field.
Read clients must handle `201 committed`, `202 pending/not_observed`, and terminal
4xx receipts; they must not interpret a retryable network failure as an unsaved
record. Principal errors are 401, missing/inaccessible scoped objects 404,
permission failures 403, stale source/challenge/policy conflicts 409, ETag mismatch
412, invalid content 422, and missing preconditions 428.

## Page behavior and remaining native acceptance

The page shows clinic/case, server clinician, frozen version, exact raw text and
source snapshot. Local editing clears acknowledgement. Saved draft changes block
review/signing of the older frozen version. Reauthentication occurs immediately
before sign/revoke; the password is cleared afterwards. A signature response is
followed by a separate GET before the UI reports confirmed success.

To revoke a signature, enter the reason first, then check the effective signed
version and its reason, enter the current account password and submit. Editing
the reason after checking it clears both the acknowledgement and the entered
password. Unchecking the acknowledgement also clears the password.

When you open or reread a frozen clinical revision, the workbench compares the
case and signing-policy versions in its source snapshot with the current record.
If either version has changed, you can still read the frozen text. Freeze the
draft again to review and sign against the updated source. An existing signature
keeps its recorded status. The server also checks the full snapshot when you
review or sign, including changes made since the last read.

Choosing **重新读取治疗记录** clears the previous independent signature readback
and withdraws the current signature card as soon as the read starts. The last
effective history entry shows **状态待核对** until the latest record arrives.
If the connection drops or the service is temporarily unavailable, new
treatment actions stay paused. Local draft text and any
pending command are retained. Use **重新读取治疗记录** to retry the read or
**查询原请求** to check a pending command. If another clinician has
revoked or replaced the signature between the independent readback and that
fetch, check **签署历史** for its updated status. The original command can be
confirmed even when the signature is no longer effective.
If the current signature and its history disagree, the page shows **状态待核对**
and pauses editing and signing. Reread the treatment record to check again.

In **签署历史**, each signed version lists its original signer and signing time.
For a revoked version, expand **查看版本 … 的作废记录** to see the account ID
that revoked that signature, the revocation time and the recorded reason.
These fields come from the matching revocation event in the loaded case record.
Opening or closing the details sends no request. An unavailable field displays
**未提供**.

For a superseded signature, expand **查看版本 … 的替代记录** to see the
revision that directly replaced it. For example, if version 2 replaced
version 1 and was later revoked, version 1 still shows **接替版本：版本 2**.
The page follows the replacement recorded for that signature in the loaded
case. If it cannot resolve the replacement version, it shows **未提供**.

If another clinician saves while you are editing, rereading the treatment record
keeps your local text and checks the version you started from. When the versions
differ, copy the changes you need, then choose **放弃本页修改并载入服务器草稿**.
Reapply your changes to the newly loaded draft before saving.

Use Enter for separate diagnoses or goals. Drafts with coded diagnoses or
stored multiline items display those lists one item per box. Moving a diagnosis
keeps its code. Renaming it clears the old code when the draft is saved.

When checking a frozen revision, the currently signed plan or an independent
signature readback, read each numbered diagnosis or treatment goal as one
stored item. A line break inside an item belongs to that item. Each diagnosis
shows its recorded coding system and code separately when present, including
when another diagnosis has the same name. Select a single name, code or goal
to copy its exact text. Copying a whole list uses the browser's plain-text
formatting for numbering and empty items.

If the password check for signing or revoking returns `REAUTHENTICATION_FAILED`
with HTTP 401, the case stays open. The password and acknowledgements are cleared.
Check the intended action again, enter the current account password, and submit.
The failed password check creates no signature or revocation request.

When the session expires, raw unsaved text remains copyable and read-only.
For a diagnosis or goal list edited in a single text box, select the whole field
to copy its lines together, including any trailing blank lines.
The page clears the previous acknowledgements and credentials. Copy any text you
need before leaving, then sign in to the same account and reopen the case. If
a command was already sent, query its original request. A different account cannot recover the
previous account's partition. Case/clinic/account navigation aborts outstanding
work and ignores late responses. “Stop waiting” retains the original request key;
it does not claim the request was cancelled or unsaved.

If a save, review or signing response is incomplete or identifies another request,
the page keeps the original request pending. Choose **查询原请求** to read its
status using the same account and case. A lookup can return `not_observed`
before a command arrives. The original key stays available for a later lookup
or explicit cancellation. Signing and revocation also require an independent
read of the matching signature before the page confirms the result.

To reopen a known case, select its clinic, enter the case number and choose
**按号查看**. The case can be on any list page. If both views are available, use
the clinical view for treatment or the demographics view for basic details.

While a treatment draft has unsaved edits, opening another case from the list
or by number asks whether to discard those edits once the target case is read.
Cancel to stay on the original case, or confirm to open the other case. Changing
the clinic or view, reloading the case list, and paging also ask before closing
an edited draft. If you select the current row again, the page checks access.
When the server denies access to the current treatment record, the page clears
its treatment text. To keep text through logout or a browser reload, save the
draft first, or copy it if the session has expired.

Native Mac/Safari acceptance is still required for this **new** increment:

1. Same-clinic veterinarian versus assistant/admin/frontdesk and cross-clinic read grant.
2. Save → freeze → review → password confirmation → independent signature readback.
3. Exact café/emoji/braces, true newlines and literal backslash-n.
4. A changed draft or diagnostic source invalidates the earlier frozen revision.
5. 401 during work preserves copyable raw text and disables old confirmation.
6. Stop waiting/lost response → same-account login → original-key lookup without duplicate signing.
7. Two-person policy, amendment replacement, revocation history and a newly
   reviewed signature after revocation, preserving any open draft.
8. Different account/case/clinic and late responses cannot disclose previous content.

Existing S6–S8A evidence does not substitute for these new native-browser checks.

## Migration and controlled pilot setup

No production database is modified by the patch or its tests. The migration is
`mc01_scope_expand → mc02_treatment_store`, PostgreSQL-only, additive and forward-only.
There is no startup migration or automatic clinician provisioning.

Before applying to any clinic-owned target: verify a restorable backup on a
disposable target, finish explicit org/clinic mappings, stop old web/worker
processes, and use a separately selected administrator connection. Do not stamp a
database to bypass a failed migration. Rollback after clinical writes means restore
or a reviewed forward fix; dropping signature history is not supported.

Administrator commands (substitute reviewed IDs and a fresh request key):

```sh
# DATABASE_URL must refer to the explicitly selected PostgreSQL migration target.
cd backend
python -m alembic -c alembic.ini upgrade mc02_treatment_store
cd ..

# The read policy must already have been installed at mc01.
# MULTICLINIC_ADMIN_DATABASE_URL is separate from the runtime credential.
python scripts/treatment_store_admin.py install-policy
python scripts/treatment_store_admin.py clinician --org ORG_UUID --actor ADMIN_USER_ID --membership MEMBER_UUID --name 'Verified clinician' --credential VERIFIED_REFERENCE --key REQUEST_KEY --reason 'Verified offline'
python scripts/treatment_store_admin.py policy --org ORG_UUID --actor ADMIN_USER_ID --review-policy two_person --assurance account_attestation --key REQUEST_KEY --reason 'Approved clinic policy'
```

Clinician/policy commands are dry runs until `--apply` is explicitly added. Their
writes are audited and idempotent. A clinician profile does not grant a role.
Provision the runtime login password through the database administrator's secret
process; no credential is embedded in scripts.

Optional historical text import, one explicitly mapped case per transaction:

```sh
python scripts/treatment_store_admin.py import-legacy --org ORG_UUID --clinic CLINIC_UUID --case-id CASE_ID --actor ADMIN_USER_ID --key REQUEST_KEY --reason 'Reviewed unsigned historical import'
# Review the returned source SHA. Apply with the same arguments plus:
# --expected-sha256 RETURNED_SHA --apply
```

Import preserves original analysis/treatment text, creates `legacy_import` unsigned
revision + draft + access audit, and creates **zero signatures/reviews**. Repeat
with the same key resumes safely. Changed source checksum or an existing treatment
plan blocks overwriting. An imported revision cannot be reviewed/signed; the doctor
must complete and freeze a new clinical revision.

Only after target checks, select `PMAI_MULTICLINIC_MODE=treatment_pilot`,
`MULTICLINIC_DATABASE_URL` for `pmai_treatment_runtime` and the existing private
`MULTICLINIC_TOKEN_SECRET`. Build the frontend with both
`VITE_MULTICLINIC_READ_PILOT=1` and `VITE_TREATMENT_PILOT=1`, plus the intended
`VITE_API_BASE`/CORS configuration. Default `off` and existing read-only pilot
behavior remain available. This document is not evidence of deployment.

## Reproducible validation

In a Python environment with `backend/requirements.txt` installed, the optional offline backend configuration check is `python scripts/check_pilot_config.py treatment_pilot`. Supply only the mode on the command line. It checks the configured pilot, PostgreSQL URL user and token secret length without connecting. Exit 0 means those three settings match, 1 invalid configuration, 2 invalid invocation or unavailable backend dependencies, and 3 an indeterminate role. Database privileges, schema and service availability require separate verification.

```sh
PMAI_POSTGRES_TEST_PATTERN=test_treatment_postgres.py python scripts/run_multiclinic_tests.py
# Requires PMAI_TEST_POSTGRES_ADMIN_URL for a disposable test server;
# alternatively supply --postgres-bin /path/to/postgresql/bin.
node frontend/tests/run-consult-update-review.mjs treatment-workspace clinic-read-pilot
```

The PostgreSQL suite creates a randomly named database, runs real migrations and
policies, exercises the restricted runtime role, and drops that database. It covers
atomic rollback, duplicate concurrency, original-key recovery/cancel fencing,
source/draft changes, two-person review, cross-scope access, unsigned legacy import,
and append-only history. UI tests exercise auth/navigation/late-result/retention
boundaries. CI also retains the existing clinic, legacy browser and frozen PR72
checks. Native Safari and live certificate/provider tests are not automated here.

### Verifying the restore evidence offline

Open the treatment artifact for the candidate commit and check that
`treatment-restore/drill-receipt.json` names the same commit and tree.
The `pre_migration_restore` and `post_migration_restore` entries name the
source and restored fingerprints under `fingerprints`. From the extracted
`treatment-restore` directory, run:

```sh
sha256sum *fingerprint.json
cmp pre-source-fingerprint.json pre-restored-fingerprint.json
cmp source-fingerprint.json restored-fingerprint.json
```

Match each file's SHA-256 to its entry in the receipt. Each `cmp` exits 0
for a byte-for-byte match. For a completed drill, also check the overall
`status` and `cleanup`. A failed drill may retain just the measurements
completed before the error. If a phase has only its source measurement, the
restore comparison is pending. Earlier artifacts may report the pre-migration
match in the receipt without including the two files for independent comparison.

### Rebuilding the treatment source kit

Check out the exact PR head in a clean working tree. Using the same Python and
zlib versions as the reference build, write the archive outside the checkout:

```sh
python scripts/package_treatment_acceptance.py ../rebuilt-treatment-kit.tar.gz
```

The command prints the commit, tree, file count and SHA-256 of the finished
archive. For a CI comparison, extract `treatment-kit.tar.gz` from the GitHub
Actions artifact for that commit and compare it with the rebuilt file using
`cmp`. A zero exit status confirms byte-for-byte equality. The manifest inside
the kit also records the SHA-256 of each included source file.
