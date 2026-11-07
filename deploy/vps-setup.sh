#!/bin/bash
# Public cloud-init installer. Ubuntu 22.04/24.04, amd64 and arm64.
# Paper research ONLY. No credentials, wallets, broker, collector or new modes enabled.
set -Eeuo pipefail
if [[ "${1:-}" == "--dry-run" ]]; then
  printf '%s\n' 'DRY RUN ONLY: no machine changes.' \
    'Install native Ubuntu Python/venv/git/curl/CA/nginx/firewall packages; add 1GB swap.' \
    'Create trench; clone/update /opt/trenchfloor; create native Python venv.' \
    'Install 3 systemd services and a 5-minute update/health timer; collector stays OFF.' \
    'VPS mode: public read-only 8796; private ingest 127.0.0.1:8797; Pages disabled.' \
    'Nginx port 80 -> 127.0.0.1:8796; SSH 22 preserved. Oracle: native iptables, no ufw.'
  exit 0
fi
[[ "$EUID" -eq 0 ]] || { echo 'Run this installer as root'; exit 1; }
export DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a GIT_TERMINAL_PROMPT=0
exec > >(tee -a /var/log/trenchfloor-setup.log) 2>&1
trap 'echo "SETUP FAILED at line $LINENO (exit $?) — safe to retry"' ERR
exec 9>/run/lock/trenchfloor-deploy.lock
flock -n 9 || { echo 'Another setup/watchdog is running; retry later'; exit 1; }
echo "$(date -Is) Trenchfloor setup starting ($(uname -m))"
apt-get -o DPkg::Lock::Timeout=180 update
apt-get -o DPkg::Lock::Timeout=180 install -y python3 python3-venv git curl ca-certificates nginx ufw iptables netfilter-persistent
# Do not overwrite or reformat a pre-existing file.
if [[ ! -e /swapfile ]]; then
  fallocate -l 1G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=1024 status=none
  chmod 600 /swapfile
  mkswap /swapfile
fi
if [[ "$(blkid -o value -s TYPE /swapfile || true)" != swap ]]; then
  echo 'Existing /swapfile is not swap; refusing to overwrite it'; exit 1
fi
if ! swapon --show=NAME --noheadings | grep -Fxq /swapfile; then swapon /swapfile; fi
if ! grep -Eq '^/swapfile[[:space:]]' /etc/fstab; then echo '/swapfile none swap sw 0 0' >>/etc/fstab; fi
timedatectl set-timezone America/New_York
if ! id trench >/dev/null 2>&1; then useradd --create-home --shell /bin/bash trench; fi
install -d -m 0755 -o trench -g trench /opt/trenchfloor
as_trench() { runuser -u trench -- "$@"; }
if [[ -d /opt/trenchfloor/.git ]]; then
  as_trench git -C /opt/trenchfloor pull --ff-only origin main
else
  as_trench git clone --branch main https://github.com/joeypbrrr/trenchfloor.git /opt/trenchfloor
fi
cd /opt/trenchfloor
as_trench python3 -m venv .venv
if [[ -f requirements-collector.txt ]]; then
  as_trench .venv/bin/python -m pip install --disable-pip-version-check -r requirements-collector.txt
fi
as_trench .venv/bin/python -m compileall -q -x '/(\.git|\.venv)/' .
# Nothing edits config.json: collector/new modes remain at committed defaults OFF.
install -d -m 0755 -o trench -g trench data/cache data/ledger logs
install -d -m 0755 /var/lib/trenchfloor
for pair in research:research.py site:server.py live:live_server.py; do
  service="${pair%%:*}"; program="${pair#*:}"
  cat >"/etc/systemd/system/trenchfloor-$service.service" <<UNIT
