"""Unit tests for score validation and atomic match result recording (Engineer B)."""

import unittest
from tournament.fixtures import record_result, validate_score


class TestScoring(unittest.TestCase):
    """Test suite for score validation and atomic result mutations."""

    def setUp(self) -> None:
        self.fixtures = [
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
                "home_id": "TM003",
                "away_id": "TM004",
                "status": "played",
                "home_score": 1,
                "away_score": 0,
            },
        ]

    def test_validate_score_valid_integers(self) -> None:
        """Nonnegative integers are accepted and returned as ints."""
        self.assertEqual(validate_score(0), 0)
        self.assertEqual(validate_score(5), 5)
        self.assertEqual(validate_score(100), 100)

    def test_reject_boolean_scores(self) -> None:
        """Crucial Python edge case: True and False must be rejected, not treated as 1 and 0."""
        with self.assertRaises(ValueError) as ctx:
            validate_score(True)
        self.assertIn("score must be an integer, not bool", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            validate_score(False)
        self.assertIn("score must be an integer, not bool", str(ctx.exception))

    def test_reject_negative_scores(self) -> None:
        """Scores less than 0 must be rejected."""
        with self.assertRaises(ValueError) as ctx:
            validate_score(-1)
        self.assertIn("cannot be negative", str(ctx.exception))

    def test_reject_float_scores(self) -> None:
        """Floating point numbers must be rejected."""
        with self.assertRaises(ValueError) as ctx:
            validate_score(2.5)
        self.assertIn("score must be an integer, not float", str(ctx.exception))

    def test_reject_string_scores(self) -> None:
        """String numbers must be rejected by validate_score."""
        with self.assertRaises(ValueError) as ctx:
            validate_score("3")
        self.assertIn("score must be an integer, not str", str(ctx.exception))

    def test_record_result_success(self) -> None:
        """Recording a valid score marks fixture as played and updates scores."""
        updated = record_result(self.fixtures, "M001", 3, 2)
        self.assertEqual(updated["status"], "played")
        self.assertEqual(updated["home_score"], 3)
        self.assertEqual(updated["away_score"], 2)

    def test_reject_unknown_fixture_id(self) -> None:
        """Submitting score for non-existent fixture raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            record_result(self.fixtures, "M999", 1, 0)
        self.assertIn("fixture 'M999' not found", str(ctx.exception))

    def test_reject_duplicate_result_submission(self) -> None:
        """Submitting score for an already played fixture is rejected."""
        with self.assertRaises(ValueError) as ctx:
            record_result(self.fixtures, "M002", 2, 2)
        self.assertIn("already been played", str(ctx.exception))
        self.assertIn("Duplicate score submissions are prohibited", str(ctx.exception))

    def test_atomic_update_on_partial_failure(self) -> None:
        """If home score is valid but away score is invalid, fixture remains completely untouched."""
        with self.assertRaises(ValueError):
            record_result(self.fixtures, "M001", 3, -5)

        target = self.fixtures[0]
        self.assertEqual(target["status"], "pending")
        self.assertIsNone(target["home_score"])
        self.assertIsNone(target["away_score"])


if __name__ == "__main__":
    unittest.main()
