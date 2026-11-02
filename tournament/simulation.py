"""Seeded, reproducible demo match simulation.

Engineer B ownership:
- Provides explicit demo simulation without secretly altering records
- Uses deterministic seed (default 42) for verifiable and reproducible testing
- Operates strictly on pending fixtures
"""

import random
from typing import Any

from tournament.fixtures import record_result


def simulate_demo_fixtures(
    fixtures: list[dict[str, Any]],
    seed: int = 42,
) -> int:
    """Simulate results for all currently pending fixtures using a reproducible seed.

    This function is ONLY called upon explicit user confirmation.
    It does not mutate already played fixtures.

    Args:
        fixtures: List of tournament fixtures.
        seed: Random seed for deterministic, reproducible outcomes.

    Returns:
        The count of fixtures newly simulated and marked 'played'.
    """
    rng = random.Random(seed)
    pending_fixtures = [f for f in fixtures if f.get("status") == "pending"]

    simulated_count = 0
    for fixture in pending_fixtures:
        # Generate esports round scores between 0 and 4
        home_score = rng.randint(0, 4)
        away_score = rng.randint(0, 4)

        record_result(fixtures, fixture["id"], home_score, away_score)
        simulated_count += 1

    return simulated_count
