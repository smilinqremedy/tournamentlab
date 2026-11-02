"""Unit tests for round-robin fixture generation combinatorics (Engineer A)."""

import unittest
from tournament.fixtures import generate_round_robin, get_fixture_by_id
from tournament.teams import register_team


class TestFixtureGeneration(unittest.TestCase):
    """Test suite for round-robin schedule generation rules and invariants."""

    def setUp(self) -> None:
        self.teams: list[dict] = []
        self.fixtures: list[dict] = []

    def _setup_teams(self, count: int) -> None:
        for i in range(1, count + 1):
            register_team(self.teams, f"Esports Team {i}")

    def test_reject_generation_fewer_than_four_teams(self) -> None:
        """Generation fails when fewer than 4 teams are registered."""
        self._setup_teams(3)
        with self.assertRaises(ValueError) as ctx:
            generate_round_robin(self.teams, self.fixtures)
        self.assertIn("at least 4 teams required", str(ctx.exception))

    def test_four_teams_produce_six_fixtures(self) -> None:
        """4 teams must produce exactly 4 * 3 / 2 = 6 fixtures."""
        self._setup_teams(4)
        fixtures = generate_round_robin(self.teams, self.fixtures)
        self.assertEqual(len(fixtures), 6)

    def test_six_teams_produce_fifteen_fixtures(self) -> None:
        """6 teams must produce exactly 6 * 5 / 2 = 15 fixtures."""
        self._setup_teams(6)
        fixtures = generate_round_robin(self.teams, self.fixtures)
        self.assertEqual(len(fixtures), 15)

    def test_eight_teams_produce_twenty_eight_fixtures(self) -> None:
        """8 teams must produce exactly 8 * 7 / 2 = 28 fixtures."""
        self._setup_teams(8)
        fixtures = generate_round_robin(self.teams, self.fixtures)
        self.assertEqual(len(fixtures), 28)

    def test_no_self_match(self) -> None:
        """No fixture can pit a team against itself."""
        self._setup_teams(5)
        fixtures = generate_round_robin(self.teams, self.fixtures)
        for f in fixtures:
            self.assertNotEqual(
                f["home_id"],
                f["away_id"],
                f"Self-match detected in fixture {f['id']}",
            )

    def test_no_duplicate_unordered_pair(self) -> None:
        """Every unordered pair must appear exactly once."""
        self._setup_teams(5)
        fixtures = generate_round_robin(self.teams, self.fixtures)
        seen_pairs: set[frozenset[str]] = set()

        for f in fixtures:
            pair = frozenset([f["home_id"], f["away_id"]])
            self.assertNotIn(
                pair,
                seen_pairs,
                f"Duplicate unordered pair detected for teams {pair}",
            )
            seen_pairs.add(pair)

        # Expected unique pairs for N=5: 5 * 4 / 2 = 10
        self.assertEqual(len(seen_pairs), 10)

    def test_fixtures_initialized_pending_with_none_scores(self) -> None:
        """All newly generated fixtures must have status 'pending' and None scores."""
        self._setup_teams(4)
        fixtures = generate_round_robin(self.teams, self.fixtures)
        for f in fixtures:
            self.assertEqual(f["status"], "pending")
            self.assertIsNone(f["home_score"])
            self.assertIsNone(f["away_score"])
            self.assertTrue(f["id"].startswith("M"))

    def test_reject_generating_twice(self) -> None:
        """Fixtures cannot be generated again if fixtures already exist."""
        self._setup_teams(4)
        generated = generate_round_robin(self.teams, self.fixtures)
        self.fixtures.extend(generated)

        with self.assertRaises(ValueError) as ctx:
            generate_round_robin(self.teams, self.fixtures)
        self.assertIn("already been generated", str(ctx.exception))

    def test_get_fixture_by_id(self) -> None:
        """Finds fixture by exact ID or returns None."""
        self._setup_teams(4)
        fixtures = generate_round_robin(self.teams, self.fixtures)
        f1 = get_fixture_by_id(fixtures, "M001")
        self.assertIsNotNone(f1)
        self.assertEqual(f1["id"], "M001")
        self.assertIsNone(get_fixture_by_id(fixtures, "M999"))


if __name__ == "__main__":
    unittest.main()
