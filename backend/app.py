"""Local demonstration of risk-scored DBMS deception.

Untrusted input is inspected as text and is never executed as SQL. Only fixed,
parameterized demo lookups reach SQLite.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import queue
import re
import secrets
import sqlite3
import threading
import urllib.request
from collections import deque
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, render_template, request, make_response, redirect, Response, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO

try:
    from backend.sentinel_gateway import DEFAULT_THRESHOLD, assess_payload, inspect_and_route, classify_query
    from backend.synthetic_data import generate_synthetic_decoy, get_available_synthetic_datasets
except ImportError:
    from sentinel_gateway import DEFAULT_THRESHOLD, assess_payload, inspect_and_route, classify_query
    from synthetic_data import generate_synthetic_decoy, get_available_synthetic_datasets

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT / "frontend"
DATA_DIR = Path(os.environ.get("QUERY_TRAP_DATA", ROOT / "data"))
DATA_DIR.mkdir(exist_ok=True)

DEFAULT_PORT = int(os.environ.get("PORT", "3000"))
SERVICE_ROLE = os.environ.get("SERVICE_ROLE", "").strip().lower()
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "ALLOWED_ORIGINS",
        "http://127.0.0.1:5200,http://localhost:5200,http://127.0.0.1:3000,http://localhost:3000,http://127.0.0.1:5100,http://localhost:5100,http://127.0.0.1:5300,http://localhost:5300",
    ).split(",")
    if o.strip()
]

# SOC Dashboard Security Credentials
SOC_USERNAME = os.environ.get("SOC_USERNAME", "admin")
SOC_PASSWORD = os.environ.get("SOC_PASSWORD", "sentinel_sec_2026")
SOC_TOKEN = os.environ.get("SOC_TOKEN", "soc_token_live_2026")

app = Flask(
    __name__,
    template_folder=str(FRONTEND_DIR / "templates"),
    static_folder=str(FRONTEND_DIR / "static"),
)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Rate Limiter: Drops traffic from IPs exceeding 50 requests per minute on sensitive endpoints
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
    strategy="fixed-window",
)

socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")
LOCK = threading.Lock()
EVENTS: deque[dict] = deque(maxlen=100)
COUNTS = {"safe": 0, "suspicious": 0, "honeypot": 0}

# Asynchronous Telemetry Event Dispatcher Queue & Background Daemon
_TELEMETRY_QUEUE: queue.Queue[tuple[dict, str]] = queue.Queue(maxsize=10000)


def _telemetry_worker_loop() -> None:
    """Background daemon worker for non-blocking asynchronous telemetry dispatch."""
    while True:
        try:
            item = _TELEMETRY_QUEUE.get()
            if item is None:
                break
            event, target_url = item
            try:
                endpoint = f"{target_url.rstrip('/')}/api/internal/telemetry"
                req = urllib.request.Request(
                    endpoint,
                    data=json.dumps({"event": event}).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {SOC_TOKEN}",
                    },
                )
                with urllib.request.urlopen(req, timeout=2.0):
                    pass
            except Exception:
                pass
            finally:
                _TELEMETRY_QUEUE.task_done()
        except Exception:
            pass


_telemetry_thread = threading.Thread(target=_telemetry_worker_loop, name="SentinelTelemetryWorker", daemon=True)
_telemetry_thread.start()


def dispatch_telemetry_event(event: dict, request_host: str | None = None) -> None:
    """Non-blocking telemetry dispatch.

    Records event locally, emits over local WebSockets, and enqueues background HTTP
    push to Sentinel Port 5100 so the caller never blocks.
    """
    with LOCK:
        EVENTS.append(event)
        COUNTS[event["bucket"]] = COUNTS.get(event["bucket"], 0) + 1
        counts = COUNTS.copy()
    save_event_to_db(event)
    try:
        socketio.emit("telemetry", {"event": event, "counts": counts})
    except Exception:
        pass

    try:
        sentinel_url = get_service_url("sentinel")
        if sentinel_url and request_host and not any(p in request_host for p in ("3000", "5100")):
            _TELEMETRY_QUEUE.put_nowait((event, sentinel_url))
    except Exception:
        pass


def is_soc_authenticated() -> bool:
    """Verify SOC analyst credentials via Session, Bearer token, query token, or Basic Auth."""
    if app.testing and not app.config.get("ENFORCE_SOC_AUTH_IN_TESTS", False):
        return True

    # 1. Session check
    if session.get("soc_authenticated") is True:
        return True

    # 2. Query parameter (?token=... or ?auth_token=...)
    token = request.args.get("token") or request.args.get("auth_token")
    if token and secrets.compare_digest(str(token), SOC_TOKEN):
        session["soc_authenticated"] = True
        return True

    # 3. Authorization Header
    auth_header = request.headers.get("Authorization", "").strip()
    if auth_header.startswith("Bearer "):
        bearer_token = auth_header[7:].strip()
        if secrets.compare_digest(bearer_token, SOC_TOKEN):
            return True
    elif auth_header.startswith("Basic "):
        try:
            raw_credentials = base64.b64decode(auth_header[6:].strip()).decode("utf-8")
            if ":" in raw_credentials:
                user, pwd = raw_credentials.split(":", 1)
                if secrets.compare_digest(user, SOC_USERNAME) and secrets.compare_digest(pwd, SOC_PASSWORD):
                    session["soc_authenticated"] = True
                    return True
        except Exception:
            pass

    return False


def soc_unauthorized_response() -> Response:
    """Return 401 Unauthorized with WWW-Authenticate header."""
    if request.path.startswith("/api/") or request.is_json:
        resp = jsonify({
            "error": "Unauthorized",
            "message": "Authentication required for Sentinel SOC operations.",
            "status": 401,
        })
        resp.status_code = 401
        resp.headers["WWW-Authenticate"] = 'Basic realm="Sentinel SOC Security Operations"'
        return resp

    resp = make_response(
        "<!doctype html><html><head><title>401 Unauthorized · Sentinel SOC</title></head>"
        "<body style='font-family:sans-serif;background:#0d1117;color:#f0f6fc;padding:50px;text-align:center;'>"
        "<h1 style='color:#f85149;margin-bottom:12px;'>401 Unauthorized</h1>"
        "<p style='color:#8b949e;margin-bottom:24px;'>Access to Sentinel SOC Security Operations requires authentication.</p>"
        "<p style='font-family:monospace;background:#161b22;display:inline-block;padding:8px 16px;border-radius:6px;border:1px solid #30363d;'>"
        "Supply HTTP Basic Auth (admin / sentinel_sec_2026) or Security Token."
        "</p></body></html>",
        401,
    )
    resp.headers["WWW-Authenticate"] = 'Basic realm="Sentinel SOC Security Operations"'
    return resp


@socketio.on("connect")
def handle_socket_connect(auth=None):
    """Verify SOC authorization token before permitting Socket.IO subscription to telemetry."""
    if app.testing and not app.config.get("ENFORCE_SOC_AUTH_IN_TESTS", False):
        return True

    role = get_service_role()
    if role == "sentinel" or is_unified_mode():
        provided_token = None
        if isinstance(auth, dict):
            provided_token = auth.get("token") or auth.get("authToken")
        if not provided_token:
            provided_token = request.args.get("token") or request.args.get("auth_token")

        if provided_token and secrets.compare_digest(str(provided_token), SOC_TOKEN):
            return True
        if session.get("soc_authenticated") is True:
            return True
        return False
    return True


@app.errorhandler(429)
def ratelimit_exceeded(e):
    """Handle rate limit exceeded (50 req/min) with JSON or clean HTML."""
    if request.path.startswith("/api/") or request.is_json:
        return jsonify({
            "error": "Too Many Requests",
            "message": "Rate limit exceeded: 50 requests per minute.",
            "status": 429,
        }), 429
    return (
        "<!doctype html><html><head><title>429 Too Many Requests</title></head>"
        "<body style='font-family:sans-serif;background:#0f172a;color:#f8fafc;padding:40px;text-align:center;'>"
        "<h1 style='color:#f87171;'>429 - Rate Limit Exceeded</h1>"
        "<p>Honeypot protection policy: Maximum 50 requests per minute allowed per IP address.</p>"
        "</body></html>",
        429,
    )


def connect(path: Path) -> sqlite3.Connection:
    c = sqlite3.connect(path, timeout=5.0)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON;")
    try:
        c.execute("PRAGMA journal_mode = WAL;")
    except sqlite3.OperationalError:
        pass
    return c


@contextmanager
def db_session(path: Path):
    c = connect(path)
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init_db(path: Path, decoy: bool) -> None:
    with db_session(path) as db:
        if decoy:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    role TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS financial_records (
                    id INTEGER PRIMARY KEY,
                    account TEXT NOT NULL,
                    balance REAL NOT NULL,
                    currency TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS redirect_handoffs (
                    token TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    expires_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS public_catalog (
                    id INTEGER PRIMARY KEY,
                    item TEXT NOT NULL,
                    category TEXT NOT NULL,
                    price REAL NOT NULL
                );
                """
            )
            count = db.execute("SELECT count(*) FROM users").fetchone()[0]
            if count == 0:
                db.executemany(
                    "INSERT INTO users (id, name, email, role) VALUES (?, ?, ?, ?)",
                    [
                        (101, "Morgan Vale", "mvale@internal-decoy.corp", "auditor"),
                        (102, "Riley Chen", "rchen@internal-decoy.corp", "finance_temp"),
                    ],
                )
                db.executemany(
                    "INSERT INTO financial_records (id, account, balance, currency) VALUES (?, ?, ?, ?)",
                    [
                        (1, "DECOY-0041-A", 18450.00, "USD"),
                        (2, "DECOY-0042-B", 9200.50, "USD"),
                    ],
                )
                db.executemany(
                    "INSERT INTO public_catalog (id, item, category, price) VALUES (?, ?, ?, ?)",
                    [
                        (1, "Field notebook", "Stationery", 8.50),
                        (2, "Desk lamp", "Home", 24.00),
                        (3, "Travel mug", "Kitchen", 16.25),
                    ],
                )
        else:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    role TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS public_catalog (
                    id INTEGER PRIMARY KEY,
                    item TEXT NOT NULL,
                    category TEXT NOT NULL,
                    price REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS telemetry_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    ip TEXT NOT NULL,
                    query TEXT NOT NULL,
                    threats TEXT NOT NULL,
                    risk INTEGER NOT NULL,
                    route TEXT NOT NULL,
                    bucket TEXT NOT NULL
                );
                """
            )
            count = db.execute("SELECT count(*) FROM public_catalog").fetchone()[0]
            if count == 0:
                db.executemany(
                    "INSERT INTO users (id, name, email, role) VALUES (?, ?, ?, ?)",
                    [
                        (1, "Jordan Lee", "jordan@example.com", "analyst"),
                        (2, "Sam Rivera", "sam@example.com", "engineer"),
                    ],
                )
                db.executemany(
                    "INSERT INTO public_catalog (id, item, category, price) VALUES (?, ?, ?, ?)",
                    [
                        (1, "Field notebook", "Stationery", 8.50),
                        (2, "Desk lamp", "Home", 24.00),
                        (3, "Travel mug", "Kitchen", 16.25),
                        (4, "Fountain pen", "Stationery", 19.99),
                        (5, "Canvas backpack", "Accessories", 48.00),
                        (6, "Ceramic planter", "Home", 14.50),
                        (7, "Insulated water bottle", "Kitchen", 22.00),
                        (8, "Mechanical pencil", "Stationery", 6.00),
                    ],
                )


def load_persisted_events() -> None:
    try:
        with db_session(DATA_DIR / "production.db") as db:
            rows = db.execute(
                "SELECT timestamp, ip, query, threats, risk, route, bucket FROM telemetry_events ORDER BY id DESC LIMIT 100"
            ).fetchall()
            if rows:
                with LOCK:
                    loaded_events = []
                    counts = {"safe": 0, "suspicious": 0, "honeypot": 0}
                    for r in reversed(rows):
                        evt = {
                            "id": f"evt-{abs(hash(r['timestamp'] + r['query'])) % 100000:05d}",
                            "timestamp": r["timestamp"],
                            "ip": r["ip"],
                            "query": r["query"],
                            "threats": json.loads(r["threats"]) if r["threats"].startswith("[") else [r["threats"]],
                            "risk": r["risk"],
                            "route": r["route"],
                            "bucket": r["bucket"],
                            "query_class": classify_query(r["query"], r["risk"]),
                        }
                        loaded_events.append(evt)
                        counts[r["bucket"]] = counts.get(r["bucket"], 0) + 1
                    EVENTS.clear()
                    EVENTS.extend(loaded_events)
                    COUNTS.clear()
                    COUNTS.update(counts)
    except Exception:
        pass


init_db(DATA_DIR / "production.db", decoy=False)
init_db(DATA_DIR / "honeypot.db", decoy=True)
load_persisted_events()


def save_event_to_db(event: dict) -> None:
    try:
        with db_session(DATA_DIR / "production.db") as db:
            db.execute(
                """
                INSERT INTO telemetry_events (timestamp, ip, query, threats, risk, route, bucket)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    event.get("ip", "unknown"),
                    event.get("query", "")[:500],
                    json.dumps(event.get("threats", [])),
                    int(event.get("risk", 0)),
                    event.get("route", "production"),
                    event.get("bucket", "safe"),
                ),
            )
    except Exception:
        pass


