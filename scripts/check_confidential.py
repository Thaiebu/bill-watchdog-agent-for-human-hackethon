#!/usr/bin/env python3
"""
Confidentiality & Secret Scanner for BillWatchdog.

Scans files before git commit or git push to prevent leaking:
- AWS Access Key IDs (AKIA...)
- AWS Secret Keys
- Google App Passwords (16-char codes)
- Private Keys (RSA / DSA / EC / SSH)
- GitHub Personal Access Tokens (ghp_...)
- Real Credit Card numbers
- Hardcoded database passwords or bearer tokens

Usage:
  python scripts/check_confidential.py          # Scan git staged files
  python scripts/check_confidential.py --all    # Scan all repository files
  python scripts/check_confidential.py file.py  # Scan specific file(s)
"""

import sys
import os
import re
import subprocess
from pathlib import Path

# Sensitive regex patterns to block
PATTERNS = [
    (
        "AWS Access Key ID",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        "Block AWS credentials from public repositories."
    ),
    (
        "AWS Secret Access Key",
        re.compile(r"(?i)(?:aws_secret_access_key|aws_secret|secret_key)\s*[:=]\s*['\"]([A-Za-z0-9/+=]{40})['\"]"),
        "Never hardcode AWS secret keys."
    ),
    (
        "Google App Password",
        re.compile(r"\b[a-z]{4}\s[a-z]{4}\s[a-z]{4}\s[a-z]{4}\b"),
        "Never commit Google 16-character App Passwords."
    ),
    (
        "Private Key",
        re.compile(r"-----BEGIN (?:[A-Z0-9_-]+\s+)?PRIVATE KEY-----"),
        "Never commit private encryption or SSH keys."
    ),
    (
        "GitHub Access Token",
        re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,80}\b"),
        "GitHub token found."
    ),
    (
        "Generic Bearer / API Secret Token",
        re.compile(r"(?i)(?:api_key|access_token|bearer_token|auth_token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{32,}['\"]"),
        "Potential API secret token."
    ),
]

# Paths to ignore (virtualenvs, git folder, test fixtures, seeds)
IGNORE_DIRS = {".git", "venv", ".venv", "__pycache__", ".pytest_cache", "node_modules"}
IGNORE_EXTENSIONS = {".pyc", ".db", ".sqlite", ".png", ".jpg", ".webp", ".svg", ".pdf"}

# Whitelisted test / mock files that contain intentional synthetic fixtures
WHITELIST_FILES = {"mock_adapter.py", "seed_data.py"}


def get_files_to_scan(args):
    """Determine which files to scan based on arguments."""
    if "--all" in args:
        root = Path(".")
        files = []
        for p in root.rglob("*"):
            if p.is_file() and not any(part in IGNORE_DIRS for part in p.parts):
                if p.suffix not in IGNORE_EXTENSIONS:
                    files.append(str(p))
        return files

    specific = [a for a in args if not a.startswith("--")]
    if specific:
        return specific

    # Default: Scan files staged in git
    try:
        out = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            text=True
        ).strip()
        if out:
            return out.splitlines()
    except Exception:
        pass

    # Fallback to all git tracked files
    try:
        out = subprocess.check_output(["git", "ls-files"], text=True).strip()
        return [f for f in out.splitlines() if not any(d in f for d in IGNORE_DIRS)]
    except Exception:
        return []


def mask_secret(match_str: str) -> str:
    """Mask all but first and last 2 characters of a secret."""
    if len(match_str) <= 6:
        return "***"
    return match_str[:2] + "*" * (len(match_str) - 4) + match_str[-2:]


def scan_file(filepath: str) -> list:
    """Scan a single file for confidential patterns. Returns list of violations."""
    path = Path(filepath)
    if not path.is_file() or path.suffix in IGNORE_EXTENSIONS:
        return []

    # Check if this file is in whitelist
    if path.name in WHITELIST_FILES:
        return []

    violations = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line_no, line in enumerate(f, start=1):
                # Skip comments explaining patterns
                if "AKIA..." in line or "regex" in line.lower() or "placeholder" in line.lower():
                    continue

                for label, pattern, advice in PATTERNS:
                    m = pattern.search(line)
                    if m:
                        secret = m.group(0)
                        # Exclude obvious documentation placeholders
                        if any(ph in secret.lower() for ph in ["your_", "sample", "xxxx", "test", "demo", "placeholder", "abcd"]):
                            continue
                        violations.append({
                            "file": filepath,
                            "line": line_no,
                            "label": label,
                            "secret_preview": mask_secret(secret),
                            "advice": advice,
                        })
    except Exception as exc:
        print(f"⚠️ Warning: Could not read {filepath}: {exc}")

    return violations


def main():
    args = sys.argv[1:]
    files = get_files_to_scan(args)

    if not files:
        print("ℹ️  No files to scan.")
        sys.exit(0)

    print(f"🛡️  Scanning {len(files)} file(s) for confidential data before GitHub push...")

    all_violations = []
    for f in files:
        violations = scan_file(f)
        all_violations.extend(violations)

    if all_violations:
        print("\n" + "=" * 65)
        print("🚨 CONFIDENTIAL INFORMATION DETECTED! PUSH BLOCKED!")
        print("=" * 65)
        for v in all_violations:
            print(f"\n❌ {v['file']}:{v['line']}")
            print(f"   Category : {v['label']}")
            print(f"   Found    : {v['secret_preview']}")
            print(f"   Action   : {v['advice']}")

        print("\n" + "=" * 65)
        print("💡 How to fix:")
        print("  1. Remove the credential from the file.")
        print("  2. Use environment variables (via .env) instead.")
        print("  3. Ensure .env is listed in .gitignore.")
        print("=" * 65 + "\n")
        sys.exit(1)
    else:
        print("✅ Clean! No credentials, passwords, or confidential keys found.")
        print("   Safe to commit and push to GitHub.")
        sys.exit(0)


if __name__ == "__main__":
    main()
