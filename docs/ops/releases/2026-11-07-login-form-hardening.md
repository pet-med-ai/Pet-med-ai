# Login form parser hardening (security-only candidate)

Status: local validation completed for draft-PR review. Publication and the first
automatic CI run are authorized for this nine-file batch. Merge, deployment,
migrations and production-data operations remain out of scope. CI outcomes are
reported on the draft PR for its exact head commit, not asserted in this file.

## Scope and evidence

The production source baseline is `793894523be602bd8da265f8f7e8e63e417027a7`.
The existing draft PR #72 baseline is `58cdf136093d129fca71fb246a88d7cc896f1c91`.
Their original `backend/auth_jwt.py` and `backend/requirements.txt` are identical.
The production installed packages, ingress body limits and rate limits have not
been established. No production exploit test or attack evidence is claimed.

The source's FastAPI 0.110.0 requires Starlette >=0.36.3,<0.37.0. The login route
uses OAuth2PasswordRequestForm, reaching both URL-encoded and multipart parsing.
The browser uses multipart FormData, so rejecting all multipart would break login.

Upstream advisories:
- https://github.com/Kludex/starlette/security/advisories/GHSA-82w8-qh3p-5jfq
- https://github.com/Kludex/starlette/security/advisories/GHSA-f96h-pmfr-66vw

## Candidate changes

- Pin FastAPI 0.137.2 and Starlette 1.3.1 as a compatible framework pair; do not
  override the old FastAPI dependency constraint.
- Pin Pydantic 2.14.2, satisfying FastAPI's >=2.9 requirement while avoiding the
  published Pydantic advisories fixed in 2.14.0 and 2.14.2. Pin python-multipart
  0.0.33 for the tested parser. This is not a whole-dependency security audit.
- Apply a route wrapper before FastAPI parses the OAuth form. Read at most
  16 KiB of actual body bytes, with a 5-second read deadline. Content-Length is
  checked but not trusted to bound the stream. Reject encoded bodies, malformed
  or duplicate length headers, and mismatched completed body lengths.
- Preparse with max_files=0, max_fields=6 and max_part_size=4096, caching the form
  on a bounded replacement Request used by the original login handler. URL-encoded
  field size includes its encoded name and value; multipart size limits values,
  while names and part headers remain within the total body cap.
- Keep ordinary multipart and URL-encoded login, JWT response, signup, CORS,
  redirects and OAuth OpenAPI schema. Other request bodies are unchanged.
- Add isolated regression tests and a command in the existing PR test workflow.
- Update only three locked frontend packages needed for the existing audit gate:
  Vite 6.4.3 -> 6.4.5, follow-redirects 1.16.0 -> 1.16.2 and source-map-js
  1.2.1 -> 1.2.2. No frontend application code or other locked package changes.
- Preserve the old browser/PostgreSQL workflow's exact five-file driver-repair
  scope against its immutable main merge, then require exactly these nine
  security-batch files against main `7938945`. Keep all audit, regression,
  browser/PostgreSQL and evidence verification steps enabled.

## Local validation

Run each test file in a separate process because existing fixtures install
process-wide environment and network/database isolation guards:

```
python -m pip install -r requirements.txt -r backend/requirements.txt
python -m pip check
python tests/test_login_form_limits.py
```

The 29 new tests cover both successful login encodings, JWT protected reads,
Unicode/reserved characters, incorrect credentials, missing fields, OAuth fields,
16 KiB exact/over boundaries, missing/false/invalid Content-Length, chunks, excessive
fields and field sizes, multipart files/malformed input, timeout/disconnect,
CORS/redirect/OpenAPI and other-route compatibility. Rejected form tests verify
that password verification and SQL execution have not started.

The main-based backend suite passes 123 tests in 7 separate files on Python
3.11.17, including all 29 new login tests. The isolated Node 20.20.2 frontend
passes 231 tests, production build and deferred-route budget checks. Its updated
lockfile reports zero vulnerabilities at all npm audit levels at validation time.
The complete static gate also passes. These are local checks, not a claim that
remote Chromium/PostgreSQL acceptance has already passed.

Additional evidence is packaged separately: complete backend-file regression
results, resolved package versions, small synthetic baseline probes, source
patches and hashes. No external service, production database, migration, clinical
patient data, live login credential or large resource-exhaustion payload is used.

## Release boundary and remaining work

The recommended release path is a small security-only branch based on current
main, rather than deploying the unrelated pending PR #72 features. The same
patch can also be carried forward into the existing candidate. Only this
main-based, nine-file draft PR and its first automatic CI are authorized. Do not
modify PR #72, rerun failed CI blindly, merge, deploy or operate production data.

Before any later separately authorized rollout: recheck main and live commit,
validate the installed dependency versions and current ingress limits, review
first-run CI for the exact new commit (including applicable browser/PostgreSQL
acceptance), and agree deployment/rollback scope. Do not combine this change
with migrations, production data modifications or the older certificate issue.

This fixes the identified parser dependency exposure in the proposed stack and
bounds login parser work. It is not a general DoS guarantee. Ingress read timeouts,
connection/concurrency limits and distributed login rate limiting still need a
separate configuration review. No guessed forwarded IP is used for rate limiting.

Dependency metadata: https://github.com/fastapi/fastapi/blob/0.137.2/pyproject.toml
Pydantic advisory context:
https://github.com/pydantic/pydantic/security/advisories/GHSA-955g-x97g-8mcp
https://github.com/pydantic/pydantic/security/advisories/GHSA-qpmf-fgh3-ff25
