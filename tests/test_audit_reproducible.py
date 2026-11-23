"""A fresh mock run must match the checked-in stable scorecard.

The raw JSON carries a timestamp. The comparison uses the canonical projection
the experiment writes to results/mock-audit/canonical.json.
"""

from __future__ import annotations

import json
from pathlib import Path

from ifixai._version import VERSION
from ifixai.harness.registry import ALL_SPECS
from ifixai.harness.suites import ESSENTIAL_TEST_IDS

from pe_audit.canonical import canonical_scorecard
from pe_audit.constants import AUDIT_DIR, FIXTURE_PATH, REPO_ROOT
from pe_audit.narrative import EXPERIMENT_REPOSITORY_URL
from pe_audit.runner import author_fixture, execute_audit, load_scorecard, validate_fixture
from pe_audit.sanitise import scan_tree


def test_authored_fixture_matches_the_committed_file(tmp_path: Path) -> None:
    destination = tmp_path / "quay_ledger.yaml"
    author_fixture(destination)
    assert destination.read_text(encoding="utf-8") == FIXTURE_PATH.read_text(encoding="utf-8")
    validate_fixture(destination)


def test_checked_in_scorecard_is_the_essential_suite() -> None:
    scorecard = json.loads((AUDIT_DIR / "scorecard.json").read_text(encoding="utf-8"))
    assert scorecard["metadata"]["provider"] == "mock"
    assert scorecard["metadata"]["self_judged"] is True
    got = [item["test_id"] for item in scorecard["test_results"]]
    aside = [item["test_id"] for item in scorecard.get("not_applicable") or []]
    assert set(got + aside) == set(ESSENTIAL_TEST_IDS)
    assert len(ALL_SPECS) == 61
    assert len(ESSENTIAL_TEST_IDS) == 10
    findings = (REPO_ROOT / "reports" / "findings.md").read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    grade = str(scorecard["overall"]["grade"])
    assert grade in findings
    assert grade in readme
    assert VERSION in findings
    assert "self-judged" in findings.lower() or "self_judged" in findings
    assert "synthetic" in findings.lower()
    assert "ACK" in findings
    assert "no_rule_for_role:deal_partner" in findings
    assert "Blue" + "print" not in findings
    assert "06_partner_distribute" in findings
    assert "does not record employer or IP clearance" in findings
    assert "not a defect in iFixAi" in findings
    assert not (REPO_ROOT / "notes" / "linkedin-draft.md").exists()
    assert scan_tree(AUDIT_DIR) == []


def test_fresh_mock_run_matches_canonical_scorecard(tmp_path: Path) -> None:
    output = tmp_path / "audit"
    reliability = tmp_path / "runs"
    completed = execute_audit(output, reliability)
    fresh = canonical_scorecard(load_scorecard(output))
    recorded = json.loads((AUDIT_DIR / "canonical.json").read_text(encoding="utf-8"))
    assert fresh == recorded
    assert completed.returncode == int((AUDIT_DIR / "exit-code.txt").read_text().strip())
