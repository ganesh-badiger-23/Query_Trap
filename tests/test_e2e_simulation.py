"""Comprehensive end-to-end multi-service simulation test.

Simulates all 3 services (Sentinel :5100, Storefront :5200, Honeypot :5300)
running together, validating cross-service redirects, handoff lifecycle,
durable SQLite telemetry, and attack diversions.
"""
import json
import unittest
from app import app, load_persisted_events, DATA_DIR, db_session


class TestEndToEndSimulation(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def sentinel_req(self, method: str, path: str, **kwargs):
        return getattr(self.client, method)(path, base_url="http://127.0.0.1:3000", **kwargs)

    def storefront_req(self, method: str, path: str, **kwargs):
        return getattr(self.client, method)(path, base_url="http://127.0.0.1:5200", **kwargs)

    def honeypot_req(self, method: str, path: str, **kwargs):
        return getattr(self.client, method)(path, base_url="http://127.0.0.1:5300", **kwargs)

    def test_01_all_services_health(self):
        """Verify health endpoints on all three distinct demo service ports."""
        h_sentinel = self.sentinel_req("get", "/api/health").get_json()
        self.assertEqual(h_sentinel["status"], "ok")
        self.assertEqual(h_sentinel["service_port"], 3000)
        self.assertEqual(h_sentinel["mode"], "sentinel")

        h_storefront = self.storefront_req("get", "/api/health").get_json()
        self.assertEqual(h_storefront["status"], "ok")
        self.assertEqual(h_storefront["service_port"], 5200)
        self.assertEqual(h_storefront["mode"], "storefront")

        h_honeypot = self.honeypot_req("get", "/api/health").get_json()
        self.assertEqual(h_honeypot["status"], "ok")
        self.assertEqual(h_honeypot["service_port"], 5300)
        self.assertEqual(h_honeypot["mode"], "honeypot")

    def test_02_storefront_normal_search_flow(self):
        """Normal catalog search on storefront should route to production demo DB."""
        payload = {
            "query": "field notebook",
            "search_term": "notebook",
            "site_context": "http://127.0.0.1:5200/",
        }
        res = self.sentinel_req(
            "post",
            "/api/query",
            data=json.dumps(payload),
            headers={"Origin": "http://127.0.0.1:5200", "Content-Type": "application/json"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["bucket"], "safe")
        self.assertEqual(data["route"], "production")
        self.assertIsNone(data["handoff"])
        self.assertLess(data["risk"], 31)
        self.assertTrue(any("notebook" in row.get("item", "").lower() for row in data["rows"]))

    def test_03_storefront_sqli_attack_and_honeypot_handoff(self):
        """SQLi tautology attack should be diverted to honeypot with a single-use token."""
        attack_payload = {
            "query": "notebook' OR '1'='1",
            "search_term": "' OR '1'='1",
            "site_context": "http://127.0.0.1:5200/",
        }
        res = self.sentinel_req(
            "post",
            "/api/query",
            data=json.dumps(attack_payload),
            headers={"Origin": "http://127.0.0.1:5200", "Content-Type": "application/json"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["bucket"], "honeypot")
        self.assertEqual(data["route"], "honeypot")
        self.assertIn("SQLi · tautology", data["threats"])
        self.assertIsNotNone(data["handoff"])
        token = data["handoff"]

        # 1. Honeypot service (5300) consumes the handoff token
        hp_res = self.honeypot_req("get", f"/api/handoff/{token}")
        self.assertEqual(hp_res.status_code, 200)
        hp_data = hp_res.get_json()
        self.assertEqual(hp_data["bucket"], "honeypot")
        self.assertEqual(hp_data["site_context"], "http://127.0.0.1:5200/")
        self.assertGreater(len(hp_data["rows"]), 0)

        # 2. Token should be deleted from DB (single-use guarantee)
        replay_res = self.honeypot_req("get", f"/api/handoff/{token}")
        self.assertEqual(replay_res.status_code, 404)

        # 3. Sentinel telemetry on 5100 should record this attack
        events_res = self.sentinel_req("get", "/api/events")
        self.assertEqual(events_res.status_code, 200)
        events_data = events_res.get_json()
        self.assertGreaterEqual(events_data["counts"]["honeypot"], 1)
        latest_event = events_data["events"][-1]
        self.assertEqual(latest_event["bucket"], "honeypot")
        self.assertIn("SQLi · tautology", latest_event["threats"])

    def test_04_xss_attack_containment(self):
        """XSS payload should trigger event handler/script signatures and honeypot isolation."""
        xss_payload = {
            "query": "<script>alert('xss')</script> SELECT * FROM public_catalog",
            "site_context": "http://127.0.0.1:5200/",
        }
        res = self.sentinel_req(
            "post",
            "/api/query",
            data=json.dumps(xss_payload),
            headers={"Origin": "http://127.0.0.1:5200", "Content-Type": "application/json"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["bucket"], "honeypot")
        self.assertIn("XSS · script tag", data["threats"])

    def test_05_destructive_sqli_flagged_critical(self):
        """Destructive SQL commands (DROP TABLE) must be flagged with critical risk band."""
        destructive_payload = {
            "query": "SELECT * FROM users; DROP TABLE users; --",
            "site_context": "http://127.0.0.1:5200/",
        }
        res = self.sentinel_req(
            "post",
            "/api/query",
            data=json.dumps(destructive_payload),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["risk_band"], "critical")
        self.assertGreaterEqual(data["risk"], 70)
        self.assertEqual(data["bucket"], "honeypot")

    def test_06_decoy_records_live_refresh(self):
        """Decoy explorer can dynamically fetch records from honeypot database."""
        for table in ("users", "financial_records", "public_catalog"):
            res = self.honeypot_req("get", f"/api/decoy/records?table={table}")
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertEqual(data["table"], table)
            self.assertGreater(len(data["rows"]), 0)

    def test_07_cors_validation_across_ports(self):
        """Verify CORS allows storefront origin :5200 and handles OPTIONS preflight."""
        preflight = self.sentinel_req(
            "options",
            "/api/query",
            headers={
                "Origin": "http://127.0.0.1:5200",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        self.assertIn(preflight.status_code, (200, 204))
        self.assertEqual(preflight.headers.get("Access-Control-Allow-Origin"), "http://127.0.0.1:5200")

    def test_08_persistent_telemetry_across_reloads(self):
        """Verify telemetry events are durable in SQLite and reloadable."""
        unique_marker = "audit_marker_verify_12345"
        self.sentinel_req(
            "post",
            "/api/query",
            data=json.dumps({"query": f"SELECT * FROM public_catalog -- {unique_marker}"}),
            headers={"Content-Type": "application/json"},
        )
        with db_session(DATA_DIR / "production.db") as db:
            row = db.execute("SELECT * FROM telemetry_events WHERE query LIKE ?", (f"%{unique_marker}%",)).fetchone()
            self.assertIsNotNone(row)

        load_persisted_events()
        events_res = self.sentinel_req("get", "/api/events").get_json()
        self.assertTrue(any(unique_marker in e["query"] for e in events_res["events"]))


if __name__ == "__main__":
    unittest.main()
