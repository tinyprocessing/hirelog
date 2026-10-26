#!/bin/sh
# Zero-downtime deploy: sync → build → recreate app_a (wait healthy) → app_b → reload Caddy if its config changed.
set -e
HOST=${HOST:-hirelog}
cd "$(dirname "$0")"
python -m pytest -q tests >/dev/null 2>&1 || .venv/bin/python -m pytest -q tests
rsync -az --delete --exclude .venv --exclude .git --exclude __pycache__ --exclude .pytest_cache --exclude .env --exclude backups ./ "$HOST":~/hirelog/
ssh "$HOST" 'set -e; cd ~/hirelog
  sudo docker compose build -q app_a
  sudo docker compose up -d --no-deps db
  for s in app_a app_b; do
    sudo docker compose exec -T "$s" touch /tmp/drain 2>/dev/null && sleep 7   # Caddy marks it down first
    sudo docker compose up -d --no-deps --force-recreate --wait --wait-timeout 90 "$s"
    echo "$s healthy"
  done
  sudo docker compose up -d --no-deps caddy
  sudo docker compose exec -T caddy caddy reload --config /etc/caddy/Caddyfile >/dev/null 2>&1 || true
  sudo docker image prune -f >/dev/null'
curl -fsS https://hirelog.dev/health && echo " deployed"
