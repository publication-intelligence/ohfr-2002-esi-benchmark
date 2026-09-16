# Source successor draft handoff

The complete source-only synthesis is registered as `ohfr-2002-study-source-successor-v1`, version 1. It is a draft awaiting independent editorial review. Neither historical release is declared the study winner, and neither historical freeze, discovery history or review history has been changed.

The immutable [draft](../successor/source/source-benchmark.draft.v1.json) has SHA-256 `c614e709cbe049bde88a5c1f77c27dd77334b2932bb0bbf0593f2ed08b742678`. The isolated [canonical state](../successor/evaluation-state.json) records completed discovery and synthesis, with review and freeze not started and candidate `null`. Its handoff snapshot hash is `f5694dd568fb71d784c019aa1c1ce868064446119da5f7d35fc0b797cf961f7e`. The state may subsequently advance through the independent workflow; the draft bytes remain fixed.

The principal author and two source authors read all 425 owned pages and completed a source-first omission pass across all 17 chapters. The earlier comparison supplied 128 transparently reused pages; the remaining 297 pages were newly inspected during synthesis. Subsequent targeted rereading is recorded separately and does not inflate coverage. The authors reviewed both exact final-release lineages, including changes made after their original discoveries. Mechanical inventories are not represented as semantic review, and author review is not represented as independent approval.

| Entity | Historical records reconciled | Successor draft |
|---|---:|---:|
| Subjects | 2,004 | 531 |
| Evidence records | 4,823 | 3,341 |
| Relationships | 3,741 | 493 |
| Reader tasks | 1,664 | 599 |
| Exclusions | 307 | 248 |
| Uncertainties and resolved editorial controls | 169 | 151 |

The draft also preserves 921 unique, unweighted specific-question facets inside reader tasks. Their exact required-subject bindings matter: a broad host question is not treated as equivalent to each attached question. Generic historical prompts are retired. Fifty-three groups of identical authored questions were consolidated with their complete target sets.

Native organizing units served as a provisional scaffold. Whole-book decisions combine compatible repeated treatments while preserving different actors, phases and access routes. The source led to separate requirements for the February levy and August levée en masse; assignat abandonment and territorial mandates; Austrian peace and failed British negotiations; preserved slavery, free coloured citizenship, the slave uprising and wartime abolition. Free coloured rights on pages 151 and 411–412 are consolidated without confusing either with emancipation. Repeated events and institutions are merged only where their source meaning permits it. Priority follows explanatory importance and sustained treatment, with no count or density quota.

The p151 reconciliation disposes all seven incident historical edges. It preserves the valid qualification of universal liberty by retained slavery, corrects the inverse qualification, removes duplicated slavery scope, and binds Robespierre’s rights victory and Barnave’s opposition to the free coloured population. The p275 requirement restores the changed-phase inference toward greater social discrimination while retaining the source’s qualification about guilt; the unsupported lower-class counterargument is removed. Other repairs include narrowed causal operators, wrong task targets, fiscal direction, chronology and phase errors, and cross-chapter evidence restoration. The draft keeps source-internal date conflicts visible rather than silently correcting the supplied edition.

The exact [subject](../successor/synthesis/lineage/subjects.json), [evidence](../successor/synthesis/lineage/evidence.json), [relationship](../successor/synthesis/lineage/relationships.json), [task](../successor/synthesis/lineage/tasks.json), and [auxiliary](../successor/synthesis/lineage/auxiliary.json) ledgers enumerate every historical final ID. They preserve exact before-values, explicit successor identities and field dispositions. The [change catalogue](../successor/synthesis/source-change-catalog.json) binds those ledgers and enumerates additions in the distinct successor namespace. Retired historical graph links may be redundant, descriptive, or internal to a coherent requirement; retirement does not by itself assert that the historical relation was false. Same-page evidence links and related current edges are trace pointers, not automatic equivalence claims.

The operational density basis is the separately source-reviewed measurement of **193,118 words**, with all 425 page counts and 17 chunk counts retained. Original measurements remain unchanged in their original lineages. The installed methodology is `c11c6ccb16000fe79646af16b7be01f6cbeeac78`; the new policy identity is `63f4cdebb96137b32874df6a0a5035ca638519892ff72e444dcbc925e1ef42ae`. The measurement excludes chapter display words and map internals from prose density while preserving the semantic eligibility of substantive headings, maps and legends. Reproduction:

```sh
python3 scripts/measure_source_density.py \
  --source .source-only/source/source.pdf \
  --manifest .source-only/source/chunk-manifest.json \
  --page-map .source-only/source/page-map.json \
  --private-dir .source-only/review-work/principal \
  --output validation/reconciliation/source-review/source-density-measurement.json
```

The [author validation](../successor/validation/author-synthesis-validation.json) passes exact historical-ID closure, unique new IDs, page labels, source-page bounds, relationship and task targets, facet references, task coverage and preservation of both old final releases. The installed discovery validator passed all 17 artifacts, which were registered through its supported command. The installed draft screen reports 40 cross-chapter subjects, no unresolved relationships, no duplicate or near-duplicate labels, no missing task coverage or required fields, and no invalid targets. It classifies six newly authored questions as fallback review items; they remain explicitly queued for independent review. These checks establish structural consistency, not editorial approval.

The [temporary review inventory](../successor/validation/source-benchmark-review-inventory.json) remains unregistered. The [hash-bound handoff](../successor/synthesis/synthesis-handoff.json) enumerates the full actual-draft review queue, including every evidence record, exclusion, uncertainty and nested question facet. Independent reviewers must examine this exact draft, revisit all consolidated cross-chapter subjects, and bind their separately completed source-first omission pass. The authors report no outstanding blocking synthesis issue. Source uncertainties—including estimates, alleged motives and printed date conflicts—remain qualified requirements rather than hidden corrections.

The source authors remained candidate-unexposed. No candidate index, audit, score, result, name, ranking or outcome informed the synthesis. This delivery does not approve a freeze, select audit transfers or authorize reuse of historical audits against changed requirements.
