"""Root compatibility shim for sentinel_gateway."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.sentinel_gateway import *
from backend.sentinel_gateway import (
    DEFAULT_THRESHOLD,
    RiskAssessment,
    GatewayOutcome,
    assess_payload,
    inspect_and_route,
    classify_query,
)
