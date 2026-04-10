import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from ..extensions import db

logger = logging.getLogger(__name__)


def run_migrations(app):
    migrations_dir = Path(app.config["MIGRATIONS_DIR"])
    if not migrations_dir.exists():
        return

    with app.app_context():
        engine = db.engine
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version TEXT PRIMARY KEY,
                        applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )

            applied_versions = {
                row[0] for row in connection.execute(text("SELECT version FROM schema_migrations")).fetchall()
            }

            for migration_file in sorted(migrations_dir.glob("*.sql")):
                version = migration_file.stem
                if version in applied_versions:
                    continue

                sql_text = migration_file.read_text(encoding="utf-8")
                statements = [statement.strip() for statement in sql_text.split(";") if statement.strip()]
                for statement in statements:
                    try:
                        connection.exec_driver_sql(statement)
                    except OperationalError as exc:
                        # "Table already exists" and similar — safe to skip
                        logger.warning(
                            "Migration '%s' statement skipped (likely already applied): %s — %s",
                            version,
                            statement[:80],
                            exc,
                        )
                    except Exception as exc:
                        # Real errors — log and abort the migration
                        logger.error("Migration '%s' failed: %s — %s", version, statement[:80], exc)
                        raise
                connection.execute(
                    text("INSERT INTO schema_migrations (version) VALUES (:version)"),
                    {"version": version},
                )

        # Ensure all SQLAlchemy models have tables (fallback for in-memory or skipped migrations)
        db.create_all()
