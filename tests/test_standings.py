"""Unit tests for standings calculation, tie-break sorting and champion status (Engineer B)."""

import unittest
from tournament.standings import (
    compute_standings,
    get_tournament_status,
    verify_league_invariants,
)


class TestStandings(unittest.TestCase):
    """Test suite for standings aggregation, tie-breaking, and tournament status."""

    def setUp(self) -> None:
        self.teams = [
            {"id": "TM001", "name": "Red Comets"},
            {"id": "TM002", "name": "Blue Sharks"},
            {"id": "TM003", "name": "Green Vipers"},
        ]

    def test_points_awarded_correctly(self) -> None:
        """3 points for win, 0 for loss; 1 point each for draw."""
        fixtures = [
            {
                "id": "M001",
                "home_id": "TM001",
                "away_id": "TM002",
                "status": "played",
                "home_score": 3,
                "away_score": 1,
            },
            {
                "id": "M002",
                "home_id": "TM002",
                "away_id": "TM003",
                "status": "played",
                "home_score": 2,
                "away_score": 2,
            },
        ]
        standings = compute_standings(self.teams, fixtures)

        by_id = {r["team_id"]: r for r in standings}
        # Red: 1 game, 1 win, 3 pts, GF=3, GA=1, GD=+2
        self.assertEqual(by_id["TM001"]["points"], 3)
        self.assertEqual(by_id["TM001"]["wins"], 1)
        self.assertEqual(by_id["TM001"]["goal_difference"], 2)

        # Blue: 2 games, 0 wins, 1 draw, 1 loss, 1 pt, GF=3, GA=5, GD=-2
        self.assertEqual(by_id["TM002"]["points"], 1)
        self.assertEqual(by_id["TM002"]["draws"], 1)
        self.assertEqual(by_id["TM002"]["losses"], 1)
        self.assertEqual(by_id["TM002"]["goal_difference"], -2)

        # Green: 1 game, 0 wins, 1 draw, 0 loss, 1 pt, GF=2, GA=2, GD=0
        self.assertEqual(by_id["TM003"]["points"], 1)
        self.assertEqual(by_id["TM003"]["draws"], 1)
        self.assertEqual(by_id["TM003"]["goal_difference"], 0)

    def test_stage_zero_diagnostic_scenario(self) -> None:
        """Verify the exact diagnostic match outcomes from Stage 0:
        Red 2-0 Blue, Blue 1-1 Green, Red 0-1 Green.
        Expected Champion: Green (4 pts), followed by Red (3 pts), Blue (1 pt).
        """
        diagnostic_fixtures = [
            {
                "id": "M001",
                "home_id": "TM001",
                "away_id": "TM002",
                "status": "played",
                "home_score": 2,
                "away_score": 0,
            },
            {
                "id": "M002",
                "home_id": "TM002",
                "away_id": "TM003",
                "status": "played",
                "home_score": 1,
                "away_score": 1,
            },
            {
                "id": "M003",
                "home_id": "TM001",
                "away_id": "TM003",
                "status": "played",
                "home_score": 0,
                "away_score": 1,
            },
        ]
        standings = compute_standings(self.teams, diagnostic_fixtures)

        self.assertEqual(len(standings), 3)
        self.assertEqual(standings[0]["name"], "Green Vipers")
        self.assertEqual(standings[0]["points"], 4)
        self.assertEqual(standings[0]["goal_difference"], 1)

        self.assertEqual(standings[1]["name"], "Red Comets")
        self.assertEqual(standings[1]["points"], 3)
        self.assertEqual(standings[1]["goal_difference"], 1)

        self.assertEqual(standings[2]["name"], "Blue Sharks")
        self.assertEqual(standings[2]["points"], 1)
        self.assertEqual(standings[2]["goal_difference"], -2)

        # Verify invariants
        valid, msg = verify_league_invariants(standings, diagnostic_fixtures)
        self.assertTrue(valid, msg)

    def test_four_level_tie_break_hierarchy(self) -> None:
        """Craft 4 teams to rigorously test:
        1. Points DESC
        2. Goal Difference DESC (equal points)
        3. Goals For DESC (equal points and GD)
        4. Name ASC (equal points, GD, and GF)
        """
        teams = [
            {"id": "TM001", "name": "Bravo"},
            {"id": "TM002", "name": "Alpha"},
            {"id": "TM003", "name": "Charlie"},
            {"id": "TM004", "name": "Delta"},
        ]
        # Fixtures crafted such that:
        # - Charlie: 6 pts (Top by points)
        # - Delta: 3 pts, GD: +2 (Top among 3-pointers by GD)
        # - Alpha & Bravo: both 3 pts, GD: 0.
        #   Alpha: GF=3, GA=3
        #   Bravo: GF=3, GA=3 (Tied on points, GD, GF -> Broken by name: Alpha before Bravo!)
        fixtures = [
            # Charlie wins twice -> 6 pts
            {"id": "M001", "home_id": "TM003", "away_id": "TM001", "status": "played", "home_score": 1, "away_score": 0},
            {"id": "M002", "home_id": "TM003", "away_id": "TM002", "status": "played", "home_score": 1, "away_score": 0},
            # Delta wins once with +2 GD
            {"id": "M003", "home_id": "TM004", "away_id": "TM003", "status": "played", "home_score": 3, "away_score": 1},
            # Alpha scores 3, concedes 2 against Delta
            {"id": "M004", "home_id": "TM002", "away_id": "TM004", "status": "played", "home_score": 3, "away_score": 2},
            # Bravo scores 3, concedes 2 against Delta
            {"id": "M005", "home_id": "TM001", "away_id": "TM004", "status": "played", "home_score": 3, "away_score": 2},
        ]
        standings = compute_standings(teams, fixtures)

        # 1st: Charlie (6 pts)
        self.assertEqual(standings[0]["name"], "Charlie")
        self.assertEqual(standings[0]["points"], 6)

        # 2nd: Alpha (3 pts, GD=0, GF=3, name 'Alpha' < 'Bravo')
        # Wait, Delta has played 3 games:
        # vs TM003: W 3-1 (GF+3, GA+1) -> pts 3
        # vs TM002: L 2-3 (GF+2, GA+3)
        # vs TM001: L 2-3 (GF+2, GA+3)
        # Total Delta: GF=7, GA=7, GD=0, pts=3
        # Let's inspect Alpha:
        # vs TM003: L 0-1 (GF 0, GA 1)
        # vs TM004: W 3-2 (GF 3, GA 2)
        # Total Alpha: pts=3, GF=3, GA=3, GD=0
        # Total Bravo:
        # vs TM003: L 0-1 (GF 0, GA 1)
        # vs TM004: W 3-2 (GF 3, GA 2)
        # Total Bravo: pts=3, GF=3, GA=3, GD=0
        # Delta has GF=7, so Delta has higher GF than Alpha/Bravo!
        # Delta is 2nd (pts=3, GD=0, GF=7).
        # Alpha and Bravo both have pts=3, GD=0, GF=3.
        # Alpha must rank before Bravo because 'alpha' < 'bravo'!
        self.assertEqual(standings[1]["name"], "Delta")
        self.assertEqual(standings[1]["goals_for"], 7)

        self.assertEqual(standings[2]["name"], "Alpha")
        self.assertEqual(standings[3]["name"], "Bravo")

    def test_champion_shown_only_when_all_fixtures_played(self) -> None:
        """Tournament is 'in progress' if any fixture is pending; 'complete' when all played."""
        fixtures = [
            {"id": "M001", "home_id": "TM001", "away_id": "TM002", "status": "played", "home_score": 2, "away_score": 0},
            {"id": "M002", "home_id": "TM002", "away_id": "TM003", "status": "pending", "home_score": None, "away_score": None},
        ]
        standings = compute_standings(self.teams, fixtures)

        status, champion = get_tournament_status(fixtures, standings)
        self.assertEqual(status, "in progress")
        self.assertIsNone(champion)

        # Complete the pending match
        fixtures[1]["status"] = "played"
        fixtures[1]["home_score"] = 0
        fixtures[1]["away_score"] = 0

        standings = compute_standings(self.teams, fixtures)
        status, champion = get_tournament_status(fixtures, standings)
        self.assertEqual(status, "complete")
        self.assertIsNotNone(champion)
        self.assertEqual(champion["team_id"], "TM001")


if __name__ == "__main__":
    unittest.main()
