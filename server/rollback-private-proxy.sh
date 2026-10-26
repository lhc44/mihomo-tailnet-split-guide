#!/usr/bin/env bash
set -euo pipefail
test "$(id -u)" -eq 0
UNIT=/etc/systemd/system/tailnet-private-proxy.service
test -f /var/backups/tailnet-private-proxy/managed.sha256
sha256sum -c /var/backups/tailnet-private-proxy/managed.sha256
systemctl disable --now tailnet-private-proxy
test -z "$(ss -H -lnt '( sport = :10808 )')"
rm -- "$UNIT"
systemctl daemon-reload
echo 'Proxy disabled. Original Tailscale service, DNS, and exit-node settings are unchanged.'
echo 'Inactive files and backup retained for inspection; no directory is recursively removed.'
