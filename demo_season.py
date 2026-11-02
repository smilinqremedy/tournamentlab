"""Demonstration script showcasing the exact controlled demonstration dataset from the curriculum."""

import json
from pathlib import Path

from tournament.fixtures import (
    generate_round_robin,
    get_fixture_by_id,
    record_result,
)
from tournament.standings import (
    compute_standings,
    get_tournament_status,
    verify_league_invariants,
)
from tournament.storage import load_tournament, save_tournament
from tournament.teams import register_team


def run_controlled_demo():
    print("=" * 76)
    print("    TOURNAMENTLAB: CONTROLLED DEMONSTRATION DATASET WALKTHROUGH")
    print("=" * 76)

    # 1. Register 4 Teams
    teams = []
    for name in ["Thunder", "Comets", "Phoenix", "Rockets"]:
        register_team(teams, name)
    print(f"\n[1] Registered {len(teams)} Teams:")
    for t in teams:
        print(f"    - {t['id']}: {t['name']}")

    # 2. Generate 6 Round-Robin Fixtures
    fixtures = generate_round_robin(teams, [])
    print(f"\n[2] Generated {len(fixtures)} Round-Robin Fixtures (Expected 4*3/2 = 6):")
    for f in fixtures:
        print(f"    - {f['id']}: {f['home_id']} vs {f['away_id']} [{f['status']}]")

    # 3. Play 2 Fixtures: One Win, One Draw
    # M001: Thunder (TM001) 2 - 1 Comets (TM002)
    record_result(fixtures, "M001", 2, 1)
    # Find Phoenix (TM003) vs Rockets (TM004)
    m_draw = next(f for f in fixtures if f["home_id"] == "TM003" and f["away_id"] == "TM004")
    record_result(fixtures, m_draw["id"], 0, 0)
    print("\n[3] Recorded 2 Match Results:")
    print("    - M001: Thunder 2 - 1 Comets (Win: Thunder)")
    print(f"    - {m_draw['id']}: Phoenix 0 - 0 Rockets (Draw)")

    # 4. Display Standings (In Progress)
    standings = compute_standings(teams, fixtures)
    status, champ = get_tournament_status(fixtures, standings)
    print("\n[4] Standings Table (After 2 Matches):")
    print("+-----+--------+----------------------+----+----+----+----+----+----+----+-----+")
    print("| Pos | ID     | Team Name            | P  | W  | D  | L  | GF | GA | GD | PTS |")
    print("+-----+--------+----------------------+----+----+----+----+----+----+----+-----+")
    for idx, r in enumerate(standings, start=1):
        gd_str = f"{r['goal_difference']:+d}"
        print(
            f"| {idx:<3} | {r['team_id']:<6} | {r['name'][:20]:<20} | "
            f"{r['played']:<2} | {r['wins']:<2} | {r['draws']:<2} | {r['losses']:<2} | "
            f"{r['goals_for']:<2} | {r['goals_against']:<2} | {gd_str:>3} | {r['points']:<3} |"
        )
    print("+-----+--------+----------------------+----+----+----+----+----+----+----+-----+")
    print(f"Tournament Status: [{status.upper()}] (Champion: {champ})")

    # 5. Submit Intentionally Invalid Score & Confirm No Mutation
    print("\n[5] Attempting Invalid Score Submissions:")
    for test_desc, fid, h, a in [
        ("Negative score (-5)", "M002", -5, 1),
        ("Boolean score (True)", "M002", True, 1),
        ("Duplicate completed match submission", "M001", 1, 1),
    ]:
        try:
            record_result(fixtures, fid, h, a)
            print(f"    [FAIL] {test_desc} was unexpectedly accepted!")
        except ValueError as err:
            print(f"    [PASS] Correctly rejected {test_desc}: {err}")

    # Verify standings unchanged
    standings_check = compute_standings(teams, fixtures)
    assert standings == standings_check, "Standings mutated after invalid submission!"
    print("    [PASS] Standings verified 100% unchanged after invalid inputs.")

    # 6. Save & Reload from JSON
    demo_file = Path("demo_season.json")
    save_tournament(demo_file, teams, fixtures)
    reloaded_teams, reloaded_fixtures = load_tournament(demo_file)
    reloaded_standings = compute_standings(reloaded_teams, reloaded_fixtures)
    assert standings == reloaded_standings, "Reloaded standings do not match original!"
    print(f"\n[6] JSON Persistence Round-Trip Verified via '{demo_file}'.")
    demo_file.unlink(missing_ok=True)  # Clean up temporary file

    # 7. Complete Remaining 4 Fixtures & Crown Champion
    pending = [f for f in fixtures if f["status"] == "pending"]
    print(f"\n[7] Completing Remaining {len(pending)} Fixtures:")
    for p in pending:
        # Give Thunder wins to cement championship
        if p["home_id"] == "TM001":
            record_result(fixtures, p["id"], 3, 0)
        elif p["away_id"] == "TM001":
            record_result(fixtures, p["id"], 0, 3)
        else:
            record_result(fixtures, p["id"], 1, 1)
        print(f"    - {p['id']}: Played ({p['home_id']} {p['home_score']} - {p['away_score']} {p['away_id']})")

    final_standings = compute_standings(teams, fixtures)
    final_status, final_champ = get_tournament_status(fixtures, final_standings)

    print("\n[8] FINAL LEAGUE STANDINGS:")
    print("=" * 76)
    print("+-----+--------+----------------------+----+----+----+----+----+----+----+-----+")
    print("| Pos | ID     | Team Name            | P  | W  | D  | L  | GF | GA | GD | PTS |")
    print("+-----+--------+----------------------+----+----+----+----+----+----+----+-----+")
    for idx, r in enumerate(final_standings, start=1):
        gd_str = f"{r['goal_difference']:+d}"
        print(
            f"| {idx:<3} | {r['team_id']:<6} | {r['name'][:20]:<20} | "
            f"{r['played']:<2} | {r['wins']:<2} | {r['draws']:<2} | {r['losses']:<2} | "
            f"{r['goals_for']:<2} | {r['goals_against']:<2} | {gd_str:>3} | {r['points']:<3} |"
        )
    print("+-----+--------+----------------------+----+----+----+----+----+----+----+-----+")
    print(f"Tournament Status: [{final_status.upper()}]")
    print("*" * 60)
    print(f"  🏆 CHAMPION: {final_champ['name']} ({final_champ['team_id']}) with {final_champ['points']} PTS! 🏆")
    print("*" * 60)

    # Invariants Verification
    valid, msg = verify_league_invariants(final_standings, fixtures)
    print(f"\n[9] Mathematical Invariants Check: {msg}")
    assert valid, f"Invariants failed: {msg}"
    print("=" * 76)


if __name__ == "__main__":
    run_controlled_demo()