def get_current_port() -> int:
    try:
        if request.host:
            host_parts = request.host.split(":")
            if len(host_parts) == 2 and host_parts[1].isdigit():
                return int(host_parts[1])
            if "SERVER_PORT" in request.environ and str(request.environ["SERVER_PORT"]).isdigit():
                p = int(request.environ["SERVER_PORT"])
                if p not in (80, 443):
                    return p
            return 0
    except RuntimeError:
        pass
    return DEFAULT_PORT


def get_service_role() -> str:
    if SERVICE_ROLE:
        return SERVICE_ROLE
    port = get_current_port()
    if port == 5200:
        return "storefront"
    if port == 5300:
        return "honeypot"
    if port in (3000, 5100):
        return "sentinel"
    return "unified"


def is_unified_mode() -> bool:
    role = get_service_role()
    return role in ("unified", "all")


def get_service_url(target: str) -> str:
    if is_unified_mode():
        return ""
    host = "127.0.0.1"
    try:
        if request.host:
            host = request.host.split(":")[0]
    except RuntimeError:
        pass

    target_ports = {"sentinel": 3000, "storefront": 5200, "honeypot": 5300}
    port = target_ports.get(target, 3000)
    return f"http://{host}:{port}"


def get_template_context() -> dict:
    return {
        "sentinel_url": get_service_url("sentinel"),
        "storefront_url": get_service_url("storefront"),
        "honeypot_url": get_service_url("honeypot"),
        "is_unified": is_unified_mode(),
        "service_role": get_service_role(),
        "soc_token": SOC_TOKEN,
    }


