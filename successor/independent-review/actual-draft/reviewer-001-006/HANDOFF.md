The assigned actual-draft review is complete and requires revisions. This is not approval of draft v1, a freeze, or a candidate evaluation.

I reviewed all 202 assigned whole subjects, 1,840 evidence records, 211 subject facets, 134 relationships, 336 reader tasks and 327 task facets. All 181 source-first findings have explicit draft mappings and dispositions. Exact IDs and coverage checks are in `coverage-and-validation.json`; source-grounded decisions and fixes are in the four review ledgers.

- `subject-review.jsonl`: 86 faithful, 115 requiring revision, and one faithful with lineage repair. The principal problems are copied whole historical dossiers under narrower subjects, distinctions present only in nested material, a few unsupported formulations, and incorrect page boundaries.
- `relationship-review.jsonl`: 107 faithful and 27 requiring semantic, directional, scope, locator or historical-mapping repair. A valid current edge does not automatically preserve a different historical relation.
- `task-review.jsonl`: 204 faithful and 132 requiring changes or dependent on subject repairs. Every attached facet was read separately for its question and targets. One spatial task requires retirement because it depends on excluded map internals.
- `source-finding-reconciliation.jsonl`: 82 faithful, 83 partially lost or diluted, and 16 referred to the lead. “Lost” here usually means a particular source distinction needs repair, not that the entire topic is absent. These counts are not scoring denominators or automatic deductions.

Parent meaning and stance must carry substantive retained distinctions. Required access facets are unweighted; task facets must fit the main question and have their necessary subjects represented in the parent links. Unrelated attachments should be rehomed rather than adding every projected historical subject to a narrow question.

The most consequential repairs include:

- Remove semantically excluded map internals and numbered keys on pages 3, 127 and 129. Keep eligible captions and developed institutional prose. Retire task `TASK-SUCC-039417B07401` and its spatial facet.
- Preserve the ordinary-account versus extraordinary war-expense distinction in Necker’s accounts; the limited 1780 torture reform; Rousseau’s literary, religious and small-state qualifications; and the exceptions to female exclusion in freemasonry.
- Retain the full Declaration principles and qualifications, the difference between civil equality and political suffrage, elected/free justice and abolished venality, and the paradox of tax reconstruction without effective compulsory collection. The Guard’s copied fiscal claim belongs with the tax parent, where the source-backed demand already exists.
- Preserve genuine Jacobin/Varennes distinctions on page 153: club growth, deposition demands without a republican majority, and the unresolved Paris position. General national vigilance belongs with Varennes. Duplicate domestic Pillnitz claims can retire with these explicit bindings.
- Correct task attachments that move the July Bastille sequence into a pre-May food-riot question, the elected-orders comparison into representation/cahier questions, or the full Church reform–oath–Rome sequence into narrow dispossession and Dom Gerle questions. Exact destinations and the proposed coherent Church sequence task are in `lead-referrals.json`.

The lead referrals also preserve uncertainty rather than harmonizing the source silently: generalities versus intendancies; Dom Gerle’s April date; Lafayette’s October date; the Church-property vote date as printed; early Robespierre republicanism; Saint-Cloud intentions; Varennes intentions; the potentially apocryphal revolt/Revolution exchange; and the assignat legal-tender chronology referred by the lead. Whole-book controls and cross-chapter entities remain the lead’s responsibility.

The immutable draft retains SHA256 `c614e709cbe049bde88a5c1f77c27dd77334b2932bb0bbf0593f2ed08b742678`. All 109 original packet files and 146 addendum files passed final identity checks. Phase-one outputs remain byte-for-byte unchanged. Candidate content/results remain unseen. No canonical or historical state was edited. `review-attestation.json` records the visibility and scope limits; `output-receipt.json` binds this handoff’s public artifacts.
