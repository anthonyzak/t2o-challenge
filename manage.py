#!/usr/bin/env python
"""
Management CLI for Weather Data API.
"""

import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.cli.commands import cli  # noqa: E402

if __name__ == "__main__":
    cli()
