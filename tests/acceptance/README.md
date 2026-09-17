# Consultation and case acceptance

## Current candidate: manual creation review and readback

Baseline: merged main `5f937c122e2f6c2d6efa246aa895927e17c26476`.
PR #26 is already merged. This is a separate local candidate; no new remote PR,
commit, CI run, deployment or production data operation has occurred for it.

The homepage manual-create entry carries its current fields to the independent
new-case editor. Both entries now use one fifteen-field preview, explicit
confirmation, one creation request, and an independent authenticated GET of the
returned case ID. Changing input or account invalidates the confirmation. The
new-case API now accepts analysis, treatment and prognosis, matching the existing
ORM columns and editor fields that it previously silently ignored. No model,
schema, migration or deployment configuration changes are needed by this patch.

Nonempty clinical strings retain their original whitespace. Empty optional
strings become null; required name and chief complaint must contain text. No
consultation, AI analysis or audit is created by this manual flow. It is a local
UI preview over the existing authenticated API, not a server-side preview-token
requirement, diagnosis signature or global idempotency contract.

Before POST, the current tab stores an account-bound receipt containing the
fifteen-field payload and, once available, the returned case ID. It contains no
credential or confirmation. An unknown POST result blocks another creation,
including after refresh. Known-ID verification retries GET only and compares all
fifteen fields; mismatches do not report success. The request interceptor also
checks the expected account at dispatch. Unrelated API callers remain unchanged.

The receipt is plaintext sessionStorage for this tab, separate from the existing
eight-hour workbench/editor drafts. It has no expiry that could silently unlock
an unresolved create; logout, switching accounts, or explicitly starting another
case after successful readback clears it. Same-account login preserves it, including after expiry and a page refresh.
Closing a tab, browser storage loss and cross-tab requests are outside this
protection. A response lost before receiving the ID needs manual case-list
verification; the UI cannot automatically identify the created row. This patch
does not add standalone unsaved-new-case draft recovery or server idempotency.

Local execution: React/interceptor regression suite 87/87 (18 new), authenticated
ASGI/SQLite manual-create tests 5/5, and frontend production build passed. These
are local results and do not certify native PostgreSQL or real Chromium.

Prepared new acceptance coverage:

- Seven Chromium scenarios in `manual_create_checks.cjs`: read-only preview and
  input invalidation; double-click/15-field readback; receipt recovery after
  refresh; case-detail refresh; homepage handoff; failed GET with refresh and
  GET-only retry; and a dropped actual POST response that blocks recreation.
- One native PostgreSQL assertion verifies all fifteen creation fields through
  an independent connection, ownership isolation and no consultation creation.
- Retained suites yield configured totals of 74 Chromium scenarios (67 + 7)
  and 28 PostgreSQL checks (27 + 1). These new totals have NOT been executed.

The workflow records exact tested HEAD and main baseline, pins every changed
application/test blob, and rejects other application/test changes. It retains
native PostgreSQL on loopback, synthetic JWT accounts, Chromium restricted to
loopback, and cleanup. No Docker or production credentials are used. `PR26` in
the fixture environment remains a legacy isolation sentinel, not a claim that
this candidate is part of the merged PR. A newly authorized commit must pass its
own CI; no previous passing workflow run is rerun or reused as new evidence.

The following sections are historical PR #26 development records. Their candidate
wording and recorded results apply to those commits only.

# PR26 browser and PostgreSQL acceptance

Application baseline for the editor-draft candidate: `ce52b3ec20a2a4ef0c065131c997e19bc1bace1f`.
This candidate extends the existing-case editor reached from Case Detail. Editing
an existing case now uses read state -> changed-field preview -> explicit
confirmation -> save -> independent server readback. The manual new-case flow is
outside this change; no model, migration or deployment setting is changed.

## Existing-case editor candidate

Only form fields actually changed from the loaded form are sent. Unchanged raw
history, chief complaint, examination, nullable fields and whitespace retain their
stored values. Intentionally editing history remains a full-field replacement,
shown before confirmation; this is different from appending a consultation note.
A clear-to-empty edit is shown explicitly. The server rejects empty patches,
unknown fields, non-string values and blank required patient name/chief complaint.

