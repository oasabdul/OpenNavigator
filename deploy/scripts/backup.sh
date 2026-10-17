#!/usr/bin/env bash
set -euo pipefail
umask 077

BACKUP_DIR="/var/backups/opennavigator"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

install -d -m 750 "$BACKUP_DIR"

runuser -u postgres -- pg_dump \
  --format=custom \
  --no-owner \
  --dbname=opennavigator \
  > "$BACKUP_DIR/opennavigator-db-$STAMP.dump"

tar -czf "$BACKUP_DIR/opennavigator-var-$STAMP.tar.gz" \
  -C /opt/opennavigator var

find "$BACKUP_DIR" -type f -mtime +7 -delete
