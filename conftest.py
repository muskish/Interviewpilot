"""Pytest root configuration: ensures project root is on sys.path for test modules."""

import sys
from pathlib import Path

# Add project root directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.resolve()))
