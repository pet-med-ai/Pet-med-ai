# PR26 browser and PostgreSQL acceptance

Application under test: `d8dd219d9daaf00ba7f865990c3236dca165d280`.
The workflow rejects any change to backend, frontend, knowledge-base or the root
Python requirements relative to that commit. Only these acceptance files and the
new workflow are added. Existing PR remains draft; no merge or deployment.

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

Artifacts contain logs, JSON assertions and screenshots with synthetic data only.
A failed browser visibility assertion remains a failure even if PostgreSQL stored
the correct history; the test continues the other fault cases when possible.
Run attempts are bounded by the workflow's 15-minute job timeout. This workflow
does not rerun an old GitHub run or modify existing CI workflows.

References: https://playwright.dev/docs/ci and
https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md
