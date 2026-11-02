# TournamentLab — Esports League Manager

A robust, production-grade Python CLI application for managing esports leagues with strict fairness guarantees, deterministic round-robin scheduling, mathematical invariant checks, and corruption-proof JSON persistence.

Built with pure Python standard library modules (`sys`, `json`, `pathlib`, `random`, `unittest`, `tempfile`).

---

## 1. Key Features & Business Rules

1. **Strict Team Registration (4–8 Teams)**:
   - Trimmed display names between 2 and 30 characters.
   - Case-insensitive uniqueness enforcement (`casefold()`).
   - Stable sequential identifiers (`TM001`, `TM002`, ...).

2. **Deterministic Round-Robin Scheduling**:
   - Single round-robin: every unordered team pair meets exactly once.
   - Formula: $\frac{N(N-1)}{2}$ matches (e.g. 4 teams = 6 fixtures; 6 teams = 15 fixtures; 8 teams = 28 fixtures).
   - Zero self-matches, zero duplicate reversed fixtures.
   - Fixture IDs formatted as `M001`, `M002`, ...

3. **Atomic Result Recording**:
   - Strictly validates nonnegative integers for home and away scores.
   - Explicitly rejects Python booleans (`isinstance(True, int)` trap), floats, strings, and negative values.
   - Validate-before-mutate: partial score failures do not alter fixture status.
   - Duplicate score entry on completed fixtures is strictly prohibited.

4. **Pure Derived Standings (Single Source of Truth)**:
   - Standings are never maintained as a mutable, drift-prone table. They are aggregated on-demand purely from played match records.
   - Standard 3/1/0 points system: Win = 3 points, Draw = 1 point, Loss = 0 points.
   - Mathematical invariants automatically verified:
     - Total league points = $3 \times \text{non-draws} + 2 \times \text{draws}$
     - Total goals for (GF) = Total goals against (GA)
     - Total team games played = $2 \times \text{played fixtures}$

5. **Strict 4-Tier Tie-Break Ranking Hierarchy**:
   1. **Points** (descending)
   2. **Goal Difference** (descending)
   3. **Goals For** (descending)
   4. **Normalized Team Name** (casefolded, ascending alphabetical)

6. **Validate-Before-Replace JSON Persistence (`schema_version: 1`)**:
   - Full referential integrity: rejects fixtures referencing unknown team IDs.
   - Rejects schema discrepancies, duplicate IDs, duplicate names, or score anomalies before touching active memory.

7. **Reproducible Demo Simulation**:
   - Explicit user choice only (never runs silently).
   - Seeded pseudo-random generator (`random.Random(seed)`) ensures deterministic testing.

8. **Season Status & Champion Report**:
   - Displays "IN PROGRESS" with pending fixture count while matches remain.
   - Once all fixtures are played, crowns the #1 ranked team as Champion.

---

## 2. Project Directory Structure

```text
tournamentlab/
├── main.py                     # Application CLI entry point
├── tournament/                 # Core engine package
│   ├── __init__.py             # Package declaration & version
│   ├── teams.py                # Team registration & validation (Engineer A)
│   ├── fixtures.py             # Round-robin generator & scoring (Engineer A & B)
│   ├── standings.py            # Pure standings aggregation & invariants (Engineer B)
│   ├── simulation.py           # Seeded reproducible demo simulation (Engineer B)
│   ├── storage.py              # Schema-versioned JSON persistence (Engineer A)
│   └── cli.py                  # Resilient interactive terminal interface (Engineer B)
├── tests/                      # Automated test suite (60 unit & integration tests)
│   ├── __init__.py
│   ├── test_teams.py           # Team registration & boundary tests
│   ├── test_fixtures_generation.py # Combinatorics & scheduling tests
│   ├── test_scoring.py         # Type safety & atomic result mutation tests
│   ├── test_standings.py       # Standings, tie-breaks & invariants tests
│   ├── test_simulation.py      # Seeded simulation reproducibility tests
│   ├── test_storage.py         # JSON schema & referential integrity tests
│   └── test_integration.py    # All 16 curriculum scenarios & demo dataset
├── docs/                       # Engineering documentation
│   ├── design-decisions.md     # Architecture, invariants & PR review records
│   └── ai-learning-log.md      # 6 structured AI learning cycles & reflections
├── README.md                   # Complete documentation & usage guide
└── .gitignore                  # Clean git exclusion rules
```

---

## 3. Quick Start & CLI Usage

### Launching the Application
```bash
python3 main.py
```

