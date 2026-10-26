#!/usr/bin/env python3
"""Fail closed on unexpected publication files and common credential markers.

PRIVATE_DENY_JSON optionally supplies case-insensitive strings from outside the repo.
Only file/line/category is reported; matching content is never printed.
This scanner is a guard, not a replacement for manual review.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

TOP_LEVEL = {"README.md", "SECURITY.md", "LICENSE", "requirements.txt", ".gitignore", ".gitattributes"}
DIRS = {"client", "server", "docs", "tools", "tests", ".github"}
SUFFIXES = {".py", ".ps1", ".sh", ".md", ".yml", ".yaml"}
PATTERNS = {
    "github-token": r"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}",
    "tailscale-key": r"tskey-[A-Za-z0-9-]{16,}",
    "private-key": r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----",
    "live-uuid": r"\b[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}\b",
    "personal-windows-path": r"[A-Z]:[\\/]Users[\\/](?!Public\b|Default\b)[^\s'\"<>]+",
}


def scan(root, staged=False):
    if staged:
        data = subprocess.check_output(["git", "-C", str(root), "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"])
        names = [x.decode("utf-8") for x in data.split(b"\0") if x]
    else:
        names = [p.relative_to(root).as_posix() for p in root.rglob("*")
                 if p.is_file() and not any(x in {".git", "__pycache__", ".pytest_cache"} for x in p.relative_to(root).parts)]
    denied = [x.lower() for x in json.loads(os.environ.get("PRIVATE_DENY_JSON", "[]")) if len(x) >= 4]
    findings = []
    for name in names:
        rel = Path(name)
        if not (name in TOP_LEVEL or rel.parts[0] in DIRS and rel.suffix in SUFFIXES):
            findings.append((name, 0, "unexpected-file")); continue
        file = root/rel
        if file.is_symlink():
            findings.append((name, 0, "symlink")); continue
        if staged:
            text = subprocess.check_output(["git", "-C", str(root), "show", ":"+name]).decode("utf-8-sig")
        else:
            text = file.read_text("utf-8-sig")
        for line_no, line in enumerate(text.splitlines(), 1):
            for kind, regex in PATTERNS.items():
                if re.search(regex, line, re.IGNORECASE):
                    findings.append((name, line_no, kind))
            if any(value in line.lower() for value in denied):
                findings.append((name, line_no, "private-deny-value"))
    for name, line, kind in findings:
        print(f"{name}:{line}: {kind}")
    if not findings:
        print(f"PUBLICATION_SCAN_OK files={len(names)}; matched content not logged")
    return 1 if findings else 0


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--staged", action="store_true")
    args=parser.parse_args()
    raise SystemExit(scan(args.root.resolve(), args.staged))
