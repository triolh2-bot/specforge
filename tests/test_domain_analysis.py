import unittest

from specforge.services.domain_analysis import (
    calculate_rms,
    detect_conflicts,
    detect_domain,
    detect_implied_users,
    detect_missing_features,
    generate_functional_reqs,
    generate_questions,
)


class DomainAnalysisTests(unittest.TestCase):
    def test_detect_domain_prefers_ecommerce_for_store_requirements(self):
        text = "Build an online bakery store where customers can order products, pay online, and manage inventory."
        self.assertEqual(detect_domain(text), "e-commerce")

    def test_detect_domain_falls_back_to_general_without_matching_keywords(self):
        self.assertEqual(detect_domain("Need help coordinating office moves and staff seating."), "general")

    def test_detect_missing_features_returns_domain_specific_gaps(self):
        missing = detect_missing_features("e-commerce", "Bakery store with product catalog, checkout, and admin dashboard.")

        self.assertIn("Shipping calculation", missing)
        self.assertLessEqual(len(missing), 7)

    def test_detect_implied_users_infers_multiple_roles(self):
        users = detect_implied_users("Customers place orders while admin staff manage the dashboard.")
        self.assertEqual(users, ["Admin", "Customer", "Employee"])

    def test_calculate_rms_rewards_specific_requirements(self):
        short_score = calculate_rms("Simple app.", "saas")
        detailed_score = calculate_rms(
            "SaaS platform with authentication, billing, analytics dashboard, API access, security controls, and mobile responsive support.",
            "saas",
        )

        self.assertGreater(detailed_score, short_score)
        self.assertLessEqual(detailed_score, 100)

    def test_generate_questions_includes_domain_specific_prompts(self):
        questions = generate_questions(
            "e-commerce",
            "E-commerce bakery storefront for browsing products and managing inventory.",
            ["Shipping calculation"],
        )

        self.assertTrue(any("shipping providers" in question for question in questions))
        self.assertLessEqual(len(questions), 5)

    def test_detect_conflicts_flags_timeline_budget_and_security_tension(self):
        conflicts = detect_conflicts(
            "Need a simple but secure enterprise app delivered fast on a cheap budget with advanced AI features."
        )

        self.assertGreaterEqual(len(conflicts), 3)

    def test_generate_functional_reqs_adds_payment_search_and_notifications(self):
        requirements = generate_functional_reqs(
            "e-commerce",
            "Users should receive email notifications when orders are updated.",
        )

        self.assertIn("Notification system", requirements)

    def test_generate_functional_reqs_adds_payment_and_search_paths(self):
        requirements = generate_functional_reqs(
            "e-commerce",
            "Users need to search products, place orders, and make payments.",
        )

        self.assertIn("Shopping cart functionality", requirements)
        self.assertIn("Advanced search and filtering", requirements)


if __name__ == "__main__":
    unittest.main()
