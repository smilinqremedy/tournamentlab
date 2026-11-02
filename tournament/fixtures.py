"""Fixtures generation, management and scoring module.

Round-robin scheduling (Engineer A) & Result entry (Engineer B).
"""

from typing import Any


def generate_round_robin(
    teams: list[dict[str, Any]],
    existing_fixtures: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Generate a single round-robin schedule for 4-8 registered teams.

    Combinatorics:
        Every pair meets once: N * (N - 1) / 2 fixtures.
        Each team plays exactly N - 1 matches.

    Args:
        teams: List of registered team dicts. Must contain between 4 and 8 teams.
        existing_fixtures: List of existing fixtures. Must be empty.

    Returns:
        List of generated pending fixture dictionaries.

    Raises:
        ValueError: If fixtures were already generated, or team count is not in [4, 8].
    """
    if len(existing_fixtures) > 0:
        raise ValueError("Fixtures have already been generated for this tournament.")

    num_teams = len(teams)
    if num_teams < 4:
        raise ValueError(
            f"Cannot generate fixtures: at least 4 teams required (currently {num_teams})."
        )
    if num_teams > 8:
        raise ValueError(
            f"Cannot generate fixtures: at most 8 teams allowed (currently {num_teams})."
        )

    # Verify all team IDs are unique
    team_ids = [t["id"] for t in teams]
    if len(team_ids) != len(set(team_ids)):
        raise ValueError("Duplicate team IDs detected in teams list.")

    fixtures: list[dict[str, Any]] = []
    match_counter = 1

    # Deterministic round-robin generation: all unique unordered pairs (i, j) where i < j
    for i in range(num_teams):
        for j in range(i + 1, num_teams):
            fixture_id = f"M{match_counter:03d}"
            home_team = teams[i]
            away_team = teams[j]

            fixtures.append({
                "id": fixture_id,
                "home_id": home_team["id"],
                "away_id": away_team["id"],
                "status": "pending",
                "home_score": None,
                "away_score": None,
            })
            match_counter += 1

    return fixtures


def get_fixture_by_id(
    fixtures: list[dict[str, Any]],
    fixture_id: str,
) -> dict[str, Any] | None:
    """Find a fixture dictionary by its identifier."""
    for fixture in fixtures:
        if fixture.get("id") == fixture_id:
            return fixture
    return None


def list_fixtures(fixtures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a shallow copy of the fixtures list."""
    return list(fixtures)


# --- Engineer B Ownership: Score Validation and Recording ---


def validate_score(score: Any) -> int:
    """Validate that a score is a nonnegative integer.

    Critical Python edge-case:
    In Python, `bool` is a subclass of `int` (`isinstance(True, int) is True`).
    We explicitly reject booleans to prevent `True` from being treated as 1 goal.
    Floats, strings, None and negative values are strictly prohibited.

    Args:
        score: The candidate score value.

    Returns:
        The validated integer score.

    Raises:
        ValueError: If score is not a strict, nonnegative integer.
    """
    if isinstance(score, bool) or not isinstance(score, int):
        raise ValueError(
            f"Invalid score {repr(score)}: score must be an integer, not {type(score).__name__}."
        )

    if score < 0:
        raise ValueError(f"Invalid score {score}: scores cannot be negative.")

    return score


def record_result(
    fixtures: list[dict[str, Any]],
    fixture_id: str,
    home_score: Any,
    away_score: Any,
) -> dict[str, Any]:
    """Atomically record match scores for a scheduled pending fixture.

    Enforces validate-before-mutate semantics:
    Both scores are verified before updating any fixture fields.
    Already played fixtures or non-existent fixture IDs are rejected.

    Args:
        fixtures: List of fixtures.
        fixture_id: Identifier of the target fixture (e.g. 'M001').
        home_score: Goals / rounds won by the home team.
        away_score: Goals / rounds won by the away team.

    Returns:
        The updated fixture dictionary.

    Raises:
        ValueError: If fixture does not exist, was already played, or scores are invalid.
    """
    fixture = get_fixture_by_id(fixtures, fixture_id)
    if fixture is None:
        raise ValueError(f"Cannot record result: fixture '{fixture_id}' not found.")

    if fixture.get("status") == "played":
        raise ValueError(
            f"Cannot record result: fixture '{fixture_id}' has already been played. "
            f"Duplicate score submissions are prohibited."
        )

    if fixture.get("status") != "pending":
        raise ValueError(
            f"Cannot record result: fixture '{fixture_id}' has invalid status '{fixture.get('status')}'."
        )

    # Validate both scores before mutating fixture state
    clean_home = validate_score(home_score)
    clean_away = validate_score(away_score)

    # Atomic state update
    fixture["home_score"] = clean_home
    fixture["away_score"] = clean_away
    fixture["status"] = "played"

    return fixture