### CLI Menu Interface
```text
================================================================
      TOURNAMENTLAB | THE ULTIMATE ESPORTS LEAGUE MANAGER
================================================================

--- MAIN MENU ---
 1. Register a Team (4-8 required)
 2. List Registered Teams
 3. Generate Round-Robin Schedule
 4. List Fixtures & Scores
 5. Record Match Result
 6. View League Standings & Champion
 7. Simulate Remaining Fixtures (Seeded Demo)
 8. Save Tournament State (JSON)
 9. Load Tournament State (JSON)
10. Reset Tournament (Start Fresh)
 0. Exit
```

---

## 4. Running the Automated Test Suite

Run all 60 tests via Python's standard `unittest` test discovery:

```bash
python3 -m unittest discover -s tests -v
```

Expected output:
```text
Ran 60 tests in 0.031s

OK
```

All 16 curriculum scenarios required by the specification are verified:
1. Reject duplicate casefolded team name (`test_scenario_01_reject_duplicate_casefolded_name`)
2. Reject blank / too-long name (`test_scenario_02_reject_blank_or_too_long_name`)
3. Reject fixture generation with fewer than 4 teams (`test_scenario_03_reject_generation_under_four_teams`)
4. Four teams produce six fixtures (`test_scenario_04_four_teams_produce_six_fixtures`)
5. Six teams produce fifteen fixtures (`test_scenario_05_six_teams_produce_fifteen_fixtures`)
6. No self-match (`test_scenario_06_no_self_match`)
7. No duplicate unordered pair (`test_scenario_07_no_duplicate_unordered_pair`)
8. Reject negative / float / bool goals (`test_scenario_08_reject_negative_float_bool_goals`)
9. Reject unknown fixture (`test_scenario_09_reject_unknown_fixture`)
10. Reject duplicate result (`test_scenario_10_reject_duplicate_result`)
11. Correct 3/1/0 points (`test_scenario_11_correct_points_calculation`)
12. Tie-break sorting (`test_scenario_12_tie_break_sorting`)
13. Standings re-computed from matches (`test_scenario_13_standings_recomputed_purely_from_matches`)
14. JSON bad references rejected without state change (`test_scenario_14_bad_references_rejected_without_state_change`)
15. Reload preserves IDs and standings (`test_scenario_15_reload_preserves_ids_and_standings`)
16. Champion shown only when all matches played (`test_scenario_16_champion_shown_only_when_all_matches_played`)

---

## 5. Controlled Demonstration Dataset Walkthrough

The project includes an end-to-end verified walkthrough matching the curriculum requirements:

1. **Teams Registered**:
   - `TM001`: Thunder
   - `TM002`: Comets
   - `TM003`: Phoenix
   - `TM004`: Rockets

2. **Fixtures Generated**: 6 matches total ($4 \times 3 / 2 = 6$).

3. **Two Fixtures Played Initially**:
   - `M001`: Thunder 2 – 1 Comets (Win for Thunder, 3 pts; Loss for Comets, 0 pts)
   - `M006`: Phoenix 0 – 0 Rockets (Draw for both, 1 pt each)

4. **Standings Table (In Progress)**:
```text
============================================================================
                            LEAGUE STANDINGS
============================================================================
+-----+--------+----------------------+----+----+----+----+----+----+----+-----+
| Pos | ID     | Team Name            | P  | W  | D  | L  | GF | GA | GD | PTS |
+-----+--------+----------------------+----+----+----+----+----+----+----+-----+
| 1   | TM001  | Thunder              | 1  | 1  | 0  | 0  | 2  | 1  | +1 | 3   |
| 2   | TM003  | Phoenix              | 1  | 0  | 1  | 0  | 0  | 0  | +0 | 1   |
| 3   | TM004  | Rockets              | 1  | 0  | 1  | 0  | 0  | 0  | +0 | 1   |
| 4   | TM002  | Comets               | 1  | 0  | 0  | 1  | 1  | 2  | -1 | 0   |
+-----+--------+----------------------+----+----+----+----+----+----+----+-----+

Tournament Status: [IN PROGRESS]
Standings are currently IN PROGRESS (4 pending fixture(s) remain).
```

5. **Rejection of Invalid Score & Preservation of State**:
   - Entering an invalid score (e.g. `home=-5`, `home=True`, or re-submitting `M001`) raises a descriptive `ValueError`.
   - Standings and fixtures remain unchanged.

6. **JSON Save & Load**:
   - Saved to `tournament_state.json`.
   - Reloaded: data, standings, and IDs are identical.

7. **Season Completion & Champion Report**:
   - Complete remaining matches.
   - Status changes to `[COMPLETE]` and Champion is announced!
