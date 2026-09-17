# Successor release validation

The historical v3 validator still runs every original check with unchanged constants. Only after they succeed does it dispatch `scripts/run_successor_checks.py --if-selected`. Before the first `successor-release.json` exists, that runner explicitly reports `historical_v3_only`. Once the descriptor exists, malformed/incomplete proof fails CI. Deleting a previously committed descriptor also fails because complete repository history records its selection. A deliberate future descriptor-path change requires a reviewed dispatch change; it cannot silently disable the selected release.

No workflow edit, Python startup hook or installed skill change is needed. The existing workflow already checks out full history and invokes the v3 script. A public successor descriptor must not be created until actual approved final artifacts and the common lock are ready. This infrastructure does not select a benchmark, manufacture approvals or certify editorial judgments.

## Runtime

The descriptor version selects an explicitly pinned runtime before any workflow modules are imported. Descriptor v1 retains V8.2 at `7ed97581c1e82eb13052874b0e82eb429580a7b1`. Descriptor v2 selects V9 and descriptor v3 selects V10, using the exact commits declared in `scripts/validate_successor_release.py`; an arbitrary commit or mismatched descriptor/profile is rejected. V10 preparation does not lift the [methodology sequencing hold](v10-methodology-cutover.md).

The default runner fetches the selected public methodology commit, creates a temporary virtual environment, installs that commit's declared requirements, checks dependencies, runs the corresponding focused synthetic suite and validates the selected release. All imported skill files must exactly match the pinned Git blobs, with no additional skill files (bytecode caches ignored). Temporary checkout and environment are deleted afterward.

This needs read-only GitHub access and package-download access, not workflow-write scope or a cross-repository secret. It fails closed if retrieval or dependencies fail. It deliberately uses the methodology's dependency ranges rather than introducing a second package lock; the tests exercise the actual resolved environment. The existing runner Python must support the pinned methodology (tested locally with Python 3.12). No private PDF, extracted source text or actual candidate data is loaded. Source-state references to excluded private inputs need not be hydrated: required public proof registrations are checked explicitly, while the pinned native-lineage validator validates state structure without reading every historical artifact.

For offline local review, use an already compatible interpreter and an exact-byte methodology Git checkout:

```sh
/absolute/compatible/python scripts/run_successor_checks.py \
  --root /absolute/benchmark/repository \
  --release successor-release.json \
  --python /absolute/compatible/python \
  --methodology-repo /absolute/pinned/methodology/repository
```

For just the read-only validator with that runtime:

```sh
PYTHONDONTWRITEBYTECODE=1 /absolute/compatible/python scripts/validate_successor_release.py \
  --root /absolute/benchmark/repository --release successor-release.json \
  --methodology-repo /absolute/pinned/methodology/repository
```

## Release metadata, constructed only from the actual freeze

`successor-release.json` is a small repository metadata object, not a replacement methodology schema. It has exactly these fields:

| Field | Meaning |
| --- | --- |
| `schema_version` | `subject-index-successor-release-v1` for V8.2; `subject-index-successor-release-v2` for V9; `subject-index-successor-release-v3` for V10 |
| `release_id` | Actual selected lock's release ID |
| `methodology_commit` | The exact reviewed commit pinned for that descriptor version |
| `artifact_freeze_commit` | Actual ancestor commit of this benchmark repository containing every bound frozen artifact and supporting evidence file |
| `artifacts` | Object with exactly the nine base roles below, plus the two access roles for V10, each a binding |
| `evidence` | Array of additional bindings: density measurement and all required correction provenance; no duplicate paths |
| `checkpoints` | Array of optional post-freeze snapshot checkpoint descriptions; empty is valid |
| `release_sha256` | SHA-256 of canonical UTF-8 JSON of this metadata object excluding only this field (sorted keys, compact separators, unescaped Unicode) |

A binding contains exactly `path` and `sha256`: a nonempty repository-relative POSIX path, and SHA-256 of the exact file bytes. Paths cannot be absolute, contain empty/dot/traversal components, or use symlinks. The descriptor cannot bind itself as a frozen artifact.

The nine artifact roles are `state`, `draft`, `review`, `benchmark`, `study_lock`, `page_map`, `chunk_manifest`, `source_policy`, and `policy_template`. The state is the completed source-only typed freeze; the source policy is the real registered frozen policy, while the template is the separately selected unfrozen common policy. Preserve source-state-relative registered paths when assembling these files. The validator requires each typed registration's exact path and hash, not merely a matching hash elsewhere in the state.

The study lock must use `current_source_freeze`. Its final/draft/review/state identities are validated through pinned `validate_release` and `validate_native_lineage`; temporary screening is recomputed and removed. Canonical policy/map/manifest/final identities, benchmark and template semantic identities, source scope, policy profile/mode, density page ownership, labels and totals are checked with pinned methodology logic. Policy-template schema checking uses an in-memory view with real source-policy identity/freeze wrappers; no new policy or freeze is written or asserted.

For V9, the source state, policy, draft, review and final remain unchanged V8.2 proof. The validator passes the actual `source_policy` file to `validate_native_lineage`, validates the source policy and state under the preserved V8 schemas, and validates the new target template under V9. The lock must carry the exact V8.2 source methodology and policy hashes. Its V9 policy semantics must equal the preserved source policy after only the runtime's enumerated version substitutions. Missing policy, unknown source profiles or fields, rewritten source proof, and fully rebound substantive policy changes fail. Descriptor versioning never authorizes relabeling the source freeze.

