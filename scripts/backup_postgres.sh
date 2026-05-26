#!/usr/bin/env bash
set -euo pipefail
# Usage: DB_NAME=labdb DB_USER=labuser BACKUP_DIR=/backups ./backup_postgres.sh
BACKUP_DIR="${BACKUP_DIR:-./backups}"
DB_NAME="${DB_NAME:-labdb}"
DB_USER="${DB_USER:-$USER}"
mkdir -p "$BACKUP_DIR"
STAMP=$(date +%F_%H-%M-%S)
pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_DIR/${DB_NAME}_${STAMP}.sql.gz"
echo "Backup written to $BACKUP_DIR/${DB_NAME}_${STAMP}.sql.gz"
