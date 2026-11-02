"""Standings aggregation, tie-break ranking and champion determination.

Engineer B ownership:
- Derives league table purely from played match results (single source of truth)
- Multi-key sorting: Points DESC, Goal Difference DESC, Goals For DESC, Normalized Name ASC
- Determines tournament completion status and champion report
- Verifies mathematical league invariants
"""

from typing import Any


def compute_standings(
    teams: list[dict[str, Any]],
    fixtures: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compute league standings dynamically from registered teams and played fixtures.

    Standings are never stored as mutable state; they are reconstructed on demand
    to guarantee zero state drift and perfect consistency.

    Points system:
        - Win: 3 points
        - Draw: 1 point
        - Loss: 0 points

    Ranking hierarchy (tie-break):
        1. Points descending
        2. Goal Difference descending
        3. Goals For descending
        4. Normalized team name (casefolded) ascending

    Args:
        teams: List of registered team dictionaries.
        fixtures: List of fixture dictionaries.

    Returns:
        List of standings rows sorted according to the ranking hierarchy.
    """
    # Initialize zeroed record for every registered team
    table: dict[str, dict[str, Any]] = {
        team["id"]: {
            "team_id": team["id"],
            "name": team["name"],
            "played": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
            "goal_difference": 0,
            "points": 0,
        }
        for team in teams
    }

    # Aggregate played fixtures
    for fixture in fixtures:
        if fixture.get("status") != "played":
            continue

        home_id = fixture["home_id"]
        away_id = fixture["away_id"]
        home_score = fixture["home_score"]
        away_score = fixture["away_score"]

        # Only process if both teams exist in current tournament
        if home_id not in table or away_id not in table:
            continue

        home_row = table[home_id]
        away_row = table[away_id]

        home_row["played"] += 1
        away_row["played"] += 1

        home_row["goals_for"] += home_score
        home_row["goals_against"] += away_score
        away_row["goals_for"] += away_score
        away_row["goals_against"] += home_score

        if home_score > away_score:
            home_row["wins"] += 1
            home_row["points"] += 3
            away_row["losses"] += 1
        elif away_score > home_score:
            away_row["wins"] += 1
            away_row["points"] += 3
            home_row["losses"] += 1
        else:
            home_row["draws"] += 1
            home_row["points"] += 1
            away_row["draws"] += 1
            away_row["points"] += 1

    # Calculate goal difference for each team
    for row in table.values():
        row["goal_difference"] = row["goals_for"] - row["goals_against"]

    # Multi-key tie-break sorting:
    # 1. points DESC (negated numeric)
    # 2. goal_difference DESC (negated numeric)
    # 3. goals_for DESC (negated numeric)
    # 4. name.casefold() ASC (lexicographical string)
    sorted_standings = sorted(
        table.values(),
        key=lambda r: (
            -r["points"],
            -r["goal_difference"],
            -r["goals_for"],
            r["name"].casefold(),
        ),
    )

    return sorted_standings


def get_tournament_status(
    fixtures: list[dict[str, Any]],
    standings: list[dict[str, Any]],
) -> tuple[str, dict[str, Any] | None]:
    """Determine whether the tournament is complete or in progress.

    Args:
        fixtures: List of all tournament fixtures.
        standings: Current sorted standings list.

    Returns:
        A tuple: (status_label, champion_row_or_None).
        Status label is 'complete' if all scheduled fixtures have been played;
        otherwise 'in progress'.
    """
    if len(fixtures) == 0:
        return "in progress", None

    has_pending = any(f.get("status") == "pending" for f in fixtures)
    if has_pending:
        return "in progress", None

    # All fixtures have been played: crown top-ranked team as champion
    champion = standings[0] if standings else None
    return "complete", champion


def verify_league_invariants(
    standings: list[dict[str, Any]],
    fixtures: list[dict[str, Any]],
) -> tuple[bool, str]:
    """Verify core mathematical invariants across played matches and standings.

    Invariants checked:
        1. Total points across league == 3 * non_draw_matches + 2 * draw_matches
        2. Total goals for == Total goals against
        3. Total played appearances across teams == 2 * played_matches_count

    Returns:
        (True, "All invariants hold") or (False, reason_string).
    """
    played_fixtures = [f for f in fixtures if f.get("status") == "played"]

    draws_count = sum(
        1 for f in played_fixtures if f["home_score"] == f["away_score"]
    )
    non_draws_count = len(played_fixtures) - draws_count

    expected_total_points = (3 * non_draws_count) + (2 * draws_count)
    actual_total_points = sum(r["points"] for r in standings)

    if actual_total_points != expected_total_points:
        return (
            False,
            f"Point invariant violated: expected {expected_total_points} total league points, "
            f"found {actual_total_points}.",
        )

    total_gf = sum(r["goals_for"] for r in standings)
    total_ga = sum(r["goals_against"] for r in standings)
    if total_gf != total_ga:
        return (
            False,
            f"Goal balance invariant violated: total GF ({total_gf}) != total GA ({total_ga}).",
        )

    total_team_played = sum(r["played"] for r in standings)
    expected_team_played = 2 * len(played_fixtures)
    if total_team_played != expected_team_played:
        return (
            False,
            f"Match count invariant violated: expected {expected_team_played} cumulative team games, "
            f"found {total_team_played}.",
        )

    return True, "All league invariants verified successfully."