def inspect_payload(raw: str) -> tuple[list[str], int, int, int]:
    a = assess_payload(raw)
    return list(a.threats), a.risk_score, a.char_length, a.token_count


def fixed_lookup(raw: str, db: sqlite3.Connection, search_term: str | None = None) -> tuple[str, list[dict]]:
    target = "public_catalog"
    if search_term is not None and search_term.strip():
        term = f"%{search_term.strip().lower()}%"
        rows = db.execute(
            f"SELECT * FROM {target} WHERE instr(lower(item), ?) > 0 ORDER BY id LIMIT ?",
            (search_term.strip().lower(), 12),
        ).fetchall()
        return target, [dict(row) for row in rows]
    rows = db.execute(f"SELECT * FROM {target} ORDER BY id LIMIT ?", (5,)).fetchall()
    return target, [dict(row) for row in rows]


def safe_production_lookup(term: str | None) -> tuple[str, list[dict]]:
    with db_session(DATA_DIR / "production.db") as db:
        return fixed_lookup(term or "", db, term)


def handle_storefront_route():
    q = (request.args.get("q") or request.args.get("query") or request.args.get("search") or "").strip()
    port_param = request.args.get("port") or request.args.get("dest_port")
    if port_param:
        q = f"{q} port={port_param}".strip()

    if not q:
        with db_session(DATA_DIR / "production.db") as db:
            rows = db.execute("SELECT * FROM public_catalog ORDER BY id LIMIT 12").fetchall()
            products = [dict(r) for r in rows]
        ctx = get_template_context()
        ctx["products"] = products
        return render_template("portal.html", **ctx)

    client_ip = request.remote_addr or "local"
    site_ctx = f"{request.host_url.rstrip('/')}/?q={q[:60]}"
    explicit_asset = "public_catalog" if not any(t in q.lower() for t in ("users", "financial", "secret", "admin")) else None

    outcome = inspect_and_route(
        q,
        production_operation=lambda: safe_production_lookup(q),
        honeypot_operation=lambda: generate_synthetic_decoy(q),
        asset=explicit_asset,
        threshold=DEFAULT_THRESHOLD,
        client_ip=client_ip,
        site_context=f"{site_ctx} [Address Bar GET]",
        audit=lambda e: dispatch_telemetry_event(e, request.host),
    )

    if outcome.bucket == "honeypot":
        table, synthetic_rows = outcome.result
        handoff_token = secrets.token_urlsafe(24)
        handoff_payload = json.dumps({
            "query": q,
            "risk": outcome.assessment.risk_score,
            "risk_band": outcome.assessment.risk_band,
            "route": outcome.route,
            "bucket": outcome.bucket,
            "table": table,
            "site_context": site_ctx,
            "threats": list(outcome.assessment.threats),
            "rows": synthetic_rows,
            "is_synthetic": True,
            "source_type": "dynamic_synthetic_honeytoken",
            "trigger_channel": "Address Bar (GET URL Query)",
        })
        with db_session(DATA_DIR / "honeypot.db") as db:
            db.execute("DELETE FROM redirect_handoffs WHERE expires_at < ?", (int(datetime.now(timezone.utc).timestamp()),))
            db.execute(
                "INSERT INTO redirect_handoffs (token, payload, expires_at) VALUES (?, ?, ?)",
                (handoff_token, handoff_payload, int(datetime.now(timezone.utc).timestamp()) + 600),
            )

        honeypot_url = get_service_url("honeypot")
        if honeypot_url:
            return redirect(f"{honeypot_url.rstrip('/')}/?handoff={handoff_token}", code=302)
        return redirect(f"/honeypot?handoff={handoff_token}", code=302)

    _, safe_rows = outcome.result
    ctx = get_template_context()
    ctx.update({
        "initial_query": q,
        "initial_rows": safe_rows,
        "initial_searched": True,
        "products": safe_rows,
    })
    return render_template("portal.html", **ctx)


