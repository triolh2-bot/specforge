from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parent.parent


class DeploymentAssetTests(unittest.TestCase):
    def test_dockerfile_uses_gunicorn_web_process(self):
        dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn("FROM python:3.12-slim", dockerfile)
        self.assertIn("gunicorn", dockerfile)
        self.assertIn("app:app", dockerfile)

    def test_compose_declares_postgres_web_and_worker(self):
        compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

        self.assertIn("postgres:", compose)
        self.assertIn("web:", compose)
        self.assertIn("worker:", compose)
        self.assertIn("python\", \"-m\", \"specforge.worker", compose)
        self.assertIn("gunicorn\", \"--bind\", \"0.0.0.0:5000", compose)

    def test_env_example_documents_required_runtime_values(self):
        env_example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")

        self.assertIn("DATABASE_URL=", env_example)
        self.assertIn("SECRET_KEY=", env_example)
        self.assertIn("TOKEN_ENCRYPTION_SECRET=", env_example)


if __name__ == "__main__":
    unittest.main()
