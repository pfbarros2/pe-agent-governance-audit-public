#!/usr/bin/env python3
"""Reproduce the offline Quay Ledger experiment and refresh checked-in results.

No API key is read and no live model is called. Policy Lab directories are
created in a temporary folder because iFixAi refuses to overwrite evidence.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from ifixai._version import VERSION
from ifixai.harness.registry import ALL_SPECS
from ifixai.harness.suites import ESSENTIAL_TEST_IDS
from ifixai.policy_lab.executor import execute_witness
from ifixai.policy_lab.integrity import load_exploration_bundle

from pe_audit.canonical import canonical_scorecard, observe_scorecard
from pe_audit.constants import (
    AUDIT_DIR,
    BRIDGE_MODEL_PATH,
    MODEL_PATH,
    REPO_ROOT as ROOT,
    RUNS_DIR,
    UNSAFE_POLICY_PATH,
)
from pe_audit.narrative import findings_markdown, results_block
from pe_audit.policy_model import PortfolioDesk
from pe_audit.runner import (
    audit_invocation,
    author_fixture,
    execute_audit,
    load_fixture,
    load_scorecard,
    publish_dir,
    run_ifixai,
    scorecard_path,
    validate_fixture,
    write_policy_files,
)

KEEP = ("bundle.json", "report.json", "report.md", "metadata.json", "repair.json", "selected-bundle.json")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.replace(str(ROOT) + "/", ""), encoding="utf-8")


def _replace_results_block(readme: Path, block: str) -> None:
    text = readme.read_text(encoding="utf-8")
    start = "<!-- RESULTS:START -->"
    end = "<!-- RESULTS:END -->"
    if start not in text or end not in text:
        raise RuntimeError("README.md is missing RESULTS markers")
    before, rest = text.split(start, 1)
    _, after = rest.split(end, 1)
    readme.write_text(f"{before}{start}\n{block.strip()}\n{end}{after}", encoding="utf-8")


def _policy_lab(workspace: Path) -> dict:
    unsafe_dir = workspace / "unsafe"
    repair_dir = workspace / "repair"
    bridge_dir = workspace / "bridge"
    replay_dir = workspace / "replay"
    check = run_ifixai(
        [
            "policy-lab",
            "check",
            str(MODEL_PATH.relative_to(ROOT)),
            str(UNSAFE_POLICY_PATH.relative_to(ROOT)),
            "--output",
            str(unsafe_dir),
        ],
        accept={1},
    )
    repair = run_ifixai(
        [
            "policy-lab",
            "repair",
            str(unsafe_dir / "bundle.json"),
            "--max-removals",
            "1",
            "--output",
            str(repair_dir),
        ],
        accept={0},
    )
    bridge = run_ifixai(
        [
            "policy-lab",
            "from-fixture",
            str(BRIDGE_MODEL_PATH.relative_to(ROOT)),
            str(ROOT / "fixture" / "quay_ledger.yaml"),
            "--output",
            str(bridge_dir),
        ],
        accept={0},
    )
    replay = run_ifixai(
        ["policy-lab", "replay", str(unsafe_dir / "bundle.json"), "--output", str(replay_dir)],
        accept={1},
    )
    return {"check": check, "repair": repair, "bridge": bridge, "replay": replay, "workspace": workspace}


def _replay_local(unsafe_bundle_path: Path, selected_bundle_path: Path) -> dict:
    unsafe = load_exploration_bundle(unsafe_bundle_path)
    selected = load_exploration_bundle(selected_bundle_path)
    desk = PortfolioDesk()
    harm = unsafe.report.safety_witnesses[0]
    harm_run = execute_witness(unsafe, harm, desk.bindings(), desk.reset, desk.observe)
    leaked = [dict(item) for item in desk.distributions]
    escalation_witness = next(
        item for item in selected.report.goal_witnesses if item.objective_id == "legitimate_escalation"
    )
    distribution_witness = next(
        item for item in selected.report.goal_witnesses if item.objective_id == "partner_distribution"
    )
    escalation_run = execute_witness(
        selected, escalation_witness, desk.bindings(), desk.reset, desk.observe
    )
    escalations = list(desk.escalations)
    distribution_run = execute_witness(
        selected, distribution_witness, desk.bindings(), desk.reset, desk.observe
    )
    approved = [dict(item) for item in desk.distributions]
    return {
        "synthetic": True,
        "no_live_warehouse": True,
        "unsafe_replay": harm_run.decision,
        "unsafe_steps": [step.action_id for step in harm.steps],
        "leaked_distributions": leaked,
        "escalation_replay": escalation_run.decision,
        "escalations": escalations,
        "distribution_replay": distribution_run.decision,
        "approved_distributions": approved,
    }


def main() -> None:
    author_fixture()
    validate_fixture()
    fixture = load_fixture()
    write_policy_files(fixture)

    catalogue = ROOT / "results" / "catalogue"
    suites = run_ifixai(["list", "suites"], accept={0})
    tests = run_ifixai(["list", "tests"], accept={0})
    _write(catalogue / "list-suites.txt", suites.stdout)
    _write(catalogue / "list-tests.txt", tests.stdout)

    dry = run_ifixai(audit_invocation(AUDIT_DIR, RUNS_DIR, dry_run=True), accept={0})
    audit = execute_audit(AUDIT_DIR, RUNS_DIR)
    report_file = scorecard_path(AUDIT_DIR)
    scorecard = load_scorecard(AUDIT_DIR)
    stable_json = AUDIT_DIR / "scorecard.json"
    stable_md = AUDIT_DIR / "scorecard.md"
    stable_summary = AUDIT_DIR / "summary.md"
    shutil.copyfile(report_file, stable_json)
    md_candidates = list(AUDIT_DIR.glob("ifixai-*.md"))
    summary_candidates = [path for path in md_candidates if path.name.endswith("-summary.md")]
    full_candidates = [path for path in md_candidates if path not in summary_candidates]
    if len(full_candidates) != 1 or len(summary_candidates) != 1:
        raise RuntimeError(f"unexpected markdown reports: {md_candidates}")
    shutil.copyfile(full_candidates[0], stable_md)
    shutil.copyfile(summary_candidates[0], stable_summary)
    _write(AUDIT_DIR / "stdout.txt", audit.stdout)
    _write(AUDIT_DIR / "dry-run.txt", dry.stdout)
    _write(AUDIT_DIR / "exit-code.txt", f"{audit.returncode}\n")
    _write(
        AUDIT_DIR / "canonical.json",
        json.dumps(canonical_scorecard(scorecard), indent=2) + "\n",
    )
    for generated in list(AUDIT_DIR.glob("ifixai-*")):
        generated.unlink()

    with tempfile.TemporaryDirectory(prefix="quay-policy-") as raw:
        workspace = Path(raw)
        _policy_lab(workspace)
        evidence = ROOT / "results" / "policy-lab"
        publish_dir(workspace / "unsafe", evidence / "unsafe-check", KEEP)
        publish_dir(workspace / "repair", evidence / "repair", KEEP)
        publish_dir(workspace / "bridge", evidence / "fixture-projection", KEEP)
        publish_dir(workspace / "replay", evidence / "replay", KEEP)
        observed = _replay_local(
            workspace / "unsafe" / "bundle.json",
            workspace / "repair" / "selected-bundle.json",
        )
        _write(evidence / "observed-desk.json", json.dumps(observed, indent=2) + "\n")

    unsafe_report = json.loads((ROOT / "results" / "policy-lab" / "unsafe-check" / "report.json").read_text())
    repair_report = json.loads((ROOT / "results" / "policy-lab" / "repair" / "repair.json").read_text())
    selected = json.loads((ROOT / "results" / "policy-lab" / "repair" / "selected-bundle.json").read_text())
    bridge_report = json.loads(
        (ROOT / "results" / "policy-lab" / "fixture-projection" / "report.json").read_text()
    )
    removed_index = repair_report["candidates"][-1]["removed_rule_indices"][0]
    removed_rule = json.loads(UNSAFE_POLICY_PATH.read_text())["permissions"][removed_index]

    def goal_steps(report: dict, goal_id: str) -> list[str]:
        for item in report["goal_witnesses"]:
            if item["objective_id"] == goal_id:
                return [step["action_id"] for step in item["steps"]]
        raise KeyError(goal_id)

    inputs = {
        "observations": observe_scorecard(scorecard),
        "ifixai_version": VERSION,
        "catalogue_count": len(ALL_SPECS),
        "essential_ids": list(ESSENTIAL_TEST_IDS),
        "audit_exit_code": audit.returncode,
        "scorecard": scorecard,
        "unsafe_decision": unsafe_report["decision"],
        "safety_action_ids": [step["action_id"] for step in unsafe_report["safety_witnesses"][0]["steps"]],
        "repair_status": repair_report["status"],
        "removed_rule": removed_rule,
        "repaired_decision": selected["report"]["decision"],
        "goal_status": unsafe_report["goal_status"],
        "fixture_projection_decision": bridge_report["decision"],
        "unsafe_replay": observed["unsafe_replay"],
        "escalation_replay": observed["escalation_replay"],
        "distribution_replay": observed["distribution_replay"],
        "unsafe_partner_action_ids": goal_steps(unsafe_report, "partner_distribution"),
        "repaired_partner_action_ids": goal_steps(selected["report"], "partner_distribution"),
    }
    _write(ROOT / "reports" / "findings.md", findings_markdown(**inputs))
    _replace_results_block(ROOT / "README.md", results_block(inputs))
    print(
        f"audit exit {audit.returncode} grade {scorecard['overall'].get('grade')} "
        f"policy {unsafe_report['decision']} repair {repair_report['status']} "
        f"projection {bridge_report['decision']}"
    )


if __name__ == "__main__":
    main()
