# Self-installing Trenchfloor VPS

Public root installer: https://raw.githubusercontent.com/joeypbrrr/trenchfloor/main/deploy/vps-setup.sh

Supports native Ubuntu 22.04/24.04 amd64 and arm64 (including Oracle Ampere A1).
Run as root from cloud-init. It retries safely after ordinary installation/network
failures; it never resets Git or overwrites an unknown existing swap file.
`bash deploy/vps-setup.sh --dry-run` describes actions without changing the host.

The installer installs native packages, adds/enables 1 GB swap, sets Eastern Time,
creates non-root `trench`, clones/fast-forwards `/opt/trenchfloor`, creates a venv,
and installs the optional collector dependencies **without starting the collector**.
It never changes config.json, scan cadence, paper strategy or opt-in feature flags.

Three systemd services run Python as `trench`: research; localhost-only static site
8795; read-only dashboard 0.0.0.0:8796 with ingest only at 127.0.0.1:8797.
Nginx proxies public port 80 with WebSocket upgrade support. No Cloudflare tunnel,
GitHub token or broker/wallet is installed. VPS-mode publishing returns a successful
no-op before even inspecting Git. The original box remains the Pages publisher.

On ordinary Ubuntu/Vultr, ufw is configured to allow incoming TCP 22 and 80 only
(plus its standard connection/ICMP handling). **Existing ufw custom rules are reset
as requested for this dedicated server.** Oracle is detected by DMI asset tag or
InstanceServices chain: ufw is disabled, an explicit input chain is inserted ahead
of the image's REJECT, and v4/v6 rules are saved with netfilter-persistent. Oracle's
InstanceServices/output rules are preserved. DHCP/ICMP and established traffic are
preserved; other new inbound traffic is dropped.

## Cloud firewall still requires the owner

Allow ingress TCP 80 in the Vultr firewall or Oracle VCN security list/NSG; keep
TCP 22 allowed. OS rules cannot change the provider's cloud firewall. No DNS or
paid domain is needed. The dashboard is public/read-only and HTTP, not HTTPS;
never enter passwords, keys or payment details there.

## Automatic recovery and updates

`trenchfloor-watchdog.timer` runs every five minutes. Its root-owned installed
script pulls main as `trench`, checks syntax and dependencies on new commits, then
restarts the services. It also checks systemd, local dashboard and nginx and
restarts unhealthy services. Git update failures do not skip health checks.
Generated research data is preserved: a conflicting pull is refused, not reset.
The marker at `/var/lib/trenchfloor/deployed-commit` advances after health passes.
Setup/watchdog use a shared flock to avoid concurrent deployment.

Root-owned unit/nginx/watchdog configuration is installed by the bootstrap, not
silently overwritten from the non-root checkout on each timer tick. Rerun setup
if infrastructure/unit configuration itself changes; normal Python/UI fixes ship
through main automatically.

Logs: `/var/log/trenchfloor-setup.log`; `journalctl -u trenchfloor-live`,
`journalctl -u trenchfloor-research`, and `journalctl -u trenchfloor-watchdog`.
`systemctl list-timers trenchfloor-watchdog.timer` shows the next check.
Setup exits zero only after dashboard and nginx both return HTTP 200 locally.

## Verify from this box after Joey supplies the IP

    curl -f http://IP/health
    curl -f http://IP/

The first returns read-only paper-mode health JSON; the second the real floor.
Tested here: shell syntax, nonmutating dry run, full unit suite, publisher no-op
without any Git call, and a spare-port VPS-mode server: dashboard 0.0.0.0:18896
returns 200; private ingest listens only on 127.0.0.1:18897; public POST returns 405.
No apt, swap, firewall, systemd, or existing box services were modified during tests.
A real Ubuntu/Vultr/Oracle installation remains to be verified on the new server.
