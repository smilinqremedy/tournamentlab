# TournamentLab — AI Learning Log & Engineering Reflection

This document records the six structured learning cycles (three for Engineer A, three for Engineer B) completed during the development of TournamentLab.

---

## Engineer A (Scheduling, Data Structures & Persistence)

### Cycle A-1: Unordered Combinatorics vs. Permutations in Round-Robin Scheduling
- **Topic I did not know:**
  How to programmatically generate an exact single round-robin schedule without generating duplicate reverse matches (e.g., both A vs B and B vs A) or self-matches (A vs A), without relying on heavy external dependencies.
- **Exact Prompt:**
  *"I am generating a round-robin schedule for N teams where every pair plays once. How do I generate every unique pair without self-matches or duplicate reversed pairs using basic Python loops, and how do I calculate the expected total count?"*
- **AI's Explanation in My Own Words:**
  For $N$ items, a single round-robin is the number of 2-combinations from $N$, represented by the binomial coefficient $\binom{N}{2} = \frac{N(N-1)}{2}$. By using a nested loop where the outer loop variable $i$ ranges from $0$ to $N-1$ and the inner loop variable $j$ starts strictly at $i+1$ up to $N$, every index pair $(i, j)$ satisfies $i < j$. This guarantees that no element is ever paired with itself ($i \neq j$) and no pair is ever visited in reverse order ($j > i$), naturally yielding exactly $\frac{N(N-1)}{2}$ unique matches.
- **Tiny Independent Experiment:**
  ```python
  names = ["A", "B", "C", "D"]
  pairs = []
  for i in range(len(names)):
      for j in range(i + 1, len(names)):
          pairs.append((names[i], names[j]))
  print("Count:", len(pairs), "Pairs:", pairs)
  ```
- **Actual Results:**
  ```text
  Count: 6 Pairs: [('A', 'B'), ('A', 'C'), ('A', 'D'), ('B', 'C'), ('B', 'D'), ('C', 'D')]
  ```
- **Corrected Misconception / Decision:**
  Initially, I thought about using `itertools.permutations` and then filtering with a `set(frozenset(...))`. The AI suggestion demonstrated that nested loops with index bounds $j \in [i+1, N)$ are deterministic, require zero auxiliary hashing, and naturally avoid self-matches in $O(N^2)$ time.
- **Related Code & Commit:**
  - File: `tournament/fixtures.py` (`generate_round_robin`)
  - Commit: `e4bd101` (*feat(teams,fixtures): team registration, constraints and round-robin generator*)

---

### Cycle A-2: Casefolded Strings vs. Standard Lowercasing for Uniqueness
- **Topic I did not know:**
  Why `.casefold()` is preferred over `.lower()` for enforcing case-insensitive uniqueness in internationalized or diverse user-supplied strings.
- **Exact Prompt:**
  *"What is the difference between string.lower() and string.casefold() in Python, and why does it matter when validating uniqueness of team names in a sports database?"*
- **AI's Explanation in My Own Words:**
  While `.lower()` handles standard ASCII case conversions (e.g. `'A'` to `'a'`), `.casefold()` implements the full Unicode Case Folding algorithm. It strips case distinctions across scripts and characters with non-1:1 mappings (such as the German lowercase sharp s `'ß'` expanding to `'ss'`, or Greek uppercase sigma variants). Using `.casefold()` ensures aggressive and safe collision detection so users cannot bypass uniqueness checks with Unicode variants.
- **Tiny Independent Experiment:**
  ```python
  s1 = "ß"
  s2 = "SS"
  print("lower equality:", s1.lower() == s2.lower())
  print("casefold equality:", s1.casefold() == s2.casefold())
  ```
- **Actual Results:**
  ```text
  lower equality: False
  casefold equality: True
  ```
- **Corrected Misconception / Decision:**
  I had assumed `.lower()` was sufficient for all text normalization. I decided to standardize on `name.strip().casefold()` across all name validation, duplicate checks, and tie-breaking tie-breakers.
- **Related Code & Commit:**
  - File: `tournament/teams.py` (`is_name_duplicate`, `validate_team_name`)
  - Commit: `e4bd101` (*feat(teams,fixtures): team registration, constraints and round-robin generator*)

---

### Cycle A-3: Referential Integrity & Validate-Before-Mutate Persistence (AI Suggestion Rejected)
- **Topic I did not know:**
  How to safely load JSON files without partially modifying in-memory state when a data anomaly or referential integrity error is encountered halfway through the file.
