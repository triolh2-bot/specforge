#!/bin/bash
# SpecForge PostgreSQL Backup Script
# This script performs a pg_dump of the database and manages rotation.

# Load environment variables if .env exists
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

DB_URL=${DATABASE_URL}
BACKUP_DIR=${BACKUP_DIR:-"./backups"}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="specforge_db_${TIMESTAMP}.sql.gz"
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-7}

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup to ${BACKUP_DIR}/${FILENAME}..."

# Perform backup using pg_dump via the connection string
# We use -c to include commands to clean (drop) database objects before recreating them.
if pg_dump "$DB_URL" -c | gzip > "${BACKUP_DIR}/${FILENAME}"; then
  echo "[$(date)] Backup completed successfully."
else
  echo "[$(date)] ERROR: Backup failed!"
  exit 1
fi

# Cleanup old backups
echo "[$(date)] Cleaning up backups older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -name "specforge_db_*.sql.gz" -mtime +"$RETENTION_DAYS" -exec rm {} \;

echo "[$(date)] Cleanup finished."
