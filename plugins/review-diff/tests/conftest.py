import sys
from pathlib import Path

# Make the bundled scripts importable as top-level modules in tests.
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
