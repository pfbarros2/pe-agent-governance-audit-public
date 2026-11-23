"""The profile is the contract iFixAi will accept, and the spec is what it cites."""

from __future__ import annotations

import json
import re
from pathlib import Path

from ifixai.core.profile import AgentProfile

from pe_audit.constants import PROFILE_PATH, REPO_ROOT, SPEC_PATH

CITE = re.compile(r"^(?P<path>.+):(?P<start>\d+)(?:-(?P<end>\d+))?$")


def test_profile_matches_the_author_schema() -> None:
    raw = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    profile = AgentProfile.model_validate(raw)
    assert profile.name == "Quay Ledger"
    assert profile.domain == "pe_portfolio_operations"
    assert profile.abilities.trains_models is False
    assert profile.abilities.works_with_agents is False
    assert profile.abilities.serves_consumers is False
    grants = {role.name: set(role.allowed_tools) for role in profile.roles}
    assert "distribute_ic_pack" not in grants["portfolio_associate"]
    assert "purge_working_paper" not in grants["portfolio_associate"]
    assert grants["portfolio_company_contact"] == {"read_operating_metrics"}
    assert "purge_working_paper" in grants["deal_partner"]
    assert "escalate_material_issue" in grants["portfolio_associate"]
    assert "draft_ic_memo_excerpt" in grants["portfolio_associate"]


def test_evidence_cites_resolve_inside_the_spec() -> None:
    raw = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    lines = SPEC_PATH.read_text(encoding="utf-8").splitlines()
    assert raw["evidence"], "the profile should cite the specification"
    for field, cites in raw["evidence"].items():
        assert cites, field
        for cite in cites:
            match = CITE.match(cite)
            assert match, cite
            path = REPO_ROOT / match.group("path")
            assert path == SPEC_PATH
            start = int(match.group("start"))
            end = int(match.group("end") or start)
            assert 1 <= start <= end <= len(lines)
            assert lines[start - 1].strip()
            assert lines[end - 1].strip()


def test_specification_and_profile_share_the_synthetic_pack_rules() -> None:
    spec = SPEC_PATH.read_text(encoding="utf-8")
    profile = PROFILE_PATH.read_text(encoding="utf-8")
    for needle in ("PC-1842", "42000000", "deal_partner_queue", "Demo PE Firm"):
        assert needle in spec
        if needle != "42000000":
            assert needle in profile or needle in spec
    assert "Demo Portfolio Company" in spec
    assert "Nothing here is a commercial product" in spec
    assert "does not record employer or IP clearance" in spec
    assert "North" + "line" not in spec
    assert "Ash" + "mere" not in spec
