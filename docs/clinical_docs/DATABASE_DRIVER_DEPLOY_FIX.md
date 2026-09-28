# PostgreSQL driver startup repair

## Failure and reviewed baseline

- Application baseline: `393e3366055e759b760abacf584b48f3203253da`.
- Reviewed PR #42 HEAD: `2b04d38873b680de4e52309ec42d7bb4ccec8118`.
- Both have tree `c52b3d2815a744f61ac4f6298ee97c19ce5faabc`.
- The failed Render build resolved the open `SQLAlchemy>=2.0` requirement to
  SQLAlchemy 2.1.1. Its bare `postgresql://` dialect selects psycopg v3, while
  the application installs psycopg2. Importing the application therefore
  failed with `ModuleNotFoundError: No module named 'psycopg'`.
- Successful acceptance run `35996282101`, job `107621880002`, had installed
  SQLAlchemy 2.0.54 and psycopg2-binary 2.9.13 on Python 3.11.16.

## Repair scope

1. Pin that already tested SQLAlchemy/psycopg2 pair in backend requirements.
2. Normalize only bare `postgresql://` and legacy `postgres://` schemes to
   `postgresql+psycopg2://`. Preserve the remaining URL, explicit drivers,
   SQLite fallback and connection-pool settings.
3. Add fresh-process startup tests using the real DBAPI, real Uvicorn import
   target and the application's `/healthz`. Audit hooks and connection guards
   reject network/database access; synthetic URLs and a clean environment
   exclude inherited credentials. This proves import/startup, not DB health.
4. Add a clean backend-requirements-only environment to the existing browser
   and PostgreSQL acceptance workflow, with logs included in its artifacts.
   Replace pre-squash branch ancestry checks with the immutable integrated
   baseline tree and exactly these five changed paths. The existing native
   PostgreSQL, Chromium and document checks remain in place.
5. Record the repair in this document.

The main CI workflow and its protected historical hashes remain unchanged.
No schema, migration, template, frontend or application-route changes are
part of this repair. Existing Word/WPS review evidence continues to describe
the unchanged templates; this repair does not claim a new manual review.

## Local validation (2026-09-28)

- Python 3.11.16, a fresh environment installed from backend requirements
  only: `pip check` passed; seven startup tests passed.
- Existing regressions passed: consultation update preview 36, first save 16,
  manual case create 5, clinical document lifecycle 18, history merge 12.
  Total: 87 existing tests plus seven startup tests, 94 passing tests.
- An isolated SQLAlchemy 2.1.1 overlay reproduced the baseline missing-psycopg
  failure. The repaired URL selection loaded the real application and passed
  `/healthz` with that overlay. The deployment candidate remains pinned to
  2.0.54; the overlay is only a fault reproduction experiment.
- Native PostgreSQL is unavailable in the local container. Actual PostgreSQL
  transactions and the combined Chromium acceptance require the PR workflow
  on the new commit. Prior CI does not count as acceptance of this repair.

## Release boundary

This is a candidate repair, not deployment approval. A new commit must pass
the static gate and the combined acceptance workflow before a deployment
decision can bind it. The failed-deployment authorization bound the old
393e3366 release and does not silently advance to this repair. No production
database, migration, restore or Render setting operation is required here.
