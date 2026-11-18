# Sentinel DB — Intrusion Detection & Honeypot Demo

A local demonstration of text-based XSS/SQL injection detection, dynamic risk scoring, separate production/decoy SQLite databases, and live SOC telemetry.

The demo runs as three local services on separate ports. The SOC dashboard and alert stream are on `3000`, the normal storefront is on `5200`, and the decoy honeypot is on `5300`. Launch the storefront from the SOC page; it opens in a second tab so the analyst view stays open while the storefront tab is redirected.

## Run locally

Requires Python 3.10 or later.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
.\start_demo.ps1
```

Open <http://127.0.0.1:3000>. Stop the three services with `.\stop_demo.ps1`. The two SQLite databases are created and seeded in `data/` on first run. The storefront sends requests to the Sentinel API on port 3000; suspicious requests open the honeypot service on port 5300. Dashboard alerts stream over Socket.IO. Chart.js and the Socket.IO browser client are loaded from public CDNs.

## Teacher presentation flow

1. In PowerShell, go to the project folder, activate `.venv` if you created it, and run `.\start_demo.ps1`. Wait for the message that all three services passed their health checks. Keep this PowerShell window open.
2. Open these URLs in three browser tabs: Sentinel analyst dashboard <http://127.0.0.1:3000/>, normal storefront <http://127.0.0.1:5200/>, and honeypot decoy <http://127.0.0.1:5300/>. The honeypot tab can be left open as a preview; an attack from the storefront will redirect its tab into the honeypot.
3. On the storefront, search for `notebook`. This is a normal product search and should remain on the storefront.
4. **Address Bar Attack Demonstration (Key Feature for Judges):**
   - Type or paste an attack directly into your browser's address bar:  
     `http://127.0.0.1:5200/?q=' OR '1'='1` or `http://127.0.0.1:5200/?q=SELECT * FROM users`
   - The Sentinel gateway automatically intercepts the GET request, scores the payload, records SOC telemetry, issues a single-use handoff token, and **redirects the browser to the honeypot workspace (port 5300)**.
   - The attacker is served **dynamic synthetic honeytokens** (fabricated on the fly with unique canary tokens, secrets, and hashes — never stored in any production database).
   - Attackers can even explore different synthetic tabs (Credentials, Financial Ledger, Cloud Keys, Hardware Inventory) or download fake exfiltration exports.
