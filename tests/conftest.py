import sys
import pathlib

# Ensure the backend package is importable
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))
