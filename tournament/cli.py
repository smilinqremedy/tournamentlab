"""Terminal user interface and menu driver for TournamentLab.

Engineer B ownership:
- Friendly, robust CLI experience
- Clear tabular formatting for standings and fixtures
- Input validation loops that never crash on empty/invalid inputs
- Prominent champion and tournament progress banners
"""

import sys
from pathlib import Path
from typing import Any

from tournament.fixtures import (
    generate_round_robin,
    get_fixture_by_id,
    list_fixtures,
    record_result,
)
from tournament.simulation import simulate_demo_fixtures
from tournament.standings import (
    compute_standings,
    get_tournament_status,
    verify_league_invariants,
)
from tournament.storage import load_tournament, save_tournament
from tournament.teams import (
    get_team_name,
    list_teams,
    register_team,
)


def print_banner() -> None:
    """Print the application welcome banner."""
    print("=" * 64)
    print("      TOURNAMENTLAB | THE ULTIMATE ESPORTS LEAGUE MANAGER")
    print("=" * 64)


def display_menu() -> None:
    """Display the main menu options."""
    print("\n--- MAIN MENU ---")
    print(" 1. Register a Team (4-8 required)")
    print(" 2. List Registered Teams")
    print(" 3. Generate Round-Robin Schedule")
    print(" 4. List Fixtures & Scores")
    print(" 5. Record Match Result")
    print(" 6. View League Standings & Champion")
    print(" 7. Simulate Remaining Fixtures (Seeded Demo)")
    print(" 8. Save Tournament State (JSON)")
    print(" 9. Load Tournament State (JSON)")
    print("10. Reset Tournament (Start Fresh)")
    print(" 0. Exit")


def render_teams_table(teams: list[dict[str, Any]]) -> None:
    """Display registered teams in a clean formatted table."""
    if not teams:
        print("\n[!] No teams registered yet.")
        return

    print("\n+--------+--------------------------------+")
    print("| Team ID| Team Name                      |")
    print("+--------+--------------------------------+")
    for team in teams:
        print(f"| {team['id']:<6} | {team['name']:<30} |")
    print("+--------+--------------------------------+")
    print(f"Total registered teams: {len(teams)} / 8")


def render_fixtures_table(
    fixtures: list[dict[str, Any]],
    teams: list[dict[str, Any]],
) -> None:
    """Display fixtures and their statuses."""
    if not fixtures:
        print("\n[!] No fixtures generated yet.")
        return

    print("\n+-------+-------------------------+-------------------------+-----------+-------+")
    print("| ID    | Home Team               | Away Team               | Status    | Score |")
    print("+-------+-------------------------+-------------------------+-----------+-------+")
    for f in fixtures:
        home_name = get_team_name(teams, f["home_id"])
        away_name = get_team_name(teams, f["away_id"])
        score_str = (
            f"{f['home_score']}-{f['away_score']}" if f["status"] == "played" else " - "
        )
        status_str = f["status"].upper()
        print(
            f"| {f['id']:<5} | {home_name[:23]:<23} | {away_name[:23]:<23} | {status_str:<9} | {score_str:^5} |"
        )
    print("+-------+-------------------------+-------------------------+-----------+-------+")
    played = sum(1 for f in fixtures if f["status"] == "played")
    print(f"Progress: {played}/{len(fixtures)} matches played.")


def render_standings_table(
    standings: list[dict[str, Any]],
    fixtures: list[dict[str, Any]],
) -> None:
    """Display league standings with champion status."""
    if not standings:
        print("\n[!] No standings available (no teams registered).")
        return

    status, champion = get_tournament_status(fixtures, standings)

    print("\n" + "=" * 76)
    print("                      LEAGUE STANDINGS")
    print("=" * 76)
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

    # Invariants verification report
    valid, reason = verify_league_invariants(standings, fixtures)
    if not valid:
        print(f"[!] WARNING: Data integrity issue: {reason}")

    # Tournament Status / Champion announcement
    print(f"\nTournament Status: [{status.upper()}]")
    if status == "complete" and champion:
        print("*" * 60)
        print(f"  🏆 CHAMPION: {champion['name']} ({champion['team_id']}) with {champion['points']} PTS! 🏆")
        print("*" * 60)
    else:
        pending_count = sum(1 for f in fixtures if f.get("status") == "pending")
        print(f"Standings are currently IN PROGRESS ({pending_count} pending fixture(s) remain).")


