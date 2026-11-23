#!/usr/bin/env python3
"""Regenerate the walkthrough screenshots from a fresh offline run.

The pictures in docs/walkthrough/ are the output of this script. It does not
change results/. It needs a display, xfce4-terminal, ImageMagick's import,
and Google Chrome. websockets is used only to scroll the Policy Lab HTML.

    pip install websockets
    python3 scripts/capture_walkthrough.py
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from pe_audit.canonical import observe_scorecard  # noqa: E402
from pe_audit.constants import FIXTURE_PATH, MODEL_PATH, UNSAFE_POLICY_PATH  # noqa: E402
from pe_audit.runner import audit_invocation, load_scorecard  # noqa: E402

WORK = REPO / "build" / "walkthrough"
SHOTS = REPO / "docs" / "walkthrough"
DISPLAY = os.environ.get("DISPLAY", ":1")
ENV = {**os.environ, "DISPLAY": DISPLAY, "TERM": "xterm-256color"}


def ifixai(*args: str) -> str:
    return " ".join(shlex.quote(part) for part in ("python3", "-m", "ifixai.cli.main", *args))


def terminal(title: str, body: str, columns: int, rows: int, dest: Path) -> None:
    script_path = WORK / f"{title}.sh"
    ready = WORK / f"{title}.ready"
    ready.unlink(missing_ok=True)
    script_path.write_text(
        "#!/bin/bash\n"
        "cd /workspace\n"
        f"{body}\n"
        f"touch {shlex.quote(str(ready))}\n"
        "sleep 40\n",
        encoding="utf-8",
    )
    script_path.chmod(0o755)
    proc = subprocess.Popen(
        [
            "xfce4-terminal",
            "--disable-server",
            "--hide-menubar",
            "--hide-toolbar",
            "--hide-scrollbar",
            "--font=JetBrains Mono 15",
            f"--geometry={columns}x{rows}",
            "--color-text=#14202b",
            "--color-bg=#f7f8fa",
            "--title",
            title,
            "--command",
            str(script_path),
        ],
        env=ENV,
    )
    deadline = time.time() + 60
    while time.time() < deadline and not ready.exists():
        if proc.poll() is not None:
            raise RuntimeError(f"{title} terminal exited before it was ready")
        time.sleep(0.2)
    if not ready.exists():
        proc.terminate()
        raise RuntimeError(f"{title} did not finish")
    time.sleep(0.4)
    window = subprocess.check_output(["xdotool", "search", "--name", title], env=ENV, text=True).split()[0]
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["import", "-window", window, str(dest)], env=ENV, check=True, timeout=20)
    proc.terminate()
    subprocess.run(["xdotool", "windowkill", window], env=ENV, check=False, timeout=5)


def show_roles() -> None:
    fixture = yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))
    print("Read from fixture/quay_ledger.yaml")
    print(f"name: {fixture['metadata']['name']}")
    print("Granted tools:")
    for block in fixture["permissions"]:
        print(f"  {block['role']}")
        for tool in block["tools"]:
            print(f"    {tool}")
    associate = next(block["tools"] for block in fixture["permissions"] if block["role"] == "portfolio_associate")
    print("Not granted to portfolio_associate:")
    for tool in ("approve_ic_distribution", "distribute_ic_pack", "purge_working_paper"):
        print(f"  {tool}: {'present' if tool in associate else 'absent'}")


def show_ack() -> None:
    report = load_scorecard(WORK / "audit")
    observed = observe_scorecard(report)
    example = observed["example"]
    evidence = next(
        row
        for item in report["test_results"]
        if item["test_id"] == "B12"
        for row in item["evidence"]
        if row.get("test_case_id") == example["test_case_id"]
    )
    dimension = evidence["dimension_scores"][0]
    overall = report["overall"]
    print("Read from this run's scorecard JSON")
    print(f"self_judged: {report['metadata']['self_judged']}")
    print(f"grade: {overall['grade']}")
    print(f"score_pct: {overall['score_pct']}")
    print(f"verdict: {overall['verdict']}")
    print(f"scored replies that are ACK and passed: {observed['ack_passed']}")
    print(f"judge_provider: {observed['judge_provider']}")
    print(f"judge_calls: {observed['judge_calls']}")
    print(f"test_case_id: {evidence['test_case_id']}")
    print(f"expected: {evidence['expected']}")
    print(f"actual: {evidence['actual']}")
    print(f"passed: {evidence['passed']}")
    print(f"evaluation_result: {evidence['evaluation_result']}")
    print(f"dimension: {dimension['dimension_name']}")
    print(f"dimension_passed: {dimension['passed']}")
    print(f"reasoning: {dimension['reasoning']}")
    print(f"prompt_sent: {evidence['prompt_sent']}")


def show_retest() -> None:
    repair = json.loads((WORK / "repair" / "repair.json").read_text(encoding="utf-8"))
    selected = json.loads((WORK / "repair" / "selected-bundle.json").read_text(encoding="utf-8"))
    candidate = repair["candidates"][0]
    print("policy-lab repair stdout:")
    print((WORK / "repair.stdout").read_text(encoding="utf-8").rstrip())
    print("Read from repair.json and selected-bundle.json")
    print(f"repair.status: {repair['status']}")
    print(f"removed_rule_indices: {candidate['removed_rule_indices']}")
    print(f"candidate decision: {candidate['report']['decision']}")
    print(f"selected decision: {selected['report']['decision']}")
    print(f"property: {selected['report']['property_status']}")
    for goal in selected["report"]["goal_witnesses"]:
        print(f"{goal['objective_id']}:")
        for step in goal["steps"]:
            print(f"  {step['actor_id']}  {step['action_id']}  {step['tool']}")
    bridge = (WORK / "bridge.stdout").read_text(encoding="utf-8").strip()
    print(f"from-fixture stdout: {bridge}")


def run_checked(args: list[str], accept: set[int], stdout_path: Path | None = None) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, "-m", "ifixai.cli.main", *args],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode not in accept:
        raise RuntimeError(
            f"{args} exited {completed.returncode}\n{completed.stdout}\n{completed.stderr}"
        )
    if stdout_path is not None:
        stdout_path.write_text(completed.stdout, encoding="utf-8")
    return completed


class Page:
    def __init__(self) -> None:
        self._proc: subprocess.Popen[bytes] | None = None

    def start(self, html: Path) -> None:
        subprocess.run(["pkill", "-f", "user-data-dir=/tmp/chrome-walk-docs"], check=False)
        time.sleep(0.4)
        profile = Path("/tmp/chrome-walk-docs")
        if profile.exists():
            shutil.rmtree(profile)
        self._proc = subprocess.Popen(
            [
                "google-chrome",
                "--no-sandbox",
                "--disable-gpu",
                "--force-device-scale-factor=1",
                "--remote-debugging-port=9333",
                f"--user-data-dir={profile}",
                "--no-first-run",
                "--disable-extensions",
                f"--app=file://{html}",
                "--window-size=1000,880",
            ],
            env=ENV,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.time() + 20
        while time.time() < deadline:
            try:
                subprocess.check_output(["curl", "-sf", "http://127.0.0.1:9333/json"], timeout=2)
                return
            except subprocess.CalledProcessError:
                time.sleep(0.3)
        raise RuntimeError("Chrome debugging port did not open")

    def shot(self, html: Path, script: str, dest: Path) -> None:
        import asyncio

        import websockets

        async def run() -> None:
            tabs = json.loads(subprocess.check_output(["curl", "-sf", "http://127.0.0.1:9333/json"], timeout=5))
            page = next(item for item in tabs if item.get("type") == "page")
            async with websockets.connect(page["webSocketDebuggerUrl"], max_size=8_000_000) as ws:
                seq = 0

                async def call(method: str, params: dict | None = None) -> dict:
                    nonlocal seq
                    seq += 1
                    await ws.send(json.dumps({"id": seq, "method": method, "params": params or {}}))
                    while True:
                        raw = json.loads(await ws.recv())
                        if raw.get("id") == seq:
                            if "error" in raw:
                                raise RuntimeError(raw["error"])
                            return raw.get("result") or {}

                await call("Page.enable")
                await call("Page.navigate", {"url": f"file://{html}"})
                await call("Runtime.enable")
                deadline = time.time() + 10
                while time.time() < deadline:
                    state = await call(
                        "Runtime.evaluate",
                        {"expression": "document.readyState", "returnByValue": True},
                    )
                    if state.get("result", {}).get("value") == "complete":
                        break
                    time.sleep(0.1)
                await call(
                    "Runtime.evaluate",
                    {"expression": script, "returnByValue": True},
                )

        asyncio.run(run())
        time.sleep(0.5)
        window = subprocess.check_output(
            ["xdotool", "search", "--name", "Business Policy Lab"],
            env=ENV,
            text=True,
        ).split()[0]
        subprocess.run(["import", "-window", window, str(dest)], env=ENV, check=True, timeout=20)

    def stop(self) -> None:
        if self._proc is not None:
            self._proc.terminate()


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--show":
        {"roles": show_roles, "ack": show_ack, "retest": show_retest}[sys.argv[2]]()
        return
    WORK.mkdir(parents=True, exist_ok=True)
    SHOTS.mkdir(parents=True, exist_ok=True)
    audit_dir = WORK / "audit"
    runs_dir = WORK / "runs"
    if audit_dir.exists():
        shutil.rmtree(audit_dir)
    if runs_dir.exists():
        shutil.rmtree(runs_dir)

    terminal(
        "walk-01-roles",
        "python3 scripts/capture_walkthrough.py --show roles",
        88,
        24,
        SHOTS / "01-roles.png",
    )
    dry = audit_invocation(Path("build/walkthrough/dry"), Path("build/walkthrough/dry-runs"), dry_run=True)
    terminal(
        "walk-02-dry-run",
        ifixai(*dry) + " 2>/dev/null",
        92,
        16,
        SHOTS / "02-dry-run.png",
    )
    audit = audit_invocation(Path("build/walkthrough/audit"), Path("build/walkthrough/runs"), dry_run=False)
    terminal(
        "walk-03-grade",
        ifixai(*audit) + f" > {shlex.quote(str(WORK / 'audit.stdout'))} 2>/dev/null\n"
        f"tail -n 21 {shlex.quote(str(WORK / 'audit.stdout'))}",
        100,
        26,
        SHOTS / "03-grade.png",
    )
    terminal(
        "walk-04-ack",
        "python3 scripts/capture_walkthrough.py --show ack",
        100,
        20,
        SHOTS / "04-ack.png",
    )

    for name in ("unsafe", "repair", "bridge"):
        target = WORK / name
        if target.exists():
            shutil.rmtree(target)
    run_checked(
        ["policy-lab", "check", str(MODEL_PATH.relative_to(REPO)), str(UNSAFE_POLICY_PATH.relative_to(REPO)), "--output", str(WORK / "unsafe")],
        {1},
        WORK / "check.stdout",
    )
    run_checked(
        ["policy-lab", "repair", str(WORK / "unsafe" / "bundle.json"), "--max-removals", "1", "--output", str(WORK / "repair")],
        {0},
        WORK / "repair.stdout",
    )
    run_checked(
        ["policy-lab", "from-fixture", "policy/fixture-bridge-model.json", "fixture/quay_ledger.yaml", "--output", str(WORK / "bridge")],
        {0},
        WORK / "bridge.stdout",
    )
    page = Page()
    page.start(WORK / "unsafe" / "report.html")
    try:
        page.shot(
            WORK / "unsafe" / "report.html",
            """(() => {
              const el = document.querySelector('#witness-0');
              const details = el.querySelector('details');
              if (details) details.open = true;
              el.scrollIntoView({block: 'start'});
              return true;
            })()""",
            SHOTS / "05-unapproved-path.png",
        )
        page.shot(
            WORK / "repair" / "report.html",
            """(() => {
              const heading = [...document.querySelectorAll('h2')].find((node) => node.textContent.includes('Goal-preserving'));
              heading.scrollIntoView({block: 'start'});
              return heading.textContent;
            })()""",
            SHOTS / "06-repair.png",
        )
        page.shot(
            WORK / "unsafe" / "report.html",
            """(() => {
              const heading = [...document.querySelectorAll('h2')].find((node) => node.textContent.includes('Portable'));
              heading.scrollIntoView({block: 'start'});
              return heading.textContent;
            })()""",
            SHOTS / "08-boundaries.png",
        )
    finally:
        page.stop()
    terminal(
        "walk-07-retest",
        "python3 scripts/capture_walkthrough.py --show retest",
        100,
        22,
        SHOTS / "07-retest.png",
    )
    print("wrote", SHOTS)


if __name__ == "__main__":
    main()
