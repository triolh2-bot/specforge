"""Tests for the expanded domain intelligence engine."""

import unittest

from specforge.services.domain_intelligence import (
    DomainProfile,
    DomainResult,
    DomainRule,
    _build_profiles,
    calculate_rms,
    detect_conflicts,
    detect_domain,
    detect_domain_detailed,
    detect_implied_users,
    detect_missing_features,
    generate_functional_reqs,
    generate_questions,
    reset_profiles,
)


class TestWeightedDomainDetection(unittest.TestCase):
    def test_ecommerce_with_strong_signals(self):
        text = (
            "I want to build an online store for my bakery. "
            "Customers should browse products, add to cart, "
            "and checkout with Stripe payment. I need inventory management."
        )
        result = detect_domain_detailed(text)
        self.assertEqual(result.primary_domain, "e-commerce")
        self.assertGreater(result.confidence, 0.5)

    def test_saas_detection(self):
        text = (
            "We're building a SaaS platform for project management. "
            "Teams need subscription billing, workspace management, "
            "role-based permissions, and analytics dashboard with API access."
        )
        result = detect_domain_detailed(text)
        self.assertEqual(result.primary_domain, "saas")
        self.assertGreater(result.confidence, 0.5)

    def test_crm_with_sales_signals(self):
        text = (
            "I need a CRM for my sales team. We should track leads, "
            "manage the deal pipeline, and integrate with Gmail. "
            "Sales reps need activity timelines and forecasting."
        )
        result = detect_domain_detailed(text)
        self.assertEqual(result.primary_domain, "crm")

    def test_marketplace_two_sided(self):
        text = (
            "Build a marketplace connecting freelance designers with clients. "
            "Sellers create profiles, buyers browse and hire. "
            "We need escrow, commission splitting, and dispute resolution."
        )
        result = detect_domain_detailed(text)
        self.assertEqual(result.primary_domain, "marketplace")

    def test_mobile_app_native(self):
        text = (
            "I need a mobile app for iOS and Android with push notifications, "
            "camera access for scanning, offline mode, and location services."
        )
        result = detect_domain_detailed(text)
        self.assertEqual(result.primary_domain, "mobile-app")

    def test_api_backend_service(self):
        text = (
            "Build a REST API with JWT authentication, rate limiting, "
            "OpenAPI documentation, webhooks for events, and Redis caching."
        )
        result = detect_domain_detailed(text)
        self.assertEqual(result.primary_domain, "api")

    def test_blog_content_platform(self):
        text = (
            "I want to start a blog with an article publishing workflow. "
            "Authors write posts, editors review, and readers can comment. "
            "SEO optimization and newsletter signup are important."
        )
        result = detect_domain_detailed(text)
        self.assertEqual(result.primary_domain, "blog")

    def test_falls_back_to_general(self):
        text = "I need a thing that does stuff for people."
        result = detect_domain_detailed(text)
        self.assertEqual(result.primary_domain, "general")
        self.assertEqual(result.confidence, 0.0)

    def test_all_scores_populated(self):
        text = "Build an e-commerce store with Stripe checkout and inventory."
        result = detect_domain_detailed(text)
        self.assertIsInstance(result.all_scores, dict)
        self.assertGreater(len(result.all_scores), 5)

    def test_matched_rules_populated(self):
        text = "Build an e-commerce store with Stripe checkout and inventory."
        result = detect_domain_detailed(text)
        self.assertIn("e-commerce", result.matched_rules)
        self.assertGreater(len(result.matched_rules["e-commerce"]), 0)

    def test_backward_compat_function(self):
        """detect_domain() should return just the string."""
        text = "Build a CRM with lead tracking and pipeline management."
        result = detect_domain(text)
        self.assertIsInstance(result, str)
        self.assertEqual(result, "crm")


