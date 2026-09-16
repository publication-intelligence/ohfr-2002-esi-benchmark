# Subject Index Benchmark: The Oxford History of the French Revolution (2002)

This repository contains the frozen, candidate-independent source benchmark for evaluating subject indexes to William Doyle's *The Oxford History of the French Revolution*, 2002 edition.

## Frozen benchmark release

Benchmark v3 is an immutable historical release. It completed source-led discovery, whole-book synthesis, and a full independent candidate-blind review before freeze.

**Study reconciliation is pending.** A later, independently reviewed native V8 release covers the same supplied source. A bounded candidate-unexposed comparison and a separate source check found material defects in both unchanged releases and recommended an independently reviewed successor. The complete source-only successor draft is registered and undergoing a distinct item-complete independent review. See [study reconciliation](docs/study-benchmark-reconciliation.md) and [draft PR 17](https://github.com/publication-intelligence/ohfr-2002-esi-benchmark/pull/17). Until the reviewed release and shared bindings are complete, the four candidate evaluation PRs and comparative bundle cutover remain on hold.

| Release fact | Value |
| --- | --- |
| Artifact freeze commit | [`98dbffd0ca171b5b7db76dbe1b2b5d5265ccacab`](https://github.com/publication-intelligence/ohfr-2002-esi-benchmark/commit/98dbffd0ca171b5b7db76dbe1b2b5d5265ccacab) |
| Benchmark path | [`source/source-benchmark.v3.json`](source/source-benchmark.v3.json) |
| Canonical benchmark SHA-256 | `b925797fcab50b2008ad5974590e323f772e5ea7013efa84ce7606007439aeb3` |
| Benchmark file SHA-256 | `34a399cda8ca9f1b07b9fa0ddad36ac4f5073ef12d8b12df42fb023818508b27` |
| Subjects | 1,366 |
| Relationships | 3,460 |
| Reader tasks | 1,026 |
| Independent review | Full, completed, candidate blindness preserved |

The machine-readable release bindings are in [`benchmark-release.v3.json`](benchmark-release.v3.json). Commits after the artifact freeze may improve documentation, control metadata, checkpoints, or validation automation, but they do not redefine benchmark v3. Evaluations reusing v3 must continue to pin the artifact freeze commit above.

## Source scope and limitations

The supplied study source is the IndexerLabs-distributed special PDF. Its 425 supplied document pages map directly to printed/source page labels 1–425.

The supplied PDF omits the book's front matter and endnotes. Those unavailable regions are outside the benchmark denominator. The repository also excludes the copyrighted source PDF, chapter packet PDFs, and extracted source text; the book must be obtained separately from an authorized source.

The review retains 303 label-only relationships where no single stable subject is coextensive with the access route, plus 94 documented editorial uncertainties. These are nonblocking, explicit limitations rather than missing review work.

## Contents

- `source/page-map.json`: frozen one-record-per-page map;
- `source/chunk-manifest.json`: the 17 user-approved chapter ownership units;
- `source/evaluation-policy.v2.json`: active source-bound standard policy and rubric identity;
- `source/source-subject-chunk.*.json`: candidate-blind chapter discoveries;
- `source/source-benchmark.v3.json`: final frozen benchmark;
- `validation/source-benchmark-review-inventory.json`: deterministic review denominator;
- `validation/source-benchmark-review.v1.json`: completed independent review ledger;
- `benchmark-release.v3.json`: release commit, hashes, counts, and reuse rules;
- `evaluation-state.json` and `artifact-manifest.json`: current control state; and
- `exports/`: versioned portable checkpoints.

## Reuse in candidate repositories

The historical v3 reuse contract is preserved below. It governs reuse of v3; it does not preselect the outcome of the current study reconciliation. An evaluation reusing v3 must:

1. pin benchmark repository commit `98dbffd0ca171b5b7db76dbe1b2b5d5265ccacab` as its immutable benchmark artifact reference;
2. bind `source/source-benchmark.v3.json` to canonical SHA-256 `b925797fcab50b2008ad5974590e323f772e5ea7013efa84ce7606007439aeb3` and file SHA-256 `34a399cda8ca9f1b07b9fa0ddad36ac4f5073ef12d8b12df42fb023818508b27`;
3. verify the source, policy, page-map, chunk-manifest, rubric, audit-mode, and edition identities recorded in `benchmark-release.v3.json`; and
4. preserve that lock for the entire candidate audit and any published comparison.

Do not pin a later `main` head merely to receive documentation or checkpoint updates. The artifact freeze commit is the comparison boundary.

## Review history and final control state

The independent review found systemic defects in benchmark v2 and triggered a temporary merge stop. Focused candidate-blind adjudication corrected those defects in v3. The final coordinator then approved and merged corrected v3 at the artifact freeze commit. The review ledger preserves the contemporaneous stop decision as historical provenance; `evaluation-state.json` records that the stop is cleared and is not an active blocker.

## Versioning and invalidation

`source/source-benchmark.v3.json` is immutable. Any substantive change to benchmark meaning, subjects, priorities, relationships, evidence, exclusions, or reader tasks requires a new versioned benchmark artifact and a new freeze commit. Such a revision invalidates or makes non-comparable every dependent result tied to v3 until that candidate is explicitly re-evaluated and locked to the new version.

## Automated validation

Pull requests and pushes to `main` run [`scripts/validate_benchmark_release.py`](scripts/validate_benchmark_release.py). The check verifies the release hashes, frozen counts, independent-review status, cleared control gate, checkpoint integrity, and byte-for-byte identity of benchmark v3 with the artifact freeze commit.

Successor release validation is separate: after every historical v3 check passes, the validator explicitly dispatches the [pinned successor checks](docs/successor-release-validation.md) if a successor release descriptor has been selected. Until then, CI remains historical-v3-only. The workflow and immutable v3 enforcement remain unchanged.

## Rights

This repository contains source-derived analytical metadata and evidence summaries, not the copyrighted source text. No repository license has been selected; technical reuse instructions do not grant rights beyond those separately held or authorized by the repository owner.
