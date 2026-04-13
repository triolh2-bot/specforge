"""Frontend regression and E2E-style tests.

These tests verify the rendered HTML template, client-side JavaScript contracts,
accessibility structure, responsive behavior, and error state handling without
requiring a real browser. They use the Flask test client to render the full page
and assert on DOM structure, content, and API response shapes.

For full browser E2E tests (Playwright/Selenium), see docs/e2e-setup.md.
"""

import json
import os
import re
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from specforge import create_app
from specforge.extensions import db

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestConfig:
    SECRET_KEY = "test-secret"
    TESTING = True
    PORT = 5000
    TOKEN_ENCRYPTION_SECRET = "encryption-secret"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    OPENROUTER_API_KEY = ""
    OPENROUTER_MODEL = "openai/gpt-4o-mini"
    SQLALCHEMY_TRACK_MODIFICATIONS = False


# ---------------------------------------------------------------------------
# Minimal HTML parser for structural assertions
# ---------------------------------------------------------------------------

class _DOMExtractor(HTMLParser):
    """Extract tag info from HTML for structural testing."""

    def __init__(self):
        super().__init__()
        self.tags = []
        self.links = []
        self.scripts = []
        self.aria_roles = []
        self.labels = []
        self.headings = []
        self.forms = []
        self.buttons = []
        self.meta_viewport = False
        self.skip_link = False
        self.lang_attr = None

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        self.tags.append({"tag": tag, "attrs": attrs_dict})

        if tag == "a" and "href" in attrs_dict:
            self.links.append({"href": attrs_dict["href"], "text": ""})
        elif tag == "script" and "src" in attrs_dict:
            self.scripts.append(attrs_dict["src"])
        elif tag == "button":
            self.buttons.append(attrs_dict)
        elif tag == "form":
            self.forms.append(attrs_dict)

        role = attrs_dict.get("role")
        if role:
            self.aria_roles.append({"tag": tag, "role": role})

        aria_label = attrs_dict.get("aria-label")
        if aria_label:
            self.labels.append({"tag": tag, "label": aria_label})

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.headings.append({"tag": tag, "level": int(tag[1])})

        if tag == "meta" and attrs_dict.get("name") == "viewport":
            self.meta_viewport = True

        # Detect skip link
        if tag == "a" and "sr-only" in attrs_dict.get("class", ""):
            self.skip_link = True

    def handle_data(self, data):
        # Capture link text (simplified)
        if self.links and not self.links[-1]["text"]:
            self.links[-1]["text"] += data.strip()

    def get_html_lang(self):
        for t in self.tags:
            if t["tag"] == "html":
                return t["attrs"].get("lang")
        return None


