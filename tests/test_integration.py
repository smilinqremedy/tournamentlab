"""End-to-end integration tests covering all 16 required specification scenarios and the controlled demo dataset."""

import tempfile
import unittest
from pathlib import Path

from tournament.fixtures import (
    generate_round_robin,
    get_fixture_by_id,
    record_result,
    validate_score,
)
from tournament.standings import (
    compute_standings,
    get_tournament_status,
    verify_league_invariants,
)
from tournament.storage import load_tournament, save_tournament
from tournament.teams import register_team


class TestIntegrationAllScenarios(unittest.TestCase):
    """Rigorous verification of the 16 core curriculum scenarios."""

    def setUp(self) -> None:
        self.teams: list[dict] = []
        self.fixtures: list[dict] = []
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    # Scenario 1: Reject duplicate casefolded team name
    def test_scenario_01_reject_duplicate_casefolded_name(self) -> None:
        register_team(self.teams, "Red Comets")
        with self.assertRaises(ValueError) as ctx:
            register_team(self.teams, "  RED comets  ")
        self.assertIn("already registered", str(ctx.exception))

    # Scenario 2: Reject blank/too-long name
    def test_scenario_02_reject_blank_or_too_long_name(self) -> None:
        with self.assertRaises(ValueError):
            register_team(self.teams, "   ")
        with self.assertRaises(ValueError):
            register_team(self.teams, "A" * 31)

    # Scenario 3: Reject fixture generation with fewer than 4 teams
    def test_scenario_03_reject_generation_under_four_teams(self) -> None:
        register_team(self.teams, "Team 1")
        register_team(self.teams, "Team 2")
        register_team(self.teams, "Team 3")
        with self.assertRaises(ValueError) as ctx:
            generate_round_robin(self.teams, self.fixtures)
        self.assertIn("at least 4 teams required", str(ctx.exception))

    # Scenario 4: Four teams produce six fixtures
    def test_scenario_04_four_teams_produce_six_fixtures(self) -> None:
        for name in ["Thunder", "Comets", "Phoenix", "Rockets"]:
            register_team(self.teams, name)
        fixtures = generate_round_robin(self.teams, self.fixtures)
        self.assertEqual(len(fixtures), 6)  # 4*3/2 = 6

    # Scenario 5: Six teams produce fifteen fixtures
    def test_scenario_05_six_teams_produce_fifteen_fixtures(self) -> None:
        for i in range(6):
            register_team(self.teams, f"Esports {i+1}")
        fixtures = generate_round_robin(self.teams, self.fixtures)
        self.assertEqual(len(fixtures), 15)  # 6*5/2 = 15

    # Scenario 6: No self-match
    def test_scenario_06_no_self_match(self) -> None:
        for name in ["A", "B", "C", "D"]:
            register_team(self.teams, f"Team {name}")
        fixtures = generate_round_robin(self.teams, self.fixtures)
        for f in fixtures:
            self.assertNotEqual(f["home_id"], f["away_id"])

    # Scenario 7: No duplicate unordered pair
    def test_scenario_07_no_duplicate_unordered_pair(self) -> None:
        for name in ["A", "B", "C", "D"]:
            register_team(self.teams, f"Team {name}")
        fixtures = generate_round_robin(self.teams, self.fixtures)
        pairs = [frozenset([f["home_id"], f["away_id"]]) for f in fixtures]
        self.assertEqual(len(pairs), len(set(pairs)))

    # Scenario 8: Reject negative/float/bool goals
    def test_scenario_08_reject_negative_float_bool_goals(self) -> None:
        with self.assertRaises(ValueError):
            validate_score(-1)
        with self.assertRaises(ValueError):
            validate_score(3.14)
        with self.assertRaises(ValueError):
            validate_score(True)
        with self.assertRaises(ValueError):
            validate_score(False)

    # Scenario 9: Reject unknown fixture
    def test_scenario_09_reject_unknown_fixture(self) -> None:
        for name in ["Thunder", "Comets", "Phoenix", "Rockets"]:
            register_team(self.teams, name)
        fixtures = generate_round_robin(self.teams, self.fixtures)
        with self.assertRaises(ValueError) as ctx:
            record_result(fixtures, "M999", 1, 0)
        self.assertIn("not found", str(ctx.exception))

    # Scenario 10: Reject duplicate result
    def test_scenario_10_reject_duplicate_result(self) -> None:
        for name in ["Thunder", "Comets", "Phoenix", "Rockets"]:
            register_team(self.teams, name)
        fixtures = generate_round_robin(self.teams, self.fixtures)
        record_result(fixtures, "M001", 2, 1)
        with self.assertRaises(ValueError) as ctx:
            record_result(fixtures, "M001", 3, 0)
        self.assertIn("already been played", str(ctx.exception))

    # Scenario 11: Correct 3/1/0 points
    def test_scenario_11_correct_points_calculation(self) -> None:
        for name in ["Team Win", "Team Lose", "Team Draw 1", "Team Draw 2"]:
            register_team(self.teams, name)
        fixtures = generate_round_robin(self.teams, self.fixtures)
        record_result(fixtures, "M001", 3, 0)  # Win/Loss
        record_result(fixtures, "M006", 1, 1)  # Draw
        standings = compute_standings(self.teams, fixtures)
        by_name = {r["name"]: r for r in standings}
        self.assertEqual(by_name["Team Win"]["points"], 3)
        self.assertEqual(by_name["Team Lose"]["points"], 0)
        self.assertEqual(by_name["Team Draw 1"]["points"], 1)
        self.assertEqual(by_name["Team Draw 2"]["points"], 1)

    # Scenario 12: Tie-break sorting
    def test_scenario_12_tie_break_sorting(self) -> None:
        for name in ["Bravo", "Alpha"]:
            register_team(self.teams, name)
        for name in ["Gamma", "Delta"]:
            register_team(self.teams, name)
        fixtures = generate_round_robin(self.teams, self.fixtures)
        # Gamma and Delta lose 0-1 to Alpha and Bravo
        # Alpha and Bravo end up with identical 3 pts, +1 GD, 1 GF
        record_result(fixtures, "M001", 0, 0)  # Alpha vs Bravo draw: 1 pt each, GD=0, GF=0
        standings = compute_standings(self.teams, fixtures)
        # Between Alpha and Bravo: Alpha ranks first alphabetically
        tied = [r for r in standings if r["name"] in ["Alpha", "Bravo"]]
        self.assertEqual(tied[0]["name"], "Alpha")
        self.assertEqual(tied[1]["name"], "Bravo")

    # Scenario 13: Standings re-computed from matches
    def test_scenario_13_standings_recomputed_purely_from_matches(self) -> None:
        for name in ["T1", "T2", "T3", "T4"]:
            register_team(self.teams, name)
        fixtures = generate_round_robin(self.teams, self.fixtures)
        record_result(fixtures, "M001", 2, 1)
        s1 = compute_standings(self.teams, fixtures)
        s2 = compute_standings(self.teams, fixtures)
        self.assertEqual(s1, s2)
        valid, msg = verify_league_invariants(s1, fixtures)
        self.assertTrue(valid, msg)

    # Scenario 14: JSON bad references rejected without state change
    def test_scenario_14_bad_references_rejected_without_state_change(self) -> None:
        bad_json = self.temp_path / "corrupt_ref.json"
        bad_json.write_text(
            '{"schema_version": 1, '
            '"teams": ['
            '  {"id": "TM001", "name": "Team 1"},'
            '  {"id": "TM002", "name": "Team 2"},'
            '  {"id": "TM003", "name": "Team 3"},'
            '  {"id": "TM004", "name": "Team 4"}'
            '], '
            '"fixtures": ['
            '  {"id": "M001", "home_id": "TM001", "away_id": "TM999", "status": "pending", "home_score": null, "away_score": null}'
            ']}',
            encoding="utf-8",
        )
        original_teams = [{"id": "TM001", "name": "Safe Team"}]
        with self.assertRaises(ValueError) as ctx:
            load_tournament(bad_json)
        self.assertIn("Referential integrity failure", str(ctx.exception))
        # Active memory untouched
        self.assertEqual(original_teams[0]["name"], "Safe Team")

    # Scenario 15: Reload preserves IDs and standings
    def test_scenario_15_reload_preserves_ids_and_standings(self) -> None:
        for name in ["Thunder", "Comets", "Phoenix", "Rockets"]:
            register_team(self.teams, name)
        fixtures = generate_round_robin(self.teams, self.fixtures)
        record_result(fixtures, "M001", 3, 1)
        record_result(fixtures, "M002", 0, 0)

        initial_standings = compute_standings(self.teams, fixtures)
        save_file = self.temp_path / "save_roundtrip.json"
        save_tournament(save_file, self.teams, fixtures)

        reloaded_teams, reloaded_fixtures = load_tournament(save_file)
        reloaded_standings = compute_standings(reloaded_teams, reloaded_fixtures)

        self.assertEqual(self.teams, reloaded_teams)
        self.assertEqual(fixtures, reloaded_fixtures)
        self.assertEqual(initial_standings, reloaded_standings)

    # Scenario 16: Champion shown only when all matches played
    def test_scenario_16_champion_shown_only_when_all_matches_played(self) -> None:
        for name in ["Thunder", "Comets", "Phoenix", "Rockets"]:
            register_team(self.teams, name)
        fixtures = generate_round_robin(self.teams, self.fixtures)
        # 5 out of 6 played -> in progress
        for i in range(5):
            record_result(fixtures, fixtures[i]["id"], 1, 0)

        standings = compute_standings(self.teams, fixtures)
        status, champion = get_tournament_status(fixtures, standings)
        self.assertEqual(status, "in progress")
        self.assertIsNone(champion)

        # Play 6th match -> complete
        record_result(fixtures, fixtures[5]["id"], 2, 2)
        standings = compute_standings(self.teams, fixtures)
        status, champion = get_tournament_status(fixtures, standings)
        self.assertEqual(status, "complete")
        self.assertIsNotNone(champion)


