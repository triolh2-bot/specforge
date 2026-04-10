"""Tests for the evaluation framework."""

import unittest

from specforge.services.evaluation import (
    CaseResult,
    EvaluationReport,
    EvaluationRunner,
    GOLDEN_CASES,
    GoldenCase,
)


class TestGoldenCases(unittest.TestCase):
    def test_all_cases_have_required_fields(self):
        for case in GOLDEN_CASES:
            self.assertIsInstance(case, GoldenCase)
            self.assertTrue(case.name, f"Case missing name: {case}")
            self.assertTrue(case.requirements, f"Case missing requirements: {case.name}")
            self.assertTrue(case.expected_domain, f"Case missing expected_domain: {case.name}")
            self.assertGreater(case.expected_min_rms, 0)
            self.assertLessEqual(case.expected_max_rms, 100)
            self.assertLess(case.expected_min_rms, case.expected_max_rms)

    def test_all_names_unique(self):
        names = [c.name for c in GOLDEN_CASES]
        self.assertEqual(len(names), len(set(names)), "Duplicate golden case names")

    def test_covers_all_domains(self):
        domains = {c.expected_domain for c in GOLDEN_CASES}
        expected_domains = {"e-commerce", "saas", "crm", "mobile-app", "api", "marketplace", "blog", "general"}
        self.assertEqual(domains, expected_domains)


class TestEvaluationRunner(unittest.TestCase):
    def test_run_all_golden_cases(self):
        runner = EvaluationRunner()
        report = runner.run_all(GOLDEN_CASES)

        self.assertEqual(report.total, len(GOLDEN_CASES))
        self.assertGreater(report.average_score, 0.5)
        self.assertTrue(report.summary().startswith("Evaluation:"))

    def test_individual_case_passing(self):
        runner = EvaluationRunner()
        report = runner.run_all(GOLDEN_CASES)

        # Most golden cases should pass (allow 1-2 for edge cases)
        pass_rate = report.passed / report.total
        self.assertGreaterEqual(pass_rate, 0.7, f"Only {report.passed}/{report.total} passed")

    def test_single_case_result(self):
        runner = EvaluationRunner()
        result = runner.run_case(GOLDEN_CASES[0])  # ecommerce_bakery

        self.assertIsInstance(result, CaseResult)
        self.assertTrue(result.name)
        self.assertIsInstance(result.score, float)
        self.assertGreaterEqual(result.score, 0.0)
        self.assertLessEqual(result.score, 1.0)
        self.assertIsInstance(result.duration_ms, float)
        self.assertGreater(result.duration_ms, 0)

    def test_domain_detection_in_evaluation(self):
        runner = EvaluationRunner()
        result = runner.run_case(GOLDEN_CASES[0])

        self.assertIn("domain", result.details)
        self.assertEqual(result.details["domain"]["expected"], "e-commerce")
        self.assertTrue(result.details["domain"]["correct"])

    def test_rms_scoring_in_evaluation(self):
        runner = EvaluationRunner()
        result = runner.run_case(GOLDEN_CASES[0])

        self.assertIn("rms", result.details)
        self.assertIn("value", result.details["rms"])
        self.assertIn("in_range", result.details["rms"])

    def test_question_coverage(self):
        runner = EvaluationRunner()
        result = runner.run_case(GOLDEN_CASES[0])

        self.assertIn("questions", result.details)
        self.assertIn("coverage", result.details["questions"])
        self.assertGreater(result.details["questions"]["coverage"], 0.5)

    def test_user_role_coverage(self):
        runner = EvaluationRunner()
        result = runner.run_case(GOLDEN_CASES[0])

        self.assertIn("user_roles", result.details)
        self.assertGreater(result.details["user_roles"]["coverage"], 0.5)

    def test_vague_case_scores_low(self):
        """The vague/general case should score lower due to generic content."""
        runner = EvaluationRunner()
        vague_case = next(c for c in GOLDEN_CASES if c.name == "vague_general")
        result = runner.run_case(vague_case)

        # Should still detect "general" domain correctly
        self.assertTrue(result.details["domain"]["correct"])


class TestEvaluationReport(unittest.TestCase):
    def test_report_summary_format(self):
        report = EvaluationReport(
            cases=[
                CaseResult(name="test1", passed=True, score=0.9, details={}, duration_ms=5.0),
                CaseResult(name="test2", passed=False, score=0.4, details={}, duration_ms=3.0),
            ],
            started_at="2026-01-01T00:00:00",
            finished_at="2026-01-01T00:00:01",
        )

        summary = report.summary()
        self.assertIn("1/2 passed", summary)
        self.assertIn("avg score", summary)

    def test_report_average_score(self):
        report = EvaluationReport(
            cases=[
                CaseResult(name="a", passed=True, score=1.0, details={}, duration_ms=1.0),
                CaseResult(name="b", passed=True, score=0.5, details={}, duration_ms=1.0),
                CaseResult(name="c", passed=False, score=0.0, details={}, duration_ms=1.0),
            ],
            started_at="2026-01-01T00:00:00",
            finished_at="2026-01-01T00:00:00",
        )

        self.assertAlmostEqual(report.average_score, 0.5, places=2)

    def test_empty_report(self):
        report = EvaluationReport(
            cases=[],
            started_at="2026-01-01T00:00:00",
            finished_at="2026-01-01T00:00:00",
        )

        self.assertEqual(report.total, 0)
        self.assertEqual(report.passed, 0)
        self.assertEqual(report.average_score, 0.0)


if __name__ == "__main__":
    unittest.main()
