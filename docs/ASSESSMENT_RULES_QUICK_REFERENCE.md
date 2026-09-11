# Evidence and assessment rules — quick reference

Current production canonical-assessment path; September 10, 2026.
This is not a claim that a new live run has passed. Existing saved results require
a new analysis; changing code does not rewrite approved profiles or old assessments.

## Evidence gates

| Rule | Decision |
|---|---|
| Opening count | Discovery volume is not complete-description or completed-comparison volume. |
| Source grounding | Keep posting IDs, original quotes and source lineage; do not invent requirements. |
| Role scope | Exact/validated variants define the baseline; related roles are context. |
| Statement type | Duties, hiring capabilities, prerequisites, preferences and metadata stay separate. Duties/preferences do not automatically create hiring gaps. |
| Independence | Fewer than 2 usable primary support identities => insufficient role evidence. Identity is employer when known, otherwise posting ID. |
| Baseline breadth | At least 2 distinct non-employer-specific hiring expectations. |
| Content quality | At least 50% of analyzed primary postings must count as high quality. Existing implementation also counts missing quality metadata as passing; this behavior was not changed. |
| Resolved comparison | Non-null match, Moderate/High confidence, no UNKNOWN/OPERATION_FAILED status and no pending clarification. A confirmed mismatch is resolved, not unknown. |
| Completion gate | At least 2 baseline expectations AND strictly more than half of baseline expectations resolved. |
| Mandatory eligibility | An unverified mandatory baseline prerequisite blocks an overall verdict; it is not a confirmed disqualification. |
| Employer-specific conditions | Keep and compare them, but do not require all of them to be resolved to assess the general role. |
| Remaining questions | Preserve names under candidate clarification, employer-specific verification or processing retry. Unknown/failed comparisons do not become negative fit votes. |
| Confidence with questions | Cap at Moderate (keep Low if already Low); Apply now becomes Apply selectively. Other evidence-backed verdicts remain possible. |
| Individual strengths | Preserve completed comparisons, approved evidence and demonstrated strengths even when the overall verdict is withheld. |

## Role-profile confidence (unchanged)

- Insufficient: fewer than 2 usable primary support identities, or no usable primary hiring items.
- Stable / High: at least 5 analyzed primary postings, 3 primary support identities,
  3 usable exact support identities, 50% repeated hiring requirements across employers,
  70% extraction success and 50% high-quality content.
- Otherwise Provisional. Moderate requires at least 3 analyzed primary postings,
  2 primary identities, 2 usable exact identities, 25% repeated requirements,
  50% extraction success, and either 2 providers or 4 analyzed primary postings.
- Other provisional cases are Low. Market uncertainty does not prove candidate inability.

## Synthesized accessibility (unchanged fit thresholds)

Only resolved baseline comparisons vote once the new coverage gate passes.
Direct = 1.0; transferable = 0.7; partial with capability present/maturity gap = 0.55;
ownership/scope partial = 0.40; adjacent/unspecified partial = 0.30;
confirmed no-match = 0. Weighted support is the mean, not a public readiness score.

Rules run in order:

1. Failed coverage gate => insufficient, with the specific reason. Legacy/noncanonical
   callers retain their original policy. Synthesis also retains its 50% insufficient
   or 50% Low-confidence guard on primary comparisons.
2. Confirmed primary hard blocker => Poor fit.
3. At least 75% no-matches plus a High gap => Poor fit.
4. Severe barriers in at least 2 independent dimensions => Aspirational.
5. One severe dimension => Near-term if weighted support >= 0.50, otherwise Aspirational.
   Existing small-sample exception: <=3 comparisons, no no-matches, a capability-present
   maturity partial, and >=2 direct/transferable/capability-present partial comparisons.
6. Moderate gaps => Selective at support >=0.65 and direct share >=0.40;
   Near-term at support >=0.40; otherwise Aspirational.
7. No material barriers => Apply now at direct share >=0.60, support >=0.75 and no no-matches;
   Selective at support >=0.65 and direct share >=0.35; Near-term at support >=0.40;
   otherwise Aspirational.
8. Remaining evidence questions/employer conditions downgrade Apply now to Selective,
   not Aspirational. Known gaps and hard blockers are not erased.

## Plan boundaries (unchanged)

- Use the synthesized assessment; do not invent gaps, bridge roles, certifications or durations.
- No fixed timeline remains an ordered, untimed plan, not a missing-timeline error.
- Provider failures retain safe validated fallback behavior, never substitute demo evidence.
- Approval remains tied to an exact plan version; an existing result is not recalculated silently.
