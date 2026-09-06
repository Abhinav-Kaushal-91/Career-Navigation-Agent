# Confidence Model

## 1. Purpose

Confidence communicates evidence quality and uncertainty without pretending that complex conclusions can be reduced to one global score.

## 2. Levels

Use `HIGH`, `MODERATE`, `LOW`, and `INSUFFICIENT`. Every level includes reasons, evidence references, limitations, and relevant scope.

## 3. Dimension-Specific Confidence

Track separately:

- Profile extraction confidence
- Evidence maturity confidence
- Search coverage confidence
- Posting validity confidence
- Requirement extraction confidence
- Title normalization confidence
- Historical-market confidence
- Requirement-stringency confidence
- Market-verdict confidence
- Transferability confidence
- Gap confidence
- Candidate-accessibility confidence
- Bridge confidence
- Timeline confidence
- Career-plan confidence

One dimension must not silently substitute for another.

## 4. Inputs to Confidence

Confidence may depend on source quality, completeness, consistency, number and diversity of observations, role-scope match, geography match, freshness, extraction validation, profile confirmation, model validation, retry/fallback use, and conflicting evidence. Numeric thresholds are intentionally undefined.

Current-market source coverage reports Adzuna-retained postings, You.com-retained postings, and
cross-source matches separately. Parallel completion by both lanes may improve source-coverage
confidence, while a single available lane lowers it. Source agreement does not automatically raise
posting validity, requirement-extraction confidence, or the overall market verdict.

## 5. Reporting Rules

Confidence is not a guarantee and is not an unexplained percentage. Current and historical market confidence remain distinct. Bridge and timeline confidence remain distinct. Candidate confidence remains separate from market confidence. Missing evidence lowers or makes confidence insufficient; it does not justify invention.

For Activity 6B, gap confidence describes support for one categorized difference, while role-
assessment confidence describes the reliability of the accessibility conclusion. Candidate strength
does not raise confidence by itself. Insufficient exact-target comparisons or a high proportion of
insufficient comparison results produce an insufficient or reduced-confidence assessment.

For Activity 7A, plan confidence is the lowest relevant confidence across the role, timeline,
supported bridge assessments, and current-market evidence. Optional wording fallback cannot raise
confidence and caps it at `MODERATE`. Plan confidence describes the reliability of the proposed
path and its traceability; it is not the probability of career success.

For career synthesis, accessibility is calculated primarily from exact-target and target-variant
comparisons. Related-title comparisons may inform adjacent or bridge interpretation but cannot
independently produce a positive target-role accessibility result. `INSUFFICIENT` comparison
confidence fails closed when it affects at least half of primary comparisons. `LOW` role or primary
comparison confidence caps accessibility at `NEAR_TERM_TARGET`; `MODERATE` confidence caps it at
`APPLY_SELECTIVELY`. These are ceilings, not upgrades.

## 6. Confidence Changes

Confidence may be lowered by blocked sources, stale data, partial retrieval, broader-role substitution, unresolved contradictions, fallback use, unconfirmed prerequisites, or invalidated upstream inputs. New confirmed evidence or refreshed sources may improve a dimension after recomputation.

## 7. Open Questions

- Whether any calibrated quantitative confidence is useful later
- Evaluation method for confidence quality
- User-facing wording for each level
- Thresholds, if ever justified by evidence

## 8. Comparison and accessibility calibration

Candidate-to-requirement comparison now separates functional overlap, ownership, scope, maturity,
and production context. Candidate maturity is derived only from cited approved evidence; target
maturity comes only from the canonical requirement. The model cannot replace either value.

Accessibility uses role-neutral evidence weights: direct `1.00`, transferable `0.70`,
capability-present partial `0.55`, ownership/scope partial `0.40`, adjacent partial `0.30`, and no
confirmed match `0.00`. Capability-present partials receive more weight than adjacency because the
required function is already demonstrated and the residual is maturity or production depth. These
weights are internal policy inputs, not a user-facing fit score.

For samples of three or fewer canonical requirements, strong functional support across at least two
requirements plus only one independent maturity barrier may resolve to `NEAR_TERM_TARGET` even when
the weighted average is slightly below `0.50`. This exception cannot override a no-match, multiple
independent severe dimensions, a blocker, or insufficient evidence. Transferable matches create a
career gap only when a validated structured residual remains.
