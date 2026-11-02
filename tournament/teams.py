"""Team registration and validation module.

Engineer A ownership:
- Handles team registration (4-8 teams allowed)
- Validates name length (2-30 characters after trim)
- Ensures case-insensitive uniqueness
- Assigns stable, sequential identifiers (TM001...)
"""

from typing import Any


def validate_team_name(raw_name: Any) -> str:
    """Validate and normalize a team display name.

    Rules:
    - Must be a string.
    - Trimmed length must be between 2 and 30 characters inclusive.

    Raises:
        ValueError: If name is not a string, or length is outside [2, 30].
    """
    if not isinstance(raw_name, str):
        raise ValueError("Team name must be a string.")

    cleaned_name = raw_name.strip()
    if len(cleaned_name) < 2:
        raise ValueError(
            f"Team name '{cleaned_name}' is too short. Minimum length is 2 characters."
        )
    if len(cleaned_name) > 30:
        raise ValueError(
            f"Team name '{cleaned_name}' is too long. Maximum length is 30 characters."
        )

    return cleaned_name


def is_name_duplicate(name: str, teams: list[dict[str, Any]]) -> bool:
    """Check if a team name already exists using casefolded comparison.

    Args:
        name: The candidate team name.
        teams: The list of currently registered team dictionaries.

    Returns:
        True if an existing team shares the same casefolded name; False otherwise.
    """
    target = name.strip().casefold()
    for team in teams:
        existing_name = str(team.get("name", "")).strip().casefold()
        if existing_name == target:
            return True
    return False


def register_team(teams: list[dict[str, Any]], raw_name: Any) -> dict[str, Any]:
    """Register a new team in the tournament.

    Args:
        teams: Active list of registered team dictionaries (mutated in-place on success).
        raw_name: Raw team name string input.

    Returns:
        The newly created team dictionary: {'id': 'TM001', 'name': '...'}

    Raises:
        ValueError: If maximum capacity (8) is reached, name is invalid, or name is duplicate.
    """
    if len(teams) >= 8:
        raise ValueError("Cannot register team: tournament capacity of 8 teams reached.")

    cleaned_name = validate_team_name(raw_name)

    if is_name_duplicate(cleaned_name, teams):
        raise ValueError(
            f"Cannot register team: '{cleaned_name}' is already registered (case-insensitive duplicate)."
        )

    # Generate sequential unique identifier (TM001, TM002, ...)
    existing_ids = {team["id"] for team in teams if "id" in team}
    counter = 1
    while f"TM{counter:03d}" in existing_ids:
        counter += 1
    team_id = f"TM{counter:03d}"

    new_team = {
        "id": team_id,
        "name": cleaned_name,
    }
    teams.append(new_team)
    return new_team


def find_team_by_id(teams: list[dict[str, Any]], team_id: str) -> dict[str, Any] | None:
    """Find a team dictionary by its stable identifier.

    Args:
        teams: List of registered team dictionaries.
        team_id: Target ID string.

    Returns:
        The team dictionary if found, or None.
    """
    for team in teams:
        if team.get("id") == team_id:
            return team
    return None


def get_team_name(teams: list[dict[str, Any]], team_id: str) -> str:
    """Get the display name of a team by ID, falling back to ID if not found."""
    team = find_team_by_id(teams, team_id)
    return team["name"] if team else team_id


def list_teams(teams: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a shallow copy of the registered teams list."""
    return list(teams)
