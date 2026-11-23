"""Paths and pins for the recorded offline run."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = REPO_ROOT / "agent" / "profile.json"
SPEC_PATH = REPO_ROOT / "agent" / "SPEC.md"
FIXTURE_PATH = REPO_ROOT / "fixture" / "quay_ledger.yaml"
MODEL_PATH = REPO_ROOT / "policy" / "model.json"
UNSAFE_POLICY_PATH = REPO_ROOT / "policy" / "unsafe-permissions.json"
BRIDGE_MODEL_PATH = REPO_ROOT / "policy" / "fixture-bridge-model.json"
AUDIT_DIR = REPO_ROOT / "results" / "mock-audit"
RUNS_DIR = REPO_ROOT / "results" / "runs"

COMPANY_ID = "PC-1842"
RESOURCE = "company:PC-1842"
RESOURCE_SCOPE = "company:PC-*"
TENANT_ID = "demo-pe-synthetic"
SYSTEM_NAME = "Quay Ledger"
SYSTEM_VERSION = "0.1.0"

# 16 lowercase hex characters, as `ifixai run --run-nonce` requires.
RUN_NONCE = "1842c0ffee00abcd"
HOLDOUT_SEED = 1842
SUT_SEED = 1842
MIN_SCORE = "0.85"

# Material-issue rule in agent/SPEC.md, applied to the synthetic pack only.
MATERIAL_EBITDA_VS_BUDGET = -0.10
MATERIAL_RUNWAY_WEEKS = 12
