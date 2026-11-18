"""Root compatibility entry point for Sentinel DB.
Re-exports the application from the backend package.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app import *
from backend.app import (
    app,
    socketio,
    DEFAULT_PORT,
    SERVICE_ROLE,
    EVENTS,
    COUNTS,
    load_persisted_events,
    DATA_DIR,
    db_session,
    generate_synthetic_decoy,
    get_available_synthetic_datasets,
    handle_storefront_route,
)

if __name__ == "__main__":
    import argparse
    import os
    parser = argparse.ArgumentParser(description="Run one Sentinel DB demo service")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--host", type=str, default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--role", type=str, default=os.environ.get("SERVICE_ROLE", ""))
    args = parser.parse_args()
    if args.role:
        import backend.app
        backend.app.SERVICE_ROLE = args.role.strip().lower()
    socketio.run(app, host=args.host, port=args.port, debug=False, allow_unsafe_werkzeug=True)