- **Exact Prompt:**
  *"How should I load a tournament JSON file in Python so that if one fixture has an invalid score or references an unknown team, the application state is not corrupted?"*
- **AI's Explanation in My Own Words:**
  The AI suggested reading the file line-by-line or updating the global `teams` and `fixtures` lists iteratively in a `try...except` block, rolling back on error by restoring a deep copy.
- **Tiny Independent Experiment & Skepticism:**
  I tested the AI's rollback recommendation with a synthetic corrupted fixture. If rollback code itself encountered an exception, or if partial state was modified before an unhandled error occurred, the system was left in an indeterminate state.
- **Rejected Suggestion & Evidence-Backed Alternative:**
  **I rejected the AI's iterative in-place modification pattern.** Instead, I designed a **two-phase validate-before-mutate parser**:
  1. Phase 1 (Pure Validation): Read and parse JSON entirely into local temporary structures (`validated_teams`, `validated_fixtures`). Run comprehensive checks: schema version, team ID uniqueness, name constraints, referential integrity (`home_id` and `away_id` in `seen_team_ids`), self-match detection, and score bounds.
  2. Phase 2 (State Replacement): Only after every single record and invariant passes validation are the active lists cleared and populated.
  If an exception occurs at any point in Phase 1, the function raises `ValueError` immediately, and the caller's active state remains 100% untouched.
- **Related Code & Commit:**
  - File: `tournament/storage.py` (`load_tournament`)
  - Test: `tests/test_storage.py` (`test_reject_phantom_team_reference`)
  - Commit: `7ec1e59` (*feat(storage): versioned JSON persistence with schema and referential integrity validation*)

---

## Engineer B (Scoring, Standings, Simulation & CLI)

### Cycle B-1: The Python Boolean Inheritance Trap in Strict Type Validation
- **Topic I did not know:**
  Why `isinstance(True, int)` evaluates to `True` in Python, and how this can silently corrupt numerical calculations like goals, points, or financial transactions.
- **Exact Prompt:**
  *"Why does isinstance(True, int) return True in Python, and how do I write a validation function that strictly accepts nonnegative integers but rejects booleans?"*
- **AI's Explanation in My Own Words:**
  In Python, the `bool` class was historically implemented as an explicit subclass of `int` (`issubclass(bool, int) is True`). Consequently, `True` behaves numerically as `1` and `False` as `0`. If a validation function checks only `isinstance(val, int)`, passing `True` or `False` (for example, from parsed JSON `true`/`false`) will silently pass and register 1 goal or 0 goals.
- **Tiny Independent Experiment:**
  ```python
  def naive_check(x):
      return isinstance(x, int) and x >= 0

  def strict_check(x):
      return not isinstance(x, bool) and isinstance(x, int) and x >= 0

  print("Naive with True:", naive_check(True))
  print("Strict with True:", strict_check(True))
  ```
- **Actual Results:**
  ```text
  Naive with True: True
  Strict with True: False
  ```
- **Corrected Misconception / Decision:**
  I learned that type checks for integers must always explicitly exclude `bool`. In `validate_score` and `storage.py`, we implemented `if isinstance(score, bool) or not isinstance(score, int): raise ValueError(...)`.
- **Related Code & Commit:**
  - File: `tournament/fixtures.py` (`validate_score`)
  - File: `tournament/storage.py` (`load_tournament`)
  - Commit: `9eb3957` (*feat(scoring,standings): atomic score validation, pure standings calculation, tie-break hierarchy and invariants*)

---

### Cycle B-2: Lexicographic Multi-Key Sorting with Mixed Directionalities
- **Topic I did not know:**
  How to cleanly sort table rows in Python when numeric keys must be descending (Points, GD, GF) but the textual key must be ascending (Team Name alphabetical), without performing multiple unstable sort passes.
- **Exact Prompt:**
  *"In Python, how do I sort a list of dicts by points descending, goal difference descending, goals for descending, and team name ascending in a single sorted() call?"*
- **AI's Explanation in My Own Words:**
  Python's `sorted()` function uses Timsort and accepts a `key` parameter that can return a tuple. Python compares tuples lexicographically: element by element from left to right. If we set `reverse=True`, all elements (including the team name) would be reversed, sorting names Z to A instead of A to Z. To achieve mixed directionality, we keep the default `reverse=False`, invert the signs of numeric values (`-row['points']`, `-row['goal_difference']`, `-row['goals_for']`), and leave the string name as `row['name'].casefold()`.
