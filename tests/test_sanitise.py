"""The tree that will be committed must not contain credential-shaped text."""

from __future__ import annotations

from pe_audit.constants import REPO_ROOT
from pe_audit.sanitise import scan_text, scan_tree


def test_scanner_flags_a_constructed_credential() -> None:
    sample = "token = '" + ("k" * 12) + "'"
    findings = scan_text(sample, "sample.env")
    assert any(item.rule == "assigned-secret" for item in findings)


def test_scanner_flags_a_constructed_cloud_key() -> None:
    sample = "AKIA" + ("A" * 16)
    findings = scan_text(sample, "sample.txt")
    assert any(item.rule == "aws-access-key" for item in findings)


def test_repository_tree_has_no_secret_patterns() -> None:
    findings = scan_tree(REPO_ROOT)
    assert findings == [], "\n".join(str(item) for item in findings)


def test_worktree_has_no_retired_publication_names() -> None:
    """Current files only. Git history is a separate publication decision."""
    banned = ("North" + "line", "Ash" + "mere", "Snow" + "flake", "Blue" + "print")
    hits: list[str] = []
    for path in sorted(REPO_ROOT.rglob("*")):
        if not path.is_file():
            continue
        if any(part in {".git", ".venv", "venv", "__pycache__", ".pytest_cache"} for part in path.parts):
            continue
        if path.suffix.lower() in {".pyc", ".png", ".zip"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for name in banned:
            if name in text:
                hits.append(f"{path.relative_to(REPO_ROOT)}:{name}")
    assert hits == []