The edit-state token covers all 15 editable fields, case/owner identity and update
time. Preview rejects a stale opened case; confirmation rejects changed payloads
and stale previews. Confirmation locks the case row before checking and writing.
Authentication, ownership and soft-deleted visibility checks remain required.
The dedicated preview/confirm routes leave legacy PUT and manual creation intact;
this does not make all legacy writers participate in optimistic version checks.

Conflict recovery reads the latest case, keeps the doctor's changed fields, and
adopts latest server values for untouched fields. It requires another comparison
and confirmation. If both doctors changed the same field, the operator must review
the difference; there is no automatic same-field merge. On missing save responses,
the UI reads all 15 fields before claiming matching saved content. Failed or
mismatching readback keeps input and offers GET-only verification or explicit
reload/repreview. Saving and unresolved readback disable form edits. Later edits
are marked unsaved while the previous verified readback remains separately shown.
The editor-draft candidate below adds explicit recovery of changed fields after
refresh or same-tab navigation; it does not restore a save confirmation.

The editor and login-race fixes are already present in this baseline. This
candidate changes App.jsx, CaseEditorLite.jsx, the new caseEditDraft.js module
and the existing case-edit-review.test.jsx regression suite. The workflow pins
these blobs, retains existing application/test pins, rejects other application
changes from this baseline, and records actual tested HEAD in artifacts.

## Editor-draft candidate (local verification only)

Existing-case edits cache only changed string fields in current-tab
sessionStorage, separately for each case and account, for up to eight hours.
They contain no authentication token, case/preview token, confirmation or saved
receipt. Login/logout clears editor drafts; another tab changing the login
identity clears this tab's drafts and reloads it. This is temporary plaintext
browser storage, not a server draft, encrypted storage or a cross-device backup.
Closing a tab does not guarantee later recovery. Manual new-case drafts are
outside this candidate.

After refresh or returning to the editor, the user explicitly restores or discards
the offer before editing. Restore performs only an authenticated GET of that case,
then applies the cached changed fields to the freshly read form. Untouched fields
use the latest server values. Old preview and confirmation state are not restored.
The user must compare and confirm again; simultaneous changes to the same field
are not automatically merged. In particular, editing history remains an explicit
full-field replacement requiring review, not an append-only note.

If the server already contains every cached changed value, recovery clears the
cache without another POST and reports only that the values match. It does not
claim which writer saved them. An inaccessible case or failed/wrong-case GET
retains the offer without enabling writes. Successful save and complete readback
clear that case's draft; later input starts a new draft. Storage failure keeps
visible input, removes an older copy when possible and warns about loss. Dirty
input also installs the browser's standard unload warning; the browser controls
whether that prompt appears.

Fifteen additional local regressions cover exact/empty text, account/case
partitioning, expiry/corruption, quota failure, discard, current-state recovery,
failed reads, already-committed saves, save/clear/later edits, identity changes,
unload warning, unmounts and SPA case changes. Thirteen new real-browser scenarios
are prepared in editor_draft_checks.cjs. They exercise the real application and
native PostgreSQL fixture with synthetic data; fault cases only block GET or
browser storage. These new browser scenarios have not yet run.

## Login-race follow-up

A real Chromium run observed login HTTP 200 followed by an older anonymous case
list HTTP 401 and a logged-out reload. The old Axios interceptor unconditionally
removed the stored token on non-authentication 401 responses. The local regression
reproduced both late anonymous and late old-token responses clearing a newer token.

The fix only clears the stored token when the failed request carried that current
token. It still rejects the HTTP error, preserves expiry handling for the current
credential, and leaves authentication failures to their caller. It neither retries
writes nor fabricates a successful login. The four regression tests exercise the
actual Axios interceptors with controlled response ordering; these are local unit
tests, not an additional real-browser acceptance claim.

## Retained editor checks

The existing 42 browser scenarios and 20 PostgreSQL assertions remain. Eight added
browser scenarios cover changed-field preview without writes, input invalidation,
exact save/readback, stale-open recovery, stale confirmation, a dropped response,
failed GET with GET-only retry, and case-detail refresh. No successful response is
fabricated. Twelve new React tests cover the component and actual editor wiring.
Nine new ASGI/SQLite route tests cover all 15 fields, tokens, invalid inputs,
ownership, hidden deleted fixtures, repeats, and cross-flow stale confirmations.

