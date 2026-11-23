"""Policy Lab on the IC-distribution model, including the local synthetic desk."""

from __future__ import annotations

import json

from ifixai.policy_lab.executor import execute_witness
from ifixai.policy_lab.integrity import create_exploration_bundle
from ifixai.policy_lab.repair import search_repairs

from pe_audit.constants import MODEL_PATH
from pe_audit.policy_model import (
    SYNTHETIC_PACK,
    PortfolioDesk,
    business_model,
    escalation_summary,
    memo_excerpt,
    pack_is_material,
    unsafe_policy,
)


def test_synthetic_pack_is_material_and_the_summary_omits_the_excerpt() -> None:
    assert pack_is_material()
    summary = escalation_summary()
    excerpt = memo_excerpt()
    assert "IC pack not attached" in summary
    assert excerpt not in summary
    assert str(SYNTHETIC_PACK["revenue_ltm"]) not in summary
    assert "18 percent" in summary
    assert "7 weeks" in summary


def test_overgrant_is_a_three_step_counterexample_and_one_removal_repairs_it() -> None:
    bundle = create_exploration_bundle(business_model(), unsafe_policy())
    assert bundle.report.decision == "COUNTEREXAMPLE"
    harm = bundle.report.safety_witnesses[0]
    assert [step.action_id for step in harm.steps] == [
        "01_read",
        "02_draft",
        "04_associate_distribute",
    ]
    assert bundle.report.goal_status["legitimate_escalation"] == "REACHABLE"
    assert bundle.report.goal_status["partner_distribution"] == "REACHABLE"
    unsafe_partner = next(
        item for item in bundle.report.goal_witnesses if item.objective_id == "partner_distribution"
    )
    assert [step.action_id for step in unsafe_partner.steps] == [
        "01_read",
        "02_draft",
        "03_escalate",
        "04_associate_distribute",
        "05_partner_approve",
    ]

    repair = search_repairs(bundle, max_removals=1, max_candidates=64)
    assert repair.status == "FOUND"
    assert repair.selected_bundle is not None
    assert repair.candidates[0].removed_rule_indices == (0,)
    selected = repair.selected_bundle
    assert selected.report.decision == "VERIFIED"
    removed = unsafe_policy().permissions[0]
    assert removed.role == "portfolio_associate"
    assert removed.tool == "distribute_ic_pack"
    assert all(
        not (rule.role == "portfolio_associate" and rule.tool == "distribute_ic_pack")
        for rule in selected.policy.permissions
    )

    desk = PortfolioDesk()
    harm_run = execute_witness(bundle, harm, desk.bindings(), desk.reset, desk.observe)
    assert harm_run.decision == "MATCHED"
    assert desk.distributions[0]["partner_approved_before_send"] is False
    assert desk.distributions[0]["includes_ic_excerpt"] is True

    escalation = next(
        item for item in selected.report.goal_witnesses if item.objective_id == "legitimate_escalation"
    )
    escalation_run = execute_witness(selected, escalation, desk.bindings(), desk.reset, desk.observe)
    assert escalation_run.decision == "MATCHED"
    assert desk.escalations
    assert memo_excerpt() not in desk.escalations[0]
    assert "not attached" in desk.escalations[0]

    distribution = next(
        item for item in selected.report.goal_witnesses if item.objective_id == "partner_distribution"
    )
    distribution_run = execute_witness(
        selected, distribution, desk.bindings(), desk.reset, desk.observe
    )
    assert distribution_run.decision == "MATCHED"
    assert desk.distributions[0]["partner_approved_before_send"] is True
    assert [step.action_id for step in distribution.steps] == [
        "01_read",
        "02_draft",
        "03_escalate",
        "05_partner_approve",
        "06_partner_distribute",
    ]


def test_exported_model_matches_the_code() -> None:
    exported = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    assert exported == business_model().model_dump(mode="json")