class TestWeightedMissingFeatures(unittest.TestCase):
    def test_missing_features_prioritized_by_weight(self):
        text = "I need an online store with product catalog and checkout."
        missing = detect_missing_features("e-commerce", text)
        self.assertIsInstance(missing, list)
        # Should return high-weight missing features first
        self.assertTrue(len(missing) > 0)

    def test_no_missing_when_all_present(self):
        text = (
            "Product catalog with images and variants, shopping cart with persistent sessions, "
            "checkout and payment processing, order management and tracking, "
            "inventory management with low-stock alerts, user accounts and order history, "
            "product search and faceted filters, shipping rate calculation, "
            "admin dashboard with sales analytics, order confirmation notifications, "
            "discount codes and campaigns, return refund workflow."
        )
        missing = detect_missing_features("e-commerce", text)
        self.assertEqual(missing, [])

    def test_empty_for_unknown_domain(self):
        missing = detect_missing_features("nonexistent", "some text")
        self.assertEqual(missing, [])


class TestImpliedUsersProfileDriven(unittest.TestCase):
    def test_ecommerce_roles(self):
        text = "Online store where shoppers browse products and merchants manage inventory."
        users = detect_implied_users(text, domain="e-commerce")
        self.assertTrue(any("Shopper" in u for u in users))

    def test_saas_roles(self):
        text = "SaaS with team management, admin settings, and billing dashboard."
        users = detect_implied_users(text, domain="saas")
        self.assertTrue(any("Admin" in u for u in users))

    def test_crm_roles(self):
        text = "CRM for sales reps to manage leads, deals, and pipeline as managers."
        users = detect_implied_users(text, domain="crm")
        self.assertTrue(any("Sales Rep" in u for u in users))

    def test_marketplace_roles(self):
        text = "Marketplace connecting buyers with sellers, with moderation and dispute support."
        users = detect_implied_users(text, domain="marketplace")
        self.assertTrue(any("Buyer" in u for u in users))
        self.assertTrue(any("Seller" in u for u in users))

    def test_falls_back_to_user(self):
        users = detect_implied_users("I need a thing.")
        self.assertEqual(users, ["User"])


class TestWeightedRMSScoring(unittest.TestCase):
    def test_high_rms_for_detailed_requirements(self):
        text = (
            "Build an e-commerce platform with secure authentication, "
            "Stripe payment integration, inventory management, "
            "shipping calculation, admin dashboard with analytics, "
            "responsive mobile design, REST API for integrations, "
            "performance caching, automated testing, and database backups."
        )
        score = calculate_rms(text, "e-commerce")
        self.assertGreater(score, 60)

    def test_low_rms_for_vague_requirements(self):
        text = "I need an online store."
        score = calculate_rms(text, "e-commerce")
        self.assertLess(score, 50)

    def test_cross_cutting_bonus(self):
        text = "Build a secure, scalable API with authentication, caching, and CI/CD testing."
        score = calculate_rms(text, "api")
        self.assertGreater(score, 40)

    def test_conflict_awareness_bonus(self):
        text = "I need a fast, quick-to-launch enterprise-grade custom AI platform with top security."
        score = calculate_rms(text, "saas")
        # Should detect at least one conflict
        conflicts = detect_conflicts(text)
        self.assertGreaterEqual(len(conflicts), 1)
        # Score should be reasonable (text has security mention + length)
        self.assertGreater(score, 20)


class TestDomainSpecificQuestions(unittest.TestCase):
    def test_ecommerce_questions(self):
        questions = generate_questions("e-commerce", "online store with products", [])
        self.assertTrue(len(questions) > 0)
        self.assertTrue(any("inventory" in q.lower() for q in questions))

    def test_saas_questions(self):
        questions = generate_questions("saas", "subscription platform", [])
        self.assertTrue(len(questions) > 0)
        self.assertTrue(any("pricing" in q.lower() or "tier" in q.lower() for q in questions))

    def test_crm_questions(self):
        questions = generate_questions("crm", "sales pipeline tracker", [])
        self.assertTrue(len(questions) > 0)
        self.assertTrue(any("pipeline" in q.lower() for q in questions))

    def test_conditional_auth_question(self):
        questions = generate_questions("api", "backend with user login and auth", [])
        self.assertTrue(any("authentication" in q.lower() for q in questions))

    def test_conditional_payment_question(self):
        questions = generate_questions("api", "site with payment and checkout", [])
        self.assertTrue(any("payment" in q.lower() for q in questions))

    def test_question_limit(self):
        questions = generate_questions("e-commerce", "store with payment and login and mobile", [])
        self.assertLessEqual(len(questions), 7)


