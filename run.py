"""Single-command runner for the entire Sentinel DB & Query Trap project.

Usage:
    python run.py
"""
import sys
import os
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    from scripts.start_demo import start_services
    start_services()

