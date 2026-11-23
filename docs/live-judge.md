# Optional live judge

This experiment did not run the commands below. They spend money and send probes to whatever endpoint you name. Use a staging agent and keep the fixture synthetic. Do not point them at production, and do not load a real portfolio extract into the fixture.

iFixAi treats a grade as independently judged only when the judge is a different provider from the agent. One credential is refused unless you pass `--eval-mode self`, and that grade is flagged as not citable. `--dry-run` prints the inspection count and the judge-call estimate, then stops, and it does not bill.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install 'ifixai[anthropic]'
python scripts/run_experiment.py

export AGENT_API_KEY='...'
export ANTHROPIC_API_KEY='...'
ifixai run \
  --provider http \
  --endpoint "$STAGING_AGENT_URL" \
  --api-key "$AGENT_API_KEY" \
  --fixture fixture/quay_ledger.yaml \
  --eval-mode single \
  --judge-provider anthropic \
  --judge-api-key "$ANTHROPIC_API_KEY" \
  --grounding fixture \
  --name "Quay Ledger" \
  --version 0.1.0 \
  --no-promo \
  --dry-run
```

Read the estimate. Drop `--dry-run` only after that. Write the reports outside `results/mock-audit/`, and do not commit them if they can contain anything other than synthetic data.

`--mode full` needs this hand-built fixture and at least two distinct judge providers. That was not run.

```bash
ifixai run \
  --mode full \
  --provider http \
  --endpoint "$STAGING_AGENT_URL" \
  --api-key "$AGENT_API_KEY" \
  --fixture fixture/quay_ledger.yaml \
  --eval-mode full \
  --judge-provider anthropic \
  --judge-api-key "$ANTHROPIC_API_KEY" \
  --judge-provider openai \
  --judge-api-key "$OPENAI_API_KEY" \
  --no-promo \
  --dry-run
```

A live grade still does not prove row-level company scope. The fixture cannot express it. Policy Lab remains a check of the declared model.
