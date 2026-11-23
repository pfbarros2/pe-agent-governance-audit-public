"""Reject credentials, live warehouse hosts, and client-confidential markers.

The scanner looks at text this repository authored. It does not decide that a
file is safe for a client environment. A miss is not evidence that no secret exists.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "agent-tools",
    "runs",
    "htmlcov",
    "dist",
    "build",
}
SKIP_SUFFIXES = {".pyc", ".png", ".zip", ".gz", ".whl", ".so", ".dll"}

# Patterns are written so this source file does not itself contain a match.
_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("aws-access-key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("private-key", re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----")),
    ("vendor-api-key", re.compile(r"sk-(?:proj-|ant-)?[A-Za-z0-9_\-]{20,}")),
    ("slack-token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("github-token", re.compile(r"ghp_[A-Za-z0-9]{20,}")),
    ("github-fine-grained", re.compile(r"github_pat_[A-Za-z0-9_]{20,}")),
    (
        "assigned-secret",
        re.compile(
            r"(?i)(?:api[_-]?key|password|secret|token)\s*[:=]\s*['\"][^'\"]{8,}['\"]"
        ),
    ),
    ("warehouse-host", re.compile("snow" + "flakecomputing\\.com", re.IGNORECASE)),
    ("deloitte-mailbox", re.compile(r"@deloitte\.(?:com|co\.uk)\b", re.IGNORECASE)),
    (
        "client-confidential-marker",
        re.compile(r"(?i)\b(?:client\s+confidential|strictly\s+confidential\s+client)\b"),
    ),
)


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    rule: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.rule}"


def scan_text(text: str, relpath: str = "<text>") -> list[Finding]:
    findings: list[Finding] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for rule, pattern in _PATTERNS:
            if pattern.search(line):
                findings.append(Finding(relpath, line_no, rule))
    return findings


def scan_tree(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        if path.name == ".gitignore":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        relpath = path.relative_to(root).as_posix()
        findings.extend(scan_text(text, relpath))
    return findings
