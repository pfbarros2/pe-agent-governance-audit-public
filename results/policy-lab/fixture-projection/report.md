# Business Policy Lab

Decision: **VERIFIED**

Model: Quay Ledger IC distribution. Policy: fixture permission projection.

States: 6. Examinations: 36. Complete frontier: True.

## Safety and completion

- Property no\_unapproved\_distribution: VERIFIED
- Goal legitimate\_escalation: REACHABLE
- Goal partner\_distribution: REACHABLE

## goal: legitimate\_escalation

1. u005 → 01\_read (read\_operating\_metrics).
2. u005 → 02\_draft (draft\_ic\_memo\_excerpt).
3. u005 → 03\_escalate (escalate\_material\_issue).

## goal: partner\_distribution

1. u005 → 01\_read (read\_operating\_metrics).
2. u005 → 02\_draft (draft\_ic\_memo\_excerpt).
3. u005 → 03\_escalate (escalate\_material\_issue).
4. u001 → 05\_partner\_approve (approve\_ic\_distribution).
5. u001 → 06\_partner\_distribute (distribute\_ic\_pack).

## Boundaries

- Reachability and verification apply only to the explicit finite model and policy.
- Unmodelled history, actors, effects and business constraints are not evaluated.
- Declared cost units are model counters, not observed billing or runtime resource use.
- Model witnesses are not observed production behavior or runtime enforcement.
- Goals establish existential reachability, not universal liveness.

Bundle SHA-256: `7a2109b0a9a83f6b79ac33838a060c9f231504ec3dc1d8e9ec520e6f7e17b2ff`
