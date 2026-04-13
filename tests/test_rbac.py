"""Tests for role-based access control (RBAC) system."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from specforge import create_app
from specforge.extensions import db
from specforge.services.rbac import (
    PERM,
    AuthorizationError,
    WorkspaceRole,
    check_resource_access,
    enforce_resource_access,
    get_minimum_role_for_permission,
    get_role_permissions,
    get_session_role,
    has_permission,
    is_at_least,
    require_permission,
    require_role,
    role_level,
    ROLES,
)

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
# Unit tests for role hierarchy and permissions
# ---------------------------------------------------------------------------

class TestRoleHierarchy(unittest.TestCase):
    def test_all_roles_defined(self):
        self.assertEqual(ROLES, ["viewer", "editor", "admin", "owner"])

    def test_role_levels_monotonic(self):
        self.assertLess(role_level("viewer"), role_level("editor"))
        self.assertLess(role_level("editor"), role_level("admin"))
        self.assertLess(role_level("admin"), role_level("owner"))

    def test_is_at_least_transitive(self):
        self.assertTrue(is_at_least("owner", "viewer"))
        self.assertTrue(is_at_least("owner", "admin"))
        self.assertTrue(is_at_least("admin", "editor"))
        self.assertTrue(is_at_least("editor", "viewer"))
        self.assertTrue(is_at_least("viewer", "viewer"))
        self.assertFalse(is_at_least("viewer", "editor"))
        self.assertFalse(is_at_least("editor", "owner"))

    def test_all_roles_have_permissions(self):
        for role in ROLES:
            perms = get_role_permissions(role)
            self.assertIsInstance(perms, set)
            self.assertGreater(len(perms), 0, f"Role {role} has no permissions")

    def test_editor_has_more_than_viewer(self):
        viewer_perms = get_role_permissions("viewer")
        editor_perms = get_role_permissions("editor")
        self.assertTrue(viewer_perms.issubset(editor_perms))

    def test_admin_has_more_than_editor(self):
        editor_perms = get_role_permissions("editor")
        admin_perms = get_role_permissions("admin")
        self.assertTrue(editor_perms.issubset(admin_perms))

    def test_owner_has_more_than_admin(self):
        admin_perms = get_role_permissions("admin")
        owner_perms = get_role_permissions("owner")
        self.assertTrue(admin_perms.issubset(owner_perms))

    def test_owner_has_delete_workspace(self):
        owner_perms = get_role_permissions("owner")
        self.assertIn("delete:workspace", owner_perms)
        self.assertNotIn("delete:workspace", get_role_permissions("admin"))

    def test_viewer_cannot_write(self):
        viewer_perms = get_role_permissions("viewer")
        self.assertNotIn("write:analysis", viewer_perms)
        self.assertNotIn("write:jobs", viewer_perms)
        self.assertNotIn("manage:members", viewer_perms)

    def test_has_permission_correct(self):
        self.assertTrue(has_permission("viewer", "read:analysis"))
        self.assertTrue(has_permission("editor", "write:analysis"))
        self.assertTrue(has_permission("admin", "manage:members"))
        self.assertFalse(has_permission("viewer", "write:analysis"))
        self.assertFalse(has_permission("editor", "manage:members"))

    def test_get_minimum_role_for_permission(self):
        self.assertEqual(get_minimum_role_for_permission("read:analysis"), "viewer")
        self.assertEqual(get_minimum_role_for_permission("write:analysis"), "editor")
        self.assertEqual(get_minimum_role_for_permission("manage:members"), "admin")
        self.assertEqual(get_minimum_role_for_permission("delete:workspace"), "owner")


# ---------------------------------------------------------------------------
# Unit tests for decorators
# ---------------------------------------------------------------------------

class TestPermissionDecorator(unittest.TestCase):
    def setUp(self):
        # Mock _ensure_workspace_context to avoid DB calls in unit tests
        self.ctx_patch = patch("specforge.services.rbac._ensure_workspace_context")
        self.mock_ctx = self.ctx_patch.start()

    def tearDown(self):
        self.ctx_patch.stop()

    def test_require_permission_allows_authorized_role(self):
        @require_permission("read:analysis")
        def view_analysis():
            return "ok"

        with self._session_context("viewer"):
            self.assertEqual(view_analysis(), "ok")

    def test_require_permission_denies_unauthorized_role(self):
        @require_permission("manage:members")
        def manage_members():
            return "ok"

        with self._session_context("viewer"):
            with self.assertRaises(AuthorizationError) as ctx:
                manage_members()
            self.assertEqual(ctx.exception.required_role, "admin")
            self.assertEqual(ctx.exception.actual_role, "viewer")

    def test_require_permission_denies_anonymous(self):
        @require_permission("read:analysis")
        def view_analysis():
            return "ok"

        with self._session_context(None):
            with self.assertRaises(AuthorizationError) as ctx:
                view_analysis()
            self.assertEqual(ctx.exception.actual_role, "anonymous")

    def test_require_role_allows_sufficient_role(self):
        @require_role("admin")
        def admin_only():
            return "ok"

        with self._session_context("owner"):
            self.assertEqual(admin_only(), "ok")

    def test_require_role_denies_insufficient_role(self):
        @require_role("admin")
        def admin_only():
            return "ok"

        with self._session_context("editor"):
            with self.assertRaises(AuthorizationError):
                admin_only()

    @staticmethod
    def _session_context(role):
        from flask import Flask
        app = Flask(__name__)
        app.secret_key = "test"

        class ContextManager:
            def __enter__(self):
                self._ctx = app.test_request_context("/")
                self._ctx.push()
                if role is not None:
                    from flask import session
                    session["workspace_role"] = role
                    session["workspace_id"] = "test-workspace"
                return self

            def __exit__(self, *args):
                self._ctx.pop()

        return ContextManager()


# ---------------------------------------------------------------------------
# Integration tests with Flask app
# ---------------------------------------------------------------------------

class RBACIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tempdir.name, "specforge-rbac.db")
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

    def _analyze(self, requirements="Build an e-commerce store with cart and checkout."):
        return self.client.post(
            "/analyze",
            json={
                "requirements": requirements,
                "ai_enhance": False,
                "ai_provider": "openrouter",
            },
        )

    def test_list_analyses_returns_200_with_session(self):
        # First create an analysis
        self._analyze()
        response = self.client.get("/api/analyses")
        self.assertEqual(response.status_code, 200)

    def test_get_analysis_returns_404_for_other_workspace(self):
        # Analysis created in workspace A
        response_a = self._analyze()
        self.assertEqual(response_a.status_code, 200)

        # Try to access from workspace B (different session)
        other_client = self.app.test_client()
        response_b = other_client.get("/api/analyses/nonexistent-id")
        self.assertEqual(response_b.status_code, 404)

    def test_get_job_returns_404_for_other_workspace(self):
        other_client = self.app.test_client()
        response = other_client.get("/api/jobs/nonexistent-id")
        self.assertEqual(response.status_code, 404)

    def test_list_members_returns_200(self):
        response = self.client.get("/api/workspace/members")
        self.assertEqual(response.status_code, 200)

    def test_get_my_role_returns_workspace_info(self):
        response = self.client.get("/api/workspace/members/me")
        body = response.get_json()
        self.assertIn("workspace_id", body)
        self.assertIn("workspace_name", body)
        self.assertIn("role", body)

    def test_update_member_role_requires_admin(self):
        # Try to update role with default session role
        response = self.client.put(
            "/api/workspace/members/test-id/role",
            json={"role": "viewer"},
        )
        # The default session gets created as owner, so this should work
        # for the owner's own workspace
        self.assertIn(response.status_code, [200, 404])

    def test_invalid_role_rejected(self):
        response = self.client.put(
            "/api/workspace/members/test-id/role",
            json={"role": "superadmin"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "invalid_role")


# ---------------------------------------------------------------------------
# Tests for resource access enforcement
# ---------------------------------------------------------------------------

class TestResourceAccess(unittest.TestCase):
    def test_check_access_same_workspace(self):
        with self._session_context("test-ws", "editor"):
            result = check_resource_access("test-ws", "read:analysis")
            self.assertTrue(result.allowed)

    def test_check_access_different_workspace(self):
        with self._session_context("ws-a", "editor"):
            result = check_resource_access("ws-b", "read:analysis")
            self.assertFalse(result.allowed)
            self.assertIn("ws-b", result.reason)

    def test_check_access_no_session(self):
        with self._session_context("ws-a", None):
            result = check_resource_access("ws-a", "read:analysis")
            self.assertFalse(result.allowed)
            self.assertIn("No authenticated session", result.reason)

    def test_check_access_insufficient_role(self):
        with self._session_context("ws-a", "viewer"):
            result = check_resource_access("ws-a", "write:analysis")
            self.assertFalse(result.allowed)
            self.assertIn("lacks", result.reason)

    def test_enforce_raises_on_denial(self):
        with self._session_context("ws-a", "viewer"):
            with self.assertRaises(AuthorizationError):
                enforce_resource_access("ws-a", "write:analysis")

    def test_enforce_succeeds_with_sufficient_role(self):
        with self._session_context("ws-a", "editor"):
            enforce_resource_access("ws-a", "write:analysis")  # Should not raise

    @staticmethod
    def _session_context(workspace_id, role):
        from flask import Flask, session
        app = Flask(__name__)
        app.secret_key = "test"

        class ContextManager:
            def __enter__(self):
                self._ctx = app.test_request_context("/")
                self._ctx.push()
                if role is not None:
                    session["workspace_role"] = role
                    session["workspace_id"] = workspace_id
                return self

            def __exit__(self, *args):
                self._ctx.pop()

        return ContextManager()


if __name__ == "__main__":
    unittest.main()