def run_cli() -> None:
    """Main CLI execution loop."""
    teams: list[dict[str, Any]] = []
    fixtures: list[dict[str, Any]] = []

    print_banner()

    while True:
        try:
            display_menu()
            choice = input("\nEnter choice [0-10]: ").strip()

            if choice == "1":
                # Register team
                if len(teams) >= 8:
                    print("\n[!] Error: Maximum limit of 8 teams already reached.")
                    continue
                name_input = input("Enter team display name (2-30 chars): ")
                try:
                    new_team = register_team(teams, name_input)
                    print(f"\n[+] Success: Registered {new_team['name']} (ID: {new_team['id']}).")
                except ValueError as err:
                    print(f"\n[!] Registration Error: {err}")

            elif choice == "2":
                # List teams
                render_teams_table(teams)

            elif choice == "3":
                # Generate schedule
                try:
                    generated = generate_round_robin(teams, fixtures)
                    fixtures.extend(generated)
                    print(
                        f"\n[+] Success: Generated {len(fixtures)} round-robin fixtures "
                        f"for {len(teams)} teams."
                    )
                except ValueError as err:
                    print(f"\n[!] Scheduling Error: {err}")

            elif choice == "4":
                # List fixtures
                render_fixtures_table(fixtures, teams)

            elif choice == "5":
                # Record result
                if not fixtures:
                    print("\n[!] No fixtures exist. Generate schedule first.")
                    continue

                fid = input("Enter Fixture ID (e.g. M001): ").strip().upper()
                target_fixture = get_fixture_by_id(fixtures, fid)
                if not target_fixture:
                    print(f"\n[!] Error: Fixture '{fid}' does not exist.")
                    continue

                if target_fixture["status"] == "played":
                    print(f"\n[!] Error: Fixture '{fid}' is already completed. Duplicates prohibited.")
                    continue

                home_name = get_team_name(teams, target_fixture["home_id"])
                away_name = get_team_name(teams, target_fixture["away_id"])
                print(f"Match: {home_name} (Home) vs {away_name} (Away)")

                raw_h = input(f"Enter score for {home_name}: ").strip()
                raw_a = input(f"Enter score for {away_name}: ").strip()

                try:
                    h_score = int(raw_h)
                    a_score = int(raw_a)
                    record_result(fixtures, fid, h_score, a_score)
                    print(f"\n[+] Result recorded: {home_name} {h_score} - {a_score} {away_name}.")
                except ValueError as err:
                    print(f"\n[!] Score Error: {err}")

            elif choice == "6":
                # View standings
                standings = compute_standings(teams, fixtures)
                render_standings_table(standings, fixtures)

            elif choice == "7":
                # Simulate remaining fixtures
                pending_count = sum(1 for f in fixtures if f.get("status") == "pending")
                if pending_count == 0:
                    print("\n[!] No pending fixtures available to simulate.")
                    continue

                confirm = input(
                    f"Simulate all {pending_count} pending fixture(s) using reproducible seed? (y/N): "
                ).strip().lower()
                if confirm == "y":
                    seed_str = input("Enter integer seed [default 42]: ").strip()
                    seed_val = int(seed_str) if seed_str.isdigit() else 42
                    count = simulate_demo_fixtures(fixtures, seed=seed_val)
                    print(f"\n[+] Successfully simulated {count} fixtures (seed={seed_val}).")
                    standings = compute_standings(teams, fixtures)
                    render_standings_table(standings, fixtures)
                else:
                    print("\n[*] Simulation cancelled.")

            elif choice == "8":
                # Save tournament
                default_file = "tournament_state.json"
                filename = input(f"Enter destination JSON path [default: {default_file}]: ").strip()
                target_path = filename if filename else default_file
                try:
                    save_tournament(target_path, teams, fixtures)
                    print(f"\n[+] Tournament state successfully saved to '{target_path}'.")
                except Exception as err:
                    print(f"\n[!] Save Error: {err}")

            elif choice == "9":
                # Load tournament
                default_file = "tournament_state.json"
                filename = input(f"Enter source JSON path [default: {default_file}]: ").strip()
                target_path = filename if filename else default_file
                try:
                    loaded_teams, loaded_fixtures = load_tournament(target_path)
                    teams.clear()
                    teams.extend(loaded_teams)
                    fixtures.clear()
                    fixtures.extend(loaded_fixtures)
                    print(
                        f"\n[+] Successfully loaded {len(teams)} teams and {len(fixtures)} fixtures from '{target_path}'."
                    )
                    standings = compute_standings(teams, fixtures)
                    render_standings_table(standings, fixtures)
                except Exception as err:
                    print(f"\n[!] Load Error: {err}")

            elif choice == "10":
                # Reset tournament
                confirm = input("Are you sure you want to erase all teams and fixtures? (y/N): ").strip().lower()
                if confirm == "y":
                    teams.clear()
                    fixtures.clear()
                    print("\n[+] Tournament state reset. Ready for a new season.")
                else:
                    print("\n[*] Reset aborted.")

            elif choice == "0":
                print("\nThank you for using TournamentLab. Fair play wins championships!")
                sys.exit(0)

            else:
                print(f"\n[!] Invalid option '{choice}'. Please select a number from 0 to 10.")

        except KeyboardInterrupt:
            print("\n\nSession terminated by user. Goodbye!")
            sys.exit(0)
