#!/usr/bin/env bash
set -euo pipefail
test "$(id -u)" -eq 0
sha256sum -c /var/backups/tailnet-tailscale-install/managed.sha256
test "$(readlink /usr/local/bin/tailscale)" = /opt/tailnet-tailscale/1.104.2/tailscale
test "$(readlink /usr/local/sbin/tailscaled)" = /opt/tailnet-tailscale/1.104.2/tailscaled
if systemctl is-active --quiet tailnet-private-proxy; then
  echo 'Roll back the dependent private proxy first.' >&2; exit 1
fi
systemctl disable --now tailscaled
rm -- /etc/systemd/system/tailscaled.service /usr/local/bin/tailscale /usr/local/sbin/tailscaled
systemctl daemon-reload
echo 'Static installation disabled. Private state, binaries, and backup retained.'
echo 'This does not apply to a pre-existing package-manager installation.'
