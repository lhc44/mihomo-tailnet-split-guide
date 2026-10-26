#!/usr/bin/env bash
set -euo pipefail
test "$(id -u)" -eq 0
B=/var/backups/tailnet-networkmanager-dns
CON=$(cat "$B/connection")
DEV=$(cat "$B/device")
test "$(nmcli -g GENERAL.CON-UUID device show "$DEV")" = "$CON"
nmcli connection modify "$CON" ipv4.ignore-auto-dns "$(cat "$B/ignore.before")" ipv4.dns "$(cat "$B/dns.before")"
nmcli device reapply "$DEV"
echo 'Original NetworkManager DNS settings restored; backup retained.'
