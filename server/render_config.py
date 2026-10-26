#!/usr/bin/env python3
"""Render a VLESS listener bound only to the server's tailnet address."""
import argparse
import ipaddress
import json
from pathlib import Path
import uuid


def render(address, identity, port=10808):
    ip = ipaddress.ip_address(address)
    if ip.version != 4 or ip not in ipaddress.ip_network("100.64.0.0/10"):
        raise ValueError("Listener must bind to a Tailscale IPv4 address")
    identity = uuid.UUID(identity)
    if identity.int == 0 or not 1 <= port <= 65535:
        raise ValueError("Invalid identity or port")
    return {
        "log": {"loglevel": "warning"},
        "inbounds": [{"tag": "tailnet-vless", "listen": str(ip), "port": port,
            "protocol": "vless", "settings": {"users": [{"id": str(identity)}], "decryption": "none"},
            "streamSettings": {"network": "raw", "security": "none"}}],
        "outbounds": [{"tag": "direct", "protocol": "freedom",
                       "streamSettings": {"sockopt": {"domainStrategy": "UseIPv4"}}},
                      {"tag": "block", "protocol": "blackhole"}],
        "routing": {"rules": [{"type": "field", "outboundTag": "block", "ip": [
            "127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
            "169.254.0.0/16", "100.64.0.0/10", "::1/128", "fc00::/7", "fe80::/10",
        ]}]},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--address", required=True)
    parser.add_argument("--uuid", required=True)
    parser.add_argument("--port", type=int, default=10808)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    value = render(args.address, args.uuid, args.port)
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
