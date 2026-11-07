#!/bin/bash
# Installed root-owned by vps-setup.sh. Git/Python/pip always run as trench.
set -Eeuo pipefail
exec 9>/run/lock/trenchfloor-deploy.lock
flock -n 9 || exit 0
cd /opt/trenchfloor
as_trench() { runuser -u trench -- "$@"; }
export GIT_TERMINAL_PROMPT=0
as_trench git -c safe.directory=/opt/trenchfloor pull --ff-only origin main
head="$(as_trench git rev-parse HEAD)"
deployed="$(< /var/lib/trenchfloor/deployed-commit)" || deployed=""
if [[ "$head" != "$deployed" ]]; then
  as_trench .venv/bin/python -m compileall -q -x '/(\.git|\.venv)/' .
  if [[ -f requirements-collector.txt ]]; then
    as_trench .venv/bin/python -m pip install --disable-pip-version-check -r requirements-collector.txt
  fi
  systemctl restart trenchfloor-live.service trenchfloor-site.service trenchfloor-research.service
fi
for service in trenchfloor-live trenchfloor-site trenchfloor-research; do
  if ! systemctl is-active --quiet "$service.service"; then systemctl restart "$service.service"; fi
done
if ! curl -fsS --max-time 15 http://127.0.0.1:8796/health >/dev/null; then
  systemctl restart trenchfloor-live.service trenchfloor-site.service trenchfloor-research.service
  exit 1
fi
printf '%s\n' "$head" >/var/lib/trenchfloor/deployed-commit
