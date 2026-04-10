import unittest
from unittest.mock import MagicMock, patch

from specforge import create_app
from specforge.services.ai_providers import ProviderResponse, registry


class TestConfig:
    SECRET_KEY = "test-secret"
    TESTING = True
    PORT = 5000
    MINIMAX_CLIENT_ID = ""
    MINIMAX_CLIENT_SECRET = ""
    MINIMAX_REDIRECT_URI = ""
    MINIMAX_AUTH_URL = "https://platform.minimaxi.com/oauth/authorize"
    MINIMAX_TOKEN_URL = "https://platform.minimaxi.com/oauth/token"
    MINIMAX_API_BASE = "https://api.minimaxi.com/v1"
    MINIMAX_API_KEY = ""
    MINIMAX_GROUP_ID = ""
    MINIMAX_CHAT_API_URL = "https://api.minimax.chat/v1/text/chatcompletion_v2"
    MINIMAX_MODEL = "MiniMax-M2.5"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MIGRATIONS_DIR = "migrations"


class PrdGenerationTests(unittest.TestCase):
    def setUp(self):
        # Reset registry before each test
        registry._providers.clear()
        registry._fallback_order.clear()

    def test_generate_prd_uses_rule_based_output_when_ai_is_disabled(self):
        app = create_app(TestConfig)
        with app.test_request_context("/"):
            from specforge.services.prd import generate_prd

            result = generate_prd(
                "Create a CRM for sales teams with contact management, reporting, and admin controls.",
                use_ai=False,
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["domain"], "crm")
        self.assertIsNone(result["ai_enhanced"])
        self.assertIn("functional_requirements", result["prd"])

    def test_generate_prd_marks_fallback_when_ai_call_returns_nothing(self):
        config = type("Config", (TestConfig,), {"MINIMAX_API_KEY": "test-key"})
        app = create_app(config)

        mock_provider = MagicMock()
        mock_provider.name = "minimax"
        mock_provider.display_name = "MiniMax AI"
        mock_provider.is_configured.return_value = True
        mock_provider.health_check.return_value = MagicMock(value=lambda: "healthy")
        mock_provider.capabilities = ()
        mock_provider.get_available_models.return_value = ()
        mock_provider.chat_completion.return_value = ProviderResponse(
            success=False, error="Provider unavailable"
        )
        registry.register(mock_provider)

        with app.test_request_context("/"):
            from specforge.services.prd import generate_prd

            result = generate_prd(
                "Create a SaaS app with subscriptions, billing, and team workspaces.",
                use_ai=True,
            )

        self.assertEqual(result["domain"], "saas")
        self.assertEqual(result["ai_enhanced"]["status"], "fallback")
        self.assertEqual(result["ai_enhanced"]["provider"], "minimax")

    def test_generate_prd_uses_ai_questions_when_provider_returns_them(self):
        config = type("Config", (TestConfig,), {"MINIMAX_API_KEY": "test-key"})
        app = create_app(config)

        ai_result = {
            "clarification_questions": [
                "What pricing tiers should be offered?",
                "Do you need SSO support?",
                "Should teams have separate workspaces?",
                "What reporting export formats are required?",
                "Do you need role-based permissions?",
                "Extra question that should be trimmed",
            ],
            "prd_summary": "AI summary",
            "tech_stack_recommendation": "Flask + Postgres",
            "risk_factors": ["Risk one", "Risk two", "Risk three", "Risk four"],
            "estimated_timeline": "10 weeks",
        }

        mock_provider = MagicMock()
        mock_provider.name = "minimax"
        mock_provider.display_name = "MiniMax AI"
        mock_provider.is_configured.return_value = True
        mock_provider.health_check.return_value = MagicMock(value=lambda: "healthy")
        mock_provider.capabilities = ()
        mock_provider.get_available_models.return_value = ()
        mock_provider.chat_completion.return_value = ProviderResponse(
            success=True, data=ai_result, model="test-model"
        )
        registry.register(mock_provider)

        with app.test_request_context("/"):
            from specforge.services.prd import generate_prd

            result = generate_prd(
                "Create a SaaS app with subscriptions, billing, and team workspaces.",
                use_ai=True,
            )

        self.assertEqual(result["ai_enhanced"]["status"], "success")
        self.assertEqual(result["clarification_questions"], ai_result["clarification_questions"][:5])
        self.assertEqual(result["prd"]["overview"]["summary"], "AI summary")
        self.assertEqual(result["prd"]["technical_constraints"]["tech_stack"], "Flask + Postgres")
        self.assertEqual(result["prd"]["technical_constraints"]["timeline"], "10 weeks")
        self.assertEqual(result["prd"]["risks"], ["Risk one", "Risk two", "Risk three"])


if __name__ == "__main__":
    unittest.main()
