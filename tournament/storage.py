"""Persistence, JSON schema versioning and integrity validation.

Engineer A ownership:
- Saves tournament state with schema versioning
- Rigorously validates schema, referential integrity and business invariants upon load
- Protects in-memory state with validate-before-replace semantics
"""

import json
from pathlib import Path
from typing import Any

from tournament.teams import validate_team_name

SCHEMA_VERSION = 1


def save_tournament(
    filepath: str | Path,
    teams: list[dict[str, Any]],
    fixtures: list[dict[str, Any]],
) -> None:
    """Save the tournament state to a JSON file.

    Args:
        filepath: Target destination file path.
        teams: List of team dictionaries.
        fixtures: List of fixture dictionaries.
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "schema_version": SCHEMA_VERSION,
        "teams": teams,
        "fixtures": fixtures,
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def load_tournament(
    filepath: str | Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Load and strictly validate a tournament state from a JSON file.

    Performs validate-before-mutate parsing into temporary data structures.
    Rejects malformed JSON, unsupported schema versions, unknown teams,
    duplicate IDs or names, duplicate fixtures, and illegal scores.

    Args:
        filepath: Path to the JSON file to read.

    Returns:
        A tuple of (validated_teams, validated_fixtures).

    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If file content violates schema, referential integrity, or tournament invariants.
    """
    path = Path(filepath)
    if not path.is_file():
        raise FileNotFoundError(f"Tournament file not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as err:
        raise ValueError(f"Invalid JSON syntax in '{path}': {err}") from err

    if not isinstance(data, dict):
        raise ValueError("Invalid tournament file format: top-level element must be a JSON object.")

    # 1. Schema version check
    version = data.get("schema_version")
    if version != SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported schema version: {version}. Expected version {SCHEMA_VERSION}."
        )

    # 2. Teams validation
    teams_raw = data.get("teams")
    if not isinstance(teams_raw, list):
        raise ValueError("Malformed tournament data: 'teams' must be a list.")

    if len(teams_raw) > 8:
        raise ValueError(
            f"Invalid team count: {len(teams_raw)} teams found (maximum 8 allowed)."
        )

    validated_teams: list[dict[str, Any]] = []
    seen_team_ids: set[str] = set()
    seen_team_names: set[str] = set()

    for idx, team_entry in enumerate(teams_raw):
        if not isinstance(team_entry, dict):
            raise ValueError(f"Malformed team record at index {idx}: must be a dictionary.")

        team_id = team_entry.get("id")
        if not isinstance(team_id, str) or not team_id.strip():
            raise ValueError(f"Invalid team ID at index {idx}: must be a non-empty string.")
        if team_id in seen_team_ids:
            raise ValueError(f"Duplicate team ID detected: '{team_id}'.")
        seen_team_ids.add(team_id)

        raw_name = team_entry.get("name")
        cleaned_name = validate_team_name(raw_name)
        casefolded_name = cleaned_name.casefold()
        if casefolded_name in seen_team_names:
            raise ValueError(
                f"Duplicate team name detected: '{cleaned_name}' (case-insensitive match)."
            )
        seen_team_names.add(casefolded_name)

        validated_teams.append({
            "id": team_id,
            "name": cleaned_name,
        })

    # 3. Fixtures validation
    fixtures_raw = data.get("fixtures")
    if not isinstance(fixtures_raw, list):
        raise ValueError("Malformed tournament data: 'fixtures' must be a list.")

    if len(fixtures_raw) > 0 and len(validated_teams) < 4:
        raise ValueError(
            f"Inconsistent tournament data: fixtures exist but only {len(validated_teams)} teams are present (minimum 4)."
        )

    validated_fixtures: list[dict[str, Any]] = []
    seen_fixture_ids: set[str] = set()
    seen_pairs: set[frozenset[str]] = set()

    for idx, fixture_entry in enumerate(fixtures_raw):
        if not isinstance(fixture_entry, dict):
            raise ValueError(f"Malformed fixture record at index {idx}: must be a dictionary.")

        fixture_id = fixture_entry.get("id")
        if not isinstance(fixture_id, str) or not fixture_id.strip():
            raise ValueError(f"Invalid fixture ID at index {idx}: must be a non-empty string.")
        if fixture_id in seen_fixture_ids:
            raise ValueError(f"Duplicate fixture ID detected: '{fixture_id}'.")
        seen_fixture_ids.add(fixture_id)

        home_id = fixture_entry.get("home_id")
        away_id = fixture_entry.get("away_id")

        if not isinstance(home_id, str) or not isinstance(away_id, str):
            raise ValueError(f"Fixture '{fixture_id}' contains non-string team references.")

        # Referential integrity checks
        if home_id not in seen_team_ids:
            raise ValueError(
                f"Referential integrity failure: fixture '{fixture_id}' references unknown home team '{home_id}'."
            )
        if away_id not in seen_team_ids:
            raise ValueError(
                f"Referential integrity failure: fixture '{fixture_id}' references unknown away team '{away_id}'."
            )

        if home_id == away_id:
            raise ValueError(
                f"Invalid self-match in fixture '{fixture_id}': home and away teams are identical ('{home_id}')."
            )

        pair = frozenset([home_id, away_id])
        if pair in seen_pairs:
            raise ValueError(
                f"Duplicate fixture pair detected in fixture '{fixture_id}': teams '{home_id}' and '{away_id}' are scheduled more than once."
            )
        seen_pairs.add(pair)

        status = fixture_entry.get("status")
        home_score = fixture_entry.get("home_score")
        away_score = fixture_entry.get("away_score")

        if status == "pending":
            if home_score is not None or away_score is not None:
                raise ValueError(
                    f"Pending fixture '{fixture_id}' cannot have non-None scores (got home={home_score}, away={away_score})."
                )
            clean_home_score = None
            clean_away_score = None
        elif status == "played":
            # Strict non-boolean integer check
            if isinstance(home_score, bool) or not isinstance(home_score, int) or home_score < 0:
                raise ValueError(
                    f"Played fixture '{fixture_id}' has invalid home score: {repr(home_score)}."
                )
            if isinstance(away_score, bool) or not isinstance(away_score, int) or away_score < 0:
                raise ValueError(
                    f"Played fixture '{fixture_id}' has invalid away score: {repr(away_score)}."
                )
            clean_home_score = home_score
            clean_away_score = away_score
        else:
            raise ValueError(
                f"Fixture '{fixture_id}' has unrecognized status: {repr(status)}. Expected 'pending' or 'played'."
            )

        validated_fixtures.append({
            "id": fixture_id,
            "home_id": home_id,
            "away_id": away_id,
            "status": status,
            "home_score": clean_home_score,
            "away_score": clean_away_score,
        })

    return validated_teams, validated_fixtures
