#!/usr/bin/env bash
set -euo pipefail
test "$(id -u)" -eq 0
B=/var/backups/tailnet-exit-node
sha256sum -c "$B/managed.sha256"
ROUTES=$(python3 - "$B/preferences.json" <<'PY'
import json,sys
with open(sys.argv[1]) as stream:
    prefs=json.load(stream)
print(','.join(prefs.get('AdvertiseRoutes') or []))
PY
)
tailscale set "--advertise-routes=$ROUTES"
rm -- /etc/sysctl.d/99-tailnet-exit-node.conf
sysctl -w "net.ipv4.ip_forward=$(cat "$B/ipv4.before")"
sysctl -w "net.ipv6.conf.all.forwarding=$(cat "$B/ipv6.before")"
echo 'Previous advertised routes and runtime forwarding values restored; backup retained.'