[Unit]
Description=Trenchfloor $service (paper research only)
Wants=network-online.target
After=network-online.target
[Service]
Type=simple
User=trench
Group=trench
WorkingDirectory=/opt/trenchfloor
Environment=TRENCHFLOOR_SERVER_MODE=vps
Environment=TRENCHFLOOR_SKIP_PUBLISH=1
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/trenchfloor/.venv/bin/python -u /opt/trenchfloor/$program
Restart=always
RestartSec=5
TimeoutStopSec=20
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
[Install]
WantedBy=multi-user.target
UNIT
done
# Port 80 is handled by nginx; Python never needs root or privileged capabilities.
cat >/etc/nginx/sites-available/trenchfloor <<'NGINX'
map $http_upgrade $trenchfloor_connection {
    default upgrade;
    '' close;
}
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    location / {
        proxy_pass http://127.0.0.1:8796;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $trenchfloor_connection;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
        proxy_buffering off;
    }
}
NGINX
ln -sfn /etc/nginx/sites-available/trenchfloor /etc/nginx/sites-enabled/trenchfloor
rm -f /etc/nginx/sites-enabled/default
nginx -t
oracle=false
if [[ -r /sys/class/dmi/id/chassis_asset_tag ]] && [[ "$(</sys/class/dmi/id/chassis_asset_tag)" == OracleCloud.com ]]; then oracle=true; fi
if iptables -S InstanceServices >/dev/null 2>&1; then oracle=true; fi
if "$oracle"; then
  echo 'Oracle image detected: preserving InstanceServices; use iptables instead of enabling ufw.'
  # A chain inserted at INPUT position 1 accepts 80 before Oracle's existing REJECT.
  # Preserve established sessions, loopback, ICMP and DHCP, deny other new ingress.
  iptables -N TRENCHFLOOR-IN 2>/dev/null || true
  iptables -F TRENCHFLOOR-IN
  iptables -A TRENCHFLOOR-IN -i lo -j ACCEPT
  iptables -A TRENCHFLOOR-IN -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
  iptables -A TRENCHFLOOR-IN -p tcp -m multiport --dports 22,80 -j ACCEPT
  iptables -A TRENCHFLOOR-IN -p icmp -j ACCEPT
  iptables -A TRENCHFLOOR-IN -p udp --sport 67 --dport 68 -j ACCEPT
  iptables -A TRENCHFLOOR-IN -j DROP
  iptables -C INPUT -j TRENCHFLOOR-IN 2>/dev/null || iptables -I INPUT 1 -j TRENCHFLOOR-IN
  if ip6tables -S >/dev/null 2>&1; then
    ip6tables -N TRENCHFLOOR-IN 2>/dev/null || true
    ip6tables -F TRENCHFLOOR-IN
    ip6tables -A TRENCHFLOOR-IN -i lo -j ACCEPT
    ip6tables -A TRENCHFLOOR-IN -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
    ip6tables -A TRENCHFLOOR-IN -p tcp -m multiport --dports 22,80 -j ACCEPT
    ip6tables -A TRENCHFLOOR-IN -p ipv6-icmp -j ACCEPT
    ip6tables -A TRENCHFLOOR-IN -p udp --sport 547 --dport 546 -j ACCEPT
    ip6tables -A TRENCHFLOOR-IN -j DROP
    ip6tables -C INPUT -j TRENCHFLOOR-IN 2>/dev/null || ip6tables -I INPUT 1 -j TRENCHFLOOR-IN
  fi
  # Save explicitly: netfilter-persistent alone may have no save plugin installed.
  install -d /etc/iptables
  iptables-save >/etc/iptables/rules.v4
  if ip6tables -S >/dev/null 2>&1; then ip6tables-save >/etc/iptables/rules.v6; fi
  echo iptables-persistent iptables-persistent/autosave_v4 boolean false | debconf-set-selections
  echo iptables-persistent iptables-persistent/autosave_v6 boolean false | debconf-set-selections
  apt-get -o DPkg::Lock::Timeout=180 install -y iptables-persistent
  systemctl enable netfilter-persistent
else
  ufw default deny incoming
  ufw default allow outgoing
  ufw allow 22/tcp
  ufw allow 80/tcp
  ufw --force enable
fi
install -m 0755 deploy/vps-watchdog.sh /usr/local/sbin/trenchfloor-watchdog
cat >/etc/systemd/system/trenchfloor-watchdog.service <<'UNIT'
[Unit]
Description=Trenchfloor five-minute update and health watchdog
Wants=network-online.target
After=network-online.target
[Service]
Type=oneshot
ExecStart=/usr/local/sbin/trenchfloor-watchdog
TimeoutStartSec=240
UNIT
cat >/etc/systemd/system/trenchfloor-watchdog.timer <<'UNIT'
[Unit]
Description=Check Trenchfloor health and main every five minutes
[Timer]
OnBootSec=5min
OnUnitActiveSec=5min
Persistent=true
[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload
systemctl enable nginx trenchfloor-research.service trenchfloor-site.service trenchfloor-live.service trenchfloor-watchdog.timer
systemctl restart nginx trenchfloor-site.service trenchfloor-live.service trenchfloor-research.service
systemctl start trenchfloor-watchdog.timer
# Wait for the supervised dashboard, not for research/network scans to finish.
for attempt in {1..60}; do
  code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://127.0.0.1:8796/ || true)"
  if [[ "$code" == 200 ]]; then
    as_trench git rev-parse HEAD >/var/lib/trenchfloor/deployed-commit
    echo "$(date -Is) SETUP COMPLETE: dashboard HTTP 200. Open http://YOUR_VPS_IP/"
    echo 'If Oracle, also allow TCP 80 in its VCN security list/NSG (cloud firewall).'
    exit 0
  fi
  sleep 2
done
echo 'Dashboard did not return HTTP 200. Inspect journalctl -u trenchfloor-live -n 80.'
exit 1
