"""Readable findings text, filled only from recorded results."""

from __future__ import annotations

from typing import Any


def _pct(score: object) -> str:
    if score is None:
        return "n/a"
    return f"{float(score):.1%}"


def _arrow(steps: list[str]) -> str:
    return " → ".join(f"`{step}`" for step in steps) or "not recorded"


def findings_markdown(
    *,
    observations: dict[str, Any],
    ifixai_version: str,
    catalogue_count: int,
    essential_ids: list[str],
    audit_exit_code: int,
    scorecard: dict[str, Any],
    unsafe_decision: str,
    safety_action_ids: list[str],
    repair_status: str,
    removed_rule: dict[str, str] | None,
    repaired_decision: str,
    goal_status: dict[str, str],
    fixture_projection_decision: str,
    unsafe_replay: str,
    escalation_replay: str,
    distribution_replay: str,
    unsafe_partner_action_ids: list[str],
    repaired_partner_action_ids: list[str],
) -> str:
    meta = scorecard["metadata"]
    overall = scorecard["overall"]
    rows = []
    for item in scorecard["test_results"]:
        rows.append(
            f"| {item['test_id']} | {item['name']} | {item['status']} | {item.get('score_pct', _pct(item.get('score')))} |"
        )
    aside = scorecard.get("not_applicable") or []
    aside_lines = [
        f"- `{item.get('test_id')}`: {item.get('reason')}" for item in aside
    ] or ["- None. Every inspection in the essential suite was run."]
    removed = "not recorded"
    if removed_rule:
        removed = (
            f"role `{removed_rule['role']}`, tool `{removed_rule['tool']}`, "
            f"scope `{removed_rule['resource_scope']}`"
        )
    self_judged = meta.get("self_judged")
    example = observations.get("example") or {}
    example_block = "No B12 item with actual reply `ACK` was found in this scorecard."
    if example:
        example_block = (
            f"One scored B12 item is `{example['test_case_id']}`. "
            f"The prompt was: \"{example['prompt_sent']}\" "
            f"The mock reply was `{example['actual']}`. "
            f"A rubric dimension was marked passed with reasoning `{example['reasoning']}`."
        )
    rules = ", ".join(f"`{rule}`" for rule in observations.get("policy_rules") or []) or "none"
    return f"""# Quay Ledger findings

Independent synthetic demonstration. This file is generated from the checked-in mock scorecard and the Policy Lab reports. It is not a certification, not a commercial deliverable, and not evidence that a deployed agent is safe. The copyright notice does not record employer or IP clearance. The letter grade is a self-judged mock smoke test. Policy Lab is a separate offline check of a declared permission model.

## Two results, kept apart

The grade in **Mock scorecard** is only the mock provider grading its own canned replies. It is self-judged. The decisions in **Policy Lab** are a separate offline search of a declared permission model. They do not change that grade. A model decision of VERIFIED does not make the grade evidence that Quay Ledger is safe. A model decision of COUNTEREXAMPLE does not mean the letter grade failed.

## What was executed

- iFixAi `{ifixai_version}`, provider `{meta.get("provider")}`, fixture `{meta.get("fixture_name")}`.
- JSON metadata: self-judged `{self_judged}`, run mode `{meta.get("run_mode")}`, judge provider `{observations.get("judge_provider")}`, judge calls `{observations.get("judge_calls")}`.
- The terminal banner on this run says the grade is self-judged and not a citable result. The Markdown header instead says `Evaluation Mode: single`, and that file does not repeat the banner. Read `results/mock-audit/stdout.txt` next to `scorecard.md`.
- The installed package registers **{catalogue_count}** inspections. `ifixai list suites` describes the default suite as `essential`.
- That essential suite, read from the installed package, is **{len(essential_ids)}** inspections: {", ".join(f"`{item}`" for item in essential_ids)}.
- The scorecard contains **{len(scorecard["test_results"])}** inspection results. Process exit code of `ifixai run`: `{audit_exit_code}`.
- No live model and no paid API were called. There is no live warehouse connection.

## Mock scorecard — self-judged mock only

Grade **{overall.get("grade")}**, score **{overall.get("score_pct", _pct(overall.get("score")))}**, verdict **{overall.get("verdict")}**, passed at the run's minimum **{overall.get("passed")}** (minimum {overall.get("min_score")}). Mandatory-minimums flag on the overall section: `{overall.get("mandatory_minimums_passed")}`.

The grade is not a control test. Scored evidence includes **{observations.get("ack_passed")}** items whose reply was `ACK` and whose passed flag is true. {example_block} iFixAi's mock judge passes a reply that is not one of the planted unsafe strings. `ACK` is the mock's default reply. Passing it does not show that a model refused the prompt.

Separate from the grade, the scorecard holds **{observations.get("hook_notes_failed")}** diagnostic hook notes with `passed: false`. `ifixai author` does not write a `governance:` block, and these notes are marked `hook_note` so they do not change the inspection status. The policy rules on those notes are {rules}. For the deal partner, `authorize_tool` returned `authorized=False` where the note's expected value was `authorized=True`. The letter grade stayed A. A partner-permission gap that is only in the notes will not fail a CI gate that reads the grade.

| ID | Inspection | Status | Score |
|---|---|---|---|
{chr(10).join(rows)}

B20 case ids are resampled. iFixAi 4.3.0 has a seed flag for B12 and for the B01/B16 holdouts, and none for B20. The reproduction check compares B20's status, score and pass count. It does not require the same case ids.

### Set aside

{chr(10).join(aside_lines)}

## Policy Lab — declared model only, not an inspection grade

Policy Lab does not change the inspection grade and does not grade the agent. The model is declared in `src/pe_audit/policy_model.py` and exported to `policy/`.

The unsafe permission file adds `distribute_ic_pack` for `portfolio_associate`. That grant is not in `agent/profile.json`. This repository introduces that grant on purpose, as a test input in `policy/unsafe-permissions.json`. It is not a defect in iFixAi. The offline check reported the counterexample; it did not create the grant.

- Check decision: **{unsafe_decision}**.
- Shortest retained harm witness, by action id: {_arrow(safety_action_ids)}. This path reads, drafts, and distributes with no partner approval.
- Repair status: **{repair_status}**. Removed rule: {removed}.
- Selected permissions, re-checked: **{repaired_decision}**.
- Goal status on the unsafe check: {", ".join(f"`{key}` {value}" for key, value in goal_status.items())}. Reachable does not mean the retained witness is a clean partner send.
- Unsafe partner-distribution witness: {_arrow(unsafe_partner_action_ids)}. Read this as the over-granted model. The associate distributes the pack, and partner approval is recorded afterwards. It is not the repaired path.
- Repaired partner-distribution witness: {_arrow(repaired_partner_action_ids)}. Read this as the model after that one grant is removed. The partner approves, then the partner distributes. `04_associate_distribute` is not on this path.
- `results/policy-lab/repair/report.md` and `results/policy-lab/replay/report.md` repeat the pre-repair bundle. The repair outcome is `results/policy-lab/repair/repair.json` and `results/policy-lab/repair/selected-bundle.json`.
- Fixture permission projection (`policy-lab from-fixture` on the authored fixture): **{fixture_projection_decision}**.

Local replay through `execute_witness` on the synthetic desk: unsafe witness **{unsafe_replay}**, escalation goal **{escalation_replay}**, partner-distribution goal **{distribution_replay}**. The desk's escalation string does not include the memo excerpt. It still names the material miss and the runway, which the specification allows. The associate distribute path records that the IC excerpt was included while partner approval was still false. Those are observations of this local object, not of a production tool.

`VERIFIED` means the declared model had a complete frontier, the forbidden state was unreachable, and both completion goals were reachable. It does not mean a tenant boundary, a row-level company scope, or a live agent was tested. `from-fixture` widens every tool grant to resource scope `*`, which the Policy Lab report states. Company id PC-1842 is a label in the model, not an enforced warehouse predicate.

## What this does not prove

- That a model in production would refuse a partner-queue email of the IC pack.
- That the mock grade would survive a cross-provider judge. iFixAi marks self-judged runs as not citable.
- That row-level access ("this contact may read only their company") holds. The fixture grants `read_operating_metrics` to the contact role with no company predicate.
- That purge resistance (P01) covers quiet leakage. Leakage of the pack is the Policy Lab property, not a claim that P01 measured it.
- Anything about a real portfolio company, a real IC paper, or a real client.

## Remediation priorities

1. Keep this mock grade out of any go-live decision. The next evidence that could count is a staging agent, a judge from a different provider, and a dry-run cost check. Commands are in `docs/live-judge.md`. They were not run.
2. Do not grant `distribute_ic_pack` to the associate, including by a wildcard. In this model that single extra grant is a three-step path from a permitted read and draft to an unapproved send. Removing it left escalation reachable. The partner send that remains is the repaired path: approval first, then distribution. The unsafe witness had sent the pack before approval.
3. Make the escalation tool incapable of accepting the memo body or the operating pack. The local desk enforces that on a string. A deployed tool needs a schema that has no attachment field, not a sentence in the prompt.
4. Add company-scoped authorization before a portfolio-company contact can use the same assistant. This fixture cannot say "PC-1842 only".
5. Treat B01, B08 and P01 as mandatory gates on a live judge. A self-judged pass is not that gate.

## How this could become a go-live gate

Use the pieces as gates, in order, and do not collapse them into the letter grade:

1. The profile is generated from the agent repository, with citations, and `ifixai validate` passes for the suite you will run.
2. A secret scan of the fixture and the profile is clean.
3. Policy Lab on the declared permission projection is `VERIFIED` for the IC-distribution model, and a checked-in over-grant still produces the known counterexample. That is a regression test of the model, not of the model weights.
4. The mock run is a pipeline smoke test. It has to complete. Its grade is not the gate.
5. On a staging endpoint, a cross-provider judge runs the essential suite. B01, B08 and P01 pass, and the score meets the bar you set with `--min-score`, after `--dry-run` has been read.
6. A person reads a sample of escalation payloads and confirms the IC pack is absent.

This repository implements steps 1 to 4 for a fictional agent. It does not implement step 5 or step 6.
"""


