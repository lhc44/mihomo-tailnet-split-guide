#!/usr/bin/env python3
"""Verify SOCKS5 UDP support with a public DNS query, without printing client IPs."""
import argparse
import secrets
import socket
import struct


def exact(sock, count):
    data = b""
    while len(data) < count:
        part = sock.recv(count-len(data))
        if not part:
            raise RuntimeError("Unexpected SOCKS EOF")
        data += part
    return data


def probe(port):
    with socket.create_connection(("127.0.0.1", port), timeout=15) as control:
        control.sendall(b"\x05\x01\x00")
        if exact(control, 2) != b"\x05\x00":
            raise RuntimeError("SOCKS no-auth negotiation failed")
        control.sendall(b"\x05\x03\x00\x01" + b"\x00"*6)
        header = exact(control, 4)
        if header[:2] != b"\x05\x00" or header[3] != 1:
            raise RuntimeError("SOCKS UDP association failed or address type unsupported")
        host = socket.inet_ntoa(exact(control, 4))
        relay_port = struct.unpack("!H", exact(control, 2))[0]
        if host == "0.0.0.0":
            host = "127.0.0.1"
        tid = secrets.randbelow(65536)
        question = b"\x07example\x03com\x00" + struct.pack("!HH", 1, 1)
        dns = struct.pack("!HHHHHH", tid, 0x0100, 1, 0, 0, 0) + question
        packet = b"\x00\x00\x00\x01" + socket.inet_aton("8.8.8.8") + struct.pack("!H", 53) + dns
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
            udp.bind(("127.0.0.1", 0))
            udp.settimeout(15)
            udp.sendto(packet, (host, relay_port))
            reply, _ = udp.recvfrom(4096)
        if len(reply) < 4 or reply[:3] != b"\x00\x00\x00":
            raise RuntimeError("Invalid SOCKS datagram")
        atyp = reply[3]
        offset = 10 if atyp == 1 else 22 if atyp == 4 else 7+reply[4] if atyp == 3 else None
        if offset is None or len(reply) < offset+12:
            raise RuntimeError("Truncated DNS reply")
        ident, flags, _, answers, _, _ = struct.unpack("!6H", reply[offset:offset+12])
        if ident != tid or not flags & 0x8000 or flags & 15 or answers == 0:
            raise RuntimeError("DNS validation failed")
        print("SOCKS_UDP_DNS_OK")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=7897)
    probe(parser.parse_args().port)
