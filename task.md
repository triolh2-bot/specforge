# SpecForge Production Task List

This backlog turns the current MVP into a production-grade product. Tasks are ordered roughly from foundational platform work to launch readiness.

## Core Platform

### SPECFG-01: Restructure the application into a maintainable package layout
- Split `app.py` into modules for routes, services, domain analysis, AI providers, config, and templates.
- Introduce an app factory pattern and environment-specific configuration classes.
- Remove unused imports and dead code paths.
- Acceptance criteria: the app boots through a single entrypoint, core logic is organized by responsibility, and imports are no longer circular or ad hoc.

### SPECFG-02: Add typed request/response contracts and input validation
- Define explicit schemas for `/analyze`, MiniMax endpoints, and health/status responses.
- Validate JSON payloads, content types, field lengths, and enum values before business logic executes.
- Return consistent error payloads with actionable messages and request IDs.
- Acceptance criteria: malformed requests fail predictably with 4xx responses and documented error shapes.

### SPECFG-03: Introduce a persistent data model and database layer
- Add a production database such as Postgres for analyses, exports, users, auth state, audit logs, and billing metadata.
- Define migrations and repository/service boundaries.
- Persist analysis history instead of keeping the product stateless.
- Acceptance criteria: analysis records survive restarts and schema changes are migration-driven.

### SPECFG-04: Build asynchronous job execution for AI analysis
- Move provider calls and expensive analysis work off the request thread.
- Add a queue/worker system for long-running jobs, retries, and timeout handling.
- Expose job status polling or live updates to the UI.
- Acceptance criteria: long AI operations do not block web workers and failed jobs are retryable and observable.

## Security

### SPECFG-05: Harden authentication, session management, and secret handling
- Replace ad hoc session handling with production-safe cookie settings, session rotation, and secure storage.
- Store OAuth tokens encrypted at rest and support refresh flows.
- Move secrets to a managed secret store and document rotation procedures.
- Acceptance criteria: no secrets in source control, session cookies are hardened, and token lifecycle management is implemented.

### SPECFG-06: Add authorization and multi-tenant account boundaries
- Introduce accounts, workspaces, and user roles such as owner, admin, editor, and viewer.
- Enforce server-side access checks for every resource.
- Model tenant isolation in storage and background jobs.
- Acceptance criteria: users can only access data in their own workspace and role restrictions are enforced consistently.

### SPECFG-07: Add abuse protection and API safeguards
- Rate-limit public endpoints, auth flows, and AI-intensive operations.
- Add CSRF protection where needed, request size limits, and bot mitigation.
- Sanitize and escape rendered content to prevent injection issues in PRD output.
- Acceptance criteria: abusive traffic is throttled and common web attack paths are covered by middleware and tests.

### SPECFG-08: Complete a security review and compliance baseline
- Threat-model the product, especially OAuth, prompt injection, exported documents, and stored customer requirements.
- Add dependency scanning, SAST, secret scanning, and patch management.
- Define baseline controls for data retention, privacy, and auditability.
- Acceptance criteria: critical findings are remediated and a documented security baseline exists for production.

## Reliability and Operations

### SPECFG-09: Add structured logging, tracing, and metrics
- Emit structured logs with request IDs, tenant IDs, provider name, latency, and error classes.
- Add metrics for analysis volume, latency, queue time, provider failures, export downloads, and auth errors.
- Add distributed tracing across web and worker processes.
- Acceptance criteria: key request paths are observable and incidents can be debugged without reproducing locally.

### SPECFG-10: Add health checks, readiness checks, and operational dashboards
- Expand `/health` into liveness and readiness endpoints with dependency awareness.
- Create dashboards for uptime, queue backlog, provider errors, and latency percentiles.
- Add alerting thresholds and on-call runbooks.
- Acceptance criteria: deploy health is machine-readable and alerting covers major failure modes.

### SPECFG-11: Containerize the application and define deployment infrastructure
- Add a production Dockerfile, runtime config, and process model for web plus workers.
- Define IaC for hosting, networking, TLS, storage, and environment promotion.
- Standardize deploy targets for staging and production.
- Acceptance criteria: a fresh environment can be provisioned reproducibly and deployed without manual server setup.

### SPECFG-12: Add CI/CD with gated quality checks
- Create pipelines for linting, tests, security scans, build artifacts, and deployment promotion.
- Require branch protection and green checks before merge.
- Add automated release tagging and rollback guidance.
- Acceptance criteria: every change is validated automatically and deployments are auditable.

## Quality Engineering

### SPECFG-13: Add automated backend test coverage
- Create unit tests for domain detection, RMS scoring, missing feature detection, questions, and conflict logic.
- Add integration tests for Flask routes, auth flows, error handling, and provider fallbacks.
- Seed representative client-brief fixtures across domains.
- Acceptance criteria: critical backend paths are covered and regressions are caught before deployment.

### SPECFG-14: Add frontend regression and end-to-end tests
- Cover the analyze flow, auth state display, PRD rendering, and export behavior.
- Add browser tests for loading, failure states, and responsive layouts.
- Prevent unhandled client-side exceptions when API responses are partial or failed.
- Acceptance criteria: main user journeys are testable in CI across supported browsers.

