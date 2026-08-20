# PMAI-P0-04 Active Restore Runner V3
## Sanitized Runtime Binding Evidence Collection and Review Preparation V1

```text
stage_id=PMAI-P0-04
substage=ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_EVIDENCE_COLLECTION_AND_REVIEW_PREPARATION_V1
repository=pet-med-ai/Pet-med-ai
branch=main
base_commit=ec5fd93108adf13e3570a18f37465b852f2b1484
base_parent=41cebde19b7990aff5beb27899e7892876e4a698
github_ci_gate=215
github_ci_gate_conclusion=success
github_ci_gate_run_attempt=1
source_preparation_package_sha256=f4f708aa0f5550eaeb5377e9c6787faf36349beb23958ca861420ba098524e93
activation_authorization_record_id=PMAI-P0-04-ARR-V3-CA-EXEC-AUTH-V1-20260816
implementation_candidate_sha256=91b9ba1da8cc290fd94a17b4c57c673be0a805ae25f1ddb0ace69922ff9e2081
target_contract_identity_sha256=e57fbfce3e490cdf185f83e9e376b20fe0ef665fbe293a512a6298d8a6420744
preparation_complete=true
runtime_evidence_collection_authorized=false
runtime_evidence_collected=false
runtime_evidence_reviewed=false
runtime_binding_contract_complete=false
creation_and_activation_execution_authorized=false
decision=HOLD_PENDING_SEPARATE_SANITIZED_RUNTIME_BINDING_EVIDENCE_COLLECTION_AND_REVIEW_EXECUTION_AUTHORIZATION
```

### Purpose

This repository package records the offline preparation for a later, separately
authorized sanitized runtime-binding evidence collection and review. It adds an
inert hash-only collector candidate, an offline reviewer, exact templates,
checklist, test matrix, locked baseline, package manifest, and fail-closed
validator. It does not collect runtime evidence.

No runtime binding value is present. `UNBOUND` is a stop sentinel, not a hash.
Missing or ambiguous values must remain `HOLD`; no hash may be guessed, copied
from another environment, or replaced with the target-contract hash.

### Exact mechanical hash contracts

The locked inert implementation candidate defines these byte contracts:

```text
runtime database identity:
UTF8(database) + 0x00 + UTF8(server_address) + 0x00 + UTF8(port) + 0x0a

schema manifest:
UTF8("".join(relation + "\n" for relation in sorted(relations)))
```

Target `AVAILABLE` and lifecycle observations are canonical-JSON hashed. The
reviewer mechanically computes the reviewed sanitized evidence-bundle SHA-256
from the canonical collector record. Manually supplied runtime hash values are
not a substitute for source observations.

### Output privacy contract

All runtime-derived collector values and all dynamic console values are either
lowercase SHA-256 strings or booleans. The downstream sanitized evidence file
adds only the fixed public schema identifier and activation authorization
record ID required by the already published non-secret binding confirmation
builder.

No database name, address, port, provider resource identifier, relation name,
timestamp, host, URL, username, password, token, connection string, backup
path, or credential may appear in collector console output or reviewed
downstream evidence.

### Inert collector boundary

The collector candidate is stored as `.py.txt`. Its CLI contains only
`--dry-run` and `--self-test`. There is no live collection CLI, provider SDK,
network client, database driver, credential integration, backup access,
subprocess execution, or filesystem input. Its pure normalization function is
not authority to invoke a future adapter.

Synthetic self-test observations are deterministic, remain in memory, and are
marked:

```text
fixture_only=true
collection_execution_authorized=false
release_eligible=false
```

The reviewer must reject them for release.

### Required future evidence

A separately authorized operational evidence stage must mechanically derive:

1. `expected_target_identity_sha256`;
2. `forbidden_production_identity_sha256`;
3. `forbidden_staging_identity_sha256`;
4. `expected_schema_manifest_sha256`;
5. `target_available_recheck_evidence_sha256` with status `AVAILABLE`;
6. `target_lifecycle_evidence_sha256` with age at most 72 hours; and
7. the canonical source-observation and reviewed-bundle hashes.

The target, production, and staging identity hashes must be distinct. Known
repository artifact hashes, all-zero/all-one sentinels, duplicates, malformed
values, extra keys, stale status evidence, fixture evidence, and raw connection
disclosure must all produce `HOLD`.

### Authorization separation

This repository preparation does not authorize or perform:

- provider control-plane, backup, credential, target, or database access;
- live runtime evidence collection or assertion;
- runner creation, activation, import, or execution;
- restore, migration 0010 creation or execution, deployment, or deletion;
- Git staging, commit, push, or automatic retry.

Repository apply, Git publication, GitHub CI verification, and actual sanitized
runtime evidence collection/review are separate gates. A CI PASS proves only
that this preparation package is structurally valid; it does not bind runtime
values or grant execution authority.
