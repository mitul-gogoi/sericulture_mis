#!/usr/bin/env bash
#
# Deploy the Sericulture MIS to the APP SERVER (192.168.18.193).
# Run ON that server, from /opt/sericulture.
#
#   ./deploy.sh            deploy the current master
#   ./deploy.sh --rollback go back to the previously deployed images
#
# There is no staging environment, so every deploy is a production deploy. The whole
# point of this script is that the two safety steps — back up the database, and tag the
# running images so they can be put back — happen every time and are not left to memory.
#
# What it CANNOT undo: an Alembic migration that has already altered the schema. Rolling
# the images back does not roll the schema back. That is why the database dump in step 1
# exists, and why the rule is to run any new migration against a local restore of
# production data BEFORE deploying it. See DEPLOY.md Part 10.
set -euo pipefail

COMPOSE="docker compose -f docker-compose.prod.yml"
DB_HOST="192.168.18.194"
DB_NAME="sericulture_mis"
DB_USER="seri_app"
BACKUP_DIR="${HOME}/backups"
LOG_DIR="${HOME}/logs"
IMAGES=(seri-backend seri-frontend)

log() { printf '\n\033[1;32m==>\033[0m %s\n' "$*"; }
die() { printf '\n\033[1;31mERROR:\033[0m %s\n' "$*" >&2; exit 1; }

[[ -f docker-compose.prod.yml ]] || die "run this from /opt/sericulture (docker-compose.prod.yml not found)"

# ---------------------------------------------------------------- rollback
if [[ "${1:-}" == "--rollback" ]]; then
  for img in "${IMAGES[@]}"; do
    docker image inspect "${img}:previous" >/dev/null 2>&1 \
      || die "no ${img}:previous image — nothing to roll back to"
  done
  log "Rolling back to the previous images"
  for img in "${IMAGES[@]}"; do
    docker tag "${img}:previous" "${img}:latest"
  done
  $COMPOSE up -d --no-build
  log "Rolled back. If the failed deploy included a migration, restore the matching dump from ${BACKUP_DIR} as well."
  exit 0
fi

# ---------------------------------------------------------------- 1. backup
log "1/5  Backing up the production database"
mkdir -p "$BACKUP_DIR"
STAMP="$(date +%F_%H%M%S)"
DUMP="${BACKUP_DIR}/pre-deploy_${STAMP}.dump"

# The password is read out of backend/.env.docker rather than prompted for: this script is
# normally run over SSH with no TTY, so an interactive pg_dump prompt would simply hang.
[[ -f backend/.env.docker ]] || die "backend/.env.docker not found — see DEPLOY.md Part 7"
DB_URL="$(grep -E '^DATABASE_URL=' backend/.env.docker | head -1 | cut -d= -f2-)"
[[ -n "$DB_URL" ]] || die "DATABASE_URL not set in backend/.env.docker"
# postgresql+psycopg://user:pass@host:5432/db  ->  pass
# Split on the LAST '@', not the first: a password containing '@' is legal and a naive
# match silently returns a truncated password, which then fails as a wrong-password error
# that looks nothing like the real cause.
_rest="${DB_URL#*://}"       # user:pass@host:5432/db
_userinfo="${_rest%@*}"      # user:pass          (strips from the last '@')
DB_PASS="${_userinfo#*:}"    # pass
[[ -n "$DB_PASS" && "$DB_PASS" != "$_userinfo" ]] \
  || die "could not read the database password out of DATABASE_URL in backend/.env.docker"

# Runs from the app server against the database server over the private network.
docker run --rm -e PGPASSWORD="$DB_PASS" -v "${BACKUP_DIR}:/backup" postgis/postgis:17-3.4 \
  pg_dump "postgresql://${DB_USER}@${DB_HOST}:5432/${DB_NAME}" -Fc \
  -f "/backup/pre-deploy_${STAMP}.dump"
[[ -s "$DUMP" ]] || die "backup file is empty — refusing to deploy without a usable backup"
log "     saved $(du -h "$DUMP" | cut -f1) to ${DUMP}"
echo "     copy this off the server — a backup only on the machine it protects is not a backup"

# ---------------------------------------------------------------- 1b. archive logs
# Docker keeps container logs with the container, and the rebuild below RECREATES the
# containers — so without this step every log line from the currently running version is
# destroyed. With no staging environment, those logs are the only record of what a user
# actually hit, so capture them before they are lost.
log "1b/5 Archiving the current containers' logs"
mkdir -p "$LOG_DIR"
LOGFILE="${LOG_DIR}/predeploy_${STAMP}.log"
if $COMPOSE ps --quiet 2>/dev/null | grep -q .; then
  $COMPOSE logs --no-color --timestamps > "$LOGFILE" 2>&1 || true
  if [[ -s "$LOGFILE" ]]; then
    log "     $(wc -l < "$LOGFILE") lines -> ${LOGFILE}"
  else
    rm -f "$LOGFILE"
    echo "     containers were running but produced no log output"
  fi
else
  echo "     nothing running yet (first deploy) — nothing to archive"
fi

# ---------------------------------------------------------------- 2. tag current
log "2/5  Tagging the running images as :previous"
for img in "${IMAGES[@]}"; do
  if docker image inspect "${img}:latest" >/dev/null 2>&1; then
    docker tag "${img}:latest" "${img}:previous"
    echo "     ${img}:latest -> ${img}:previous"
  else
    echo "     ${img}:latest not present (first deploy) — nothing to tag"
  fi
done

# ---------------------------------------------------------------- 3. pull code
log "3/5  Fetching the latest code"
BEFORE="$(git rev-parse --short HEAD)"
git pull --ff-only
AFTER="$(git rev-parse --short HEAD)"
echo "     ${BEFORE} -> ${AFTER}"
if git diff --name-only "${BEFORE}" "${AFTER}" | grep -q '^backend/alembic/versions/'; then
  echo
  echo "     *** This deploy contains an Alembic migration. ***"
  echo "     It will run automatically at backend startup and a code rollback will NOT undo it."
  read -r -p "     Have you already tested it against a local restore of production data? [y/N] " ok
  [[ "$ok" == "y" || "$ok" == "Y" ]] || die "stopping — test the migration locally first (DEPLOY.md Part 10)"
fi

# ---------------------------------------------------------------- 4. build + start
log "4/5  Building and starting"
$COMPOSE up -d --build

# ---------------------------------------------------------------- 5. verify
log "5/5  Waiting for the backend to come up"
for i in $(seq 1 30); do
  if curl -fsk https://localhost/api >/dev/null 2>&1; then
    log "Deployed. GET /api is responding."
    curl -sk https://localhost/api; echo
    exit 0
  fi
  sleep 2
done

echo
$COMPOSE logs --tail=40 backend
die "backend did not respond within 60s — check the log above, then ./deploy.sh --rollback"