- **Tiny Independent Experiment:**
  ```python
  teams = [
      {"name": "Bravo", "pts": 3, "gd": 0, "gf": 2},
      {"name": "Alpha", "pts": 3, "gd": 0, "gf": 2},
      {"name": "Charlie", "pts": 6, "gd": 3, "gf": 4},
  ]
  ranked = sorted(teams, key=lambda r: (-r["pts"], -r["gd"], -r["gf"], r["name"].casefold()))
  for idx, t in enumerate(ranked, 1):
      print(f"{idx}. {t['name']} ({t['pts']} pts)")
  ```
- **Actual Results:**
  ```text
  1. Charlie (6 pts)
  2. Alpha (3 pts)
  3. Bravo (3 pts)
  ```
- **Corrected Misconception / Decision:**
  Initially, I considered sorting twice: first by name with `reverse=False`, and then by points with `reverse=True`. But multiple passes are prone to subtle bugs if tie-breakers aren't completely stable. Negating the descending numeric keys within a single tuple is idiomatic, clean, and runs in a single $O(N \log N)$ pass.
- **Related Code & Commit:**
  - File: `tournament/standings.py` (`compute_standings`)
  - Test: `tests/test_standings.py` (`test_four_level_tie_break_hierarchy`)
  - Commit: `9eb3957` (*feat(scoring,standings): atomic score validation, pure standings calculation, tie-break hierarchy and invariants*)

---

### Cycle B-3: Pure Functions vs. Maintained Mutable State for League Tables (AI Suggestion Rejected)
- **Topic I did not know:**
  Whether a tournament application should maintain an updated standings table in memory and on disk, or recompute it dynamically whenever requested.
- **Exact Prompt:**
  *"Should I store standings as a mutable dictionary in the tournament state that gets updated whenever record_result() is called, or should I compute standings on demand?"*
- **AI's Explanation in My Own Words:**
  The AI suggested maintaining a cached `self.standings` dictionary that gets updated incrementally after each match to optimize performance, arguing that re-aggregating standings on every view is "inefficient".
- **Tiny Independent Experiment & Skepticism:**
  I simulated what happens if a match score is cancelled, edited, or reloaded from a partial save. When standings were stored as a mutable state, any discrepancy between match records and table updates (such as an unhandled exception or partial disk write) caused permanent state desynchronization. In a league with 4-8 teams (maximum 28 fixtures), computing standings from scratch takes less than 0.2 milliseconds.
- **Rejected Suggestion & Evidence-Backed Alternative:**
  **I firmly rejected caching/maintaining mutable standings.**
  In TournamentLab, the matches (`fixtures`) are the **single source of truth**. `compute_standings(teams, fixtures)` is a pure, idempotent function with zero side effects:
  - Standings are never persisted independently.
  - Standings cannot drift from recorded scores.
  - If a fixture is modified or loaded, standings are guaranteed to reflect reality.
  - A verification helper (`verify_league_invariants`) mathematically checks that total league points equal $3 \times non\_draws + 2 \times draws$ and total GF equals total GA.
- **Related Code & Commit:**
  - File: `tournament/standings.py` (`compute_standings`, `verify_league_invariants`)
  - Test: `tests/test_standings.py` (`test_stage_zero_diagnostic_scenario`)
  - Commit: `9eb3957` (*feat(scoring,standings): atomic score validation, pure standings calculation, tie-break hierarchy and invariants*)

---

## Summary of Personal Reflections

### Engineer A's Reflection:
> *"The toughest concept I mastered was designing a truly fail-safe JSON loading subsystem. It is easy to write a basic `json.load()`, but building a parser that enforces relational database principles (foreign keys, domain constraints, status-score consistency) in pure Python showed me the difference between scripting and engineering. The most satisfying bug we caught was in test scenario 14, where a malformed file referenced a non-existent team ID: our validate-before-mutate architecture caught it instantly and kept in-memory tournament state completely safe."*

### Engineer B's Reflection:
> *"My biggest breakthrough was discovering Python's `isinstance(True, int) is True` behavior. In an esports league, accidentally passing a boolean from a JSON payload or CLI flag could award a false round victory or corrupt goal difference. Writing a strict validator that rejects booleans and negative numbers was a simple but profound lesson in defensive programming. Additionally, rejecting mutable standings in favor of purely derived aggregations eliminated an entire class of synchronization bugs."*
