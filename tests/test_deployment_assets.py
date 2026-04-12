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

    # --- .env.example: new variables added in this PR ---

    def test_env_example_documents_minimax_oauth_vars(self):
        env_example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")

        self.assertIn("MINIMAX_CLIENT_ID=", env_example)
        self.assertIn("MINIMAX_CLIENT_SECRET=", env_example)
        self.assertIn("MINIMAX_REDIRECT_URI=", env_example)

    def test_env_example_documents_paypal_billing_vars(self):
        env_example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")

        self.assertIn("PAYPAL_CLIENT_ID=", env_example)
        self.assertIn("PAYPAL_CLIENT_SECRET=", env_example)
        self.assertIn("PAYPAL_SANDBOX=", env_example)

    def test_env_example_documents_feature_flags(self):
        env_example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")

        self.assertIn("AI_ENHANCEMENT_ENABLED=", env_example)
        self.assertIn("MINIMAX_OAUTH_ENABLED=", env_example)
        self.assertIn("EXPORT_SHARING_ENABLED=", env_example)
        self.assertIn("ANALYTICS_ENABLED=", env_example)
        self.assertIn("QUOTA_ENFORCEMENT=", env_example)

    def test_env_example_documents_rate_limits(self):
        env_example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")

        self.assertIn("RATE_LIMIT_ANALYZE=", env_example)
        self.assertIn("RATE_LIMIT_MINIMAX_CHAT=", env_example)
        self.assertIn("RATE_LIMIT_AUTH_LOGIN=", env_example)

    def test_env_example_documents_health_thresholds(self):
        env_example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")

        self.assertIn("HEALTH_QUEUE_BACKLOG_WARNING=", env_example)
        self.assertIn("HEALTH_QUEUE_BACKLOG_CRITICAL=", env_example)
        self.assertIn("HEALTH_FAILED_JOBS_CRITICAL=", env_example)

    def test_env_example_documents_content_size_and_logging(self):
        env_example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")

        self.assertIn("MAX_CONTENT_LENGTH_BYTES=", env_example)
        self.assertIn("LOG_LEVEL=", env_example)

    def test_env_example_documents_app_version(self):
        env_example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")

        self.assertIn("APP_VERSION=", env_example)

    def test_env_example_documents_port(self):
        env_example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")

        self.assertIn("PORT=", env_example)

    # --- .dockerignore ---

    def test_dockerignore_file_exists(self):
        self.assertTrue((REPO_ROOT / ".dockerignore").exists())

    def test_dockerignore_excludes_env_file(self):
        """.dockerignore must exclude .env to prevent secrets leaking into the image."""
        dockerignore = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
        self.assertIn(".env", dockerignore)

    def test_dockerignore_excludes_git_directory(self):
        dockerignore = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
        self.assertIn(".git", dockerignore)

    def test_dockerignore_excludes_pycache(self):
        dockerignore = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
        self.assertIn("__pycache__", dockerignore)

    def test_dockerignore_excludes_sqlite_database(self):
        """The local SQLite database file must not be copied into the image."""
        dockerignore = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
        self.assertIn("specforge.db", dockerignore)

    def test_dockerignore_excludes_venv(self):
        dockerignore = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
        self.assertIn("venv", dockerignore)

    def test_dockerignore_excludes_github_workflows(self):
        dockerignore = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
        self.assertIn(".github", dockerignore)

    # --- Dockerfile security: non-root user ---

    def test_dockerfile_creates_non_root_user(self):
        """Dockerfile must create a non-root user to run the application."""
        dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("useradd", dockerfile)

    def test_dockerfile_switches_to_non_root_user(self):
        """Dockerfile must switch to the non-root user before running the app."""
        dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("USER specforge", dockerfile)

    def test_dockerfile_sets_pythondontwritebytecode(self):
        """Dockerfile must set PYTHONDONTWRITEBYTECODE to keep the image clean."""
        dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("PYTHONDONTWRITEBYTECODE=1", dockerfile)

    def test_dockerfile_sets_pythonunbuffered(self):
        """Dockerfile must set PYTHONUNBUFFERED for streaming log output."""
        dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("PYTHONUNBUFFERED=1", dockerfile)

    def test_dockerfile_exposes_port_5000(self):
        dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("EXPOSE 5000", dockerfile)

    def test_dockerfile_uses_slim_base_image(self):
        """Dockerfile should use a slim Python image to minimise attack surface."""
        dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("slim", dockerfile)

    # --- docker-compose.yml: base development stack ---

    def test_compose_health_check_uses_ready_endpoint(self):
        """Web healthcheck must probe /health/ready, not the legacy /health."""
        compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("/health/ready", compose)

    def test_compose_postgres_has_healthcheck(self):
        compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("pg_isready", compose)

    def test_compose_web_depends_on_postgres(self):
        compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("depends_on", compose)
        self.assertIn("service_healthy", compose)

    def test_compose_documents_database_url_env(self):
        compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("DATABASE_URL", compose)

    def test_compose_documents_secret_key_env(self):
        compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("SECRET_KEY", compose)

    def test_compose_documents_token_encryption_secret_env(self):
        compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("TOKEN_ENCRYPTION_SECRET", compose)

    # --- docker-compose.prod.yml: production-grade settings ---

    def test_prod_compose_file_exists(self):
        self.assertTrue((REPO_ROOT / "docker-compose.prod.yml").exists())

    def test_prod_compose_binds_web_to_localhost_only(self):
        """Production web must bind to 127.0.0.1 only (reverse proxy handles TLS)."""
        compose = (REPO_ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")
        self.assertIn("127.0.0.1:5000", compose)

    def test_prod_compose_has_resource_limits(self):
        compose = (REPO_ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")
        self.assertIn("resources", compose)
        self.assertIn("limits", compose)
        self.assertIn("memory", compose)

    def test_prod_compose_has_web_health_check(self):
        compose = (REPO_ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")
        self.assertIn("/health/ready", compose)

    def test_prod_compose_uses_restart_always(self):
        """Production containers must restart automatically after failure."""
        compose = (REPO_ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")
        self.assertIn("restart: always", compose)

    def test_prod_compose_declares_internal_network(self):
        """Production compose must use an internal network to isolate the database."""
        compose = (REPO_ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")
        self.assertIn("internal:", compose)

    def test_prod_compose_documents_token_encryption_secret_env(self):
        compose = (REPO_ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")
        self.assertIn("TOKEN_ENCRYPTION_SECRET", compose)

    # --- docker-compose.staging.yml: staging-specific settings ---

    def test_staging_compose_file_exists(self):
        self.assertTrue((REPO_ROOT / "docker-compose.staging.yml").exists())

    def test_staging_compose_uses_soft_quota_enforcement(self):
        """Staging must use soft quota enforcement to allow load testing."""
        compose = (REPO_ROOT / "docker-compose.staging.yml").read_text(encoding="utf-8")
        self.assertIn("QUOTA_ENFORCEMENT: soft", compose)

    def test_staging_compose_uses_debug_log_level(self):
        """Staging must enable DEBUG logging for troubleshooting."""
        compose = (REPO_ROOT / "docker-compose.staging.yml").read_text(encoding="utf-8")
        self.assertIn("LOG_LEVEL: DEBUG", compose)

    def test_staging_compose_has_smoke_test_service(self):
        """Staging must include a smoke-test service to validate each deployment."""
        compose = (REPO_ROOT / "docker-compose.staging.yml").read_text(encoding="utf-8")
        self.assertIn("smoke-test:", compose)

    def test_staging_compose_has_health_check(self):
        compose = (REPO_ROOT / "docker-compose.staging.yml").read_text(encoding="utf-8")
        self.assertIn("/health/ready", compose)

    def test_staging_compose_uses_separate_database(self):
        """Staging must use a separate database from production."""
        compose = (REPO_ROOT / "docker-compose.staging.yml").read_text(encoding="utf-8")
        self.assertIn("specforge_staging", compose)


if __name__ == "__main__":
    unittest.main()