# PRD Platform Architecture

## Goal

SpecForge is redesigned as a production-grade SaaS platform for turning raw product ideas into versioned, reviewable PRDs. The platform treats PRD generation as a canonical pipeline instead of a best-effort text completion.

## High-Level Architecture

### Frontend layer

- Web app for idea intake, clarification workflows, draft comparison, approval, and export.
- UI submits structured intake plus optional free-text context.
- UI reads draft history, section diffs, quality scores, and approval state from analysis APIs.

### API layer

- `POST /analyze` accepts structured intake and creates either a synchronous generation run or an async queued run.
- `POST /analyze/refine` performs full regeneration from the latest canonical brief plus answered questions.
- `GET /api/analyses/:id` returns current, approved, or specific draft versions.
- `POST /api/analyses/:id/approve` promotes a draft version to the approved lifecycle state.
- `POST /api/exports` only exports approved versions.

### Core services

- Intake normalization service builds the canonical `ProductBrief`.
- Analysis service classifies product domain and detects scope gaps.
- PRD synthesis service generates the canonical `PRDDocument`.
- Analysis store persists records, versions, approval state, and section diffs.
- Billing service manages quota reservation, consumption, and release.

### AI orchestration layer

- Prompt templates are versioned and reusable.
- AI is used as a bounded stage inside the pipeline, never as the source of truth for storage shape.
- Provider output is schema-validated and repaired before it can influence the canonical document.

### Job queue / async processing

- Requests reserve quota before enqueue.
- Jobs store normalized intake plus reservation keys.
- Worker claims jobs with compare-and-swap status updates to avoid double-claim races.
- Quota is consumed only after successful persistence.
- Failed terminal jobs release their reservations.

### Database and storage

- `analysis_records` stores the latest projection and lifecycle pointers.
- `analysis_versions` stores immutable version snapshots.
- `analysis_jobs` stores async work state, intake payload, and quota reservations.
- `quota_usage` stores real usage events.
- `quota_reservations` prevents overbooking without pre-deducting quota.
- `export_records` and `share_links` only reference approved outputs.

## Canonical Models

### ProductBrief

```json
{
  "problem": "Teams need a reliable PRD generator for early product discovery.",
  "target_users": ["Startup founders", "Product managers"],
  "business_goal": "Reduce time from idea to approved PRD by 70%",
  "success_metrics": ["PRD completion rate", "Median time to approved draft"],
  "constraints": ["Small team", "SOC2 roadmap"],
  "integrations": ["Slack", "Jira"],
  "compliance": ["GDPR"],
  "monetization": "Per-workspace SaaS subscription",
  "timeline": "Launch beta in 8 weeks",
  "budget": "$40k initial budget",
  "scope_notes": "Start with SaaS teams under 100 employees",
  "source_text": "Free-form idea text from the user",
  "answered_questions": [
    {
      "question": "Do you need SSO support?",
      "answer": "Yes for enterprise plan only"
    }
  ]
}
```

### ClarificationQuestion

```json
{
  "id": "86f5b1b2d0b1",
  "question": "Which KPI defines success for the first release?",
  "why_it_matters": "The PRD cannot prioritize scope without a measurable outcome.",
  "blocking_section": "analytics",
  "answer": null,
  "status": "open"
}
```

### PRDDocument

```json
{
  "overview": {
    "title": "Project Specification Document",
    "summary": "Canonical summary of the product",
    "domain": "saas",
    "confidence": "high",
    "secondary_domains": ["crm"]
  },
  "problem_statement": "Why this product exists",
  "personas": [],
  "goals": [],
  "non_goals": [],
  "assumptions": [],
  "scope": {
    "in_scope": [],
    "out_of_scope": []
  },
  "prioritized_requirements": [],
  "user_journeys": [],
  "acceptance_criteria": [],
  "non_functional_requirements": {},
  "dependencies": [],
  "risks": [],
  "analytics": {},
  "rollout": {},
  "open_questions": [],
  "technical_recommendation": "Suggested stack"
}
```

### GenerationRun

```json
{
  "run_id": "8c95bdf2-59b8-4d09-a7ce-f8b9f0e3d8f1",
  "status": "completed",
  "provider": "openrouter",
  "model": "openai/gpt-4o-mini",
  "stages": [
    {"name": "input_normalization", "status": "completed", "message": "Structured product brief created."},
    {"name": "domain_classification", "status": "completed", "message": "Detected domain 'saas'."},
    {"name": "gap_detection", "status": "completed", "message": "Generated 5 clarification questions."},
    {"name": "prd_synthesis", "status": "completed", "message": "AI synthesis completed and validated."},
    {"name": "quality_validation", "status": "completed", "message": "Quality validation completed."}
  ],
  "quality_scores": {
    "completeness": 85,
    "consistency": 90,
    "business_coverage": 78,
    "clarity": 88
  },
  "quality_score": 85,
  "warnings": [],
  "draft_version": 3,
  "approved_version": 2
}
```

## Pipeline

1. Input normalization
   - Accept structured intake plus free text.
   - Build `ProductBrief`.
   - Sanitize hostile input and preserve original source text.
2. Domain classification
   - Detect primary domain, secondary signals, and mixed-scope risk.
3. Gap detection
   - Detect missing features, conflicts, and clarification questions.
   - Mark questions as `open` or `answered`.
4. PRD synthesis
   - Build the full `PRDDocument`.
   - AI suggestions are optional enrichments, not partial patches.
5. Quality validation
   - Score completeness, consistency, business coverage, and clarity.
   - Record warnings for missing goals, KPIs, constraints, or unresolved questions.
6. Persistence
   - Persist the full regenerated draft as a new immutable version.
   - Compute section diffs against the previous draft.

## Non-Negotiable Rules

- No partial PRD generation. The platform always emits the full canonical document.
- Refinement always performs full regeneration from the latest canonical brief plus answers.
- Quota is consumed only after successful completion.
- Async jobs keep reservations while queued or retrying, and release them on terminal failure.
- Exports and shared artifacts only use approved versions.

## AI Orchestration Design

- `brief_generation`: free-form idea to polished brief text.
- `prd_enhancement`: bounded synthesis suggestions for summary, questions, risks, timeline, and stack.
- `prd_refinement`: bounded synthesis after clarification answers.
- Every prompt is versioned in the prompt manager.
- Every AI response is validated against a schema before it affects the canonical document.
- If provider output is invalid or unavailable, the pipeline falls back to deterministic synthesis and records the warning in `GenerationRun`.

## UX Flow

1. Idea input
   - User enters a rough idea and basic context.
2. Guided intake
   - UI asks for target users, goals, KPIs, constraints, integrations, timeline, budget, and compliance.
3. Clarification
   - Platform surfaces a small set of blocking questions.
4. Draft generation
   - User gets a complete draft with quality score and open questions.
5. Refinement
   - User answers questions and sees a new full draft plus section diff.
6. Approval
   - Reviewer promotes a draft to approved.
7. Export
   - Approved version can be exported or shared.

## Production Features

- Immutable version history with current and approved pointers.
- Approval workflow separated from generation.
- Quality scoring attached to every run.
- Async-safe quota reservation and consumption.
- Export gate on approved versions only.