@app.get("/")
def index():
    role = get_service_role()
    if role == "storefront":
        return handle_storefront_route()
    if role == "honeypot":
        # Rate limit checks apply on honeypot view
        return render_template("honeypot.html", **get_template_context())

    q = request.args.get("q") or request.args.get("query") or request.args.get("search")
    if q and is_unified_mode():
        return handle_storefront_route()

    # Protected Sentinel SOC Dashboard
    if not is_soc_authenticated():
        return soc_unauthorized_response()

    return render_template("index.html", **get_template_context())


@app.get("/portal")
@app.get("/search")
def demo_portal():
    return handle_storefront_route()


@app.get("/honeypot")
@limiter.limit("50 per minute")
def honeypot_page():
    return render_template("honeypot.html", **get_template_context())


@app.get("/api/handoff/<token>")
@limiter.limit("50 per minute")
def get_handoff(token: str):
    role = get_service_role()
    if role in ("storefront", "sentinel") and not is_unified_mode():
        return jsonify({"error": "Handoffs are available only on the honeypot service or in unified mode."}), 404

    now = int(datetime.now(timezone.utc).timestamp())
    with db_session(DATA_DIR / "honeypot.db") as db:
        row = db.execute("SELECT payload FROM redirect_handoffs WHERE token = ? AND expires_at >= ?", (token, now)).fetchone()
        if row is None:
            return jsonify({"error": "This handoff is missing or expired."}), 404
        db.execute("DELETE FROM redirect_handoffs WHERE token = ?", (token,))
    return jsonify(json.loads(row["payload"]))


