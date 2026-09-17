# PR26 browser and PostgreSQL acceptance

Application baseline: `d3c7273845d15d382e2c4697d2205eb61769d684`.
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
The editor does not yet persist unsaved input across refresh or navigation.

The exact application changes are backend/main.py,
frontend/src/pages/CaseEditorLite.jsx and
frontend/src/components/CaseEditReview.jsx. The workflow pins these three blobs,
the React test and runner, and the changed backend test file. It rejects other
application changes from the baseline and records actual tested HEAD in artifacts.

## Planned checks for this candidate

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

Required totals are 50 browser scenarios (19 original + 11 draft + 12 note + 8
editor), 25 PostgreSQL assertions (24 route/transaction + one independent-process
readback), 50 React tests, and 41 ASGI/SQLite tests (31 update/editor + 10 first save).
These are planned totals until the new exact-commit workflow executes successfully.

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
not guaranteed. The editor's input is not added to this workbench draft mechanism.

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

References: https://playwright.dev/docs/ci and
https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md
