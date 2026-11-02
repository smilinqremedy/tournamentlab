# TournamentLab — Architecture & Engineering Design Decisions

## 1. System Overview & Core Philosophy
TournamentLab is a robust, localized esports league management system written in Python 3 using the standard library. Its principal objective is **league fairness and data integrity**:
- **Single Source of Truth**: Standings are never maintained as an independent, mutable tally. They are derived purely by aggregating played matches.
- **Atomic Operations & Validate-Before-Mutate**: Match records, team additions, and state transitions either succeed completely or reject invalid input without mutating existing memory.
- **Referential Integrity**: Fixtures strictly reference verified team identifiers (`TM001`...); JSON files with orphaned references are rejected prior to state replacement.
- **Deterministic Combinatorics**: Round-robin schedules are generated without self-matches or duplicate pairs using an explicit combinatoric algorithm with $N(N-1)/2$ total fixtures.

---

## 2. Canonical Data Record Shapes

### Team Record
```python
{
    "id": "TM001",           # Stable, immutable identifier (format: TM\d{3})
    "name": "Red Comets"     # Trimmed display label (2-30 characters, case-insensitively unique)
}
```

### Fixture Record (Pending)
```python
{
    "id": "M001",            # Stable fixture identifier (format: M\d{3})
    "home_id": "TM001",       # Existing team ID
    "away_id": "TM002",       # Distinct existing team ID
    "status": "pending",     # Status enum: 'pending' | 'played'
    "home_score": None,      # None when pending
    "away_score": None       # None when pending
}
```

### Fixture Record (Played)
```python
{
    "id": "M001",
    "home_id": "TM001",
    "away_id": "TM002",
    "status": "played",
    "home_score": 2,          # Nonnegative integer (strictly not boolean)
    "away_score": 1           # Nonnegative integer (strictly not boolean)
}
```

### Standings Row (Derived State)
```python
{
    "team_id": "TM001",
    "name": "Red Comets",
    "played": 1,
    "wins": 1,
    "draws": 0,
    "losses": 0,
    "goals_for": 2,
    "goals_against": 1,
    "goal_difference": 1,
    "points": 3
}
```

---

## 3. Engineer A & Engineer B Contract Agreement

Prior to writing code, Engineer A and Engineer B agreed on the following division of responsibilities and function contracts:

| Module | Primary Owner | Functions / Interfaces |
|---|---|---|
| `tournament/teams.py` | **Engineer A** | `validate_team_name(name: str) -> str`<br>`register_team(teams: list, raw_name: str) -> dict`<br>`find_team_by_id(teams: list, team_id: str) -> dict \| None`<br>`list_teams(teams: list) -> list` |
| `tournament/fixtures.py` (Gen) | **Engineer A** | `generate_round_robin(teams: list, existing_fixtures: list) -> list[dict]` |
| `tournament/storage.py` | **Engineer A** | `save_tournament(filepath, teams, fixtures) -> None`<br>`load_tournament(filepath) -> tuple[list[dict], list[dict]]` |
| `tournament/fixtures.py` (Scoring) | **Engineer B** | `validate_score(score: Any) -> int`<br>`record_result(fixtures: list, fixture_id: str, home_score: Any, away_score: Any) -> dict` |
| `tournament/standings.py` | **Engineer B** | `compute_standings(teams: list, fixtures: list) -> list[dict]`<br>`get_tournament_status(fixtures: list, standings: list) -> tuple[str, dict \| None]` |
| `tournament/simulation.py` | **Engineer B** | `simulate_demo_fixtures(fixtures: list, seed: int = 42) -> int` |
| `tournament/cli.py` & `main.py` | **Engineer B** | Interactive CLI loop, ASCII tables, user input sanitization |

---

## 4. Invariants & Critical Edge Cases

1. **The Python Boolean Trap**:
   In Python, `bool` is a subclass of `int` (`issubclass(bool, int) is True`, and `isinstance(True, int) is True`). Passing `True` to a naive integer check would record 1 goal!
   - *Mitigation*: We strictly enforce `if isinstance(val, bool) or not isinstance(val, int): raise ValueError(...)`.

2. **Atomic Score Submission**:
   If `home_score` is valid but `away_score` is invalid, the fixture must not be partially mutated. Both scores are validated prior to mutating `home_score`, `away_score`, and setting `status = 'played'`.

3. **Multi-Key Lexicographic Tie-Break Sorting**:
   Teams are ranked according to:
   1. Points (`points` descending)
   2. Goal Difference (`goal_difference` descending)
   3. Goals For (`goals_for` descending)
   4. Normalized Team Name (`name.casefold()` ascending)

   In Python, ascending string sorting cannot be inverted with a minus sign if `reverse=True`. Therefore, we use `reverse=False` with negated numeric keys:
   ```python
   key=lambda row: (-row['points'], -row['goal_difference'], -row['goals_for'], row['name'].casefold())
   ```

4. **Derivation of Round-Robin Formula**:
   For $N$ teams, each team plays every other team once ($N-1$ opponents).
   Total team-match appearances = $N \times (N-1)$.
   Since every match involves 2 teams, total fixtures = $\frac{N(N-1)}{2}$.
   - For $N=4$: $4 \times 3 / 2 = 6$ fixtures.
   - For $N=6$: $6 \times 5 / 2 = 15$ fixtures.
   - For $N=8$: $8 \times 7 / 2 = 28$ fixtures.

5. **JSON Schema Referential Integrity**:
   On load, we perform full validation on a temporary copy:
   - Validate version (`schema_version == 1`).
   - Validate teams (unique IDs, 2-30 chars, unique casefold names).
   - Validate fixtures (IDs unique, home and away IDs must exist in loaded teams, no self-match, no duplicate unordered pair, status and scores match).
   - Only when all validation checks pass does the system replace active memory.