def linkedin_post(findings_inputs: dict[str, Any]) -> str:
    """Public post. No vendor name, no employer mark, no client name."""
    overall = findings_inputs["scorecard"]["overall"]
    score = overall.get("score_pct", _pct(overall.get("score")))
    grade = overall.get("grade")
    if score == "100.0%" and grade == "A":
        opening = "My mock AI agent scored 100% on an audit smoke test."
        score_line = "The 100% came from canned, self-judged replies."
    else:
        opening = (
            f"My mock AI agent scored {score} (grade {grade}) on an audit smoke test."
        )
        score_line = f"The {score} grade {grade} result came from canned, self-judged replies."
    return f"""{opening} A separate permission check found it could bypass partner approval.

Each week I take an interesting open-source AI project, build a small synthetic experiment in one sector, and share what worked and what broke. This week the sector is private equity. The agent is fictional. It reads a synthetic operating pack, drafts an investment-committee memo, and escalates a material issue. Only a partner should send that pack.

I then gave the associate one extra permission the profile does not grant: sending the pack. That permission is a test input, not a fault in the open-source project. The check found a three-step path, read then draft then send, with no partner approval. On that unsafe model, the recorded partner path still sent the pack first and logged approval afterwards. Removing that single permission closed the bypass. Escalation still worked, and so did a partner send made only after approval.

{score_line} It is a smoke test, not an evaluation of a live model. This is an independent synthetic experiment: no real data, no live AI model, and not proof of production security.

If a score and a permission check disagree, which one would you trust before an investment committee?

#AIGovernance #PrivateEquity #AgentSafety"""


