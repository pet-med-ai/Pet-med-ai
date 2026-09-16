# PR26 browser and PostgreSQL acceptance

Application baseline: `b7bd032fb22627fa2f50e9757d0ad0220fb11d4c`.
This candidate adds an explicit doctor-history addendum input for a bound case.
The exact note participates in update preview and its fingerprint. Confirmation
appends the note to the full preserved history; it does not replace earlier text.
Changing or omitting the note invalidates confirmation. Identical complete note
blocks are not appended twice. This text deduplication is not record identity.
Other unsubmitted intake fields are explicitly excluded from bound updates.
The note does not rerun AI analysis. The existing six-field preview, AI review
requirement and server readback remain in effect.

The addendum joins the current-tab eight-hour draft. Verified readback clears only
the note that was actually saved; newer note input remains. Failed readback keeps
it and offers GET-only verification. Refresh recovery reloads current server state
and requires fresh AI review and confirmation. No schema, migration or production
setting changes are introduced.

On PostgreSQL, the bound-update route locks the consultation then the case before
recalculating its fingerprint and writing. The concurrency test holds a real
session lock and observes two HTTP writers waiting on PostgreSQL locks before
release: one succeeds, the other receives 409. Repreview preserves the first note
while appending the second. This covers this route, not all independent case-editor
writes; SQLite does not provide PostgreSQL row-lock semantics.

The exact application changes are backend/main.py, frontend/src/App.jsx,
frontend/src/components/ConsultUpdateReview.jsx and frontend/src/consultDraft.js.
The workflow pins those four blobs and four changed unit-test blobs, and rejects
other application changes from the baseline. Artifacts record actual tested HEAD.
The original 19 browser cases, 11 draft cases and 12 PostgreSQL checks remain.
Four new PostgreSQL checks cover addendum fingerprinting, exact text, deduplication
and forced writer contention. Nine new browser checks cover preview/no write,
edit invalidation, save/readback/clear, refresh/reaudit, stale server content,
lost response, failed GET, preserving newer input, and full-history detail refresh.
Named fault tests only drop actual responses or block GET; successful responses
come from the real app and database. No previous CI run is rerun.

The local Work browser rejected loopback navigation with ERR_BLOCKED_BY_CLIENT.
The local container lacks PostgreSQL and maps only UID 0, so package installation
failed. These are environment failures, not successful acceptance results.
The workflow runs on a separate ephemeral GitHub-hosted Ubuntu 24.04 VM with its
native PostgreSQL 16 binaries. It does not use Docker or a Render service.

The new cluster listens only on 127.0.0.1:55432 and uses database/user
`pmai_acceptance`. The bootstrap rejects other database URLs and existing schemas,
clears inherited application environment variables, disables dangerous feature
flags, and creates only a disposable synthetic schema from the candidate ORM.
No migration, restoration, production credential or production data is used.
This does not validate migration compatibility with any deployed schema.

`postgres_checks.py` verifies real auth and routes, fifteen first-save fields,
six update fields, original history bytes, stale confirmations, repeated saves,
two forced concurrent first-save races, and independent-process readback.
The two races add only a scheduling barrier after the real snapshot calculation;
auth, routes, ORM, PostgreSQL connections and transactions remain unchanged.

`browser_checks.cjs` uses real Chromium, the candidate's built React application,
real FastAPI HTTP responses, and the same synthetic PostgreSQL database. It covers
login, consultation and followup, AI review audit, review checkbox gating, changed
inputs invalidating review, first save, bound update, case detail and refresh.
It also tests a dropped response after a real save commit and a failed readback.
Only those named fault tests intercept traffic; they never fabricate successful
save responses. Browser traffic outside the two loopback app origins is blocked.

The original failing doctor-history visibility assertion remains in place. The
history display checks additionally compare DOM text to the full API history,
open the optional Q&A view, refresh the page, and emulate print CSS. Four cases
created through the real API cover plain text, doctor notes before/between/after
Q&A blocks with repeated numbering, CRLF/whitespace/Unicode, literal HTML, long
text wrapping, and empty history. Print checks verify Chromium print styles;
they do not certify physical printer output or PDF pagination.

The browser suite retains the original 14 scenarios and adds five workbench
checks: step access before a session/save exists, mobile intake layout with
retained input, return-to-edit with fresh confirmation, server-backed saved
content, and edits after saving that do not alter the saved view. The failed-readback scenario also navigates to intake and back before
retrying GET, without a second save POST or an incorrect unsaved-input warning.
Navigation can invalidate a confirmation without counting as a content edit;
content revision is tracked separately for the readback receipt.

Prior evidence: run 35077256108 on b7bd032 passed 12 PostgreSQL assertions,
19 original browser scenarios and 11 draft scenarios. These historical results
do not establish that doctor addenda pass. The new exact-commit workflow must
pass all 39 browser scenarios and 16 PostgreSQL assertions before acceptance.

Artifacts contain logs, JSON assertions and screenshots with synthetic data only.
A failed browser visibility assertion remains a failure even if PostgreSQL stored
the correct history; the test continues the other fault cases when possible.
Run attempts are bounded by the workflow's 15-minute job timeout. This workflow
does not rerun an old GitHub run or modify existing CI workflows.

References: https://playwright.dev/docs/ci and
https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md