@app.get("/api/decoy/records")
@limiter.limit("50 per minute")
def decoy_records():
    table = request.args.get("table", "public_catalog").strip().lower()
    source = request.args.get("source", "").strip().lower()

    if source == "synthetic" or table.startswith("synthetic") or table in ("secrets", "cloud", "canary"):
        target_name, rows = generate_synthetic_decoy(table)
        return jsonify({
            "table": target_name,
            "rows": rows,
            "is_synthetic": True,
            "count": len(rows),
            "description": "Dynamic synthetic honeytokens (fabricated on the fly, not in any database)",
        })

    if table not in ("users", "financial_records", "public_catalog"):
        table = "public_catalog"
    with db_session(DATA_DIR / "honeypot.db") as db:
        rows = db.execute(f"SELECT * FROM {table} ORDER BY id LIMIT 10").fetchall()
        return jsonify({"table": table, "rows": [dict(r) for r in rows], "is_synthetic": False})


@app.get("/api/decoy/synthetic")
@limiter.limit("50 per minute")
def decoy_synthetic():
    return jsonify(get_available_synthetic_datasets())


@app.get("/api/db/inspect")
def inspect_databases_api():
    """Returns database tables and records for presentation verification (Protected SOC route)."""
    if not is_soc_authenticated():
        return soc_unauthorized_response()

    fmt = request.args.get("format", "").strip().lower()

    def dump_db(path: Path):
        if not path.exists():
            return {}
        result = {}
        with db_session(path) as db:
            tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            for t in tables:
                rows = db.execute(f"SELECT * FROM {t} LIMIT 25").fetchall()
                result[t] = [dict(r) for r in rows]
        return result

    prod_data = dump_db(DATA_DIR / "production.db")
    honey_data = dump_db(DATA_DIR / "honeypot.db")
    synth_data = get_available_synthetic_datasets()

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "databases": {
            "production_db": {
                "file": str(DATA_DIR / "production.db"),
                "status": "active_real",
                "tables": prod_data,
            },
            "honeypot_db": {
                "file": str(DATA_DIR / "honeypot.db"),
                "status": "decoy_sqlite",
                "tables": honey_data,
            },
            "dynamic_synthetic_honeytokens": {
                "status": "in_memory_transient",
                "description": "Pre-computed cryptographic honeytokens (Argon2id, RSA, canary serials)",
                "datasets": synth_data,
            },
        },
    }

    if fmt == "html" or "text/html" in request.headers.get("Accept", ""):
        prod_users_html = "".join(f"<tr><td>{u.get('id')}</td><td>{u.get('name')}</td><td>{u.get('email')}</td><td>{u.get('role')}</td></tr>" for u in prod_data.get("users", []))
        prod_cat_html = "".join(f"<tr><td>{c.get('id')}</td><td>{c.get('item')}</td><td>{c.get('category')}</td><td>${c.get('price'):.2f}</td></tr>" for c in prod_data.get("public_catalog", []))
        honey_users_html = "".join(f"<tr><td>{u.get('id')}</td><td>{u.get('name')}</td><td>{u.get('email')}</td><td><span style='color:#f87171;'>{u.get('role')}</span></td></tr>" for u in honey_data.get("users", []))
        honey_fin_html = "".join(f"<tr><td>{f.get('id')}</td><td>{f.get('account')}</td><td>${f.get('balance'):.2f}</td><td>{f.get('currency')}</td></tr>" for f in honey_data.get("financial_records", []))
        synth_users_html = "".join(f"<tr><td>{u.get('id')}</td><td>{u.get('username')}</td><td>{u.get('role')}</td><td><code>{u.get('canary_token')}</code></td></tr>" for u in synth_data.get("synthetic_users", []))

        html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Sentinel DB · Database Verification Inspector</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0b1016; color: #e6edf3; padding: 24px; margin: 0; }}
    h1 {{ font-size: 20px; font-weight: 700; color: #38c9cf; margin-bottom: 6px; }}
    p.lead {{ color: #8b949e; margin-top: 0; margin-bottom: 24px; font-size: 13px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 20px; }}
    .card {{ background: #131c26; border: 1px solid #243342; border-radius: 8px; padding: 18px; }}
    .card h2 {{ font-size: 14px; text-transform: uppercase; letter-spacing: 0.05em; margin: 0 0 12px 0; display: flex; align-items: center; justify-content: space-between; }}
    .card h2 span.badge {{ font-size: 11px; padding: 3px 8px; border-radius: 4px; font-weight: 600; text-transform: none; }}
    .badge-prod {{ background: #1f3d32; color: #3fb950; border: 1px solid #238636; }}
    .badge-decoy {{ background: #3d231f; color: #f85149; border: 1px solid #da3633; }}
    .badge-synth {{ background: #2f2544; color: #bc8cff; border: 1px solid #8957e5; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 10px; }}
    th, td {{ padding: 6px 10px; text-align: left; border-bottom: 1px solid #1f2b37; }}
    th {{ color: #8b949e; font-weight: 600; font-size: 11px; text-transform: uppercase; }}
    code {{ background: #1b2633; padding: 2px 6px; border-radius: 3px; font-family: monospace; font-size: 11px; color: #79c0ff; }}
    .subhead {{ font-size: 12px; color: #7d8590; margin-top: 16px; margin-bottom: 6px; font-weight: 600; text-transform: uppercase; }}
  </style>
</head>
<body>
  <h1>Database Inspector &amp; Honeytoken Verification</h1>
  <p class="lead">Live proof of three-tier database isolation: Real Production Database vs. Honeypot SQLite vs. Dynamic In-Memory Honeytokens.</p>
  <div class="grid">
    <div class="card">
      <h2>1. Real Production DB <span class="badge badge-prod">data/production.db</span></h2>
      <div class="subhead">Users Table (Real Customers)</div>
      <table><thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Role</th></tr></thead><tbody>{prod_users_html}</tbody></table>
      <div class="subhead">Public Catalog (Storefront Items)</div>
      <table><thead><tr><th>ID</th><th>Item</th><th>Category</th><th>Price</th></tr></thead><tbody>{prod_cat_html}</tbody></table>
    </div>
    <div class="card">
      <h2>2. Decoy Honeypot DB <span class="badge badge-decoy">data/honeypot.db</span></h2>
      <div class="subhead">Decoy Users (Fake Personas)</div>
      <table><thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Role</th></tr></thead><tbody>{honey_users_html}</tbody></table>
      <div class="subhead">Decoy Financial Records (Fake Ledgers)</div>
      <table><thead><tr><th>ID</th><th>Account</th><th>Balance</th><th>Currency</th></tr></thead><tbody>{honey_fin_html}</tbody></table>
    </div>
    <div class="card">
      <h2>3. Dynamic Synthetic Data <span class="badge badge-synth">In-Memory Honeytokens</span></h2>
      <div class="subhead">Fabricated Credentials (Not in any DB)</div>
      <table><thead><tr><th>ID</th><th>Username</th><th>Role</th><th>Canary Token</th></tr></thead><tbody>{synth_users_html}</tbody></table>
    </div>
  </div>
</body>
</html>"""
        return html, 200, {"Content-Type": "text/html; charset=utf-8"}

    return jsonify(payload)


@app.get("/api/decoy/export")
@limiter.limit("50 per minute")
def export_decoy_data():
    dataset_type = request.args.get("type", "users").strip().lower()
    fmt = request.args.get("format", "json").strip().lower()
    table_name, rows = generate_synthetic_decoy(dataset_type)

    if fmt == "csv":
        import io
        import csv

        output = io.StringIO()
        if rows:
            writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        resp = make_response(output.getvalue())
        resp.headers["Content-Disposition"] = f"attachment; filename=exfiltrated_{table_name}.csv"
        resp.headers["Content-Type"] = "text/csv"
        return resp

    resp = make_response(json.dumps(rows, indent=2))
    resp.headers["Content-Disposition"] = f"attachment; filename=exfiltrated_{table_name}.json"
    resp.headers["Content-Type"] = "application/json"
    return resp


@app.get("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "mode": get_service_role(),
        "is_unified": is_unified_mode(),
        "service_port": get_current_port(),
        "events": len(EVENTS),
    })


@app.post("/api/internal/telemetry")
def internal_telemetry():
    """Internal telemetry intake from storefront microservice."""
    body = request.get_json(silent=True) or {}
    event = body.get("event")
    if event and isinstance(event, dict):
        with LOCK:
            if not any(x["id"] == event["id"] for x in EVENTS):
                EVENTS.append(event)
                COUNTS[event["bucket"]] = COUNTS.get(event["bucket"], 0) + 1
            counts = COUNTS.copy()
        try:
            socketio.emit("telemetry", {"event": event, "counts": counts})
        except Exception:
            pass
        return jsonify({"status": "ok"}), 200
    return jsonify({"error": "invalid event"}), 400


@app.get("/api/events")
def events():
    if (get_service_role() == "sentinel" or is_unified_mode()) and not is_soc_authenticated():
        return soc_unauthorized_response()

    load_persisted_events()
    with LOCK:
        return jsonify({"events": list(EVENTS), "counts": COUNTS.copy()})


@app.route("/api/query", methods=["POST", "OPTIONS"])
def query():
    if request.method == "OPTIONS":
        return make_response("", 204)

    role = get_service_role()
    if role in ("storefront", "honeypot") and not is_unified_mode():
        return jsonify({"error": "Send inspected queries to the Sentinel DB service or unified API."}), 404

    # Require SOC authentication when querying the Sentinel console directly
    if (role == "sentinel" or is_unified_mode()) and not is_soc_authenticated():
        return soc_unauthorized_response()

    body = request.get_json(silent=True) or {}
    raw = body.get("query", "")
    if not isinstance(raw, str) or not raw.strip():
        return jsonify({"error": "Enter a query or payload to inspect."}), 400
    raw = raw[:2000]

    search_term = body.get("search_term")
    if search_term is not None:
        if not isinstance(search_term, str):
            return jsonify({"error": "Invalid search term."}), 400
        search_term = search_term.strip()[:100]

    site_context = body.get("site_context")
    if not isinstance(site_context, str):
        site_context = ""
    site_context = site_context.strip()[:300] or request.referrer or request.host_url.rstrip("/")

    explicit_asset = "public_catalog" if search_term is not None else None
    outcome = inspect_and_route(
        raw,
        production_operation=lambda: safe_production_lookup(search_term),
        honeypot_operation=lambda: generate_synthetic_decoy(raw),
        asset=explicit_asset,
        threshold=DEFAULT_THRESHOLD,
        client_ip=request.remote_addr or "local",
        site_context=site_context,
        audit=lambda e: dispatch_telemetry_event(e, request.host),
    )
    assessment = outcome.assessment
    score, risk_band = assessment.risk_score, assessment.risk_band
    route, bucket = outcome.route, outcome.bucket
    threats = list(assessment.threats)
    table, rows = outcome.result

    handoff_token = None
    if bucket == "honeypot":
        handoff_token = secrets.token_urlsafe(24)
        handoff_payload = json.dumps({
            "query": raw,
            "risk": score,
            "risk_band": risk_band,
            "route": route,
            "bucket": bucket,
            "table": table,
            "site_context": site_context,
            "threats": threats,
            "rows": rows,
            "is_synthetic": True,
            "source_type": "dynamic_synthetic_honeytoken",
        })
        with db_session(DATA_DIR / "honeypot.db") as db:
            db.execute("DELETE FROM redirect_handoffs WHERE expires_at < ?", (int(datetime.now(timezone.utc).timestamp()),))
            db.execute(
                "INSERT INTO redirect_handoffs (token, payload, expires_at) VALUES (?, ?, ?)",
                (handoff_token, handoff_payload, int(datetime.now(timezone.utc).timestamp()) + 600),
            )

    return jsonify({
        "risk": score,
        "risk_band": risk_band,
        "route": route,
        "bucket": bucket,
        "table": table,
        "site_context": site_context,
        "threats": threats,
        "rows": rows,
        "is_synthetic": (bucket == "honeypot"),
        "handoff": handoff_token,
        "message": "Inspection complete. Suspicious payloads routed to dynamic synthetic honeypot." if bucket == "honeypot" else "Inspection complete. Safe lookup executed.",
    })


@app.after_request
def allow_cors(response):
    origin = request.headers.get("Origin")
    if not origin:
        return response

    allow = False
    if "*" in ALLOWED_ORIGINS:
        allow = True
    elif origin in ALLOWED_ORIGINS:
        allow = True
    elif is_unified_mode():
        allow = True
    else:
        if re.match(r"^https?://(127\.0\.0\.1|localhost)(:(3000|5100|5200|5300))?$", origin):
            allow = True

    if allow:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Vary"] = "Origin"
    return response


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run one Sentinel DB demo service")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--host", type=str, default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--role", type=str, default=os.environ.get("SERVICE_ROLE", ""))
    args = parser.parse_args()
    DEFAULT_PORT = args.port
    if args.role:
        SERVICE_ROLE = args.role.strip().lower()
    socketio.run(app, host=args.host, port=args.port, debug=False, allow_unsafe_werkzeug=True)
