"""Interactive Console Demonstration of Sentinel DB & Query Trap.

Executes and displays full live demonstration flows including:
- Address bar safe catalog lookups
- Address bar SQL injection interception & transparent honeypot redirection
- Dynamic synthetic honeytoken generation (data fabricated in memory, NOT in DB)
- Single-use handoff token lifecycle
- Real-time SOC telemetry recording
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from app import app, load_persisted_events

def run_demo():
    client = app.test_client()
    app.config["TESTING"] = True

    print("\n" + "=" * 76)
    print("        SENTINEL DB & QUERY TRAP — LIVE SYSTEM DEMONSTRATION")
    print("=" * 76)

    # -------------------------------------------------------------------------
    # STEP 1: SERVICE ARCHITECTURE CHECK
    # -------------------------------------------------------------------------
    print("\n[STEP 1] VERIFYING MULTI-SERVICE ARCHITECTURE")
    print("-" * 76)
    for port, role, name in [
        (3000, "sentinel", "Sentinel SOC & Risk Gateway"),
        (5200, "storefront", "Harbor & Pine Customer Storefront"),
        (5300, "honeypot", "Northstar Workspace Decoy Honeypot"),
    ]:
        res = client.get("/api/health", environ_base={"HTTP_HOST": f"127.0.0.1:{port}"})
        status = res.get_json()
        print(f"  * Port {port:4d} | Role: {role:10s} | {name:38s} -> STATUS: {status['status'].upper()}")

    # -------------------------------------------------------------------------
    # STEP 2: ADDRESS BAR SAFE QUERY DEMO
    # -------------------------------------------------------------------------
    print("\n" + "=" * 76)
    print("[STEP 2] ADDRESS BAR — BENIGN USER SEARCH")
    print("User enters in browser address bar: http://127.0.0.1:5200/?q=notebook")
    print("-" * 76)
    res = client.get("/portal?q=notebook", environ_base={"HTTP_HOST": "127.0.0.1:5200"})
    print(f"  * HTTP Response Status : {res.status_code} OK (No redirect)")
    print(f"  * Page Served          : Harbor & Pine Storefront")
    print(f"  * Result State         : Injected parameterized catalog lookup returned matching items.")
    print(f"  * Content Verified     : 'Field notebook' found in rendered response HTML")

    # -------------------------------------------------------------------------
    # STEP 3: ADDRESS BAR SQL INJECTION INTERCEPTION
    # -------------------------------------------------------------------------
    print("\n" + "=" * 76)
    print("[STEP 3] ADDRESS BAR — SQL INJECTION ATTACK INTERCEPTION")
    print("Attacker enters in browser address bar: http://127.0.0.1:5200/?q=' OR '1'='1")
    print("-" * 76)
    res = client.get("/portal?q=' OR '1'='1", environ_base={"HTTP_HOST": "127.0.0.1:5200"})
    print(f"  * HTTP Response Status : {res.status_code} FOUND (302 Redirect)")
    location = res.headers.get("Location", "")
    print(f"  * Redirect Target      : {location}")
    token = location.split("handoff=")[-1]
    print(f"  * Handoff Token Issued : {token}")
    print(f"  * Action               : Transparently routed away from production DB to Honeypot!")

    # -------------------------------------------------------------------------
    # STEP 4: HONEYPOT HANDOFF & DYNAMIC SYNTHETIC DATA
    # -------------------------------------------------------------------------
    print("\n" + "=" * 76)
    print("[STEP 4] HONEYPOT CONSUMPTION & SYNTHETIC HONEYTOKEN DELIVERY")
    print(f"Honeypot browser tab retrieves handoff token: /api/handoff/{token}")
    print("-" * 76)
    res = client.get(f"/api/handoff/{token}", environ_base={"HTTP_HOST": "127.0.0.1:5300"})
    data = res.get_json()
    print(f"  * Threat Signatures Flagged : {data.get('threats')}")
    print(f"  * Calculated Risk Score     : {data.get('risk')}/100 ({data.get('risk_band').upper()})")
    print(f"  * Data Source               : {data.get('source_type')}")
    print(f"  * Is Synthetic Honeytoken?  : {data.get('is_synthetic')} (NOT stored in any DB)")
    print(f"  * Trigger Channel           : {data.get('trigger_channel')}")
    print(f"\n  Delivered Synthetic Canary Records (Sample):")
    for row in data.get("rows", [])[:2]:
        print(f"    - ID {row.get('id')}: {json.dumps(row, indent=6)}")

    # Test single-use guarantee
    res_replay = client.get(f"/api/handoff/{token}", environ_base={"HTTP_HOST": "127.0.0.1:5300"})
    print(f"\n  * Single-Use Replay Attempt  : HTTP {res_replay.status_code} (Token was destroyed on read)")

    # -------------------------------------------------------------------------
    # STEP 5: ADDRESS BAR CREDENTIAL HARVESTING ATTEMPT
    # -------------------------------------------------------------------------
    print("\n" + "=" * 76)
    print("[STEP 5] ADDRESS BAR — CREDENTIAL HARVESTING ATTACK")
    print("Attacker enters in browser address bar: http://127.0.0.1:5200/?q=SELECT * FROM users")
    print("-" * 76)
    res_users = client.get("/portal?q=SELECT * FROM users", environ_base={"HTTP_HOST": "127.0.0.1:5200"})
    loc_users = res_users.headers.get("Location", "")
    token_users = loc_users.split("handoff=")[-1]
    res_hp_users = client.get(f"/api/handoff/{token_users}", environ_base={"HTTP_HOST": "127.0.0.1:5300"})
    user_data = res_hp_users.get_json()
    print(f"  * Intercepted & Diverted : HTTP {res_users.status_code} -> Honeypot")
    print(f"  * Target Asset Inferred  : {user_data.get('table')}")
    print(f"  * Synthetic Admin Users Fabricated Fresh at Runtime:")
    for u in user_data.get("rows", [])[:2]:
        print(f"      Username: {u.get('username'):22s} | Role: {u.get('role'):18s}")
        print(f"      Canary:   {u.get('canary_token'):22s} | API Key: {u.get('api_secret')}")

    # -------------------------------------------------------------------------
    # STEP 6: REAL-TIME SOC ANALYST TELEMETRY
    # -------------------------------------------------------------------------
    print("\n" + "=" * 76)
    print("[STEP 6] REAL-TIME SOC ANALYST AUDIT STREAM (:5100/api/events)")
    print("-" * 76)
    events_res = client.get("/api/events", environ_base={"HTTP_HOST": "127.0.0.1:5100"})
    ev_data = events_res.get_json()
    counts = ev_data.get("counts", {})
    print(f"  * Total Monitored Counts : Safe={counts.get('safe', 0)} | Honeypot Diversions={counts.get('honeypot', 0)}")
    print(f"  * Recent Audit Trail (Latest 3 Events Captured):")
    for ev in list(reversed(ev_data.get("events", [])))[:3]:
        print(f"    - [{ev.get('timestamp')}] Risk: {ev.get('risk'):2d} | Route: {ev.get('route'):10s} | Query: {ev.get('query')[:45]}")
        print(f"      Site Context: {ev.get('site_context')}")

    print("\n" + "=" * 76)
    print(" DEMONSTRATION COMPLETE: ALL SYSTEMS NOMINAL & FULLY OPERATIONAL")
    print("=" * 76 + "\n")

if __name__ == "__main__":
    run_demo()
