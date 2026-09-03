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

## 5. Reporting Rules

Confidence is not a guarantee and is not an unexplained percentage. Current and historical market confidence remain distinct. Bridge and timeline confidence remain distinct. Candidate confidence remains separate from market confidence. Missing evidence lowers or makes confidence insufficient; it does not justify invention.

## 6. Confidence Changes

Confidence may be lowered by blocked sources, stale data, partial retrieval, broader-role substitution, unresolved contradictions, fallback use, unconfirmed prerequisites, or invalidated upstream inputs. New confirmed evidence or refreshed sources may improve a dimension after recomputation.

## 7. Open Questions

- Whether any calibrated quantitative confidence is useful later
- Evaluation method for confidence quality
- User-facing wording for each level
- Thresholds, if ever justified by evidence
