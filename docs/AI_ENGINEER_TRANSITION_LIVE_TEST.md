# Senior Java Developer → AI Engineer: live backend test

Run: 2026-09-11, `20260911T164139Z`.

## Scope

- Used the existing **synthetic Senior Java Developer demo profile**, not the personal
  automation résumé: eight years of Java/Spring Boot production backend work, APIs,
  SQL, AWS/CI/CD, testing, incident support and mentoring; a personal non-production project.
- Used all five unchanged user-supplied files under `job-descriptions/AI Engineer`.
- Live model: Fireworks `accounts/fireworks/models/deepseek-v4p1-flash`.
- Production ROLE_TRANSITION graph, `career-transition-assessment-v1`.
- No Adzuna/You.com requests, browser interaction, live vacancy verification,
  automatic inferred-strength approval or plan approval.
- Core profile evidence was supplied directly; AI strength inference was deliberately
  skipped. This tests the approved-profile/goal → assessment → draft-plan path.

## Input descriptions

| File | Employer | Role | Words (importer) | Location established by text |
|---|---|---|---:|---|
| AI Engineer 1.txt | Tangerine | Senior AI Engineer | 881 | Toronto |
| AI Engineer 2.txt | Orion Innovation | AI Engineer | 397 | Mississauga |
| AI Engineer 3.txt | Definity | AI Engineering Lead | 923 | Not specified |
| AI Engineer 4.txt | Definity | Specialist, AI Engineering | 1,067 | Not specified |
| AI Engineer 5.txt | Softchoice | Sr. AI Engineer | 1,155 | Canada context; city not specified |

Five postings, four employers. The two Definity roles remain separate jobs. All five
were included together; source aliases were P1 Orion, P2 Softchoice, P3 Definity Specialist,
P4 Tangerine and P5 Definity Lead. Import classified one exact title and four related
titles; related titles were not excluded. Full description bodies were sent as numbered
nonempty lines, not shortened to snippets. Word counts vary slightly with tokenizer.

## Actual model result

**ASPIRATIONAL / HIGH confidence**, with eight retained strengths, 20 competencies,
five posting assessments and six ordered plan actions. Zero schema/reference processing
issues. Final graph state: WAITING_FOR_HUMAN at final_plan_review. Plan remains DRAFT.

The model's conclusion: software engineering is a credible foundation, but the supplied
profile does not establish the applied AI/Python/LLM experience these postings seek.
It explicitly says the assessment should be revisited if unlisted experience exists.

Retained strengths: production backend delivery; REST integration; PostgreSQL/SQL tuning;
AWS/CI/CD; automated testing; incident support; mentoring/code review; personal project delivery.

| Competency (shortened labels) | Model comparison | Next need |
|---|---|---|
| AI/ML application development | Not established | Clarify |
| Python | Not established | Clarify |
| Cloud AI platforms | Partial | Build experience |
| Docker/Kubernetes | Partial | Build experience |
| CI/CD | Demonstrated | None |
| REST API development | Partial | Clarify Azure API Management |
| Production systems/operations | Demonstrated | None |
| Data modeling/SQL | Demonstrated | None |
| Prompt engineering/LLM orchestration | Not established | Clarify |
| MLOps/LLMOps/feature stores/observability | Not established | Clarify |
| RAG/vector search | Not established | Clarify |
| Agent frameworks/A2A/MCP | Not established | Clarify |
| Responsible AI | Not established | Clarify |
| Technical leadership/mentoring | Partial | Build experience |
| Business stakeholder translation | Partial | Clarify |
| P&C insurance | Not established | Clarify |
| Five years AI agent experience (Orion) | Not established | Clarify |
| Three years production fraud AI (Definity Lead) | Not established | Clarify |
| ML/AI platforms at scale | Not established | Clarify |
| Agile | Not established | Clarify |

Counts: 3 demonstrated, 5 partial, 12 not established, **0 TRANSFERABLE labels**.
There are transfer descriptions in the strengths section, but no competency uses that status.

All five postings were labeled STRETCH. Reasons distinguish agent-experience requirements
at Orion, Azure/GenAI at Softchoice, Python/AI at Definity Specialist, platform scale at
Tangerine, and fraud/leadership experience at Definity Lead.

## Generated plan (summary, not a replacement for saved raw output)

