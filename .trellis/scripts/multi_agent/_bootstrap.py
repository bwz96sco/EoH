"""Bootstrap: add parent scripts/ directory to sys.path so common.* imports work."""
import sys
from pathlib import Path

_scripts_dir = str(Path(__file__).resolve().parent.parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)
