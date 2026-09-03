# MVP Acceptance Criteria

The MVP must satisfy the following testable criteria. A criterion is not complete until it has an implementation test or documented manual verification.

## Functional Criteria

- [ ] **AC-PROFILE-01:** The user can upload a resume or enter a profile manually.
- [ ] **AC-PROFILE-02:** Users without formal employment history can complete profile intake.
- [ ] **AC-PROFILE-03:** The system captures education, projects, work, skills, preferences, target, seniority, location, and timeline.
- [ ] **AC-STAGE-01:** The workflow supports student, early-career, mid-career, senior-leadership, explorer, and returnee contexts.
- [ ] **AC-STAGE-02:** Career stage changes analysis, but does not determine eligibility.
- [ ] **AC-MARKET-01:** The system searches exact and related titles and keeps their results separate.
- [ ] **AC-MARKET-02:** Selected postings can be retrieved, deduplicated, normalized, and structurally analyzed.
- [ ] **AC-MARKET-03:** Current results report verified postings, distinct employers, requirements, geography, freshness, and limitations.
- [ ] **AC-ROLE-01:** Roles can be classified as direct-fit, adjacent, bridge, aspirational, poor-fit, or insufficient-evidence.
- [ ] **AC-ROLE-02:** The system can return no valid bridge role.
- [ ] **AC-GAP-01:** Gap analysis distinguishes skill, experience, leadership/scope, evidence, and credential/prerequisite gaps.
- [ ] **AC-EVIDENCE-01:** Capabilities record exposure, demonstrated, applied, production, or leadership maturity.
- [ ] **AC-ACCESS-01:** Market availability and candidate accessibility produce separate verdicts.
- [ ] **AC-TIMELINE-01:** Timeline output includes assumptions, gaps, blockers, milestones, bridge role, confidence, and limitations.
- [ ] **AC-ROADMAP-01:** The system produces a phased roadmap with skills, experience, scope, evidence, actions, and measurable milestones.
- [ ] **AC-REASSESS-01:** An updated profile can be compared with a prior profile and plan, with changes explained before revision.

## Trust Criteria

- [ ] **AC-TRUST-01:** No unsupported candidate facts are saved.
- [ ] **AC-TRUST-02:** Student coursework and projects are never labeled production experience without explicit support.
- [ ] **AC-TRUST-03:** Inferred capabilities remain inferred until the user confirms them.
- [ ] **AC-TRUST-04:** Each role recommendation retains the market evidence, sources, and retrieval dates supporting it.
- [ ] **AC-TRUST-05:** Current counts state searched sources, date, geography, title scope, and coverage limitations.
- [ ] **AC-TRUST-06:** Historical availability claims require credible historical evidence; otherwise the result says insufficient evidence or identifies broader evidence.
- [ ] **AC-TRUST-07:** The system never guarantees jobs, promotions, salaries, offers, titles, or timelines.
- [ ] **AC-TRUST-08:** External job descriptions are treated as untrusted data and embedded instructions are never followed.

## Reliability Criteria

- [ ] **AC-FAILURE-01:** Resume parsing failure is explained and supports manual continuation or safe retry.
- [ ] **AC-FAILURE-02:** Search timeout supports retry, partial evidence, lower confidence, or a safe failure result.
- [ ] **AC-FAILURE-03:** Duplicate and inaccessible postings do not inflate counts and are disclosed.
- [ ] **AC-FAILURE-04:** Invalid structured model output is retried safely without saving invalid data.
- [ ] **AC-FAILURE-05:** No exact-title result can broaden to related titles while preserving the distinction.
- [ ] **AC-FAILURE-06:** Insufficient evidence is returned as a valid result rather than replaced by speculation.
- [ ] **AC-FAILURE-07:** Ambiguous targets request user clarification.
- [ ] **AC-FAILURE-08:** Unrealistic timelines and unconfirmed prerequisites are surfaced without guarantees.

## Performance Criteria

- [ ] **AC-PERF-01:** A reviewable plan is available in under five minutes, excluding external outages.
- [ ] **AC-PERF-02:** External retrieval failures do not block safe display of already validated partial results.

## Usability Criteria

- [ ] **AC-USABILITY-01:** A student profile can complete the workflow.
- [ ] **AC-USABILITY-02:** A mid-career transitioner can complete the workflow.
- [ ] **AC-USABILITY-03:** A leadership candidate can complete the workflow.
- [ ] **AC-USABILITY-04:** The user can review, correct, reject, and approve profile inferences and the final plan.
- [ ] **AC-USABILITY-05:** The user does not need to understand MCP, LangGraph, or the model provider.
- [ ] **AC-USABILITY-06:** Open exploration returns a limited, explainable set rather than overwhelming the user.

## Fairness Criteria

- [ ] **AC-FAIR-01:** Protected attributes are not used in role-fit decisions.
- [ ] **AC-FAIR-02:** A career break is not penalized solely because it exists.
- [ ] **AC-FAIR-03:** Technical seniority is not treated as automatic people leadership.
- [ ] **AC-FAIR-04:** Certifications and academic work are not treated as substitutes for applied experience without evidence.

## Human-in-the-Loop Criteria

- [ ] **AC-HITL-01:** The user confirms or corrects extracted education, employers, titles, dates, projects, skills, leadership, and preferences.
- [ ] **AC-HITL-02:** The user confirms inferred capabilities before they become confirmed profile facts.
- [ ] **AC-HITL-03:** The user confirms target role, seniority, timeline, location, industry, and bridge-role willingness.
- [ ] **AC-HITL-04:** The final plan is not active or saved as approved until the user approves it.

## Explainability Criteria

- [ ] **AC-EXPLAIN-01:** Every role classification explains overlap, gaps, evidence maturity, and relevant market support.
- [ ] **AC-EXPLAIN-02:** Requirement stringency explains its classification rather than presenting an unexplained score.
- [ ] **AC-EXPLAIN-03:** Timeline results expose assumptions, risks, confidence, and evidence limitations.
- [ ] **AC-EXPLAIN-04:** The report separates market verdict, candidate-accessibility verdict, evidence, inference, and recommendation.
