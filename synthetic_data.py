"""Root compatibility shim for synthetic_data."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.synthetic_data import *
from backend.synthetic_data import (
    generate_synthetic_decoy,
    get_available_synthetic_datasets,
)
