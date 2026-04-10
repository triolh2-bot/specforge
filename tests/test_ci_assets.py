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


if __name__ == "__main__":
    unittest.main()