### SPECFG-15: Formalize provider integration testing and fallback behavior
- Add contract tests for MiniMax and any future AI provider adapters.
- Validate retries, timeouts, malformed provider responses, and JSON parsing failures.
- Standardize fallback semantics so the UI can distinguish degraded mode from success.
- Acceptance criteria: provider failures are deterministic, tested, and surfaced correctly.

## Product and UX

### SPECFG-16: Redesign the frontend for production UX quality
- Replace the single static page with a clearer information architecture and stronger empty, loading, and error states.
- Improve accessibility, responsive behavior, and keyboard navigation.
- Remove hard-coded branding and visual shortcuts that make the app feel like a prototype.
- Acceptance criteria: the UI is accessible, responsive, and resilient under real production states.

### SPECFG-17: Add user accounts, saved projects, and analysis history
- Let users create, rename, revisit, duplicate, and delete requirement analyses.
- Add a dashboard for recent work and project organization.
- Support re-running an analysis with different provider settings.
- Acceptance criteria: users can manage work over time instead of losing output after a page refresh.

### SPECFG-18: Improve PRD generation quality and editing workflows
- Introduce richer PRD templates by domain, editable sections, and version history.
- Allow users to refine scope manually before export.
- Improve deterministic rule logic so outputs are less generic and more domain-aware.
- Acceptance criteria: users can review and edit generated specs before exporting or sharing.

### SPECFG-19: Build robust export and sharing features
- Implement server-side export generation for Markdown, PDF, and shareable links.
- Add branded export templates and stable document formatting.
- Persist generated artifacts and download history.
- Acceptance criteria: exports are reliable, consistent across browsers, and available after the initial session.

### SPECFG-20: Add usage analytics and product instrumentation
- Track funnel events such as sign-up, first analysis, export, provider opt-in, and repeat usage.
- Measure output quality feedback and drop-off points.
- Use analytics to prioritize product and prompt improvements.
- Acceptance criteria: product decisions can be driven by measurable usage and conversion data.

## AI and Domain Intelligence

### SPECFG-21: Introduce a provider abstraction layer
- Decouple MiniMax-specific code from analysis orchestration.
- Support pluggable providers with common interfaces, capability flags, and fallback order.
- Normalize response parsing and error handling across providers.
- Acceptance criteria: adding a new provider does not require route or UI rewrites.

### SPECFG-22: Improve prompt management, output validation, and guardrails
- Version prompts and system instructions outside inline source strings.
- Validate generated JSON against schemas and repair or reject invalid outputs safely.
- Add prompt-injection resilience and content safety rules for user-provided requirements.
- Acceptance criteria: AI output handling is versioned, testable, and resilient to malformed responses.

### SPECFG-23: Expand domain intelligence beyond keyword heuristics
- Replace simple substring matching with configurable domain rules, weighted features, and examples.
- Improve implied-user detection, scope inference, and requirements scoring with stronger logic.
- Add benchmark datasets for common project domains.
- Acceptance criteria: analysis quality improves measurably against a labeled evaluation set.

### SPECFG-24: Create an evaluation framework for output quality
- Define golden test cases for domain detection, missing features, questions, PRD structure, and AI enrichment.
- Score outputs for precision, usefulness, consistency, and hallucination risk.
- Run evaluations in CI when prompts or heuristics change.
- Acceptance criteria: output quality regressions are measurable before release.

## Commercial Readiness

### SPECFG-25: Add billing, quotas, and plan enforcement
- Define free and paid usage tiers with analysis limits, export limits, and provider access rules.
- Integrate a billing provider and add subscription lifecycle handling.
- Enforce quotas in both synchronous requests and background jobs.
- Acceptance criteria: paid entitlements are enforced consistently and usage is billable.

### SPECFG-26: Add admin operations and support tooling
- Create internal views for user lookup, job inspection, failed exports, provider incidents, and abuse cases.
- Add safe replay tools for failed analyses and exports.
- Log operator actions for auditability.
- Acceptance criteria: support can resolve customer issues without direct database edits.

### SPECFG-27: Prepare legal, privacy, and policy surfaces
- Publish terms, privacy policy, data retention policy, and acceptable use policy.
- Add consent handling if storing customer requirement text for analytics or training.
- Support user data export and deletion workflows.
- Acceptance criteria: the product has minimum viable legal and privacy operations for launch.

## Launch Readiness

### SPECFG-28: Stand up separate staging and production environments
- Mirror core infrastructure, provider configuration, and test data strategy.
- Add smoke tests and deployment verification in staging before production promotion.
- Document environment parity gaps and close them.
- Acceptance criteria: production releases are first exercised in a realistic staging environment.

### SPECFG-29: Complete performance testing and capacity planning
- Load-test analysis endpoints, worker throughput, auth flows, and export generation.
- Define SLOs for latency, success rate, and queue completion time.
- Tune concurrency, timeouts, and autoscaling rules.
- Acceptance criteria: expected launch traffic has validated headroom and clear scaling thresholds.

### SPECFG-30: Run final go-live checklist and incident readiness review
- Finalize runbooks, backups, rollback steps, feature flags, and launch monitoring.
- Conduct an end-to-end production readiness review across engineering, product, and support.
- Freeze scope for launch and define post-launch triage ownership.
- Acceptance criteria: go-live has explicit owners, rollback paths, and monitored success criteria.
