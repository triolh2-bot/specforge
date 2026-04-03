from pathlib import Path

from sqlalchemy import text

from ..extensions import db


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
                    connection.exec_driver_sql(statement)
                connection.execute(
                    text("INSERT INTO schema_migrations (version) VALUES (:version)"),
                    {"version": version},
                )
