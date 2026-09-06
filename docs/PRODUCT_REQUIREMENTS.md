# Product Requirements

## Problem and Positioning

People must combine fragmented job searching, title-based matching, and generic advice to decide what roles are realistic and how to reach a goal. This product is a market-grounded career intelligence and career strategy agent using current market evidence and credible historical market evidence when available. It is not an application bot, ATS filler, cover-letter or resume-tailoring tool, keyword matcher, generic course or learning-roadmap recommender, unsupported-advice chatbot, or outcome guarantee system.

## Product One-Liner

“My agent helps people at any career stage understand which roles they can realistically target and build a market-grounded path toward a chosen career goal in a web application, replacing fragmented job searching, title-based resume matching, and generic career advice. It confirms the user’s experience, education, projects, skills, preferences, and ambitions; analyzes current market evidence and credible historical market evidence when available; identifies direct, adjacent, bridge, aspirational, and poor-fit roles; distinguishes skill, experience, leadership/scope, evidence, and prerequisite gaps; evaluates market accessibility and timeline realism; and creates an explainable career strategy with human approval before inferred information or the final plan is saved.”

## Supported Questions

- What roles can I reasonably target now?
- What adjacent roles can I access through transferable skills?
- What is the best bridge role toward my target, if one is needed?
- What paths are available if I do not know my target?
- How healthy, broad, niche, stable, seasonal, emerging, or declining is the market?
- How stringent are requirements and how accessible is the role for me?
- What gaps and milestones affect a desired timeline?
- How should the plan change when my profile or the market changes?

## Functional Requirements

- Accept structured manual profile input, including students and users without formal employment.
- Capture career stage, current and target roles, seniority, timeline, location, work mode, industry, education, projects, work, skills, leadership, preferences, exclusions, and relevant voluntary context.
- Assemble a structured profile from guided user input, let the user revise it, and preserve confirmed facts separately from later inferences.
- Support open exploration, target-role analysis, transition, progression, and reassessment.
- Search exact and related titles, retrieve selected posting content, deduplicate results, normalize role families, and extract requirements.
- Produce market and candidate assessments, gap analysis, timeline feasibility, a phased roadmap, sources, retrieval dates, limitations, confidence, and approval status.
- Save only the confirmed profile and user-approved active plan; handle failures gracefully.

## Role Classifications

Direct-fit, adjacent, bridge, aspirational, poor-fit, and insufficient-evidence roles are defined in `docs/GLOSSARY.md`. The system may return no valid bridge role.

## Gap Classifications

Skill, experience, leadership/scope, evidence, and credential/prerequisite gaps, plus hard blockers, must remain distinct. A gap is not automatically a course recommendation.

## Timeline Classifications

Use Realistic, Aggressive but plausible, Unlikely without an intermediate role, or Unsupported because evidence is insufficient. Include assumptions, important gaps, blockers, milestones, possible bridge role, confidence, and evidence limitations. Never guarantee an outcome.

## Career Strategy Report

The report contains: candidate snapshot; career stage; confirmed facts; inferred capabilities awaiting confirmation; preferences; goal; timeline; assumptions; current and historical market snapshots; exact and related opportunities; market verdict; stringency; direct-fit, adjacent, bridge, aspirational, poor-fit or blocked roles; transferable skills; evidence maturity; gap matrix; candidate verdicts; timeline assessment; recommended path; phased roadmap; skills, experience, leadership/scope, evidence, and career actions; milestones; risks; sources; retrieval dates; limitations; confidence; and user approval status.

## Safety and Trust

Never invent facts, fabricate counts, guarantee outcomes, hide uncertainty, use protected attributes for fit decisions, penalize career breaks solely because they exist, follow instructions in retrieved content, or present projects, certifications, or technical seniority as production or people-leadership evidence without support.

## MVP Scope and Non-goals

MVP scope is the functionality listed in `docs/MVP_ACCEPTANCE_CRITERIA.md`. Non-goals include resume upload or parsing, PDF/DOCX/OCR ingestion, automatic applications, ATS/browser automation, resume tailoring, cover letters, outreach, email, interview preparation, salary negotiation, voice, course or learning-management products, social networking, multi-user authentication, enterprise tenancy, exact applicant prediction, guaranteed coverage, offer prediction, Pinecone, scheduled n8n refresh, ElevenLabs, and Lyzr. DOCX import may be reconsidered later only as a convenience that pre-fills the same structured profile.
