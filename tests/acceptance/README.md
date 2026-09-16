# PR26 browser and PostgreSQL acceptance

Application baseline: `f503eba7ad084e4555ef32ee2eef5cbb819ae629`.
This candidate connects the selected three-step workbench to the real React app:
intake, review before save, then server readback. Hidden step panels remain mounted
so navigation retains inputs and unresolved save state. Returning to intake
invalidates the old confirmation. Only verified readback enables the third step;
its content comes from the server response, with a warning for later input edits.

Five application files are changed: App.jsx, ConsultSaveReview.jsx,
ConsultUpdateReview.jsx, and new ConsultWorkbench.jsx / ConsultWorkbench.css.
Two existing React test files also add a regression for step navigation after
failed readback. The workflow binds all seven exact Git blobs and rejects other backend,
frontend, knowledge-base or root Python dependency change from the baseline.
Artifacts record the actual tested HEAD. APIs, database logic and the previous
complete-history display fix are unchanged. Existing PR remains draft; no merge
or deployment. This is three-step interaction integration, not completion of all
prototype features, standalone case editing or persistent draft recovery.

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

Prior evidence: run 35066070839 on f503eba7 passed 12 PostgreSQL assertions and
14 browser scenarios. Those historical results do not establish that this new
workbench passes. Its own exact-commit workflow must pass before acceptance is
reported.

Artifacts contain logs, JSON assertions and screenshots with synthetic data only.
A failed browser visibility assertion remains a failure even if PostgreSQL stored
the correct history; the test continues the other fault cases when possible.
Run attempts are bounded by the workflow's 15-minute job timeout. This workflow
does not rerun an old GitHub run or modify existing CI workflows.

References: https://playwright.dev/docs/ci and
https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md
