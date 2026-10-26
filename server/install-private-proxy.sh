#!/usr/bin/env bash
# Fresh-install helper for a Linux amd64 server already enrolled in Tailscale.
set -euo pipefail
umask 077
test "$(id -u)" -eq 0 || { echo 'Run as root on the server.' >&2; exit 1; }
for c in curl unzip sha256sum python3 systemctl tailscale ss; do command -v "$c" >/dev/null; done
test "$(uname -m)" = x86_64 || { echo 'This pinned asset supports amd64 only.' >&2; exit 1; }
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
BASE=/opt/tailnet-private-proxy
UNIT=/etc/systemd/system/tailnet-private-proxy.service
BACKUP=/var/backups/tailnet-private-proxy
test ! -e "$BASE" && test ! -e "$UNIT" && test ! -e "$BACKUP" || {
  echo 'An existing installation or backup exists; inspect it instead of overwriting.' >&2; exit 1;
}
V=26.10.21
SHA=0eec3ed4163c273d8c8bf821f7d219e257921cf584aa3fb970715e458e631978
ADDRESS=$(tailscale ip -4 | head -n 1)
IDENTITY=$(python3 -c 'import uuid;print(uuid.uuid4())')
TMP=$(mktemp -d)
trap 'rm -rf -- "$TMP"' EXIT
curl --fail --location --proto '=https' --tlsv1.2 \
  "https://github.com/XTLS/Xray-core/releases/download/v${V}/Xray-linux-64.zip" -o "$TMP/xray.zip"
printf '%s  %s\n' "$SHA" "$TMP/xray.zip" | sha256sum -c -
unzip -q "$TMP/xray.zip" xray -d "$TMP"
python3 "$HERE/render_config.py" --address "$ADDRESS" --uuid "$IDENTITY" --out "$TMP/config.json"
chmod 755 "$TMP/xray"
"$TMP/xray" run -test -config "$TMP/config.json"
# A dedicated no-login account gets access to only its own private configuration.
if ! id tailnet-proxy >/dev/null 2>&1; then
  useradd --system --no-create-home --shell /usr/sbin/nologin tailnet-proxy
fi
install -d -m 750 -o root -g tailnet-proxy "$BASE"
install -d -m 700 "$BACKUP"
install -m 755 "$TMP/xray" "$BASE/xray"
install -m 640 -o root -g tailnet-proxy "$TMP/config.json" "$BASE/config.json"
python3 - "$ADDRESS" "$IDENTITY" "$BASE/server-info.json" <<'PY'
import json,sys
with open(sys.argv[3], 'x') as stream:
    json.dump({'server':sys.argv[1], 'port':10808, 'uuid':sys.argv[2]},stream,indent=2)
PY
chmod 600 "$BASE/server-info.json"
cat > "$UNIT" <<'UNIT'
[Unit]
Description=VLESS over private Tailscale transport
Wants=tailscaled.service network-online.target
After=tailscaled.service network-online.target
StartLimitIntervalSec=0
[Service]
Type=simple
User=tailnet-proxy
Group=tailnet-proxy
ExecStart=/opt/tailnet-private-proxy/xray run -config /opt/tailnet-private-proxy/config.json
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=strict
LimitNOFILE=65536
[Install]
WantedBy=multi-user.target
UNIT
chmod 644 "$UNIT"
sha256sum "$BASE/xray" "$BASE/config.json" "$UNIT" > "$BACKUP/managed.sha256"
systemd-analyze verify "$UNIT"
systemctl daemon-reload
systemctl enable --now tailnet-private-proxy
sleep 2
systemctl is-active --quiet tailnet-private-proxy
ss -H -lnt '( sport = :10808 )' | grep -F "$ADDRESS:10808" >/dev/null
echo 'Installed: private tailnet listener only; no public firewall port opened.'
echo 'Private client parameters: /opt/tailnet-private-proxy/server-info.json'
echo 'Transfer that JSON privately; do not paste it into an issue or commit it.'