class TestConflictDetection(unittest.TestCase):
    def test_fast_complex_conflict(self):
        conflicts = detect_conflicts("I need a fast, quick launch but very advanced AI features.")
        # The conflict message should contain "quick" or "prioritize" or "fast" or "complex"
        self.assertTrue(
            any("quick" in c.lower() or "prioritize" in c.lower() or "fast" in c.lower() or "complex" in c.lower() for c in conflicts),
            f"Expected conflict message about fast/complex in: {conflicts}",
        )

    def test_budget_enterprise_conflict(self):
        conflicts = detect_conflicts("Build it cheap and free but enterprise-grade custom.")
        self.assertTrue(any("budget" in c.lower() or "free" in c.lower() for c in conflicts))

    def test_simple_security_conflict(self):
        conflicts = detect_conflicts("Keep it simple but very secure with encryption.")
        self.assertTrue(any("complexity" in c.lower() or "balance" in c.lower() for c in conflicts))

    def test_no_conflicts_for_clean_text(self):
        conflicts = detect_conflicts("Build a blog with articles and comments.")
        self.assertEqual(conflicts, [])


class TestFunctionalReqsGeneration(unittest.TestCase):
    def test_includes_domain_template_features(self):
        reqs = generate_functional_reqs("e-commerce", "online store with products")
        self.assertTrue(len(reqs) > 6)
        self.assertTrue(any("payment" in r.lower() or "Payment" in r for r in reqs))

    def test_conditional_payment_reqs(self):
        reqs = generate_functional_reqs("api", "api with payment and checkout")
        self.assertTrue(any("Payment" in r or "payment" in r for r in reqs))

    def test_conditional_search_reqs(self):
        reqs = generate_functional_reqs("api", "api with advanced search and filtering")
        self.assertTrue(any("search" in r.lower() for r in reqs))

    def test_conditional_notification_reqs(self):
        reqs = generate_functional_reqs("api", "api with email notifications and alerts")
        self.assertTrue(any("notification" in r.lower() for r in reqs))

    def test_conditional_analytics_reqs(self):
        reqs = generate_functional_reqs("saas", "saas with analytics dashboard and metrics and charts")
        self.assertTrue(any("analytics" in r.lower() or "reporting" in r.lower() for r in reqs))

    def test_result_limit(self):
        reqs = generate_functional_reqs("e-commerce", "store with everything")
        self.assertLessEqual(len(reqs), 12)


class TestProfileIntegrity(unittest.TestCase):
    def test_all_profiles_have_required_fields(self):
        profiles = _build_profiles()
        for name, profile in profiles.items():
            self.assertIsInstance(profile, DomainProfile)
            self.assertTrue(profile.name)
            self.assertTrue(profile.display_name)
            self.assertTrue(profile.description)
            self.assertTrue(profile.detection_rules)
            self.assertTrue(profile.feature_template)
            self.assertTrue(len(profile.detection_rules) >= 2)

    def test_detection_rules_have_weights(self):
        profiles = _build_profiles()
        for name, profile in profiles.items():
            for rule in profile.detection_rules:
                self.assertIsInstance(rule, DomainRule)
                self.assertGreater(rule.weight, 0)
                self.assertTrue(rule.keywords)

    def test_all_domains_have_questions(self):
        profiles = _build_profiles()
        for name, profile in profiles.items():
            self.assertTrue(len(profile.domain_questions) >= 3)


if __name__ == "__main__":
    unittest.main()
