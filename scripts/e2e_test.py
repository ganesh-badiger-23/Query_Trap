"""End-to-end multi-service live HTTP test for Query Trap."""
import json
import subprocess
import sys
import time
import urllib.request
import urllib.error

PORTS = [5100, 5200, 5300]
ROLES = ["sentinel", "storefront", "honeypot"]


def http_get(url: str):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.getcode(), json.loads(resp.read().decode("utf-8"))


def http_post_json(url: str, data: dict):
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.getcode(), json.loads(resp.read().decode("utf-8"))


def main():
    processes = []
    try:
        print("[*] Starting Sentinel (5100), Storefront (5200), Honeypot (5300)...")
        for port, role in zip(PORTS, ROLES):
            p = subprocess.Popen([sys.executable, "-u", "app.py", "--port", str(port), "--role", role])
            processes.append(p)

        print("[*] Waiting for services to become healthy...")
        deadline = time.time() + 15
        ready = False
        while time.time() < deadline:
            all_ok = True
            for port in PORTS:
                try:
                    code, data = http_get(f"http://127.0.0.1:{port}/api/health")
                    if code != 200 or data.get("status") != "ok":
                        all_ok = False
                except Exception as e:
                    all_ok = False
                    print(f"[-] Check port {port} error: {type(e).__name__}: {e}")
            if all_ok:
                ready = True
                break
            time.sleep(0.5)

        if not ready:
            print("[!] Timeout waiting for services to become healthy.")
            sys.exit(1)

        print("[+] All 3 services passed health check successfully!")

        # 1. Normal storefront query
        print("[*] Step 1: Performing normal storefront search for 'notebook'...")
        code, safe_res = http_post_json(
            "http://127.0.0.1:5100/api/query",
            {"query": "notebook", "search_term": "notebook", "site_context": "http://127.0.0.1:5200/"},
        )
        assert code == 200
        assert safe_res["bucket"] == "safe"
        assert safe_res["route"] == "production"
        assert safe_res["handoff"] is None
        print(f"[+] Normal search succeeded! Route: {safe_res['route']}, Risk: {safe_res['risk']}")

        # 2. Attack query with SQLi
        print("[*] Step 2: Performing attack query with \"' OR '1'='1\"...")
        code, attack_res = http_post_json(
            "http://127.0.0.1:5100/api/query",
            {"query": "' OR '1'='1", "search_term": "' OR '1'='1", "site_context": "http://127.0.0.1:5200/"},
        )
        assert code == 200
        assert attack_res["bucket"] == "honeypot"
        assert attack_res["route"] == "honeypot"
        assert attack_res["handoff"] is not None
        assert "SQLi · tautology" in attack_res["threats"]
        handoff_token = attack_res["handoff"]
        print(f"[+] Attack detected! Route: {attack_res['route']}, Threats: {attack_res['threats']}, Handoff: {handoff_token}")

        # 3. Retrieve handoff from port 5300 (Honeypot service)
        print(f"[*] Step 3: Retrieving handoff from Honeypot on port 5300...")
        code, handoff_data = http_get(f"http://127.0.0.1:5300/api/handoff/{handoff_token}")
        assert code == 200
        assert handoff_data["bucket"] == "honeypot"
        assert len(handoff_data["rows"]) > 0
        print(f"[+] Honeypot handoff retrieved successfully! Decoy Table: {handoff_data['table']}, Rows: {len(handoff_data['rows'])}")

        # 4. Verify single-use token protection
        print("[*] Step 4: Verifying single-use handoff token protection...")
        try:
            http_get(f"http://127.0.0.1:5300/api/handoff/{handoff_token}")
            assert False, "Handoff token was not deleted after first use"
        except urllib.error.HTTPError as e:
            assert e.code == 404
            print("[+] Token consumed and expired as expected (404 Not Found)!")

        # 5. Check live SOC telemetry on port 5100
        print("[*] Step 5: Checking live SOC telemetry stream on port 5100...")
        code, telemetry = http_get("http://127.0.0.1:5100/api/events")
        assert code == 200
        assert len(telemetry["events"]) >= 2
        assert telemetry["counts"]["safe"] >= 1
        assert telemetry["counts"]["honeypot"] >= 1
        print(f"[+] Telemetry verified! Total events: {len(telemetry['events'])}, Counts: {telemetry['counts']}")

        print("\n==============================================")
        print("ALL END-TO-END DEMO FLOW TESTS PASSED (100%)!")
        print("==============================================")

    finally:
        print("[*] Cleaning up running demo processes...")
        for p in processes:
            p.terminate()
            try:
                p.wait(timeout=2)
            except Exception:
                p.kill()
        print("[+] Cleanup complete.")


if __name__ == "__main__":
    main()
