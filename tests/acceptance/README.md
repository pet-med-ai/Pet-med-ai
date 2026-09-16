# PR26 browser and PostgreSQL acceptance

Application baseline: `d98608a79bd6b81cc76cd6a5b4c26d3ff8ec6944` (application
source identical to `d8dd219d9daaf00ba7f865990c3236dca165d280`). The candidate
changes only `frontend/src/pages/CaseDetail.jsx` in application source: complete
history is always visible as escaped, whitespace-preserving text; parsed Q&A is
an optional screen-only view. No history data or save behavior is changed.
The workflow rejects other changes to backend, frontend, knowledge-base or root
Python requirements relative to the baseline, and requires CaseDetail's exact
Git blob `f33aed9ec815323efbdc103357b0e9f890e4ff6b`. Artifacts record the actual
tested HEAD and its baseline. Existing PR remains draft; no merge or deployment.

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

Prior evidence: run 35062578627 on the baseline passed 12 PostgreSQL assertions
and 7 browser scenarios, but failed the original doctor-history visibility check.
Those historical results do not establish that this display fix passes. The new
candidate must pass its own exact-commit workflow before acceptance is reported.

Artifacts contain logs, JSON assertions and screenshots with synthetic data only.
A failed browser visibility assertion remains a failure even if PostgreSQL stored
the correct history; the test continues the other fault cases when possible.
Run attempts are bounded by the workflow's 15-minute job timeout. This workflow
does not rerun an old GitHub run or modify existing CI workflows.

References: https://playwright.dev/docs/ci and
https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md
