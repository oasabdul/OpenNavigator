# Deployment runbook

## Target

| Item | Value |
| --- | --- |
| Server | `opennikkah` (`206.81.6.97`, SSH port 2222) |
| Project directory | `/opt/opennavigator` |
| System user | `opennavigator` |
| API bind | `127.0.0.1:8010` |
| Public URL | <https://opennavigator.206.81.6.97.sslip.io> |
| TLS | Let's Encrypt via certbot |
| Web server | nginx 1.24 |
| Process manager | systemd |
| Database | PostgreSQL `opennavigator` role + database |
| Runtime data | `/opt/opennavigator/var` |
| Backups | `/var/backups/opennavigator` |

The server has ~1 GB RAM. **Build on the local Mac; never run `vite build` or `next build` on the server.** Frontend artifacts are shipped separately.

Existing services and nginx sites on the shared server are out of scope. Do not edit or restart them.

## Layout

```text
/opt/opennavigator/
├── .env                    # chmod 600, owned by opennavigator
├── backend/                # Django source
├── frontend/dist/          # built Vite assets
├── venv/                   # Python 3.12 virtualenv
├── var/                    # file cache + runtime data
└── scripts/backup.sh
```

## One-time server setup

Run as root over SSH.

### 1. System user and directories

```bash
id -u opennavigator >/dev/null 2>&1 || \
  useradd --system --create-home --home-dir /opt/opennavigator \
    --shell /usr/sbin/nologin opennavigator

install -d -o opennavigator -g opennavigator \
  /opt/opennavigator/backend \
  /opt/opennavigator/frontend/dist \
  /opt/opennavigator/var \
  /opt/opennavigator/scripts
chmod 755 /opt/opennavigator
chmod -R a+rX /opt/opennavigator/frontend/dist
```

### 2. PostgreSQL role and database

Generate a random password on the server and create the role/database without printing the password:

```bash
DB_PASS="$(openssl rand -hex 24)"
sudo -u postgres psql -v ON_ERROR_STOP=1 <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'opennavigator') THEN
    CREATE ROLE opennavigator LOGIN PASSWORD '${DB_PASS}';
  END IF;
END
\$\$;
SQL
sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='opennavigator'" \
  | grep -q 1 || sudo -u postgres createdb -O opennavigator opennavigator
```

The password is written to `.env` in the next step. Do not commit `.env`.

### 3. Environment file

```bash
umask 077
cat > /opt/opennavigator/.env <<EOF
DJANGO_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(64))')
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=opennavigator.206.81.6.97.sslip.io,206.81.6.97,127.0.0.1,localhost
DJANGO_CSRF_TRUSTED_ORIGINS=https://opennavigator.206.81.6.97.sslip.io
DB_NAME=opennavigator
DB_USER=opennavigator
DB_PASSWORD=${DB_PASS}
DB_HOST=127.0.0.1
DB_PORT=5432
DATA_DIR=/opt/opennavigator/var
PLAN_RETENTION_HOURS=24
MAX_TRIP_DAYS=14
HTTP_USER_AGENT=OpenNavigator/1.0 (+https://opennavigator.206.81.6.97.sslip.io)
LOG_LEVEL=INFO
EOF
chown opennavigator:opennavigator /opt/opennavigator/.env
chmod 600 /opt/opennavigator/.env
```

### 4. Python virtualenv and dependencies

```bash
sudo -u opennavigator python3 -m venv /opt/opennavigator/venv
sudo -u opennavigator /opt/opennavigator/venv/bin/pip install --upgrade pip
sudo -u opennavigator /opt/opennavigator/venv/bin/pip install \
  -r /opt/opennavigator/backend/requirements.txt
```

Dependencies are small wheels; no heavy build runs on the server.

### 5. systemd service

Install `deploy/systemd/opennavigator-web.service` to `/etc/systemd/system/`, then:

```bash
systemctl daemon-reload
systemctl enable --now opennavigator-web
systemctl status opennavigator-web --no-pager
```

### 6. nginx and TLS

Install `deploy/nginx/opennavigator.conf` as
`/etc/nginx/sites-available/opennavigator`, symlink it into `sites-enabled`, test, and reload:

```bash
ln -sfn /etc/nginx/sites-available/opennavigator /etc/nginx/sites-enabled/opennavigator
nginx -t
systemctl reload nginx
certbot --nginx -d opennavigator.206.81.6.97.sslip.io --redirect
```

`sslip.io` resolves the hostname to `206.81.6.97` automatically, so TLS can be issued without a DNS change. For a custom domain, point an A record at `206.81.6.97` first, replace the `server_name`, and rerun certbot.

### 7. Backups

Install the backup script and units from `deploy/`:

```bash
install -m 755 deploy/scripts/backup.sh /opt/opennavigator/scripts/backup.sh
install -m 644 deploy/systemd/opennavigator-backup.service /etc/systemd/system/
install -m 644 deploy/systemd/opennavigator-backup.timer /etc/systemd/system/
install -d -o root -g root /var/backups/opennavigator
systemctl daemon-reload
systemctl enable --now opennavigator-backup.timer
```

The timer runs daily and keeps 7 days of database dumps and runtime data archives.

## Routine deployment

From the repository root on the local Mac:

```bash
./scripts/deploy.sh
```

The script:

1. Runs backend lint/tests and frontend typecheck/tests.
2. Builds the frontend locally (`pnpm build`).
3. Rsyncs backend source with explicit excludes (`.env`, `var/`, caches).
4. Rsyncs `frontend/dist/` separately.
5. Installs Python requirements on the server.
6. Runs migrations.
7. Fixes ownership, restarts `opennavigator-web`, and checks `/api/v1/health/`.

`rsync --delete` is only used on the source and `dist` trees. It is never used on `/opt/opennavigator` as a whole, so `.env`, `var/`, and the virtualenv cannot be deleted by a blanket sync.

## Operations

```bash
systemctl status opennavigator-web
systemctl restart opennavigator-web
journalctl -u opennavigator-web -f
journalctl -u opennavigator-web --since "1 hour ago"

nginx -t && systemctl reload nginx
certbot renew --dry-run
systemctl list-timers 'opennavigator-*'
```

Health check:

```bash
curl -fsS https://opennavigator.206.81.6.97.sslip.io/api/v1/health/
```

## Rollback

The deployment is source + static artifacts, so rollback is a redeploy of the previous commit:

```bash
git checkout <previous-commit>
./scripts/deploy.sh
```

Database migrations are additive in this project (a single `trip_plans` table). If a migration must be reversed, run `manage.py migrate trips <previous>` deliberately; do not drop the database.

## Backup restore

```bash
systemctl stop opennavigator-web
sudo -u postgres dropdb --if-exists opennavigator
sudo -u postgres createdb -O opennavigator opennavigator
sudo -u postgres pg_restore -d opennavigator /var/backups/opennavigator/<file>.dump
systemctl start opennavigator-web
```

Restoring is destructive; confirm the target database name before running.

## Safety notes

- Do not touch `/opt/birthdaybuddy`, `/opt/gaara`, `/opt/opennikkah`, `/opt/job-finder`, or `/opt/resume-site`.
- Do not stop or restart `birthdaybuddy`, `gaara-web`, `gaara-worker`, `opennikkah-api`, `opennikkah-worker`, or the `gaara-*` timers.
- Do not edit existing nginx site files or the default server block.
- Do not run frontend or other heavy builds on the server.
- Verify the chosen port with `ss -tln` before changing `8010`.
