"""Stable projection of an iFixAi JSON scorecard, plus a few counts the prose cites.

Run ids, dates and durations change on every invocation. Inspection status,
score and evidence verdicts are what a fresh run is compared against.
"""

from __future__ import annotations

from typing import Any


def canonical_scorecard(report: dict[str, Any]) -> dict[str, Any]:
    metadata = report["metadata"]
    overall = report["overall"]
    kept_meta = (
        "system_name",
        "system_version",
        "provider",
        "fixture_name",
        "specification_version",
        "run_mode",
        "self_judged",
        "judge_relation",
    )
    kept_overall = (
        "score",
        "grade",
        "verdict",
        "passed",
        "min_score",
        "mandatory_minimums_passed",
        "mandatory_minimums_inconclusive",
        "score_before_cap",
        "cap_applied",
    )
    tests = []
    for item in report["test_results"]:
            evidence = [
                {
                    "test_case_id": item_evidence["test_case_id"],
                    "passed": item_evidence["passed"],
                    "evaluation_method": item_evidence["evaluation_method"],
                }
                for item_evidence in item.get("evidence", [])
            ]
            # B20 resamples its prompt corpus and iFixAi 4.3.0 has no --b20-seed.
            # The inspection score is stable; the case ids are not.
            if item["test_id"] == "B20":
                evidence_view: dict[str, Any] | list[dict[str, Any]] = {
                    "sampled": True,
                    "count": len(evidence),
                    "passed": sum(1 for row in evidence if row["passed"]),
                    "failed": sum(1 for row in evidence if not row["passed"]),
                    "methods": sorted({row["evaluation_method"] for row in evidence}),
                }
            else:
                evidence.sort(key=lambda row: (row["test_case_id"], row["evaluation_method"], str(row["passed"])))
                evidence_view = evidence
            tests.append(
                {
                    "test_id": item["test_id"],
                    "status": item["status"],
                    "score": item.get("score"),
                    "passing": item.get("passing"),
                    "evidence": evidence_view,
                }
            )
    not_applicable = [
        {"test_id": item.get("test_id"), "reason": item.get("reason")}
        for item in report.get("not_applicable") or []
    ]
    tests.sort(key=lambda row: row["test_id"])
    not_applicable.sort(key=lambda row: (row["test_id"] or "", row["reason"] or ""))
    return {
        "metadata": {key: metadata[key] for key in kept_meta if key in metadata},
        "overall": {key: overall[key] for key in kept_overall if key in overall},
        "mandatory_minimums": report.get("mandatory_minimums"),
        "not_applicable": not_applicable,
        "not_run_test_ids": sorted(report.get("not_run_test_ids") or []),
        "tests": tests,
    }


def observe_scorecard(report: dict[str, Any]) -> dict[str, Any]:
    """Counts a reader needs before treating the letter grade as a control test."""
    ack_passed = 0
    hook_notes_failed = 0
    rules: set[str] = set()
    example: dict[str, str] | None = None
    for item in report.get("test_results") or []:
        for evidence in item.get("evidence") or []:
            actual = str(evidence.get("actual") or "").strip()
            details = evidence.get("details") or {}
            if actual == "ACK" and evidence.get("passed") and not evidence.get("is_diagnostic"):
                ack_passed += 1
                if item.get("test_id") == "B12":
                    dimensions = evidence.get("dimension_scores") or []
                    reasoning = ""
                    if dimensions and isinstance(dimensions[0], dict):
                        reasoning = str(dimensions[0].get("reasoning") or "")
                    candidate = {
                        "test_id": str(item.get("test_id")),
                        "test_case_id": str(evidence.get("test_case_id")),
                        "prompt_sent": str(evidence.get("prompt_sent") or ""),
                        "actual": actual,
                        "reasoning": reasoning,
                    }
                    if example is None or candidate["test_case_id"] < example["test_case_id"]:
                        example = candidate
            if details.get("hook_note") and evidence.get("passed") is False:
                hook_notes_failed += 1
                rule = details.get("policy_rule")
                if isinstance(rule, str):
                    rules.add(rule)
    judge = (report.get("metadata") or {}).get("judge_stats") or {}
    return {
        "ack_passed": ack_passed,
        "hook_notes_failed": hook_notes_failed,
        "policy_rules": sorted(rules),
        "example": example,
        "judge_calls": judge.get("total_calls"),
        "judge_provider": judge.get("judge_provider"),
    }
