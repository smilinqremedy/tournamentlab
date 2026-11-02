"""Unit tests for demo fixture simulation reproducibility (Engineer B)."""

import unittest
from tournament.fixtures import generate_round_robin
from tournament.simulation import simulate_demo_fixtures
from tournament.standings import compute_standings, get_tournament_status
from tournament.teams import register_team


class TestSimulation(unittest.TestCase):
    """Test suite for seeded simulation reproducibility and safety."""

    def setUp(self) -> None:
        self.teams: list[dict] = []
        for name in ["Thunder", "Comets", "Phoenix", "Rockets"]:
            register_team(self.teams, name)
        self.fixtures = generate_round_robin(self.teams, [])

    def test_reproducible_simulation_with_seed(self) -> None:
        """Simulations with identical seeds produce identical scores and standings."""
        fixtures_copy = [dict(f) for f in self.fixtures]

        count1 = simulate_demo_fixtures(self.fixtures, seed=42)
        count2 = simulate_demo_fixtures(fixtures_copy, seed=42)

        self.assertEqual(count1, 6)
        self.assertEqual(count2, 6)

        standings1 = compute_standings(self.teams, self.fixtures)
        standings2 = compute_standings(self.teams, fixtures_copy)

        self.assertEqual(standings1, standings2)

    def test_simulation_does_not_mutate_already_played_fixtures(self) -> None:
        """Played fixtures maintain their custom results and are not re-simulated."""
        # Manually play M001
        self.fixtures[0]["status"] = "played"
        self.fixtures[0]["home_score"] = 99
        self.fixtures[0]["away_score"] = 99

        simulated_count = simulate_demo_fixtures(self.fixtures, seed=123)
        self.assertEqual(simulated_count, 5)  # 6 total - 1 already played = 5

        # Verify M001 was untouched
        self.assertEqual(self.fixtures[0]["home_score"], 99)
        self.assertEqual(self.fixtures[0]["away_score"], 99)

        # All matches are now played
        status, champion = get_tournament_status(self.fixtures, compute_standings(self.teams, self.fixtures))
        self.assertEqual(status, "complete")
        self.assertIsNotNone(champion)


if __name__ == "__main__":
    unittest.main()
