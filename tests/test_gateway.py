import unittest
from sentinel_gateway import assess_payload, inspect_and_route, DEFAULT_THRESHOLD


class TestSentinelGateway(unittest.TestCase):
    def test_safe_catalog_query(self):
        assessment = assess_payload("notebook", asset="public_catalog")
        self.assertEqual(assessment.threats, ())
        self.assertEqual(assessment.payload_severity, 0)
        self.assertEqual(assessment.asset_sensitivity, 10)
        self.assertEqual(assessment.risk_band, "safe")
        self.assertLess(assessment.risk_score, DEFAULT_THRESHOLD)

    def test_sqli_tautology(self):
        payloads = [
            "' OR '1'='1",
            "' OR 1=1",
            "admin' OR '1'='1' --",
            "' or ''='",
        ]
        for p in payloads:
            with self.subTest(payload=p):
                assessment = assess_payload(p)
                self.assertIn("SQLi · tautology", assessment.threats)
                self.assertGreaterEqual(assessment.payload_severity, 40)
                self.assertGreaterEqual(assessment.risk_score, DEFAULT_THRESHOLD)
                self.assertIn(assessment.risk_band, ("suspicious", "critical"))

    def test_xss_detection(self):
        payloads = [
            ("<script>alert('xss')</script>", "XSS · script tag"),
            ("javascript:alert(document.cookie)", "XSS · javascript URL"),
            ("<img src=x onerror=alert(1)>", "XSS · event handler"),
            ("<iframe src='http://evil.com'></iframe>", "XSS · embedded tag"),
        ]
        for p, expected_threat in payloads:
            with self.subTest(payload=p):
                assessment = assess_payload(p)
                self.assertIn(expected_threat, assessment.threats)
                self.assertGreaterEqual(assessment.risk_score, DEFAULT_THRESHOLD)

    def test_destructive_sqli(self):
        assessment = assess_payload("SELECT * FROM users; DROP TABLE users; --")
        self.assertTrue(any("destructive" in t for t in assessment.threats))
        self.assertIn("SQLi · comment terminator", assessment.threats)
        self.assertEqual(assessment.risk_band, "critical")
        self.assertGreaterEqual(assessment.risk_score, 70)

    def test_union_select(self):
        assessment = assess_payload("' UNION SELECT 1, null, null--")
        self.assertIn("SQLi · UNION SELECT", assessment.threats)
        self.assertGreaterEqual(assessment.risk_score, DEFAULT_THRESHOLD)

    def test_custom_sensitivity_map(self):
        custom_map = {"custom_orders": 35}
        assessment = assess_payload("SELECT * FROM custom_orders", asset="custom_orders", sensitivity_map=custom_map)
        self.assertEqual(assessment.asset_sensitivity, 35)

    def test_invalid_sensitivity_map(self):
        with self.assertRaises(ValueError):
            assess_payload("test", sensitivity_map={"bad": 100})

    def test_invalid_payload_type(self):
        with self.assertRaises(TypeError):
            assess_payload(12345)  # type: ignore

    def test_inspect_and_route_safe(self):
        prod_called = False
        decoy_called = False

        def prod_op():
            nonlocal prod_called
            prod_called = True
            return "prod_data"

        def decoy_op():
            nonlocal decoy_called
            decoy_called = True
            return "decoy_data"

        outcome = inspect_and_route(
            "notebook",
            production_operation=prod_op,
            honeypot_operation=decoy_op,
            asset="public_catalog",
        )
        self.assertTrue(prod_called)
        self.assertFalse(decoy_called)
        self.assertEqual(outcome.route, "production")
        self.assertEqual(outcome.bucket, "safe")
        self.assertEqual(outcome.result, "prod_data")

    def test_inspect_and_route_honeypot(self):
        prod_called = False
        decoy_called = False

        def prod_op():
            nonlocal prod_called
            prod_called = True
            return "prod_data"

        def decoy_op():
            nonlocal decoy_called
            decoy_called = True
            return "decoy_data"

        outcome = inspect_and_route(
            "' OR '1'='1",
            production_operation=prod_op,
            honeypot_operation=decoy_op,
        )
        self.assertFalse(prod_called)
        self.assertTrue(decoy_called)
        self.assertEqual(outcome.route, "honeypot")
        self.assertEqual(outcome.bucket, "honeypot")
        self.assertEqual(outcome.result, "decoy_data")


if __name__ == "__main__":
    unittest.main()

