"""Unit tests for JSON persistence, schema validation and referential integrity (Engineer A)."""

import json
import tempfile
import unittest
from pathlib import Path

from tournament.storage import SCHEMA_VERSION, load_tournament, save_tournament


class TestStorage(unittest.TestCase):
    """Test suite for persistence, schema enforcement, and bad input rejection."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        self.valid_teams = [
            {"id": "TM001", "name": "Thunder"},
            {"id": "TM002", "name": "Comets"},
            {"id": "TM003", "name": "Phoenix"},
            {"id": "TM004", "name": "Rockets"},
        ]
        self.valid_fixtures = [
            {
                "id": "M001",
                "home_id": "TM001",
                "away_id": "TM002",
                "status": "played",
                "home_score": 2,
                "away_score": 1,
            },
            {
                "id": "M002",
                "home_id": "TM003",
                "away_id": "TM004",
                "status": "pending",
                "home_score": None,
                "away_score": None,
            },
        ]

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_save_and_load_round_trip(self) -> None:
        """Valid tournament state is preserved faithfully across a save and load cycle."""
        file_path = self.temp_path / "tournament.json"
        save_tournament(file_path, self.valid_teams, self.valid_fixtures)

        loaded_teams, loaded_fixtures = load_tournament(file_path)
        self.assertEqual(loaded_teams, self.valid_teams)
        self.assertEqual(loaded_fixtures, self.valid_fixtures)

    def test_reject_missing_file(self) -> None:
        """Loading a non-existent file raises FileNotFoundError."""
        missing_path = self.temp_path / "does_not_exist.json"
        with self.assertRaises(FileNotFoundError):
            load_tournament(missing_path)

    def test_reject_corrupt_json_syntax(self) -> None:
        """Loading a file with broken JSON syntax raises ValueError."""
        corrupt_path = self.temp_path / "corrupt.json"
        corrupt_path.write_text("{ unquoted_key: 123, }", encoding="utf-8")
        with self.assertRaises(ValueError) as ctx:
            load_tournament(corrupt_path)
        self.assertIn("Invalid JSON syntax", str(ctx.exception))

    def test_reject_unsupported_schema_version(self) -> None:
        """Loading an incompatible schema version raises ValueError."""
        bad_version_path = self.temp_path / "bad_version.json"
        payload = {
            "schema_version": 99,
            "teams": self.valid_teams,
            "fixtures": self.valid_fixtures,
        }
        bad_version_path.write_text(json.dumps(payload), encoding="utf-8")

        with self.assertRaises(ValueError) as ctx:
            load_tournament(bad_version_path)
        self.assertIn("Unsupported schema version: 99", str(ctx.exception))

    def test_reject_phantom_team_reference(self) -> None:
        """Fixtures referencing non-existent team IDs must be rejected (referential integrity)."""
        bad_ref_path = self.temp_path / "bad_ref.json"
        bad_fixtures = [
            {
                "id": "M001",
                "home_id": "TM001",
                "away_id": "TM999",  # Phantom team!
                "status": "pending",
                "home_score": None,
                "away_score": None,
            }
        ]
        payload = {
            "schema_version": SCHEMA_VERSION,
            "teams": self.valid_teams,
            "fixtures": bad_fixtures,
        }
        bad_ref_path.write_text(json.dumps(payload), encoding="utf-8")

        with self.assertRaises(ValueError) as ctx:
            load_tournament(bad_ref_path)
        self.assertIn("Referential integrity failure", str(ctx.exception))
        self.assertIn("TM999", str(ctx.exception))

    def test_reject_duplicate_team_name_on_load(self) -> None:
        """Saved files containing duplicate team names must be rejected."""
        dup_team_path = self.temp_path / "dup_team.json"
        dup_teams = [
            {"id": "TM001", "name": "Thunder"},
            {"id": "TM002", "name": "thunder"},  # duplicate casefold!
        ]
        payload = {
            "schema_version": SCHEMA_VERSION,
            "teams": dup_teams,
            "fixtures": [],
        }
        dup_team_path.write_text(json.dumps(payload), encoding="utf-8")

        with self.assertRaises(ValueError) as ctx:
            load_tournament(dup_team_path)
        self.assertIn("Duplicate team name", str(ctx.exception))

    def test_reject_self_match_on_load(self) -> None:
        """Fixtures pairing a team against itself must be rejected."""
        self_match_path = self.temp_path / "self_match.json"
        fixtures = [
            {
                "id": "M001",
                "home_id": "TM001",
                "away_id": "TM001",  # Self match!
                "status": "pending",
                "home_score": None,
                "away_score": None,
            }
        ]
        payload = {
            "schema_version": SCHEMA_VERSION,
            "teams": self.valid_teams,
            "fixtures": fixtures,
        }
        self_match_path.write_text(json.dumps(payload), encoding="utf-8")

        with self.assertRaises(ValueError) as ctx:
            load_tournament(self_match_path)
        self.assertIn("Invalid self-match", str(ctx.exception))

    def test_reject_duplicate_fixture_pair_on_load(self) -> None:
        """Reverse duplicate or repeated fixtures must be rejected."""
        dup_path = self.temp_path / "dup_fixture.json"
        fixtures = [
            {
                "id": "M001",
                "home_id": "TM001",
                "away_id": "TM002",
                "status": "pending",
                "home_score": None,
                "away_score": None,
            },
            {
                "id": "M002",
                "home_id": "TM002",  # Reverse pair!
                "away_id": "TM001",
                "status": "pending",
                "home_score": None,
                "away_score": None,
            },
        ]
        payload = {
            "schema_version": SCHEMA_VERSION,
            "teams": self.valid_teams,
            "fixtures": fixtures,
        }
        dup_path.write_text(json.dumps(payload), encoding="utf-8")

        with self.assertRaises(ValueError) as ctx:
            load_tournament(dup_path)
        self.assertIn("Duplicate fixture pair detected", str(ctx.exception))

    def test_reject_boolean_scores_on_load(self) -> None:
        """Ensure True or False is rejected as an integer score in JSON."""
        bool_score_path = self.temp_path / "bool_score.json"
        fixtures = [
            {
                "id": "M001",
                "home_id": "TM001",
                "away_id": "TM002",
                "status": "played",
                "home_score": True,  # JSON boolean!
                "away_score": 0,
            }
        ]
        payload = {
            "schema_version": SCHEMA_VERSION,
            "teams": self.valid_teams,
            "fixtures": fixtures,
        }
        bool_score_path.write_text(json.dumps(payload), encoding="utf-8")

        with self.assertRaises(ValueError) as ctx:
            load_tournament(bool_score_path)
        self.assertIn("invalid home score", str(ctx.exception))

    def test_reject_pending_fixture_with_scores_on_load(self) -> None:
        """Pending fixtures having non-None scores must be rejected."""
        inconsistent_path = self.temp_path / "inconsistent.json"
        fixtures = [
            {
                "id": "M001",
                "home_id": "TM001",
                "away_id": "TM002",
                "status": "pending",
                "home_score": 2,  # Should be None!
                "away_score": None,
            }
        ]
        payload = {
            "schema_version": SCHEMA_VERSION,
            "teams": self.valid_teams,
            "fixtures": fixtures,
        }
        inconsistent_path.write_text(json.dumps(payload), encoding="utf-8")

        with self.assertRaises(ValueError) as ctx:
            load_tournament(inconsistent_path)
        self.assertIn("Pending fixture 'M001' cannot have non-None scores", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