Five added PostgreSQL checks exercise the editor's real authenticated routes,
exact patch preservation, replay rejection, stale versions and forced concurrency
between an editor and a consultation history-only update. The concurrency fixture
holds the actual case row, observes both HTTP writers waiting on PostgreSQL locks,
then releases it: one must succeed and one must receive 409. Repreviewing the loser
must preserve both changes. SQLite does not certify these row-lock semantics.

Candidate target totals are 63 browser scenarios (19 original + 11 workbench
draft + 12 note + 8 editor + 13 editor draft), 25 PostgreSQL assertions
(24 route/transaction + one independent-process readback), 69 React/interceptor
tests (54 existing + 15 editor-draft regressions), and 41 ASGI/SQLite tests
(31 update/editor + 10 first save). Local React 69/69 and frontend build passed.
The candidate exact-commit CI/browser/database totals remain pending authorization
to append these eight files to the existing PR; no old passed run was rerun.

## Retained consultation and history coverage

First save previews all 15 fields, binds the consultation once, and resolves a
lost response via session binding rather than duplicate POST. Existing tests
force two simultaneous saves with the same owner and competing owners. These
first-save races use only a scheduling barrier after the real snapshot; auth,
routes, PostgreSQL connections and transactions are unchanged.

Bound updates retain original history and append distinct consultation/note text.
Nonblank doctor notes default to history-only; explicit consultation sync updates
summary and AI fields while preserving saved chief complaint and examination.
Notes and modes participate in confirmation. New notes or draft recovery reset
the UI to history-only. API callers omitting mode retain sync compatibility.
Concurrent note writes lock the consultation then the case. Identical complete
text blocks are deduplicated, which is not an independent note identity or signing.

The three-step workbench retains inputs across navigation, displays actual server
readback, and distinguishes unsaved input. Current-tab eight-hour draft recovery
is account-scoped, requires fresh server state/review, and preserves newer input.
It is not a server draft or encrypted storage; cross-device/closed-tab recovery is
not guaranteed. Editor drafts use separate entries and do not overwrite the
workbench draft.

Case Detail shows complete history text, including notes around repeated Q&A
blocks, Unicode, CRLF, whitespace, literal HTML and long lines. Optional Q&A cards
do not replace the original. The original failing doctor-history visibility
assertion is retained. Print checks cover Chromium print styles only, not physical
printer output or PDF pagination.

## Isolation and evidence

The workflow runs on an ephemeral GitHub-hosted Ubuntu 24.04 VM using native
PostgreSQL 16 and real Chromium, without Docker or a Render service. The local
Work browser previously rejected loopback navigation; the local runtime lacks
application/PostgreSQL dependencies. Local component/build checks are not a claim
of real browser/database acceptance.

The fresh cluster listens only on 127.0.0.1:55432 and uses database/user
`pmai_acceptance`. Bootstrap rejects remote URLs and existing schemas, clears
inherited application environment, disables dangerous feature flags, and creates
only disposable synthetic ORM tables. No production credentials/data, migration,
restore or deployed-schema compatibility check is used. Browser traffic is limited
to the loopback UI/API origins. Named faults only drop real responses or block GET.
All services and the database are stopped at the end, including failed runs.

Prior evidence: run 35116540243 on d3c7273 passed 42 browser scenarios and 20
PostgreSQL assertions. React 38/38 and ASGI/SQLite 32/32 passed in run 35116540207.
These historical results do not validate this new editor candidate. New commits
trigger new runs; old passed runs are not rerun. Artifacts record screenshots,
JSON assertions, logs and exact commit/blob binding, with synthetic data only.

## Recorded editor attempts