# Replace this once the public repository name is known.
# Used by the optional LinkedIn text generators below; no draft is checked in.
EXPERIMENT_REPOSITORY_URL = "https://github.com/pfbarros2/pe-agent-governance-audit-public"


def linkedin_comment(findings_inputs: dict[str, Any]) -> str:
    version = findings_inputs["ifixai_version"]
    return f"""The open-source audit harness is iFixAi {version} (Apache-2.0): https://github.com/ifixai-ai/iFixAi

Experiment repository: replace the placeholder URL below once the public repository name is known. Include that URL only once the repository is actually public. No demo site exists.
{EXPERIMENT_REPOSITORY_URL}"""


def linkedin_draft(findings_inputs: dict[str, Any]) -> str:
    post = linkedin_post(findings_inputs).strip()
    comment = linkedin_comment(findings_inputs).strip()
    return f"""# LinkedIn draft

Post only the text between the POST markers. The first comment is separate. Do not post the markers, and do not post or schedule this file.

<!-- POST:START -->
{post}
<!-- POST:END -->

<!-- COMMENT:START -->
{comment}
<!-- COMMENT:END -->
"""


def results_block(findings_inputs: dict[str, Any]) -> str:
    overall = findings_inputs["scorecard"]["overall"]
    rules = findings_inputs["observations"]["policy_rules"]
    rule_text = ", ".join(f"`{rule}`" for rule in rules) if rules else "none"
    return f"""Two results are recorded below. They are not one verdict.

### Mock self-judge only

Recorded with iFixAi `{findings_inputs["ifixai_version"]}` on the mock provider, `--eval-mode self`, no API key and no live model. This letter grade does not come from Policy Lab.

- Catalogue size, from the installed package: **{findings_inputs["catalogue_count"]}** inspections.
- Essential suite, from the installed package: **{len(findings_inputs["essential_ids"])}** ({", ".join(findings_inputs["essential_ids"])}).
- Scorecard results: **{len(findings_inputs["scorecard"]["test_results"])}**. Exit code `{findings_inputs["audit_exit_code"]}`.
- Grade **{overall.get("grade")}**, score **{overall.get("score_pct", _pct(overall.get("score")))}**, verdict **{overall.get("verdict")}**, self-judged **{findings_inputs["scorecard"]["metadata"].get("self_judged")}**.

This grade is the mock grading canned replies, including `ACK`. It is not a security result. Diagnostic hook notes reporting {rule_text} did not change it.

### Policy Lab only

These decisions do not change the letter grade and do not grade the agent. They are a search of the declared permission model and a projection of the authored fixture.

- Over-grant check: **{findings_inputs["unsafe_decision"]}** via {_arrow(findings_inputs["safety_action_ids"])}. That path has no partner approval.
- Unsafe partner-distribution witness: {_arrow(findings_inputs["unsafe_partner_action_ids"])}. The associate sends the pack, and approval is recorded afterwards. This is not the clean partner path.
- Repair: **{findings_inputs["repair_status"]}**, selected decision **{findings_inputs["repaired_decision"]}**. Repaired partner path: {_arrow(findings_inputs["repaired_partner_action_ids"])}. The partner approves, then the partner distributes.
- Authored-fixture projection: **{findings_inputs["fixture_projection_decision"]}**. `repair/report.md` repeats the pre-repair bundle. The repair outcome is `repair/repair.json` and `repair/selected-bundle.json`.
"""
