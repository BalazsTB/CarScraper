"""Application paths independent of the working directory."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATABASE = ROOT / "Database" / "cars.sqlite3"
