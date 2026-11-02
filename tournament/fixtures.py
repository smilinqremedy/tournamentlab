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
