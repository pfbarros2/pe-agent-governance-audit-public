"""The picture guide points at files that are actually in the tree."""

from __future__ import annotations

import re
from pathlib import Path

from pe_audit.constants import REPO_ROOT

GUIDE = REPO_ROOT / "docs" / "walkthrough.md"


def test_walkthrough_images_resolve() -> None:
    text = GUIDE.read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/walkthrough.md" in readme
    images = re.findall(r"!\[[^\]]+\]\(([^)]+)\)", text)
    assert len(images) == 8
    for rel in images:
        path = (GUIDE.parent / rel).resolve()
        assert path.is_file(), rel
        assert path.stat().st_size > 10_000
        assert path.suffix == ".png"
    assert "self-judged" in text
    assert "COUNTEREXAMPLE" in text
    assert "VERIFIED" in text
