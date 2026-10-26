#!/usr/bin/env python3
"""Generate a private Mihomo profile; never use live credentials in the repository."""
import argparse
import ipaddress
import json
from pathlib import Path, PureWindowsPath
import uuid
import yaml


def build_profile(info, state_dir, hostname="tailnet-split-client", port=7897):
    address = ipaddress.ip_address(info["server"])
    if address.version != 4 or address not in ipaddress.ip_network("100.64.0.0/10"):
        raise ValueError("server must be a Tailscale IPv4 address")
    identity = uuid.UUID(info["uuid"])
    if identity.int == 0:
        raise ValueError("UUID must not be nil")
    if not (Path(state_dir).is_absolute() or PureWindowsPath(state_dir).is_absolute()):
        raise ValueError("state directory must be absolute and inside the Mihomo home directory")
    server_port = int(info.get("port", 10808))
    if not 1 <= server_port <= 65535 or not 1 <= port <= 65535:
        raise ValueError("invalid port")
    direct_dns = ["https://dns.alidns.com/dns-query#DIRECT", "https://doh.pub/dns-query#DIRECT"]
    node = {
        "name": "SERVER-NODE", "type": "vless", "server": str(address),
        "port": server_port, "uuid": str(identity), "udp": True,
        "tls": False, "network": "tcp", "packet-encoding": "xudp", "dialer-proxy": "TAILNET",
    }
    return {
        "mixed-port": port, "allow-lan": False, "bind-address": "127.0.0.1",
        "mode": "rule", "log-level": "info", "ipv6": False, "geodata-mode": False,
        "profile": {"store-selected": True, "store-fake-ip": True},
        "dns": {
            "enable": True, "listen": "127.0.0.1:1053", "ipv6": False,
            "enhanced-mode": "fake-ip", "fake-ip-range": "198.18.0.1/16",
            "fake-ip-filter": ["+.lan", "+.local", "localhost", "+.ts.net", "+.tailscale.com"],
            "default-nameserver": ["system", "223.5.5.5", "119.29.29.29"],
            "proxy-server-nameserver": ["system"], "direct-nameserver": direct_dns,
            "nameserver": ["https://1.1.1.1/dns-query#SERVER"],
            "nameserver-policy": {"geosite:cn": direct_dns, "geosite:private": ["system"]},
        },
        "proxies": [{
            "name": "TAILNET", "type": "tailscale", "hostname": hostname,
            "state-dir": state_dir.replace("\\", "/"), "ephemeral": False,
            "udp": True, "accept-routes": False, "ip-version": "ipv4-prefer",
        }],
        # Keep the dialer link in a provider: some GUI chain operations strip links
        # from top-level proxies. No remote provider download is required.
        "proxy-providers": {"private-egress": {
            "type": "inline", "payload": [node], "health-check": {"enable": False},
        }},
        "proxy-groups": [{"name": "SERVER", "type": "select", "use": ["private-egress"]}],
        "rules": [
            "PROCESS-NAME,tailscaled.exe,DIRECT", "PROCESS-NAME,tailscale.exe,DIRECT",
            "IP-CIDR,100.64.0.0/10,TAILNET,no-resolve",
            "IP-CIDR,127.0.0.0/8,DIRECT,no-resolve", "IP-CIDR,10.0.0.0/8,DIRECT,no-resolve",
            "IP-CIDR,172.16.0.0/12,DIRECT,no-resolve", "IP-CIDR,192.168.0.0/16,DIRECT,no-resolve",
            "IP-CIDR6,fc00::/7,DIRECT,no-resolve", "IP-CIDR6,fe80::/10,DIRECT,no-resolve",
            "GEOSITE,private,DIRECT", "GEOSITE,cn,DIRECT", "GEOIP,CN,DIRECT", "MATCH,SERVER",
        ],
        "tun": {"enable": False, "stack": "mixed", "auto-route": True,
                "auto-detect-interface": True, "strict-route": False, "dns-hijack": ["any:53"]},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-info", type=Path, required=True, help="private JSON: server, port, uuid")
    parser.add_argument("--state-dir", required=True, help="absolute subdirectory of Mihomo -d home")
    parser.add_argument("--hostname", default="tailnet-split-client")
    parser.add_argument("--port", type=int, default=7897)
    parser.add_argument("--out", type=Path, default=Path("local/split.yaml"))
    args = parser.parse_args()
    info = json.loads(args.server_info.read_text("utf-8-sig"))
    profile = build_profile(info, args.state_dir, args.hostname, args.port)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation avoids silently replacing a working credential-bearing profile.
    with args.out.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write("# PRIVATE GENERATED PROFILE: DO NOT COMMIT OR SHARE\n")
        yaml.safe_dump(profile, stream, sort_keys=False, allow_unicode=True)
    print("Profile generated. Keep the profile and enrollment state private.")


if __name__ == "__main__":
    main()
