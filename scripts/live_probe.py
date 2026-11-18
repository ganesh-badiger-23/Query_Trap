"""Live probe of the running Query Trap demo services."""
import json
import urllib.request
import urllib.error


def get(url):
    with urllib.request.urlopen(url, timeout=5) as r:
        return r.getcode(), json.loads(r.read().decode())


def post(url, data, origin="http://127.0.0.1:5200"):
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json", "Origin": origin},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.getcode(), json.loads(r.read().decode())


def main():
    print("=== 1. Checking Health of Live Services ===")
    for port, expected_role in [(5100, "sentinel"), (5200, "storefront"), (5300, "honeypot")]:
        code, h = get(f"http://127.0.0.1:{port}/api/health")
        print(f"Port {port}: status={h['status']}, role={h['mode']}, events={h['events']}")
        assert code == 200
        assert h["status"] == "ok"
        assert h["mode"] == expected_role

    print("\n=== 2. Testing Storefront Safe Search on 5100 ===")
    code, safe = post(
        "http://127.0.0.1:5100/api/query",
        {"query": "notebook", "search_term": "notebook", "site_context": "http://127.0.0.1:5200/"},
    )
    print(f"Safe Search -> Route: {safe['route']}, Bucket: {safe['bucket']}, Risk: {safe['risk']}")
    assert safe["bucket"] == "safe"
    assert safe["route"] == "production"
    assert safe["handoff"] is None

    print("\n=== 3. Testing Storefront Attack SQLi (\"' OR '1'='1\") ===")
    code, attack = post(
        "http://127.0.0.1:5100/api/query",
        {"query": "notebook' OR '1'='1", "search_term": "' OR '1'='1", "site_context": "http://127.0.0.1:5200/"},
    )
    print(f"Attack Search -> Route: {attack['route']}, Bucket: {attack['bucket']}, Threats: {attack['threats']}")
    print(f"Handoff Token Generated: {attack['handoff']}")
    assert attack["bucket"] == "honeypot"
    assert attack["route"] == "honeypot"
    assert attack["handoff"] is not None

    print("\n=== 4. Testing Decoy Handoff Retrieval on Honeypot (:5300) ===")
    code, handoff = get(f"http://127.0.0.1:5300/api/handoff/{attack['handoff']}")
    print(f"Decoy Table: {handoff['table']}")
    print(f"Decoy Rows Count: {len(handoff['rows'])}")
    print(f"Decoy Site Context: {handoff['site_context']}")
    assert handoff["bucket"] == "honeypot"
    assert len(handoff["rows"]) > 0

    print("\n=== 5. Testing Single-Use Token Invalidation ===")
    try:
        get(f"http://127.0.0.1:5300/api/handoff/{attack['handoff']}")
        print("FAILED: Token was not single-use")
        assert False
    except urllib.error.HTTPError as e:
        print(f"SUCCESS: Token expired/deleted on first use (HTTP {e.code} Not Found)")
        assert e.code == 404

    print("\n=== 6. Checking Live SOC Telemetry Stream on 5100 ===")
    code, events = get("http://127.0.0.1:5100/api/events")
    print(f"Total Events Recorded: {len(events['events'])}")
    print(f"Safe Counts: {events['counts']['safe']}")
    print(f"Honeypot Counts: {events['counts']['honeypot']}")
    print(f"Latest Event Query: {events['events'][-1]['query']}")
    print(f"Latest Event Threats: {events['events'][-1]['threats']}")

    print("\n==============================================")
    print("ALL 6 LIVE END-TO-END DEMO CHECKS PASSED (100%)!")
    print("==============================================")


if __name__ == "__main__":
    main()

