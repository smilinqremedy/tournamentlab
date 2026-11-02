#!/usr/bin/env python3
"""TournamentLab — Esports League Manager entry point."""

import sys
from tournament.cli import run_cli


def main() -> None:
    """Run the TournamentLab CLI application."""
    run_cli()


if __name__ == "__main__":
    main()