- Commit `993450489e82d6fc0a671805abb0c6d576989c49`,
  [run 35166092304](https://github.com/pet-med-ai/Pet-med-ai/actions/runs/35166092304):
  PostgreSQL 25/25 and the existing 42 browser scenarios passed. The editor suite
  failed at its initial input locator before completing any editor scenario.
- Commit `378afb3c6a07ecdadb44b78fe1936c1b18a05ac7` corrects only that selector.
  [Run 35166435168](https://github.com/pet-med-ai/Pet-med-ai/actions/runs/35166435168)
  passed PostgreSQL 25/25 and 16 original browser scenarios, then failed during
  login with the token race above. Later draft, addendum and editor steps were
  skipped. The locator correction is not yet certified by completed editor tests.
- On `378afb3`,
  [run 35166435236](https://github.com/pet-med-ai/Pet-med-ai/actions/runs/35166435236)
  passed React 50/50 and ASGI/SQLite 41/41;
  [run 35166435241](https://github.com/pet-med-ai/Pet-med-ai/actions/runs/35166435241)
  passed history preservation 12/12;
  [run 35166435174](https://github.com/pet-med-ai/Pet-med-ai/actions/runs/35166435174)
  passed backend static checks and frontend build.

Both browser runs failed overall and remain recorded as failures. No failed run
was retried merely to obtain a pass, and no previously passed run was rerun. The
login follow-up locally failed two of 54 tests before the fix and passed 54/54
after it. The authorized login fix was subsequently appended as `ce52b3e`.
[Acceptance run 35176756963](https://github.com/pet-med-ai/Pet-med-ai/actions/runs/35176756963)
passed 50/50 browser scenarios and 25/25 PostgreSQL assertions on that exact commit,
attempt 1. Its artifact digest is
`1c6b731f2746e01f32450b717eb3a122945cf1cc9ec27f3ae931aa8c5d8ae84c`.
[Run 35176756899](https://github.com/pet-med-ai/Pet-med-ai/actions/runs/35176756899)
passed 54/54 React tests and 41/41 ASGI tests; CI Gate 35176756902 and history
preservation 35176756953 also passed. These baseline results do not validate the
new editor-draft candidate above.

References: https://playwright.dev/docs/ci and
https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md

## Deleted-case consultation update boundary

Baseline: `50981642f18fb710e1aa03d5cd92caa57de3aa4e`. Its existing
[acceptance run 35180208450](https://github.com/pet-med-ai/Pet-med-ai/actions/runs/35180208450)
passed 63 browser scenarios and 25 PostgreSQL checks. Those historical results
do not validate this follow-up fix.

Both `preview-update-case` and `update-case` now use the existing owner and
active-case lookup. The write route retains its PostgreSQL case row lock.
Deleted cases return 404 before preview generation or mutation, including
legacy updates without a request body. No schema, migration, deletion/restore
implementation, frontend application, or production configuration is changed.

The two new ASGI tests cover deletion before preview and deletion between
preview and confirmation, in `history_only` and `consult_sync` modes. They
compare every column of the case and consultation rows through a fresh database
connection after each rejected request. The no-body legacy path is also covered.
On the unchanged baseline both new tests failed: deleted-case previews and a
legacy update returned 200; confirmation after deletion returned 409 instead of
404. After the fix the local ASGI/SQLite suite passed 33/33. SQLite does not
substitute for PostgreSQL or browser acceptance.

`postgres_checks.py` adds the same two checks using dedicated synthetic rows,
real DELETE/authentication/routes, and independent SQL connections to verify no
column changed after rejection. It leaves the restart-readback case intact.
The configured total is 27 PostgreSQL checks (26 plus independent process readback).

`deleted_case_checks.cjs` adds four real Chromium scenarios: each deletion timing
in both update modes. They require real 404 responses, retained unsaved notes,
no saved/readback success state and no automatic retry of a write. These run on
the same disposable native PostgreSQL instance. They create and soft-delete only
new synthetic cases, never restore them, and fabricate no successful responses.
The configured browser total is 67 (existing 63 plus these 4).

New browser/PostgreSQL results are established only by a successful new-commit
workflow run and its bound artifacts; configured counts are not pass claims.
The workflow checks that `backend/main.py` is the only application file changed
from this baseline and binds the new tests by exact Git blob IDs. No prior run is
rerun, no Docker is used, and no Render/production operation is performed.

First attempt: commit `dd5e30540bfe2b15e2712c27b1363bebf80f938a`,
[run 35182711208](https://github.com/pet-med-ai/Pet-med-ai/actions/runs/35182711208),
failed overall. PostgreSQL 27/27 and the existing 63 browser scenarios passed;
the new browser suite stopped before its first deletion scenario because an
exact accessible-name locator no longer matched the populated chief-complaint
field. The follow-up locates the textarea through its visible label and asserts
the exact restored session text. Application code and all deletion assertions
remain unchanged. This failed run is retained and is not counted as browser
acceptance for the new scenarios.
