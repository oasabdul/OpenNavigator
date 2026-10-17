#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${DEPLOY_HOST:-opennikkah}"
REMOTE="${DEPLOY_PATH:-/opt/opennavigator}"
DRY_RUN="${DRY_RUN:-0}"

echo "==> Local checks"
cd "$ROOT/backend"
"$ROOT/.venv/bin/ruff" check .
"$ROOT/.venv/bin/pytest" -q

cd "$ROOT/frontend"
pnpm install --frozen-lockfile --silent
pnpm typecheck
pnpm test
pnpm build

echo "==> Sync backend source"
RSYNC_FLAGS=(-az --delete --itemize-changes)
if [[ "$DRY_RUN" == "1" ]]; then
  RSYNC_FLAGS+=(--dry-run)
fi
rsync "${RSYNC_FLAGS[@]}" \
  --exclude '.env' \
  --exclude 'var/' \
  --exclude '__pycache__/' \
  --exclude '.pytest_cache/' \
  --exclude '.ruff_cache/' \
  --exclude '*.sqlite3' \
  "$ROOT/backend/" "$HOST:$REMOTE/backend/"

echo "==> Sync frontend build"
rsync "${RSYNC_FLAGS[@]}" "$ROOT/frontend/dist/" "$HOST:$REMOTE/frontend/dist/"

echo "==> Sync backup script"
rsync -az "$ROOT/deploy/scripts/backup.sh" "$HOST:$REMOTE/scripts/backup.sh"

if [[ "$DRY_RUN" == "1" ]]; then
  echo "Dry run complete; no remote changes were made."
  exit 0
fi

echo "==> Install dependencies, migrate, restart"
ssh "$HOST" 'bash -s' <<'REMOTE'
set -euo pipefail
cd /opt/opennavigator
test -f .env || { echo "Missing /opt/opennavigator/.env" >&2; exit 1; }

if [[ ! -x venv/bin/python ]]; then
  runuser -u opennavigator -- python3 -m venv /opt/opennavigator/venv
  runuser -u opennavigator -- /opt/opennavigator/venv/bin/pip install --upgrade pip
fi

runuser -u opennavigator -- /opt/opennavigator/venv/bin/pip install -q \
  -r /opt/opennavigator/backend/requirements.txt

chown -R opennavigator:opennavigator /opt/opennavigator
chmod 755 /opt/opennavigator
chmod -R a+rX /opt/opennavigator/frontend/dist

runuser -u opennavigator -- bash -c '
  set -a
  . /opt/opennavigator/.env
  set +a
  /opt/opennavigator/venv/bin/python /opt/opennavigator/backend/manage.py migrate --noinput
'

systemctl restart opennavigator-web

for _ in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsS http://127.0.0.1:8010/api/v1/health/ >/dev/null; then
    echo "Health check: ok"
    exit 0
  fi
  sleep 1
done

echo "Health check failed" >&2
journalctl -u opennavigator-web -n 50 --no-pager >&2
exit 1
REMOTE

echo "Deployment complete: https://opennavigator.206.81.6.97.sslip.io"