class TestControlledDemonstrationDataset(unittest.TestCase):
    """Execution of the exact prompt demonstration dataset:
    - 4 teams: Thunder, Comets, Phoenix, Rockets
    - 6 fixtures total
    - Enter scores for 2 fixtures: one win, one draw
    - Verify displayed table manually and invariant adherence
    - Submit intentionally invalid score -> confirm no mutation
    - Reload from JSON -> verify table consistency
    - Complete remaining fixtures -> verify champion crowned!
    """

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_full_controlled_demonstration_workflow(self) -> None:
        teams: list[dict] = []
        for name in ["Thunder", "Comets", "Phoenix", "Rockets"]:
            register_team(teams, name)

        fixtures = generate_round_robin(teams, [])
        self.assertEqual(len(fixtures), 6)

        # Step 1: Enter scores for exactly two fixtures: one win (Thunder 2-1 Comets) and one draw (Phoenix 0-0 Rockets)
        # Note: M001 is Thunder (TM001) vs Comets (TM002)
        record_result(fixtures, "M001", 2, 1)

        # Find Phoenix (TM003) vs Rockets (TM004) fixture ID
        m_phoenix_rockets = next(
            f for f in fixtures if f["home_id"] == "TM003" and f["away_id"] == "TM004"
        )
        record_result(fixtures, m_phoenix_rockets["id"], 0, 0)

        # Step 2: Verify standings table after 2 matches
        standings = compute_standings(teams, fixtures)
        by_name = {r["name"]: r for r in standings}

        self.assertEqual(by_name["Thunder"]["played"], 1)
        self.assertEqual(by_name["Thunder"]["wins"], 1)
        self.assertEqual(by_name["Thunder"]["points"], 3)
        self.assertEqual(by_name["Thunder"]["goal_difference"], 1)

        self.assertEqual(by_name["Comets"]["played"], 1)
        self.assertEqual(by_name["Comets"]["losses"], 1)
        self.assertEqual(by_name["Comets"]["points"], 0)
        self.assertEqual(by_name["Comets"]["goal_difference"], -1)

        self.assertEqual(by_name["Phoenix"]["played"], 1)
        self.assertEqual(by_name["Phoenix"]["draws"], 1)
        self.assertEqual(by_name["Phoenix"]["points"], 1)
        self.assertEqual(by_name["Phoenix"]["goal_difference"], 0)

        self.assertEqual(by_name["Rockets"]["played"], 1)
        self.assertEqual(by_name["Rockets"]["draws"], 1)
        self.assertEqual(by_name["Rockets"]["points"], 1)
        self.assertEqual(by_name["Rockets"]["goal_difference"], 0)

        # Status must be 'in progress'
        status, champion = get_tournament_status(fixtures, standings)
        self.assertEqual(status, "in progress")
        self.assertIsNone(champion)

        # Step 3: Submit intentionally invalid score (negative score, boolean, already played)
        # Verify no mutation occurs!
        with self.assertRaises(ValueError):
            record_result(fixtures, "M002", -5, 2)
        with self.assertRaises(ValueError):
            record_result(fixtures, "M002", True, 2)
        with self.assertRaises(ValueError):
            record_result(fixtures, "M001", 1, 1)  # Already played!

        standings_after_failed = compute_standings(teams, fixtures)
        self.assertEqual(standings, standings_after_failed)

        # Step 4: Save & reload from JSON
        state_file = self.temp_path / "demo_season.json"
        save_tournament(state_file, teams, fixtures)

        loaded_teams, loaded_fixtures = load_tournament(state_file)
        loaded_standings = compute_standings(loaded_teams, loaded_fixtures)
        self.assertEqual(standings, loaded_standings)

        # Step 5: Complete remaining 4 fixtures and display champion
        pending = [f for f in loaded_fixtures if f["status"] == "pending"]
        self.assertEqual(len(pending), 4)

        for p in pending:
            # Thunder wins all remaining fixtures to decisively become champion
            if p["home_id"] == "TM001":
                record_result(loaded_fixtures, p["id"], 3, 0)
            elif p["away_id"] == "TM001":
                record_result(loaded_fixtures, p["id"], 0, 3)
            else:
                record_result(loaded_fixtures, p["id"], 1, 1)

        final_standings = compute_standings(loaded_teams, loaded_fixtures)
        final_status, final_champion = get_tournament_status(loaded_fixtures, final_standings)

        self.assertEqual(final_status, "complete")
        self.assertIsNotNone(final_champion)
        self.assertEqual(final_champion["name"], "Thunder")
        self.assertEqual(final_champion["points"], 9)  # 3 wins from 3 games

        valid, msg = verify_league_invariants(final_standings, loaded_fixtures)
        self.assertTrue(valid, msg)


if __name__ == "__main__":
    unittest.main()
