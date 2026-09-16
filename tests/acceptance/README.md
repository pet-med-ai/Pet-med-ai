# PR26 browser and PostgreSQL acceptance

Application baseline: `2ef8bd882349f80e7329882babf14e6b0d50ac11`.
This candidate adds current-tab draft recovery to the existing three-step React
workbench. It stores doctor input, pending answers and the session identifier in
sessionStorage, partitioned by login identity, with an eight-hour freshness limit.
Recovery is explicit. Linked sessions must first be read from the authenticated
server; their current case binding determines whether first-save or update applies.
A local draft cannot restore an AI audit receipt, preview confirmation or successful
save state. Changed server questions quarantine old pending answers as readable
notes rather than submitting them to the wrong question. Failed storage warns while
preserving current React input. Logout clears the cache. Cross-device and closed-tab
recovery are not guaranteed; this is not server-side draft storage or encryption.

The exact application changes are App.jsx, consultDraft.js and useConsultDraft.js;
React test changes are consult-draft.test.jsx and run-consult-update-review.mjs.
The workflow binds these five Git blobs and rejects all other backend, frontend,
knowledge-base or root dependency changes from the baseline. Artifacts record the
actual tested HEAD. No API, database, migration or Render configuration is changed.
Verified first-save clears the draft if no newer input exists. Bound updates keep
it because that API does not save every unsubmitted field from the intake form.

`draft_checks.cjs` adds eleven real-browser checks: exact form restoration without
writes, old confirmations invalidated, pending answer restoration, changed-question
quarantine, failed session GET retaining the draft, refresh after a committed save
resolving the existing binding without a second save, verified save clearing cache,
later unsaved edits preserving saved data, logout/account isolation, corrupt-cache
rejection, and quota-failure warnings. Only the named fault checks block a GET or
sessionStorage write. Successful responses come from the real FastAPI app and
PostgreSQL; no synthetic success response is injected.

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

Prior evidence: run 35068137028 on 2ef8bd88 passed 12 PostgreSQL assertions and
19 browser scenarios for the three-step workbench. Those historical results do
not establish that draft recovery passes. The new exact-commit workflow must
pass its original 19 browser scenarios, eleven draft scenarios and PostgreSQL
checks before acceptance is reported.

Artifacts contain logs, JSON assertions and screenshots with synthetic data only.
A failed browser visibility assertion remains a failure even if PostgreSQL stored
the correct history; the test continues the other fault cases when possible.
Run attempts are bounded by the workflow's 15-minute job timeout. This workflow
does not rerun an old GitHub run or modify existing CI workflows.

References: https://playwright.dev/docs/ci and
https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md