def parse_html(html_text):
    """Parse HTML and return a _DOMExtractor instance."""
    parser = _DOMExtractor()
    parser.feed(html_text)
    return parser


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class FrontendStructureTests(unittest.TestCase):
    """Verify the rendered HTML template structure."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tempdir.name, "specforge-frontend.db")
        migrations_dir = str(REPO_ROOT / "migrations")

        class _Config(TestConfig):
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
            MIGRATIONS_DIR = migrations_dir

        self.app = create_app(_Config)
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.tempdir.cleanup()

    def _get_dom(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        return parse_html(resp.get_data(as_text=True))

    def test_page_renders_with_200(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn("<!DOCTYPE html>", html)

    def test_html_has_lang_attribute(self):
        dom = self._get_dom()
        self.assertEqual(dom.get_html_lang(), "en")

    def test_viewport_meta_present(self):
        dom = self._get_dom()
        self.assertTrue(dom.meta_viewport, "Missing <meta name='viewport'> tag")

    def test_skip_navigation_link(self):
        dom = self._get_dom()
        self.assertTrue(dom.skip_link, "Missing skip-navigation link for accessibility")

    def test_main_content_landmark(self):
        dom = self._get_dom()
        roles = [r["role"] for r in dom.aria_roles]
        self.assertIn("main", roles, "Missing main content landmark")

    def test_navigation_landmark(self):
        dom = self._get_dom()
        roles = [r["role"] for r in dom.aria_roles]
        self.assertIn("navigation", roles, "Missing navigation landmark")

    def test_banner_landmark(self):
        dom = self._get_dom()
        roles = [r["role"] for r in dom.aria_roles]
        self.assertIn("banner", roles, "Missing header/banner landmark")

    def test_primary_heading(self):
        dom = self._get_dom()
        h1s = [h for h in dom.headings if h["level"] == 1]
        self.assertGreaterEqual(len(h1s), 1, "Missing H1 heading")

    def test_requirements_textarea(self):
        dom = self._get_dom()
        textarea_tags = [t for t in dom.tags if t["tag"] == "textarea"]
        self.assertGreaterEqual(len(textarea_tags), 1, "Missing requirements textarea")
        # Check it has an id for label association
        ta = textarea_tags[0]
        self.assertIn("id", ta["attrs"], "Textarea should have an id")

    def test_analyze_button_present(self):
        dom = self._get_dom()
        analyze_btns = [
            b for b in dom.buttons
            if "analyze" in json.dumps(b).lower() or "Analyze" in json.dumps(b)
        ]
        # Also check for onclick
        onclick_btns = [
            t for t in dom.tags
            if t["tag"] == "button" and "analyze()" in t["attrs"].get("onclick", "")
        ]
        self.assertTrue(analyze_btns or onclick_btns, "Missing analyze button")

    def test_tab_list_structure(self):
        dom = self._get_dom()
        tablist = [r for r in dom.aria_roles if r["role"] == "tablist"]
        self.assertGreaterEqual(len(tablist), 1, "Missing tablist for results")
        tabs = [r for r in dom.aria_roles if r["role"] == "tab"]
        self.assertGreaterEqual(len(tabs), 2, "Should have at least 2 tabs")

    def test_sidebar_navigation_views(self):
        dom = self._get_dom()
        html_text = dom.tags.__repr__()  # Rough check
        self.assertTrue(
            any("analyze" in json.dumps(t).lower() for t in dom.tags),
            "Missing Analyze nav item",
        )
        self.assertTrue(
            any("history" in json.dumps(t).lower() for t in dom.tags),
            "Missing History nav item",
        )
        self.assertTrue(
            any("settings" in json.dumps(t).lower() for t in dom.tags),
            "Missing Settings nav item",
        )

    def test_footer_has_legal_links(self):
        dom = self._get_dom()
        html_text = " ".join(l["href"] for l in dom.links)
        self.assertIn("/legal/terms", html_text)
        self.assertIn("/legal/privacy", html_text)

    def test_no_hardcoded_personal_branding(self):
        dom = self._get_dom()
        html_text = self.client.get("/").get_data(as_text=True)
        # Should not contain personal handles from the prototype
        self.assertNotIn("fewic", html_text.lower())

    def test_loading_state_markup(self):
        dom = self._get_dom()
        html_text = self.client.get("/").get_data(as_text=True)
        self.assertIn('id="loading"', html_text, "Missing loading state element")
        self.assertIn("role=\"status\"", html_text, "Loading state should have aria-live role")

    def test_error_banner_markup(self):
        dom = self._get_dom()
        html_text = self.client.get("/").get_data(as_text=True)
        self.assertIn('id="error-banner"', html_text, "Missing error banner element")
        self.assertIn('role="alert"', html_text, "Error banner should have role=alert")

    def test_quota_warning_markup(self):
        dom = self._get_dom()
        html_text = self.client.get("/").get_data(as_text=True)
        self.assertIn('id="quota-warning"', html_text, "Missing quota warning element")

    def test_keyboard_shortcut_comment(self):
        """Verify Ctrl+Enter shortcut is wired in the JS."""
        html_text = self.client.get("/").get_data(as_text=True)
        self.assertIn("ctrlKey", html_text)
        self.assertIn("Enter", html_text)


class FrontendAPIContractTests(unittest.TestCase):
    """Verify that API responses match what the frontend JavaScript expects."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tempdir.name, "specforge-contract.db")
        migrations_dir = str(REPO_ROOT / "migrations")

        class _Config(TestConfig):
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
            MIGRATIONS_DIR = migrations_dir

        self.app = create_app(_Config)
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.tempdir.cleanup()

    def test_analyze_response_has_required_fields(self):
        resp = self.client.post(
            "/analyze",
            json={"requirements": "Build an e-commerce store.", "ai_enhance": False, "ai_provider": "openrouter"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        required = ["rms", "domain", "implied_users", "missing_features",
                     "clarification_questions", "prd", "success"]
        for field in required:
            self.assertIn(field, data, f"Missing required field: {field}")

    def test_prd_structure_has_nested_fields(self):
        resp = self.client.post(
            "/analyze",
            json={"requirements": "Build a blog platform.", "ai_enhance": False, "ai_provider": "openrouter"},
        )
        data = resp.get_json()
        prd = data["prd"]

        self.assertIn("overview", prd)
        self.assertIn("summary", prd["overview"])
        self.assertIn("project_type", prd["overview"])
        self.assertIn("target_users", prd["overview"])
        self.assertIn("scope", prd)
        self.assertIn("in_scope", prd["scope"])
        self.assertIn("out_of_scope", prd["scope"])
        self.assertIn("functional_requirements", prd)
        self.assertIn("non_functional", prd)
        self.assertIn("risks", prd)

    def test_history_response_structure(self):
        # Create an analysis first
        self.client.post(
            "/analyze",
            json={"requirements": "Build a CRM.", "ai_enhance": False, "ai_provider": "openrouter"},
        )
        resp = self.client.get("/api/analyses")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        self.assertIn("items", data)
        self.assertIn("pagination", data)
        self.assertIn("total", data["pagination"])

        if data["items"]:
            item = data["items"][0]
            self.assertIn("analysis_id", item)
            self.assertIn("domain", item)
            self.assertIn("rms", item)
            self.assertIn("created_at", item)

    def test_error_response_structure(self):
        resp = self.client.post(
            "/analyze",
            json={"requirements": "", "ai_enhance": False, "ai_provider": "openrouter"},
        )
        # Empty requirements should trigger validation error
        self.assertIn(resp.status_code, [400, 422])
        data = resp.get_json()
        self.assertIn("error", data)
        self.assertIn("code", data["error"])
        self.assertIn("message", data["error"])

    def test_billing_quota_response_structure(self):
        resp = self.client.get("/api/billing/quota")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("plan", data)
        self.assertIn("analyses", data)
        self.assertIn("used", data["analyses"])
        self.assertIn("limit", data["analyses"])

    def test_legal_policies_list(self):
        resp = self.client.get("/legal/policies")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("policies", data)
        self.assertGreaterEqual(len(data["policies"]), 3)


class ResponsiveLayoutTests(unittest.TestCase):
    """Verify responsive layout markers in the HTML."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tempdir.name, "specforge-responsive.db")
        migrations_dir = str(REPO_ROOT / "migrations")

        class _Config(TestConfig):
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
            MIGRATIONS_DIR = migrations_dir

        self.app = create_app(_Config)
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.tempdir.cleanup()

    def test_tailwind_responsive_classes(self):
        html = self.client.get("/").get_data(as_text=True)
        # Should use responsive utility classes
        self.assertTrue(
            re.search(r'md:', html) or re.search(r'lg:', html) or re.search(r'sm:', html),
            "Template should use Tailwind responsive breakpoint prefixes",
        )

    def test_mobile_menu_toggle(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn("mobile-menu-btn", html, "Missing mobile menu toggle button")
        self.assertIn("md:hidden", html, "Missing md:hidden class for mobile-only elements")

    def test_max_width_containers(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn("max-w-", html, "Missing max-width container classes")


class ErrorStateTests(unittest.TestCase):
    """Verify error states are properly represented in the frontend."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tempdir.name, "specforge-errors.db")
        migrations_dir = str(REPO_ROOT / "migrations")

        class _Config(TestConfig):
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
            MIGRATIONS_DIR = migrations_dir

        self.app = create_app(_Config)
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.tempdir.cleanup()

    def test_empty_requirements_rejected(self):
        resp = self.client.post(
            "/analyze",
            json={"requirements": "", "ai_enhance": False, "ai_provider": "openrouter"},
        )
        self.assertIn(resp.status_code, [400, 422])

    def test_missing_ai_provider_rejected(self):
        resp = self.client.post(
            "/analyze",
            json={"requirements": "test", "ai_enhance": False, "ai_provider": ""},
        )
        self.assertIn(resp.status_code, [400, 422])

    def test_404_page_exists(self):
        resp = self.client.get("/nonexistent-page-that-should-404")
        self.assertEqual(resp.status_code, 404)

    def test_health_endpoint_accessible(self):
        resp = self.client.get("/health")
        self.assertIn(resp.status_code, [200, 503])  # 503 is fine if DB not ready


if __name__ == "__main__":
    unittest.main()
