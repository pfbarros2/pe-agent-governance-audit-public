# Business Policy Lab

Decision: **COUNTEREXAMPLE**

Model: Quay Ledger IC distribution. Policy: Over-granted associate distribution.

States: 8. Examinations: 48. Complete frontier: True.

## Safety and completion

- Property no\_unapproved\_distribution: COUNTEREXAMPLE
- Goal legitimate\_escalation: REACHABLE
- Goal partner\_distribution: REACHABLE

## safety: no\_unapproved\_distribution

1. associate → 01\_read (read\_operating\_metrics).
2. associate → 02\_draft (draft\_ic\_memo\_excerpt).
3. associate → 04\_associate\_distribute (distribute\_ic\_pack).

## goal: legitimate\_escalation

1. associate → 01\_read (read\_operating\_metrics).
2. associate → 02\_draft (draft\_ic\_memo\_excerpt).
3. associate → 03\_escalate (escalate\_material\_issue).

## goal: partner\_distribution

1. associate → 01\_read (read\_operating\_metrics).
2. associate → 02\_draft (draft\_ic\_memo\_excerpt).
3. associate → 03\_escalate (escalate\_material\_issue).
4. associate → 04\_associate\_distribute (distribute\_ic\_pack).
5. partner → 05\_partner\_approve (approve\_ic\_distribution).

## Boundaries

- Reachability and verification apply only to the explicit finite model and policy.
- Unmodelled history, actors, effects and business constraints are not evaluated.
- Declared cost units are model counters, not observed billing or runtime resource use.
- Model witnesses are not observed production behavior or runtime enforcement.
- Goals establish existential reachability, not universal liveness.

Bundle SHA-256: `d6761758498043b075c9ebe1e5319ebdf927680f6ba5e9492a5ae97701cdf5f4`