1. Clarify unlisted Python, AI, Kubernetes and other relevant experience.
2. If Python is absent, build working proficiency with a small service.
3. Build a documented, deployed RAG or agentic application using a cloud AI service.
4. Add automated deployment, monitoring and evaluation.
5. Prepare accurate examples of existing transferable backend strengths.
6. Reassess against the postings and select the nearest suitable direction.

No invented deadline, certification requirement or automatic approval. No fixed timeline
is preserved. Project completion is not claimed to satisfy multi-year professional prerequisites.

## Timing and provider-reported tokens

| Step | Seconds | Input tokens | Output tokens |
|---|---:|---:|---:|
| Initial assessment | 90.80 | 10,923 | 7,908 |
| Critical review | 165.29 | 15,634 | 26,966 |
| Total graph | 256.26 | — | — |

Both model calls finished with `stop`, not token-limit truncation. Output-token figures
are provider totals and should not be interpreted as just the visible answer length.
No reference-repair call was needed. Local loading/retrieval was effectively immediate;
the two live calls dominated elapsed time.

## What worked

- All five substantive descriptions reached the model; no empty assessment or lost plan.
- Eight existing strengths survived the transition assessment.
- Review changed missing AI/Python evidence from LEARN to CLARIFY and reordered the plan.
- Review preserved Python as a requirement in Definity rather than treating Java as its substitute.
- Review surfaced Orion's five-year agent requirement and Definity Lead's fraud experience.
- Production Analysis rendered 20 rows and Plan rendered six milestones with zero AppTest
  exceptions. No website was opened; this is not browser-level visual QA.

## Remaining issues — do not call this fully calibrated

1. **Broad strength downgrade:** review changed general REST APIs from demonstrated to
   partial because Softchoice specifies Azure API Management. General REST should remain
   demonstrated; that platform-specific condition should be separate.
2. **Over-bundling:** Docker/Kubernetes, leadership/mentoring and several AI technologies
   remain combined despite different evidence levels. No TRANSFERABLE competency was used.
3. **Uneven unknown handling:** Python/AI became CLARIFY, but Kubernetes/cloud-AI/leadership
   still became BUILD_EXPERIENCE without first resolving missing information.
4. **Overbroad summary/confidence:** the rationale implies every posting requires the whole
   Python/prompt/MLOps bundle. That is not true of the individual source requirements.
   ASPIRATIONAL is defensible for this experienced/senior-heavy sample on the supplied profile,
   but HIGH confidence should not imply a settled verdict about every AI Engineer transition.
5. **Employer concentration and source scope:** Data modeling/SQL is labeled COMMON despite
   its cited support being one Definity posting; Agile is COMMON with one Softchoice citation.
   Softchoice's unknown city was described as Canada-wide, which the text does not establish.
6. **Plan focus and verbosity:** the plan broadly builds toward AI, but still mixes specialist
   needs (e.g. feature stores) instead of choosing one clear direction first. Review consumed
   nearly 65% of model time and produced a large provider-reported token count.

These are semantic/model-instruction issues, not missing descriptions or failed connections.
The assessment rules were not retuned during this test.

## Diagnostic fix and retained artifacts

First attempt `20260911T164049Z` stopped with zero model calls: the local test loader
assumed largest-employer count = 1. Two Definity postings exposed that error. Corrected
the diagnostic loader to calculate employer counts; no production assessment policy changed.
Added a regression for multiple distinct roles at one employer; local-loader tests: 3 passed.
An initial cold-start AppTest exceeded its 3-second timeout; rerun passed. Actual saved-result
rendering used a 20-second test budget and completed without errors.

Artifacts (local, sanitized; no keys or private reasoning traces):

- `outputs/local-descriptions/20260911T164139Z/results.json`: complete saved graph result.
- `outputs/local-descriptions/20260911T164139Z/model-01.json`: initial request/final response.
- `outputs/local-descriptions/20260911T164139Z/model-02.json`: review request/final response.
- `outputs/local-descriptions/20260911T164049Z/results.json`: failed loader attempt.

Reproduce:

```powershell
.venv/Scripts/python.exe scripts/check_local_descriptions.py --folder "job-descriptions/AI Engineer" --target "AI Engineer" --goal-type ROLE_TRANSITION --metadata scripts/fixtures/ai_engineer_local_metadata.json --live
```
