from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parent.parent


class CiAssetTests(unittest.TestCase):
    def test_ci_workflow_contains_lint_test_and_build_jobs(self):
        workflow = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

        self.assertIn("lint:", workflow)
        self.assertIn("test:", workflow)
        self.assertIn("build:", workflow)
        self.assertIn("python -m pytest -q", workflow)
        self.assertIn("docker build -t specforge:${{ github.sha }} .", workflow)

    def test_release_workflow_tags_main_pushes(self):
        workflow = (REPO_ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")

        self.assertIn("workflow_run:", workflow)
        self.assertIn("workflows: [\"CI\"]", workflow)
        self.assertIn("git tag", workflow)
        self.assertIn("git push origin", workflow)

    def test_ci_cd_doc_lists_required_checks(self):
        doc = (REPO_ROOT / "docs/ci-cd.md").read_text(encoding="utf-8")

        self.assertIn("CI / lint", doc)
        self.assertIn("CI / test", doc)
        self.assertIn("CI / build", doc)
        self.assertIn("Security / security", doc)

    # --- Security workflow (.github/workflows/security.yml) ---

    def test_security_workflow_file_exists(self):
        self.assertTrue((REPO_ROOT / ".github/workflows/security.yml").exists())

    def test_security_workflow_runs_bandit(self):
        workflow = (REPO_ROOT / ".github/workflows/security.yml").read_text(encoding="utf-8")

        self.assertIn("bandit", workflow)

    def test_security_workflow_runs_pip_audit(self):
        workflow = (REPO_ROOT / ".github/workflows/security.yml").read_text(encoding="utf-8")

        self.assertIn("pip-audit", workflow)

    def test_security_workflow_runs_detect_secrets(self):
        workflow = (REPO_ROOT / ".github/workflows/security.yml").read_text(encoding="utf-8")

        self.assertIn("detect-secrets", workflow)

    def test_security_workflow_triggers_on_main_push(self):
        workflow = (REPO_ROOT / ".github/workflows/security.yml").read_text(encoding="utf-8")

        self.assertIn('"main"', workflow)

    def test_security_workflow_triggers_on_pull_request(self):
        workflow = (REPO_ROOT / ".github/workflows/security.yml").read_text(encoding="utf-8")

        self.assertIn("pull_request", workflow)

    def test_security_workflow_uses_bandit_config(self):
        """Security workflow must reference the .bandit config file."""
        workflow = (REPO_ROOT / ".github/workflows/security.yml").read_text(encoding="utf-8")

        self.assertIn(".bandit", workflow)

    def test_security_workflow_uses_secrets_baseline(self):
        """Security workflow must reference .secrets.baseline for detect-secrets."""
        workflow = (REPO_ROOT / ".github/workflows/security.yml").read_text(encoding="utf-8")

        self.assertIn(".secrets.baseline", workflow)

    def test_bandit_config_excludes_tests_directory(self):
        """The .bandit config must exclude the tests/ directory from scanning."""
        bandit_config = (REPO_ROOT / ".bandit").read_text(encoding="utf-8")

        self.assertIn("tests", bandit_config)

    def test_bandit_config_skips_b101(self):
        """The .bandit config must skip B101 (assert_used) — test assertions are not vulnerabilities."""
        bandit_config = (REPO_ROOT / ".bandit").read_text(encoding="utf-8")

        self.assertIn("B101", bandit_config)

    def test_secrets_baseline_file_exists(self):
        """detect-secrets baseline file must exist for the CI scan to work."""
        self.assertTrue((REPO_ROOT / ".secrets.baseline").exists())

    def test_secrets_baseline_is_valid_json(self):
        """The .secrets.baseline file must be valid JSON."""
        import json
        content = (REPO_ROOT / ".secrets.baseline").read_text(encoding="utf-8")
        data = json.loads(content)
        self.assertIn("version", data)
        self.assertIn("plugins_used", data)
        self.assertIn("results", data)

    def test_ci_workflow_syntax_gate_covers_app_and_specforge(self):
        """CI syntax gate must cover both app.py and the specforge package."""
        workflow = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

        self.assertIn("app.py", workflow)
        self.assertIn("specforge", workflow)

    def test_release_workflow_targets_main_branch_only(self):
        """Release tagging must only run when the triggering branch is main."""
        workflow = (REPO_ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")

        self.assertIn("main", workflow)

    def test_release_tag_format_includes_timestamp(self):
        """Release tag format must contain a date component for traceability."""
        workflow = (REPO_ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")

        # The release workflow uses date -u +%Y%m%d format
        self.assertIn("%Y%m%d", workflow)


if __name__ == "__main__":
    unittest.main()