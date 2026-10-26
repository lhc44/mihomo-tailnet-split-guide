#!/usr/bin/env bash
# Usage: sudo bash server/install-tailscale-static.sh ARCHIVE EXPECTED_SHA256
set -euo pipefail
test "$(id -u)" -eq 0
test "$#" -eq 2 || { echo 'Provide the official amd64 archive and independently checked SHA256.' >&2; exit 1; }
ARCHIVE=$(realpath -- "$1")
EXPECTED=$2
[[ "$EXPECTED" =~ ^[0-9a-fA-F]{64}$ ]]
V=1.104.2
BASE=/opt/tailnet-tailscale/$V
UNIT=/etc/systemd/system/tailscaled.service
BACKUP=/var/backups/tailnet-tailscale-install
test "$(uname -m)" = x86_64
for p in "$BASE" "$UNIT" "$BACKUP" /usr/local/bin/tailscale /usr/local/sbin/tailscaled; do
  if test -e "$p" || test -L "$p"; then echo "Existing path; preserve it: $p" >&2; exit 1; fi
done
if command -v tailscale >/dev/null || systemctl cat tailscaled >/dev/null 2>&1; then
  echo 'Use the existing Tailscale installation instead of this fresh-install helper.' >&2; exit 1
fi
printf '%s  %s\n' "$EXPECTED" "$ARCHIVE" | sha256sum -c -
TMP=$(mktemp -d)
trap 'rm -rf -- "$TMP"' EXIT
tar -xzf "$ARCHIVE" -C "$TMP" --no-same-owner
test -x "$TMP/tailscale_${V}_amd64/tailscaled"
install -d -m 755 "$BASE"
install -d -m 700 "$BACKUP"
install -m 755 "$TMP/tailscale_${V}_amd64/tailscale" "$BASE/tailscale"
install -m 755 "$TMP/tailscale_${V}_amd64/tailscaled" "$BASE/tailscaled"
ln -s "$BASE/tailscale" /usr/local/bin/tailscale
ln -s "$BASE/tailscaled" /usr/local/sbin/tailscaled
cat > "$UNIT" <<'UNIT'
[Unit]
Description=Tailscale static installation
Wants=network-online.target
After=network-online.target
[Service]
ExecStart=/opt/tailnet-tailscale/1.104.2/tailscaled --state=/var/lib/tailscale/tailscaled.state --socket=/run/tailscale/tailscaled.sock --port=41641
ExecStopPost=/opt/tailnet-tailscale/1.104.2/tailscaled --cleanup
Restart=on-failure
RuntimeDirectory=tailscale
RuntimeDirectoryMode=0755
StateDirectory=tailscale
StateDirectoryMode=0700
CacheDirectory=tailscale
Type=notify
[Install]
WantedBy=multi-user.target
UNIT
chmod 644 "$UNIT"
sha256sum "$BASE/tailscale" "$BASE/tailscaled" "$UNIT" > "$BACKUP/managed.sha256"
systemd-analyze verify "$UNIT"
systemctl daemon-reload
systemctl enable --now tailscaled
tailscale version
echo 'Next run tailscale up and enroll the server using your own account. Keep enrollment links private.'
