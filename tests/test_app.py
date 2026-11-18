import json
import unittest
from app import app, EVENTS, COUNTS, load_persisted_events


class TestAppEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        app.config["TESTING"] = True

    def test_health_check(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("mode", data)
        self.assertIn("service_port", data)

    def test_safe_query(self):
        payload = {
            "query": "SELECT * FROM public_catalog",
            "search_term": "notebook",
            "site_context": "http://127.0.0.1:5200/",
        }
        response = self.client.post(
            "/api/query",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["bucket"], "safe")
        self.assertEqual(data["route"], "production")
        self.assertIsNone(data["handoff"])
        self.assertIsInstance(data["rows"], list)

    def test_sqli_attack_isolation_and_handoff(self):
        payload = {
            "query": "SELECT * FROM users WHERE name = 'x' OR '1'='1",
            "search_term": "' OR '1'='1",
            "site_context": "http://127.0.0.1:5200/",
        }
        response = self.client.post(
            "/api/query",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["bucket"], "honeypot")
        self.assertEqual(data["route"], "honeypot")
        self.assertIsNotNone(data["handoff"])
        self.assertIn("SQLi · tautology", data["threats"])

        # Test handoff token consumption
        token = data["handoff"]
        handoff_res = self.client.get(f"/api/handoff/{token}")
        self.assertEqual(handoff_res.status_code, 200)
        handoff_data = handoff_res.get_json()
        self.assertEqual(handoff_data["bucket"], "honeypot")
        self.assertIn("rows", handoff_data)

        # Single-use guarantee: second attempt should 404
        second_attempt = self.client.get(f"/api/handoff/{token}")
        self.assertEqual(second_attempt.status_code, 404)

    def test_xss_payload_isolation(self):
        payload = {
            "query": "<script>alert('pwned')</script> SELECT * FROM public_catalog",
            "site_context": "http://127.0.0.1:5200/",
        }
        response = self.client.post(
            "/api/query",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["bucket"], "honeypot")
        self.assertIn("XSS · script tag", data["threats"])

    def test_invalid_query_payload(self):
        response = self.client.post(
            "/api/query",
            data=json.dumps({"query": "   "}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_cors_preflight(self):
        response = self.client.options(
            "/api/query",
            headers={
                "Origin": "http://127.0.0.1:5200",
                "Access-Control-Request-Method": "POST",
            },
        )
        self.assertIn(response.status_code, (200, 204))
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "http://127.0.0.1:5200")

    def test_decoy_records_api(self):
        for table in ("users", "financial_records", "public_catalog"):
            with self.subTest(table=table):
                response = self.client.get(f"/api/decoy/records?table={table}")
                self.assertEqual(response.status_code, 200)
                data = response.get_json()
                self.assertEqual(data["table"], table)
                self.assertGreater(len(data["rows"]), 0)

    def test_events_api(self):
        response = self.client.get("/api/events")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("events", data)
        self.assertIn("counts", data)

    def test_html_views(self):
        for path in ("/", "/portal", "/honeypot"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn(b"<!doctype html>", response.data.lower())

    def test_address_bar_safe_query(self):
        response = self.client.get("/portal?q=notebook", environ_base={"HTTP_HOST": "127.0.0.1:5200"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Field notebook", response.data)
        self.assertIn(b"HARBOR", response.data)

    def test_address_bar_attack_redirect_to_honeypot(self):
        # Attack query in URL parameter
        response = self.client.get("/portal?q=' OR '1'='1", environ_base={"HTTP_HOST": "127.0.0.1:5200"})
        # Must issue a 302 redirect
        self.assertEqual(response.status_code, 302)
        location = response.headers.get("Location", "")
        self.assertIn("handoff=", location)
        self.assertTrue(":5300" in location or "/honeypot" in location)

        # Extract handoff token and verify synthetic honeypot data
        token = location.split("handoff=")[-1]
        handoff_res = self.client.get(f"/api/handoff/{token}")
        self.assertEqual(handoff_res.status_code, 200)
        data = handoff_res.get_json()
        self.assertTrue(data.get("is_synthetic"))
        self.assertEqual(data.get("bucket"), "honeypot")
        self.assertGreater(len(data.get("rows", [])), 0)

    def test_unauthorized_port_probe_redirect_to_honeypot(self):
        # Attack trying to probe or access internal port parameter
        response = self.client.get("/portal?port=5100", environ_base={"HTTP_HOST": "127.0.0.1:5200"})
        self.assertEqual(response.status_code, 302)
        location = response.headers.get("Location", "")
        self.assertIn("handoff=", location)

    def test_synthetic_datasets_and_export(self):
        # Test synthetic datasets catalog
        res = self.client.get("/api/decoy/synthetic")
        self.assertEqual(res.status_code, 200)
        datasets = res.get_json()
        self.assertIn("synthetic_users", datasets)
        self.assertIn("synthetic_financials", datasets)
        self.assertIn("synthetic_secrets", datasets)

        # Test CSV and JSON export
        for fmt in ("json", "csv"):
            with self.subTest(fmt=fmt):
                exp_res = self.client.get(f"/api/decoy/export?type=users&format={fmt}")
                self.assertEqual(exp_res.status_code, 200)
                if fmt == "json":
                    self.assertIsInstance(exp_res.get_json(), list)
                else:
                    self.assertIn(b"canary_token", exp_res.data)


if __name__ == "__main__":
    unittest.main()

