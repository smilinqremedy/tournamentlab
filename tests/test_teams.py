"""Unit tests for team registration, validation and indexing (Engineer A)."""

import unittest
from tournament.teams import (
    find_team_by_id,
    get_team_name,
    list_teams,
    register_team,
    validate_team_name,
)


class TestTeamRegistration(unittest.TestCase):
    """Test suite for team registration and constraints."""

    def setUp(self) -> None:
        self.teams: list[dict] = []

    def test_register_team_success(self) -> None:
        """Registering a valid team returns proper ID and trimmed name."""
        team = register_team(self.teams, "  Red Comets  ")
        self.assertEqual(team["id"], "TM001")
        self.assertEqual(team["name"], "Red Comets")
        self.assertEqual(len(self.teams), 1)

    def test_reject_duplicate_casefolded_name(self) -> None:
        """Reject teams with identical names regardless of casing or extra whitespace."""
        register_team(self.teams, "Red Comets")
        with self.assertRaises(ValueError) as ctx:
            register_team(self.teams, "  red comets  ")
        self.assertIn("already registered", str(ctx.exception))
        self.assertEqual(len(self.teams), 1)

    def test_reject_short_name(self) -> None:
        """Reject team names with fewer than 2 characters after trimming."""
        with self.assertRaises(ValueError) as ctx:
            register_team(self.teams, " A ")
        self.assertIn("too short", str(ctx.exception))

    def test_reject_blank_name(self) -> None:
        """Reject completely empty or whitespace-only names."""
        with self.assertRaises(ValueError) as ctx:
            register_team(self.teams, "   ")
        self.assertIn("too short", str(ctx.exception))

    def test_reject_long_name(self) -> None:
        """Reject team names longer than 30 characters after trimming."""
        long_name = "X" * 31
        with self.assertRaises(ValueError) as ctx:
            register_team(self.teams, long_name)
        self.assertIn("too long", str(ctx.exception))

    def test_boundary_lengths_accepted(self) -> None:
        """Verify boundary lengths of exactly 2 and 30 characters are accepted."""
        team_min = register_team(self.teams, "AB")
        self.assertEqual(team_min["name"], "AB")
        team_max = register_team(self.teams, "A" * 30)
        self.assertEqual(len(team_max["name"]), 30)

    def test_reject_more_than_eight_teams(self) -> None:
        """Reject registration when maximum limit of 8 teams is reached."""
        for i in range(1, 9):
            register_team(self.teams, f"Team {i}")
        self.assertEqual(len(self.teams), 8)

        with self.assertRaises(ValueError) as ctx:
            register_team(self.teams, "Team 9")
        self.assertIn("capacity of 8 teams reached", str(ctx.exception))

    def test_find_team_by_id_and_fallback(self) -> None:
        """find_team_by_id returns the team or None; get_team_name falls back to ID."""
        t1 = register_team(self.teams, "Thunder")
        found = find_team_by_id(self.teams, t1["id"])
        self.assertIsNotNone(found)
        self.assertEqual(found["name"], "Thunder")

        missing = find_team_by_id(self.teams, "TM999")
        self.assertIsNone(missing)

        self.assertEqual(get_team_name(self.teams, t1["id"]), "Thunder")
        self.assertEqual(get_team_name(self.teams, "TM999"), "TM999")

    def test_list_teams_returns_copy(self) -> None:
        """list_teams returns a shallow copy that does not alter original list if mutated."""
        register_team(self.teams, "Phoenix")
        copy_teams = list_teams(self.teams)
        copy_teams.clear()
        self.assertEqual(len(self.teams), 1)


if __name__ == "__main__":
    unittest.main()
