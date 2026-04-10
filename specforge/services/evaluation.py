"""Evaluation framework for AI output quality.

Defines golden test cases and scoring utilities so that prompt, heuristic,
and provider changes can be measured for regression before release.

Usage::

    from specforge.services.evaluation import EvaluationRunner, GOLDEN_CASES

    runner = EvaluationRunner()
    report = runner.run_all(GOLDEN_CASES)
    print(report.summary())
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class GoldenCase:
    """A single golden test case with expected outcomes."""

    name: str
    requirements: str
    expected_domain: str
    expected_min_rms: int
    expected_max_rms: int
    must_contain_questions: list[str] = field(default_factory=list)
    must_contain_features: list[str] = field(default_factory=list)
    must_not_contain: list[str] = field(default_factory=list)
    expected_user_roles: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class CaseResult:
    """Result of evaluating a single golden case."""

    name: str
    passed: bool
    score: float            # 0.0 – 1.0
    details: dict[str, Any]  # per-check results
    duration_ms: float
    errors: list[str] = field(default_factory=list)


@dataclass
class EvaluationReport:
    """Aggregate report across all golden cases."""

    cases: list[CaseResult]
    started_at: str
    finished_at: str

    @property
    def total(self) -> int:
        return len(self.cases)

    @property
    def passed(self) -> int:
        return sum(1 for c in self.cases if c.passed)

    @property
    def average_score(self) -> float:
        if not self.cases:
            return 0.0
        return sum(c.score for c in self.cases) / len(self.cases)

    def summary(self) -> str:
        return (
            f"Evaluation: {self.passed}/{self.total} passed, "
            f"avg score {self.average_score:.2f}, "
            f"duration {self._duration_ms:.0f}ms"
        )

    @property
    def _duration_ms(self) -> float:
        from datetime import datetime
        start = datetime.fromisoformat(self.started_at)
        end = datetime.fromisoformat(self.finished_at)
        return (end - start).total_seconds() * 1000


# ---------------------------------------------------------------------------
# Golden test cases
# ---------------------------------------------------------------------------

GOLDEN_CASES: list[GoldenCase] = [
    GoldenCase(
        name="ecommerce_bakery",
        requirements=(
            "I want to build an online bakery store where customers can browse "
            "custom cakes, add items to cart, and checkout with credit card payment. "
            "I need inventory management, order tracking, and an admin dashboard "
            "to manage products and view sales reports."
        ),
        expected_domain="e-commerce",
        expected_min_rms=45,
        expected_max_rms=100,
        must_contain_questions=["shipping", "inventory"],
        must_contain_features=["cart", "payment"],
        expected_user_roles=["Admin", "Customer"],
    ),
    GoldenCase(
        name="saas_project_mgmt",
        requirements=(
            "Build a SaaS project management tool with team workspaces, "
            "subscription billing (free, pro, enterprise tiers), role-based "
            "permissions, analytics dashboard, and a public REST API."
        ),
        expected_domain="saas",
        expected_min_rms=50,
        expected_max_rms=100,
        must_contain_questions=["pricing", "tier"],
        must_contain_features=["subscription", "team"],
        expected_user_roles=["Admin", "Member"],
    ),
    GoldenCase(
        name="crm_sales",
        requirements=(
            "I need a CRM for my sales team to track leads, manage the deal "
            "pipeline, and integrate with Gmail. Sales reps need activity "
            "timelines, and managers need forecasting reports."
        ),
        expected_domain="crm",
        expected_min_rms=40,
        expected_max_rms=100,
        must_contain_questions=["pipeline", "email integration"],
        expected_user_roles=["Sales Rep", "Manager"],
    ),
    GoldenCase(
        name="mobile_fitness",
        requirements=(
            "Build a mobile fitness tracking app for iOS and Android with "
            "push notifications, offline workout logging, camera for progress "
            "photos, and GPS route tracking for runs."
        ),
        expected_domain="mobile-app",
        expected_min_rms=35,
        expected_max_rms=100,
        must_contain_questions=["native", "cross-platform"],
        expected_user_roles=["User", "Admin"],
    ),
    GoldenCase(
        name="api_backend",
        requirements=(
            "Create a REST API backend with JWT authentication, rate limiting, "
            "OpenAPI documentation, webhook event delivery, and Redis caching "
            "layer for high-throughput request handling."
        ),
        expected_domain="api",
        expected_min_rms=40,
        expected_max_rms=100,
        must_contain_questions=["authentication", "rate limit"],
        expected_user_roles=["Developer"],
    ),
    GoldenCase(
        name="marketplace_freelance",
        requirements=(
            "Build a freelance marketplace connecting designers with clients. "
            "Sellers create portfolios, buyers browse and hire. We need escrow "
            "payments, commission splitting, ratings, and dispute resolution."
        ),
        expected_domain="marketplace",
        expected_min_rms=40,
        expected_max_rms=100,
        must_contain_questions=["dispute", "commission"],
        expected_user_roles=["Buyer", "Seller"],
    ),
    GoldenCase(
        name="blog_tech",
        requirements=(
            "I want to start a tech blog with article publishing, editor "
            "review workflow, reader comments, SEO optimization, and a "
            "weekly newsletter digest for subscribers."
        ),
        expected_domain="blog",
        expected_min_rms=35,
        expected_max_rms=100,
        must_contain_questions=["paywall", "multilingual"],
        expected_user_roles=["Author", "Editor", "Reader"],
    ),
    GoldenCase(
        name="vague_general",
        requirements="I need a thing that does stuff for people online.",
        expected_domain="general",
        expected_min_rms=10,
        expected_max_rms=50,
        must_contain_questions=["timeline", "budget"],
    ),
]


# ---------------------------------------------------------------------------
# Evaluation runner
# ---------------------------------------------------------------------------

class EvaluationRunner:
    """Runs golden cases and produces a quality report."""

    def __init__(
        self,
        domain_fn: Optional[Callable[[str], str]] = None,
        rms_fn: Optional[Callable[[str, str], int]] = None,
        questions_fn: Optional[Callable[[str, str, list], list[str]]] = None,
        missing_fn: Optional[Callable[[str, str], list[str]]] = None,
        users_fn: Optional[Callable[[str], list[str]]] = None,
    ):
        # Lazy imports to avoid circular deps
        if domain_fn is None:
            from specforge.services.domain_analysis import detect_domain
            self.domain_fn = domain_fn or detect_domain
        else:
            self.domain_fn = domain_fn

        if rms_fn is None:
            from specforge.services.domain_analysis import calculate_rms
            self.rms_fn = rms_fn or calculate_rms
        else:
            self.rms_fn = rms_fn

        if questions_fn is None:
            from specforge.services.domain_analysis import generate_questions
            self.questions_fn = questions_fn or generate_questions
        else:
            self.questions_fn = questions_fn

        if missing_fn is None:
            from specforge.services.domain_analysis import detect_missing_features
            self.missing_fn = missing_fn or detect_missing_features
        else:
            self.missing_fn = missing_fn

        if users_fn is None:
            from specforge.services.domain_analysis import detect_implied_users
            self.users_fn = users_fn or detect_implied_users
        else:
            self.users_fn = users_fn

    def run_case(self, case: GoldenCase) -> CaseResult:
        """Evaluate a single golden case."""
        start = time.perf_counter()
        details: dict[str, Any] = {}
        errors: list[str] = []
        score_components: list[float] = []

        try:
            # 1. Domain detection
            detected_domain = self.domain_fn(case.requirements)
            domain_correct = detected_domain == case.expected_domain
            details["domain"] = {
                "expected": case.expected_domain,
                "detected": detected_domain,
                "correct": domain_correct,
            }
            score_components.append(1.0 if domain_correct else 0.0)

            # 2. RMS scoring
            rms = self.rms_fn(case.requirements, detected_domain)
            rms_in_range = case.expected_min_rms <= rms <= case.expected_max_rms
            details["rms"] = {
                "value": rms,
                "expected_range": [case.expected_min_rms, case.expected_max_rms],
                "in_range": rms_in_range,
            }
            score_components.append(1.0 if rms_in_range else 0.5)

            # 3. Question quality
            domain = detected_domain
            missing = self.missing_fn(domain, case.requirements)
            questions = self.questions_fn(domain, case.requirements, missing)
            details["questions"] = {
                "count": len(questions),
                "questions": questions,
            }
            if case.must_contain_questions:
                matched_q = [
                    q for q in case.must_contain_questions
                    if any(q.lower() in question.lower() for question in questions)
                ]
                q_coverage = len(matched_q) / len(case.must_contain_questions)
                details["questions"]["coverage"] = q_coverage
                score_components.append(q_coverage)

            # 4. Missing feature quality
            if case.must_contain_features:
                matched_f = [
                    f for f in case.must_contain_features
                    if any(f.lower() in feature.lower() for feature in missing)
                ]
                f_coverage = len(matched_f) / len(case.must_contain_features)
                details["missing_features"] = {
                    "coverage": f_coverage,
                    "matched": matched_f,
                    "all": missing,
                }
                score_components.append(f_coverage)

            # 5. User role detection
            if case.expected_user_roles:
                detected_users = self.users_fn(case.requirements, domain)
                matched_roles = [
                    r for r in case.expected_user_roles
                    if any(r.lower() in user.lower() for user in detected_users)
                ]
                role_coverage = len(matched_roles) / len(case.expected_user_roles)
                details["user_roles"] = {
                    "coverage": role_coverage,
                    "matched": matched_roles,
                    "detected": detected_users,
                }
                score_components.append(role_coverage)

            # 6. Negative checks
            if case.must_not_contain:
                violations = [
                    term for term in case.must_not_contain
                    if term.lower() in json.dumps(details).lower()
                ]
                details["negative_checks"] = {
                    "violations": violations,
                    "clean": len(violations) == 0,
                }
                score_components.append(0.0 if violations else 1.0)

        except Exception as exc:
            errors.append(str(exc))
            logger.error("Evaluation case '%s' failed: %s", case.name, exc)

        duration_ms = (time.perf_counter() - start) * 1000
        avg_score = sum(score_components) / len(score_components) if score_components else 0.0

        return CaseResult(
            name=case.name,
            passed=avg_score >= 0.7 and not errors,
            score=round(avg_score, 3),
            details=details,
            duration_ms=round(duration_ms, 2),
            errors=errors,
        )

    def run_all(self, cases: list[GoldenCase]) -> EvaluationReport:
        """Run all golden cases and return aggregate report."""
        from datetime import datetime
        started = datetime.now().isoformat()
        results = [self.run_case(c) for c in cases]
        finished = datetime.now().isoformat()

        report = EvaluationReport(
            cases=results,
            started_at=started,
            finished_at=finished,
        )

        logger.info(report.summary())
        return report
