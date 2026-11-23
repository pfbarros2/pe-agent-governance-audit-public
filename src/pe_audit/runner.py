"""Deterministic wrappers around the iFixAi CLI.

The wrappers do not add a judge, a key, or a network client. Exit codes from
`ifixai run` and `policy-lab` are returned to the caller. A score below
`--min-score` is exit 2 and is still a completed scorecard.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

from pe_audit.constants import (
    BRIDGE_MODEL_PATH,
    FIXTURE_PATH,
    HOLDOUT_SEED,
    MIN_SCORE,
    MODEL_PATH,
    PROFILE_PATH,
    REPO_ROOT,
    RUN_NONCE,
    SUT_SEED,
    SYSTEM_NAME,
    SYSTEM_VERSION,
    UNSAFE_POLICY_PATH,
)
from pe_audit.policy_model import bridge_model, business_model, unsafe_policy

AUDIT_ARGS = [
    "--provider",
    "mock",
    "--eval-mode",
    "self",
    "--fixture",
    str(FIXTURE_PATH.relative_to(REPO_ROOT)),
    "--no-promo",
    "--no-telemetry",
    "--no-parallel",
    "--holdout-seed",
    str(HOLDOUT_SEED),
    "--b12-seed",
    str(HOLDOUT_SEED),
    "--sut-seed",
    str(SUT_SEED),
    "--run-nonce",
    RUN_NONCE,
    "--name",
    SYSTEM_NAME,
    "--version",
    SYSTEM_VERSION,
    "--min-score",
    MIN_SCORE,
    "--grounding",
    "fixture",
]


def command_env() -> dict[str, str]:
    env = os.environ.copy()
    env["IFIXAI_TELEMETRY"] = "0"
    env["IFIXAI_NO_PROMO"] = "1"
    env["NO_COLOR"] = "1"
    env["COLUMNS"] = "120"
    env.pop("OPENAI_API_KEY", None)
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("GEMINI_API_KEY", None)
    env.pop("GOOGLE_API_KEY", None)
    env.pop("AZURE_OPENAI_API_KEY", None)
    return env


def ifixai_args(*args: str) -> list[str]:
    return [sys.executable, "-m", "ifixai.cli.main", *args]


def run_ifixai(args: list[str], *, accept: set[int]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ifixai_args(*args),
        cwd=REPO_ROOT,
        env=command_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode not in accept:
        raise RuntimeError(
            "ifixai "
            + " ".join(args)
            + f" exited {completed.returncode}\n{completed.stdout}\n{completed.stderr}"
        )
    return completed


def author_fixture(destination: Path = FIXTURE_PATH) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    completed = run_ifixai(
        ["author", str(PROFILE_PATH.relative_to(REPO_ROOT)), "-o", str(destination), "--force"],
        accept={0},
    )
    return completed.stdout


def validate_fixture(path: Path = FIXTURE_PATH) -> str:
    completed = run_ifixai(["validate", str(path)], accept={0})
    return completed.stdout + completed.stderr


def load_fixture(path: Path = FIXTURE_PATH) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} did not contain a fixture mapping")
    return loaded


def first_user_id(fixture: dict[str, Any], role: str) -> str:
    for user in fixture["users"]:
        if role in user["roles"]:
            return str(user["user_id"])
    raise ValueError(f"no user with role {role}")


def write_policy_files(fixture: dict[str, Any] | None = None) -> None:
    """Export the explicit model and the over-grant. The profile is not modified."""
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    model = business_model()
    policy = unsafe_policy()
    MODEL_PATH.write_text(json.dumps(model.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
    UNSAFE_POLICY_PATH.write_text(
        json.dumps(policy.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8"
    )
    if fixture is None:
        if not FIXTURE_PATH.exists():
            return
        fixture = load_fixture()
    bridged = bridge_model(
        first_user_id(fixture, "deal_partner"),
        first_user_id(fixture, "portfolio_associate"),
    )
    BRIDGE_MODEL_PATH.write_text(
        json.dumps(bridged.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8"
    )


def audit_invocation(output: Path, reliability: Path, *, dry_run: bool) -> list[str]:
    args = ["run", *AUDIT_ARGS, "--output", str(output), "--reliability-out", str(reliability)]
    if dry_run:
        args.append("--dry-run")
    return args


def execute_audit(output: Path, reliability: Path) -> subprocess.CompletedProcess[str]:
    if output.exists():
        shutil.rmtree(output)
    if reliability.exists():
        shutil.rmtree(reliability)
    output.mkdir(parents=True)
    return run_ifixai(audit_invocation(output, reliability, dry_run=False), accept={0, 1, 2})


def scorecard_path(output: Path) -> Path:
    matches = [
        path
        for path in output.glob("*.json")
        if path.name != "canonical.json" and "summary" not in path.name
    ]
    documents = []
    for path in matches:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and "test_results" in payload and "overall" in payload:
            documents.append(path)
    if len(documents) != 1:
        raise RuntimeError(f"expected one scorecard JSON in {output}, found {documents}")
    return documents[0]


def load_scorecard(output: Path) -> dict[str, Any]:
    return json.loads(scorecard_path(output).read_text(encoding="utf-8"))


def publish_dir(source: Path, destination: Path, names: tuple[str, ...]) -> None:
    """Copy selected evidence out of a mode-0700 Policy Lab directory."""
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    for name in names:
        target = source / name
        if target.exists():
            shutil.copyfile(target, destination / name)
