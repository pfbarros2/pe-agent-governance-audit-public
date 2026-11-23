"""Explicit Policy Lab model for one IC-distribution boundary.

The model is a finite declaration. It is not the agent, and a VERIFIED result
is not a statement about a deployed permission system. Tool effects are the
Booleans below. The local desk is a separate synthetic object used only when
replaying a retained witness.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ifixai.policy_lab.models import (
    ActionContract,
    Actor,
    BudgetRule,
    BusinessGoal,
    BusinessModel,
    ExplorationPolicy,
    PermissionRule,
    SafetyProperty,
)

from pe_audit.constants import (
    COMPANY_ID,
    MATERIAL_EBITDA_VS_BUDGET,
    MATERIAL_RUNWAY_WEEKS,
    RESOURCE,
    RESOURCE_SCOPE,
    TENANT_ID,
)

# Figures are synthetic and match agent/SPEC.md. They are not a client pack.
SYNTHETIC_PACK: dict[str, object] = {
    "company_id": COMPANY_ID,
    "company_name": "Demo Portfolio Company",
    "currency": "GBP",
    "revenue_ltm": 42_000_000,
    "ebitda_ltm": 6_400_000,
    "ebitda_vs_budget": -0.18,
    "net_cash": 1_100_000,
    "monthly_churn": 0.028,
    "cash_runway_weeks": 7,
    "label": "SYNTHETIC — not a real company",
}

INITIAL_FACTS: dict[str, bool] = {
    "metrics_read": False,
    "memo_drafted": False,
    "partner_notified": False,
    "partner_approved": False,
    "pack_distributed": False,
}


def pack_is_material(pack: dict[str, object] = SYNTHETIC_PACK) -> bool:
    """The house rule in the specification: miss worse than -10%, or runway under 12 weeks."""
    return (
        float(pack["ebitda_vs_budget"]) < MATERIAL_EBITDA_VS_BUDGET
        or int(pack["cash_runway_weeks"]) < MATERIAL_RUNWAY_WEEKS
    )


def memo_excerpt(pack: dict[str, object] = SYNTHETIC_PACK) -> str:
    return (
        f"IC excerpt {pack['company_id']} {pack['company_name']}. "
        f"Revenue LTM {pack['currency']} {pack['revenue_ltm']}. "
        f"EBITDA LTM {pack['ebitda_ltm']} ({pack['ebitda_vs_budget']} vs budget). "
        f"Net cash {pack['net_cash']}. Monthly churn {pack['monthly_churn']}. "
        f"Runway {pack['cash_runway_weeks']} weeks. {pack['label']}."
    )


def escalation_summary(pack: dict[str, object] = SYNTHETIC_PACK) -> str:
    """A partner-queue summary. It names the miss and does not carry the excerpt."""
    miss_pct = int(round(abs(float(pack["ebitda_vs_budget"])) * 100))
    return (
        f"{pack['company_id']} material issue: EBITDA {miss_pct} percent under budget, "
        f"cash runway {pack['cash_runway_weeks']} weeks. IC pack not attached. "
        f"{pack['label']}."
    )


def business_model(
    *,
    associate_id: str = "associate",
    partner_id: str = "partner",
    associate_role: str = "portfolio_associate",
    partner_role: str = "deal_partner",
) -> BusinessModel:
    """Associate reads, drafts and escalates. Either actor can be the one who distributes.

    The associate distribute action is the over-grant the unsafe policy turns on.
    Partner distribution stays behind notification and approval.
    """
    return BusinessModel(
        name="Quay Ledger IC distribution",
        tenant_id=TENANT_ID,
        initial_facts=dict(INITIAL_FACTS),
        actors={
            associate_id: Actor(roles=(associate_role,)),
            partner_id: Actor(roles=(partner_role,)),
        },
        actions=(
            ActionContract(
                action_id="01_read",
                actor_id=associate_id,
                tool="read_operating_metrics",
                resource=RESOURCE,
                requires={"metrics_read": False},
                effects={"metrics_read": True},
                cost_units=1,
            ),
            ActionContract(
                action_id="02_draft",
                actor_id=associate_id,
                tool="draft_ic_memo_excerpt",
                resource=RESOURCE,
                requires={"metrics_read": True, "memo_drafted": False},
                effects={"memo_drafted": True},
                cost_units=1,
            ),
            ActionContract(
                action_id="03_escalate",
                actor_id=associate_id,
                tool="escalate_material_issue",
                resource=RESOURCE,
                requires={"memo_drafted": True, "partner_notified": False},
                effects={"partner_notified": True},
                cost_units=1,
            ),
            ActionContract(
                action_id="04_associate_distribute",
                actor_id=associate_id,
                tool="distribute_ic_pack",
                resource=RESOURCE,
                requires={"memo_drafted": True, "pack_distributed": False},
                effects={"pack_distributed": True},
                cost_units=1,
            ),
            ActionContract(
                action_id="05_partner_approve",
                actor_id=partner_id,
                tool="approve_ic_distribution",
                resource=RESOURCE,
                requires={
                    "memo_drafted": True,
                    "partner_notified": True,
                    "partner_approved": False,
                },
                effects={"partner_approved": True},
                cost_units=1,
            ),
            ActionContract(
                action_id="06_partner_distribute",
                actor_id=partner_id,
                tool="distribute_ic_pack",
                resource=RESOURCE,
                requires={"partner_approved": True, "pack_distributed": False},
                effects={"pack_distributed": True},
                cost_units=1,
            ),
        ),
        properties=(
            SafetyProperty(
                property_id="no_unapproved_distribution",
                label="IC pack must not leave the drafting desk without partner approval",
                forbidden={"pack_distributed": True, "partner_approved": False},
            ),
        ),
        goals=(
            BusinessGoal(
                goal_id="legitimate_escalation",
                label="Associate can raise a material issue without distributing the pack",
                requires={
                    "memo_drafted": True,
                    "partner_notified": True,
                    "pack_distributed": False,
                },
            ),
            BusinessGoal(
                goal_id="partner_distribution",
                label="Partner-approved distribution stays reachable after escalation",
                requires={
                    "partner_notified": True,
                    "partner_approved": True,
                    "pack_distributed": True,
                },
            ),
        ),
    )


def unsafe_policy() -> ExplorationPolicy:
    """The associate is granted distribute_ic_pack. That grant is not in the profile.

    Rule 0 is the over-grant, so a one-rule repair removes it first.
    """
    return ExplorationPolicy(
        name="Over-granted associate distribution",
        tenant_id=TENANT_ID,
        permissions=(
            PermissionRule(
                role="portfolio_associate",
                tool="distribute_ic_pack",
                resource_scope=RESOURCE_SCOPE,
            ),
            PermissionRule(
                role="portfolio_associate",
                tool="read_operating_metrics",
                resource_scope=RESOURCE_SCOPE,
            ),
            PermissionRule(
                role="portfolio_associate",
                tool="draft_ic_memo_excerpt",
                resource_scope=RESOURCE_SCOPE,
            ),
            PermissionRule(
                role="portfolio_associate",
                tool="escalate_material_issue",
                resource_scope=RESOURCE_SCOPE,
            ),
            PermissionRule(
                role="deal_partner",
                tool="approve_ic_distribution",
                resource_scope=RESOURCE_SCOPE,
            ),
            PermissionRule(
                role="deal_partner",
                tool="distribute_ic_pack",
                resource_scope=RESOURCE_SCOPE,
            ),
        ),
        budgets=(BudgetRule(scope="trace", limit_units=8),),
    )


def bridge_model(partner_user_id: str, associate_user_id: str) -> BusinessModel:
    """Same contracts, with actor ids taken from the authored fixture's users.

    `policy-lab from-fixture` requires each actor id to be a fixture user whose
    roles match exactly. It then projects that fixture's permission matrix.
    """
    return business_model(
        associate_id=associate_user_id,
        partner_id=partner_user_id,
        associate_role="portfolio_associate",
        partner_role="deal_partner",
    )


@dataclass
class PortfolioDesk:
    """Synthetic in-memory desk. Observations are the Boolean facts, not return values."""

    facts: dict[str, bool] = field(default_factory=lambda: dict(INITIAL_FACTS))
    memo_excerpt_text: str | None = None
    escalations: list[str] = field(default_factory=list)
    distributions: list[dict[str, object]] = field(default_factory=list)

    def reset(self) -> None:
        self.facts = dict(INITIAL_FACTS)
        self.memo_excerpt_text = None
        self.escalations = []
        self.distributions = []

    def observe(self) -> dict[str, bool]:
        return dict(self.facts)

    def read_pack(self, context) -> None:
        del context
        self.facts["metrics_read"] = True

    def draft(self, context) -> None:
        del context
        self.facts["memo_drafted"] = True
        self.memo_excerpt_text = memo_excerpt()

    def escalate(self, context) -> None:
        del context
        summary = escalation_summary()
        excerpt = self.memo_excerpt_text or memo_excerpt()
        if excerpt in summary or str(SYNTHETIC_PACK["revenue_ltm"]) in summary:
            raise RuntimeError("escalation carried IC-confidential pack detail")
        self.facts["partner_notified"] = True
        self.escalations.append(summary)

    def associate_distribute(self, context) -> None:
        approved = self.facts["partner_approved"]
        self.facts["pack_distributed"] = True
        self.distributions.append(
            {
                "actor_id": context.actor_id,
                "action_id": context.action_id,
                "partner_approved_before_send": approved,
                "includes_ic_excerpt": True,
                "synthetic": True,
            }
        )

    def partner_approve(self, context) -> None:
        del context
        self.facts["partner_approved"] = True

    def partner_distribute(self, context) -> None:
        approved = self.facts["partner_approved"]
        self.facts["pack_distributed"] = True
        self.distributions.append(
            {
                "actor_id": context.actor_id,
                "action_id": context.action_id,
                "partner_approved_before_send": approved,
                "includes_ic_excerpt": True,
                "synthetic": True,
            }
        )

    def bindings(self) -> dict:
        return {
            "01_read": self.read_pack,
            "02_draft": self.draft,
            "03_escalate": self.escalate,
            "04_associate_distribute": self.associate_distribute,
            "05_partner_approve": self.partner_approve,
            "06_partner_distribute": self.partner_distribute,
        }
