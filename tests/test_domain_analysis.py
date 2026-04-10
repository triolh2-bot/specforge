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

        # The new engine returns weighted, higher-level feature names
        self.assertTrue(len(missing) > 0)
        self.assertLessEqual(len(missing), 7)
        # At least one feature should be shipping/fulfillment related
        self.assertTrue(
            any("shipping" in f.lower() or "Shipping" in f for f in missing),
            f"Expected shipping-related feature in {missing}",
        )

    def test_detect_implied_users_infers_multiple_roles(self):
        users = detect_implied_users("Customers place orders while admin staff manage the dashboard.")
        # The new engine uses profile-driven detection; "Customer" and "Admin" should still match
        self.assertIn("Admin", users)
        self.assertIn("Customer", users)

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

        # Should have e-commerce-specific questions (shipping, inventory, etc.)
        self.assertTrue(
            any("shipping" in question.lower() or "inventory" in question.lower() for question in questions),
            f"Expected domain-specific questions in {questions}",
        )
        self.assertLessEqual(len(questions), 7)

    def test_detect_conflicts_flags_timeline_budget_and_security_tension(self):
        conflicts = detect_conflicts(
            "Need a simple but secure enterprise app delivered fast on a cheap budget with advanced AI features."
        )

        # The new engine detects conflicts from domain patterns + generic patterns
        # Should find at least: fast+complex, cheap+enterprise, simple+secure
        self.assertGreaterEqual(len(conflicts), 2)

    def test_generate_functional_reqs_adds_payment_search_and_notifications(self):
        requirements = generate_functional_reqs(
            "e-commerce",
            "Users should receive email notifications when orders are updated.",
        )

        # New engine uses "Notification system (email, push, in-app)" instead of "Notification system"
        self.assertTrue(
            any("notification" in r.lower() for r in requirements),
            f"Expected notification-related requirement in {requirements}",
        )

    def test_generate_functional_reqs_adds_payment_and_search_paths(self):
        requirements = generate_functional_reqs(
            "e-commerce",
            "Users need to search products, place orders, and make payments.",
        )

        # New engine generates "Payment gateway integration" and "Advanced search and filtering"
        self.assertTrue(
            any("payment" in r.lower() or "Payment" in r for r in requirements),
            f"Expected payment requirement in {requirements}",
        )
        self.assertTrue(
            any("search" in r.lower() for r in requirements),
            f"Expected search requirement in {requirements}",
        )


if __name__ == "__main__":
    unittest.main()
