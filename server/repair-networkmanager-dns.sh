#!/usr/bin/env bash
# Optional only: preserve a working SSH session before altering server DNS.
# Usage: sudo bash server/repair-networkmanager-dns.sh ACTIVE_CONNECTION_UUID DEVICE
set -euo pipefail
umask 077
test "$(id -u)" -eq 0
test "$#" -eq 2
CON=$1
DEV=$2
[[ "$CON" =~ ^[0-9a-fA-F-]{36}$ ]]
test "$(nmcli -g GENERAL.CON-UUID device show "$DEV")" = "$CON"
B=/var/backups/tailnet-networkmanager-dns
test ! -e "$B" || { echo 'Existing backup retained; inspect before retry.' >&2; exit 1; }
install -d -m 700 "$B"
printf '%s\n' "$CON" > "$B/connection"
printf '%s\n' "$DEV" > "$B/device"
nmcli --escape no -g ipv4.dns connection show "$CON" > "$B/dns.before"
nmcli -g ipv4.ignore-auto-dns connection show "$CON" > "$B/ignore.before"
cp -a /etc/resolv.conf "$B/resolv.conf.reference"
nmcli connection modify "$CON" ipv4.ignore-auto-dns yes ipv4.dns '1.1.1.1,8.8.8.8'
nmcli device reapply "$DEV"
echo 'Public DNS applied with NetworkManager; no interface down/up was used.'
echo 'Check getent hosts github.com, then restart Tailscale and check DNS again.'
