#!/usr/bin/env bash
# Optional fallback; the final VLESS-over-tailnet design does not require forwarding.
set -euo pipefail
umask 077
test "$(id -u)" -eq 0
B=/var/backups/tailnet-exit-node
F=/etc/sysctl.d/99-tailnet-exit-node.conf
test ! -e "$B" && test ! -e "$F"
install -d -m 700 "$B"
tailscale debug prefs > "$B/preferences.json"
sysctl -n net.ipv4.ip_forward > "$B/ipv4.before"
sysctl -n net.ipv6.conf.all.forwarding > "$B/ipv6.before"
printf 'net.ipv4.ip_forward = 1\nnet.ipv6.conf.all.forwarding = 1\n' > "$F"
chmod 644 "$F"
sha256sum "$F" > "$B/managed.sha256"
sysctl -p "$F"
tailscale set --advertise-exit-node=true
echo 'Approve the exit node in your own Tailscale console. Nothing is automatically approved.'