V10 preserves that same source proof and adds exactly `access_overlay` and `access_review` artifact roles. These internal role names bind the separately authored benchmark-access amendment and its independent review. Each must match the exact path and file hash selected by the study lock. The pinned V10 validator checks the amendment's source identities, author/reviewer independence, complete delta review, population accounting and effective benchmark fingerprint. The base benchmark role still binds the preserved source freeze; it is not replaced with the amended evaluation benchmark. Every access proof file must already exist in the selected artifact-freeze commit. Candidate factual access-review receipts are produced later, separately for each evaluation, and do not belong to this source release.

All lock density references must also appear in the explicit committed `evidence` bindings (converted from lock-relative paths to repository-relative paths). If a measurement declares `metadata_correction`, bind its original measurement, scope addendum and independent scope disposition too, at the paths named in that provenance. The validator verifies their hashes and whole-object equality to the original after removing only `metadata_correction` and restoring only `protocol.source_role_note`. It does not editorially interpret the corrected note. Source-role interpretation remains with the independent source review.

The unchanged review `approved_changes` contract records entity IDs/actions and changed field names, not before/after values. Consequently, the validator rejects changed-field sets outside that ledger, but cannot prove that a reviewer assented to a particular replacement value if someone deliberately rebuilds every state/lock/Git binding around another value in an already-listed field. The independent source reviewer must affirm the actual repaired final bytes; include that actual final-byte handoff in release evidence. The candidate-exposed coordinator selects those affirmed bytes but cannot supply the independent editorial assent. Once that artifact-freeze commit is selected, changing file bytes or merely updating a file hash cannot pass. This is a proof of binding and existing contract compliance, not a substitute for substantive review; the validator hashes supplementary handoff evidence without judging its editorial adequacy.

## Freeze and metadata order; checkpoints without cycles

1. Finish independent review and typed source freeze; preserve the exact completed state/draft/review/final and associated registered public proof files.
2. For V10, complete the separately bound amendment and independent review first. Select the policy/density evidence and construct/validate the actual common study lock. Preserve all correcting provenance. Commit these bound files as the actual artifact-freeze commit. No final commit/hash is supplied by this infrastructure.
3. Optionally create snapshot ZIPs from those already frozen bytes. A checkpoint object has exactly `path`, `sha256` and `members`. `members` maps each archive-relative file name to one of the repository-relative frozen binding paths. Include at least state/draft/review/final. The ZIP must contain exactly the declared file members, with no duplicate names; each member must match its frozen file hash. No extraction occurs. These are simple proof snapshots, not a claim of compatibility with the methodology's richer checkpoint-export format.
4. Construct the release descriptor after archives exist. Archive bytes are bound directly by its `sha256`; archive members may reference only previously bound frozen files, never this descriptor or another checkpoint. Keep post-freeze checkpoints out of the earlier lock's `checkpoint_artifacts` to avoid a dependency cycle. Any historical transport references in that lock remain methodology transport provenance, not a replacement for this release's explicit checkpoint bindings.
5. Run the validator locally, then commit descriptor/checkpoints and run the existing CI. The descriptor and post-freeze archives need not exist in the earlier freeze commit; CI checks their current checked-out hashes, while every bound frozen artifact/evidence file must match that commit exactly. Do not amend the artifact-freeze commit to insert its own ID or future archive metadata.

## Focused checks

```sh
PYTHONDONTWRITEBYTECODE=1 SUCCESSOR_METHODOLOGY_REPO=/absolute/pinned/methodology/repository \
  /absolute/compatible/python -m unittest discover -s tests -p test_successor_release.py -v
```

Tests reuse the pinned methodology's synthetic current-source-freeze fixture, then build a small temporary Git repository with public JSON proof only. They exercise valid proof, false canonical/semantic hashes, metadata/pin errors, changed-field review mismatch, missing typed registration, rehashed working-tree tampering, policy substitution, density totals and correction provenance, consistent recount falsely labeled metadata-only, unsafe paths, snapshot member corruption/self-reference, and fail-closed dispatch after descriptor deletion. No benchmark repository Git commits or actual source/candidate artifacts are created by these tests.

Run the V9 suite separately, with its exact pinned checkout:

```sh
PYTHONDONTWRITEBYTECODE=1 SUCCESSOR_METHODOLOGY_REPO=/absolute/pinned/v9/methodology/repository \
  /absolute/compatible/python -m unittest discover -s tests -p test_successor_release_v9.py -v
```

The V9 fixture is constructed in a default V8 process. Each real validation runs in a fresh process that verifies the selected runtime bytes and selects V9 before imports. The additional cases cover preserved source bytes, source-policy hashes and required role, unknown source provenance, V9 relabeling of source state, semantic drift with all transport hashes rebound, mixed lock/runtime versions, and uncommitted proof tampering. The original V8 suite remains executable against its original pin.

Run the V10 suite with its exact pinned checkout and `test_successor_release_v10.py`. It additionally exercises a nonempty amendment without modifying the V8 base, required access roles and exact selected paths, author/reviewer independence, exact delta coverage, source-scope and exposure constraints, population drift, effective fingerprint mismatch, and rehashed but uncommitted access proof. These synthetic fixtures do not authorize an actual amendment or source release.
