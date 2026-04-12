"""Tests for the SQL migration schema added in this PR.

Covers migrations/0001_create_analysis_records.sql:
- Table is created with the correct columns
- NOT NULL constraints are enforced
- Default values work as specified
- Primary key uniqueness is enforced
- Nullable columns accept NULL
- A complete valid record can be round-trip inserted and selected
"""
import sqlite3
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATION_0001 = REPO_ROOT / "migrations" / "0001_create_analysis_records.sql"

# Minimal valid record matching the schema in 0001
VALID_RECORD = {
    "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "request_id": "req-001",
    "status": "completed",
    "requirements_text": "Build an e-commerce store",
    "ai_enhance_requested": 0,
    "ai_provider": None,
    "domain": "e-commerce",
    "rms": 65,
    "implied_users_json": '["Customer","Admin"]',
    "missing_features_json": '["Shopping cart","Payment"]',
    "clarification_questions_json": '["Which payment provider?"]',
    "conflicts_json": "[]",
    "prd_json": '{"title":"Project Specification Document"}',
    "ai_enhanced_json": None,
}


def _open_migrated_db():
    """Return an in-memory SQLite connection with 0001 migration applied."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    sql = MIGRATION_0001.read_text(encoding="utf-8")
    conn.executescript(sql)
    return conn


class MigrationFileTests(unittest.TestCase):
    """Tests that the migration SQL file itself is well-formed."""

    def test_migration_file_exists(self):
        """migrations/0001_create_analysis_records.sql must exist."""
        self.assertTrue(MIGRATION_0001.exists(), f"Migration file not found: {MIGRATION_0001}")

    def test_migration_file_is_not_empty(self):
        """Migration file must not be empty."""
        content = MIGRATION_0001.read_text(encoding="utf-8").strip()
        self.assertGreater(len(content), 0)

    def test_migration_creates_analysis_records_table(self):
        """SQL must contain CREATE TABLE analysis_records."""
        content = MIGRATION_0001.read_text(encoding="utf-8")
        self.assertIn("analysis_records", content)
        self.assertIn("CREATE TABLE", content.upper())

    def test_migration_uses_if_not_exists(self):
        """Migration must use CREATE TABLE IF NOT EXISTS for idempotence."""
        content = MIGRATION_0001.read_text(encoding="utf-8").upper()
        self.assertIn("IF NOT EXISTS", content)


class AnalysisRecordsSchemaTests(unittest.TestCase):
    """Tests that verify the analysis_records table structure after migration."""

    def setUp(self):
        self.conn = _open_migrated_db()
        self.conn.row_factory = sqlite3.Row

    def tearDown(self):
        self.conn.close()

    def _table_info(self):
        cursor = self.conn.execute("PRAGMA table_info(analysis_records)")
        return {row["name"]: row for row in cursor.fetchall()}

    def test_table_is_created(self):
        """The analysis_records table must exist after running the migration."""
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='analysis_records'"
        )
        row = cursor.fetchone()
        self.assertIsNotNone(row, "analysis_records table was not created")

    def test_migration_is_idempotent(self):
        """Running the migration SQL twice must not raise an error."""
        sql = MIGRATION_0001.read_text(encoding="utf-8")
        # Should not raise
        self.conn.executescript(sql)

    # --- Column existence ---

    def test_column_id_exists(self):
        cols = self._table_info()
        self.assertIn("id", cols)

    def test_column_created_at_exists(self):
        cols = self._table_info()
        self.assertIn("created_at", cols)

    def test_column_updated_at_exists(self):
        cols = self._table_info()
        self.assertIn("updated_at", cols)

    def test_column_request_id_exists(self):
        cols = self._table_info()
        self.assertIn("request_id", cols)

    def test_column_status_exists(self):
        cols = self._table_info()
        self.assertIn("status", cols)

    def test_column_requirements_text_exists(self):
        cols = self._table_info()
        self.assertIn("requirements_text", cols)

    def test_column_ai_enhance_requested_exists(self):
        cols = self._table_info()
        self.assertIn("ai_enhance_requested", cols)

    def test_column_ai_provider_exists(self):
        cols = self._table_info()
        self.assertIn("ai_provider", cols)

    def test_column_domain_exists(self):
        cols = self._table_info()
        self.assertIn("domain", cols)

    def test_column_rms_exists(self):
        cols = self._table_info()
        self.assertIn("rms", cols)

    def test_column_implied_users_json_exists(self):
        cols = self._table_info()
        self.assertIn("implied_users_json", cols)

    def test_column_missing_features_json_exists(self):
        cols = self._table_info()
        self.assertIn("missing_features_json", cols)

    def test_column_clarification_questions_json_exists(self):
        cols = self._table_info()
        self.assertIn("clarification_questions_json", cols)

    def test_column_conflicts_json_exists(self):
        cols = self._table_info()
        self.assertIn("conflicts_json", cols)

    def test_column_prd_json_exists(self):
        cols = self._table_info()
        self.assertIn("prd_json", cols)

    def test_column_ai_enhanced_json_exists(self):
        cols = self._table_info()
        self.assertIn("ai_enhanced_json", cols)

    def test_total_column_count(self):
        """Table should have exactly 16 columns as defined in the migration."""
        cols = self._table_info()
        self.assertEqual(len(cols), 16)

    # --- Primary key ---

    def test_id_is_primary_key(self):
        """id column must be the primary key."""
        cols = self._table_info()
        self.assertEqual(cols["id"]["pk"], 1)

    def test_no_other_primary_keys(self):
        """Only id should be the primary key."""
        cols = self._table_info()
        pk_cols = [name for name, info in cols.items() if info["pk"] > 0]
        self.assertEqual(pk_cols, ["id"])

    # --- NOT NULL constraints ---

    def test_status_is_not_null(self):
        cols = self._table_info()
        self.assertEqual(cols["status"]["notnull"], 1)

    def test_requirements_text_is_not_null(self):
        cols = self._table_info()
        self.assertEqual(cols["requirements_text"]["notnull"], 1)

    def test_ai_enhance_requested_is_not_null(self):
        cols = self._table_info()
        self.assertEqual(cols["ai_enhance_requested"]["notnull"], 1)

    def test_domain_is_not_null(self):
        cols = self._table_info()
        self.assertEqual(cols["domain"]["notnull"], 1)

    def test_rms_is_not_null(self):
        cols = self._table_info()
        self.assertEqual(cols["rms"]["notnull"], 1)

    def test_implied_users_json_is_not_null(self):
        cols = self._table_info()
        self.assertEqual(cols["implied_users_json"]["notnull"], 1)

    def test_missing_features_json_is_not_null(self):
        cols = self._table_info()
        self.assertEqual(cols["missing_features_json"]["notnull"], 1)

    def test_clarification_questions_json_is_not_null(self):
        cols = self._table_info()
        self.assertEqual(cols["clarification_questions_json"]["notnull"], 1)

    def test_conflicts_json_is_not_null(self):
        cols = self._table_info()
        self.assertEqual(cols["conflicts_json"]["notnull"], 1)

    def test_prd_json_is_not_null(self):
        cols = self._table_info()
        self.assertEqual(cols["prd_json"]["notnull"], 1)

    # --- Nullable columns ---

    def test_request_id_is_nullable(self):
        """request_id may be NULL (no incoming request context for worker jobs)."""
        cols = self._table_info()
        self.assertEqual(cols["request_id"]["notnull"], 0)

    def test_ai_provider_is_nullable(self):
        """ai_provider may be NULL when AI enhancement was not requested."""
        cols = self._table_info()
        self.assertEqual(cols["ai_provider"]["notnull"], 0)

    def test_ai_enhanced_json_is_nullable(self):
        """ai_enhanced_json may be NULL for non-AI-enhanced analyses."""
        cols = self._table_info()
        self.assertEqual(cols["ai_enhanced_json"]["notnull"], 0)

    # --- Default values ---

    def test_status_default_is_completed(self):
        """status column default must be 'completed'."""
        cols = self._table_info()
        # SQLite stores default as a quoted string
        self.assertIn("completed", cols["status"]["dflt_value"])

    def test_ai_enhance_requested_default_is_0(self):
        """ai_enhance_requested default must be 0 (False)."""
        cols = self._table_info()
        self.assertIn("0", str(cols["ai_enhance_requested"]["dflt_value"]))


class AnalysisRecordsCRUDTests(unittest.TestCase):
    """Tests that DML operations work correctly against the migration schema."""

    def setUp(self):
        self.conn = _open_migrated_db()
        self.conn.row_factory = sqlite3.Row

    def tearDown(self):
        self.conn.close()

    def _insert_valid(self, record=None):
        r = record or VALID_RECORD.copy()
        self.conn.execute(
            """
            INSERT INTO analysis_records (
                id, request_id, status, requirements_text, ai_enhance_requested,
                ai_provider, domain, rms, implied_users_json, missing_features_json,
                clarification_questions_json, conflicts_json, prd_json, ai_enhanced_json
            ) VALUES (
                :id, :request_id, :status, :requirements_text, :ai_enhance_requested,
                :ai_provider, :domain, :rms, :implied_users_json, :missing_features_json,
                :clarification_questions_json, :conflicts_json, :prd_json, :ai_enhanced_json
            )
            """,
            r,
        )
        self.conn.commit()

    def test_insert_valid_record_succeeds(self):
        """A complete valid record must insert without error."""
        self._insert_valid()
        cursor = self.conn.execute("SELECT COUNT(*) FROM analysis_records")
        self.assertEqual(cursor.fetchone()[0], 1)

    def test_inserted_record_can_be_selected_by_id(self):
        """An inserted record must be retrievable by its primary key."""
        self._insert_valid()
        cursor = self.conn.execute(
            "SELECT * FROM analysis_records WHERE id = ?", (VALID_RECORD["id"],)
        )
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["domain"], "e-commerce")
        self.assertEqual(row["rms"], 65)

    def test_defaults_are_applied_when_omitted(self):
        """status and ai_enhance_requested must use defaults when not provided."""
        self.conn.execute(
            """
            INSERT INTO analysis_records (
                id, requirements_text, domain, rms,
                implied_users_json, missing_features_json,
                clarification_questions_json, conflicts_json, prd_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "bbbbbbbb-0000-0000-0000-000000000000",
                "Minimal requirements",
                "general",
                40,
                "[]",
                "[]",
                "[]",
                "[]",
                "{}",
            ),
        )
        self.conn.commit()
        cursor = self.conn.execute(
            "SELECT status, ai_enhance_requested FROM analysis_records WHERE id = ?",
            ("bbbbbbbb-0000-0000-0000-000000000000",),
        )
        row = cursor.fetchone()
        self.assertEqual(row["status"], "completed")
        self.assertEqual(row["ai_enhance_requested"], 0)

    def test_nullable_columns_accept_null(self):
        """request_id, ai_provider, and ai_enhanced_json must accept NULL."""
        r = VALID_RECORD.copy()
        r["id"] = "cccccccc-0000-0000-0000-000000000000"
        r["request_id"] = None
        r["ai_provider"] = None
        r["ai_enhanced_json"] = None
        self._insert_valid(r)

        cursor = self.conn.execute(
            "SELECT request_id, ai_provider, ai_enhanced_json FROM analysis_records WHERE id = ?",
            (r["id"],),
        )
        row = cursor.fetchone()
        self.assertIsNone(row["request_id"])
        self.assertIsNone(row["ai_provider"])
        self.assertIsNone(row["ai_enhanced_json"])

    def test_duplicate_primary_key_is_rejected(self):
        """Inserting two records with the same id must raise an IntegrityError."""
        self._insert_valid()
        with self.assertRaises(sqlite3.IntegrityError):
            self._insert_valid()  # Same id as VALID_RECORD

    def test_requirements_text_not_null_violation_raises(self):
        """Omitting requirements_text must raise an IntegrityError."""
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                """
                INSERT INTO analysis_records (id, domain, rms,
                    implied_users_json, missing_features_json,
                    clarification_questions_json, conflicts_json, prd_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "dddddddd-0000-0000-0000-000000000000",
                    "general", 40, "[]", "[]", "[]", "[]", "{}",
                ),
            )

    def test_domain_not_null_violation_raises(self):
        """Omitting domain must raise an IntegrityError."""
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                """
                INSERT INTO analysis_records (id, requirements_text, rms,
                    implied_users_json, missing_features_json,
                    clarification_questions_json, conflicts_json, prd_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "eeeeeeee-0000-0000-0000-000000000000",
                    "Some text", 40, "[]", "[]", "[]", "[]", "{}",
                ),
            )

    def test_rms_not_null_violation_raises(self):
        """Omitting rms must raise an IntegrityError."""
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                """
                INSERT INTO analysis_records (id, requirements_text, domain,
                    implied_users_json, missing_features_json,
                    clarification_questions_json, conflicts_json, prd_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "ffffffff-0000-0000-0000-000000000000",
                    "Some text", "general", "[]", "[]", "[]", "[]", "{}",
                ),
            )

    def test_prd_json_not_null_violation_raises(self):
        """Omitting prd_json must raise an IntegrityError."""
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                """
                INSERT INTO analysis_records (id, requirements_text, domain, rms,
                    implied_users_json, missing_features_json,
                    clarification_questions_json, conflicts_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "gggggggg-0000-0000-0000-000000000000",
                    "Some text", "general", 40, "[]", "[]", "[]", "[]",
                ),
            )

    def test_multiple_records_with_different_ids(self):
        """Multiple records with distinct primary keys must all be stored."""
        for i in range(3):
            r = VALID_RECORD.copy()
            r["id"] = f"rec{i:05d}-0000-0000-0000-000000000000"[:36]
            r["domain"] = ["e-commerce", "saas", "crm"][i]
            self._insert_valid(r)

        cursor = self.conn.execute("SELECT COUNT(*) FROM analysis_records")
        self.assertEqual(cursor.fetchone()[0], 3)

    def test_ai_enhance_requested_stores_true_value(self):
        """ai_enhance_requested must store 1 (True) when set."""
        r = VALID_RECORD.copy()
        r["id"] = "hhhhhhhh-0000-0000-0000-000000000000"
        r["ai_enhance_requested"] = 1
        r["ai_provider"] = "minimax"
        self._insert_valid(r)
        cursor = self.conn.execute(
            "SELECT ai_enhance_requested, ai_provider FROM analysis_records WHERE id = ?",
            (r["id"],),
        )
        row = cursor.fetchone()
        self.assertEqual(row["ai_enhance_requested"], 1)
        self.assertEqual(row["ai_provider"], "minimax")

    def test_rms_stores_boundary_values(self):
        """rms should store boundary values 0 and 100 without error."""
        for rms_val, uid in [(0, "iiiiiiii"), (100, "jjjjjjjj")]:
            r = VALID_RECORD.copy()
            r["id"] = f"{uid}-0000-0000-0000-000000000000"[:36]
            r["rms"] = rms_val
            self._insert_valid(r)

        cursor = self.conn.execute(
            "SELECT rms FROM analysis_records WHERE id IN (?, ?)",
            ("iiiiiiii-0000-0000-0000-000000000000"[:36],
             "jjjjjjjj-0000-0000-0000-000000000000"[:36]),
        )
        rows = cursor.fetchall()
        rms_values = {row["rms"] for row in rows}
        self.assertIn(0, rms_values)
        self.assertIn(100, rms_values)


if __name__ == "__main__":
    unittest.main()