5. In the storefront search box, you can also enter `' OR '1'='1` and click **Search** to see the in-page form redirection.
6. Switch to Sentinel (<http://127.0.0.1:3000/>). Show the live telemetry row with the SQLi tautology signature, risk score, client IP, origin website tagged with `[Address Bar GET]`, and `honeypot` routing action. Point out the line and doughnut charts and the diversion count.
7. For additional vectors, use **XSS payload** or **Destructive SQLi** under **Query inspector** on the Sentinel page. Inspector scenarios execute only fixed demonstration lookups and render the result inline.
8. End the demo with `.\stop_demo.ps1` in the PowerShell window.

## Demo behavior

- The request body is inspected for the listed XSS and SQLi signatures.
- Risk is the capped sum of payload severity (0–40), inferred asset sensitivity (0–40), and syntax/length anomaly (0–20).
- Scores 0–30 use the production demo DB. Any flagged score of 31 or higher (suspicious or critical) is directed to the separate honeypot DB and redirects the storefront tab to port 5300.
- The inspector includes a website/resource context field. That context is included in SOC telemetry and shown on the honeypot workspace page as text; the demo never navigates to the supplied external URL.
- The cross-port redirect uses a random, ten-minute handoff token. The query and synthetic response stay server-side; the URL contains only the token, which is removed after the honeypot page retrieves the handoff.
- The decoy workspace supports record filtering, column sorting, row detail inspection, and refresh. The storefront has interactive product buttons and a normal catalog search.
- The storefront search is an ordinary item/category search. Search text is inspected by Sentinel, but only a bound `public_catalog` filter is used for normal database lookups; raw search text is never treated as SQL. Attack samples remain in the analyst query inspector for demonstrations.
- Both SQLite files contain synthetic records. The query text is never executed. The server extracts a known table name and issues a fixed `SELECT * ... LIMIT ?` with a bound parameter.
- Telemetry lives in memory for the current server process. The dashboard's “Clear session” clears its view only; it does not clear server telemetry or reset counters.
- The table and risk chart show the latest 100 and 30 events respectively. The distribution shows counts for the current server process.

Quick scenarios are included in the inspector. A basic `users` lookup is flagged because that asset is sensitive, and the SQLi/destructive payload samples cross the honeypot threshold.

## Integrate with an existing application/database

`sentinel_gateway.py` is the database-agnostic integration point. Install it beside the existing application and call `inspect_and_route()` at the application/API layer before the normal repository call. The gateway does not open connections, alter schemas, migrate data, or require a specific database driver. The existing application supplies callbacks that use its current production repository and a separate honeypot repository; this retains its DB engine, connection pool, transaction handling, and authentication model.

```python
from sentinel_gateway import inspect_and_route

@app.post("/catalog/search")
def catalog_search():
    body = request.get_json()
    search_term = body["search_term"]
    untrusted_text = search_term

    outcome = inspect_and_route(
        untrusted_text,
        asset="public_catalog",
        sensitivity_map={"public_catalog": 10, "customers": 40},
        production_operation=lambda: production_catalog.search(search_term),
        honeypot_operation=lambda: decoy_catalog.search(search_term),
        client_ip=request.remote_addr or "unknown",
        site_context=request.host_url,
        audit=security_audit.write_event,
    )
    if outcome.route == "honeypot":
        return render_template("decoy_results.html", rows=outcome.result), 200
    return jsonify(outcome.result)
```

The repository methods in this example must use parameterized, fixed queries and the application's normal authorization checks. `search_term` is captured by the callbacks as a value; the gateway never passes the raw request string as SQL. The honeypot callback must use an isolated decoy store containing synthetic data. The audit callback can write to the existing SIEM/event pipeline; it runs before the selected DB operation. For API-only deployments, return the decision/event to the host app and let its own frontend perform the redirect so the SOC analyst session remains open.

Before connecting a production route, map each application resource to a sensitivity score (0–40), configure the redirect/decoy experience, use least-privilege production and decoy service identities, protect analyst routes with the existing identity/access controls, and verify log retention and privacy requirements. This repository's three-port Flask app remains a local synthetic demo; it is not itself a production proxy or a substitute for parameterized queries, authorization, output encoding, and database least privilege.

## Testing

Run the automated test suite covering gateway signature detection, risk scoring, API routes, honeypot handoffs, and CORS policies:

```bash
python -m unittest discover -s tests -v
```

## Production Deployment & Containerization

Query Trap supports both **Unified Single-Port Deployment** (for single containers, cloud run, render, heroku) and **Multi-Service Microservice Deployment** (for 3 isolated services on ports 3000, 5200, 5300).

### Option 1: Docker (Unified Single-Port)

Build and run a production container with Gunicorn and health checks:

```bash
docker build -t query-trap .
docker run -d -p 3000:3000 --name query-trap -e SERVICE_ROLE=unified query-trap
```

- SOC Dashboard: `http://localhost:3000/`
- Normal Storefront: `http://localhost:3000/portal`
- Decoy Honeypot: `http://localhost:3000/honeypot`

### Option 2: Docker Compose

Start the services with Docker Compose:

```bash
# Standard single-port unified deployment:
docker compose up -d

# Or multi-service 3-port deployment:
docker compose --profile multi-service up -d
```

### Option 3: Production WSGI (Linux / Cloud VM)

Run via Gunicorn directly:

```bash
gunicorn --config gunicorn.conf.py wsgi:app
```

### Cross-Platform Local Scripts

- **Windows (PowerShell)**: `.\start_demo.ps1` and `.\stop_demo.ps1`
- **Linux / macOS (Bash)**: `./start_demo.sh` and `./stop_demo.sh`

## Scope and security note

This is a teaching/demo application, not a production DBMS security gateway. It has no authentication, authorization, durable audit log, rate limiting, or production traffic integration. Signature matching is illustrative and does not replace parameterized application queries, output encoding, least privilege, or a defense-in-depth WAF/IDS. Keep the server bound to localhost; do not expose it to a network or put real records in its databases.
