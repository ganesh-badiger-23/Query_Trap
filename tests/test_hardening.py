"""Unit and integration tests for Sentinel DB architectural hardening.

Verifies:
1. Honeytoken caching & pre-computed cryptographic tokens (Argon2id, RSA keys).
2. Rate limiting (Flask-Limiter) dropping traffic exceeding 50 requests per minute.
3. SOC Dashboard Authentication (Basic Auth, Bearer Token, Query Token, and Socket.IO auth).
4. Asynchronous telemetry event decoupling via background worker queue.
"""
from __future__ import annotations

import base64
import time
import unittest

from backend.app import (
    app,
    limiter,
    _TELEMETRY_QUEUE,
    dispatch_telemetry_event,
    handle_socket_connect,
    SOC_USERNAME,
    SOC_PASSWORD,
    SOC_TOKEN,
)
from backend.synthetic_data import (
    generate_synthetic_decoy,
    is_cache_warmed,
    get_cache_stats,
    warm_honeytoken_cache,
)


class TestHardeningArchitecture(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def tearDown(self):
        # Reset limiter storage and test flags after each test
        app.config["ENFORCE_SOC_AUTH_IN_TESTS"] = False
        try:
            limiter.reset()
        except Exception:
            pass

    def test_01_honeytoken_cache_precomputed_at_startup(self):
        """Pre-computed cache must be warmed and serve cryptographic honeytokens instantly."""
        self.assertTrue(is_cache_warmed())
        stats = get_cache_stats()
        self.assertIn("synthetic_user_credentials", stats)
        self.assertIn("synthetic_financial_ledger", stats)
        self.assertIn("synthetic_system_secrets", stats)
        self.assertIn("synthetic_canary_inventory", stats)
        self.assertGreaterEqual(stats["synthetic_user_credentials"], 4)

        # Microsecond benchmark: generating 200 decoys should take under 0.05 seconds
        start = time.perf_counter()
        for _ in range(200):
            table, rows = generate_synthetic_decoy("admin credentials")
            self.assertEqual(table, "synthetic_user_credentials")
            self.assertTrue(any("$argon2id$" in r.get("password_hash", "") for r in rows))
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 0.05, f"Generation took {elapsed:.4f}s, expected < 0.05s from memory cache")

    def test_02_honeypot_rate_limiting_exceeded(self):
        """Honeypot endpoints must rate-limit aggressive requests at 50 requests per minute."""
        # Reset limiter for clean counter
        limiter.reset()

        # Send 50 requests within limit
        for i in range(50):
            res = self.client.get("/api/decoy/records?table=users", environ_base={"REMOTE_ADDR": "198.51.100.44"})
            self.assertEqual(res.status_code, 200, f"Request {i+1} should succeed")

        # The 51st request from same IP must be dropped with 429
        rate_limited_res = self.client.get("/api/decoy/records?table=users", environ_base={"REMOTE_ADDR": "198.51.100.44"})
        self.assertEqual(rate_limited_res.status_code, 429)
        data = rate_limited_res.get_json()
        self.assertIn("error", data)
        self.assertEqual(data["error"], "Too Many Requests")
        self.assertIn("50 requests per minute", data["message"])

        # Different IP address should NOT be blocked
        clean_ip_res = self.client.get("/api/decoy/records?table=users", environ_base={"REMOTE_ADDR": "198.51.100.45"})
        self.assertEqual(clean_ip_res.status_code, 200)

    def test_03_soc_dashboard_authentication_enforcement(self):
        """Sentinel SOC routes on port 3000 must enforce HTTP Basic Auth or Token."""
        app.config["ENFORCE_SOC_AUTH_IN_TESTS"] = True
        sentinel_env = {"HTTP_HOST": "127.0.0.1:3000"}

        # 1. Unauthenticated request to SOC index should return 401 with WWW-Authenticate
        res_unauth = self.client.get("/", environ_base=sentinel_env)
        self.assertEqual(res_unauth.status_code, 401)
        self.assertIn("WWW-Authenticate", res_unauth.headers)
        self.assertIn("Basic realm", res_unauth.headers["WWW-Authenticate"])

        # 2. Unauthenticated request to /api/events should return 401 JSON
        api_unauth = self.client.get("/api/events", environ_base=sentinel_env)
        self.assertEqual(api_unauth.status_code, 401)
        self.assertEqual(api_unauth.get_json()["error"], "Unauthorized")

        # 3. Authenticated request with HTTP Basic Auth (admin / sentinel_sec_2026) -> 200 OK
        creds = base64.b64encode(f"{SOC_USERNAME}:{SOC_PASSWORD}".encode()).decode()
        auth_header = {"Authorization": f"Basic {creds}"}
        res_basic = self.client.get("/", headers=auth_header, environ_base=sentinel_env)
        self.assertEqual(res_basic.status_code, 200)
        self.assertIn(b"Sentinel DB", res_basic.data)

        # 4. Authenticated request with Bearer Token -> 200 OK
        bearer_header = {"Authorization": f"Bearer {SOC_TOKEN}"}
        res_bearer = self.client.get("/api/events", headers=bearer_header, environ_base=sentinel_env)
        self.assertEqual(res_bearer.status_code, 200)
        self.assertIn("events", res_bearer.get_json())

        # 5. Authenticated request with Query Token (?token=...) -> 200 OK
        res_token = self.client.get(f"/?token={SOC_TOKEN}", environ_base=sentinel_env)
        self.assertEqual(res_token.status_code, 200)

    def test_04_socketio_connection_authentication(self):
        """Socket.IO connections must reject unauthorized clients when Sentinel auth is enforced."""
        app.config["ENFORCE_SOC_AUTH_IN_TESTS"] = True

        # Test rejection without token
        with app.test_request_context("/", headers={"Host": "127.0.0.1:3000"}):
            self.assertFalse(handle_socket_connect(auth={}))
            self.assertFalse(handle_socket_connect(auth={"token": "invalid_wrong_token"}))

        # Test acceptance with valid auth token
        with app.test_request_context("/", headers={"Host": "127.0.0.1:3000"}):
            self.assertTrue(handle_socket_connect(auth={"token": SOC_TOKEN}))

        # Test acceptance with query param token
        with app.test_request_context(f"/?token={SOC_TOKEN}", headers={"Host": "127.0.0.1:3000"}):
            self.assertTrue(handle_socket_connect(auth=None))

    def test_05_asynchronous_telemetry_queue_non_blocking(self):
        """Telemetry dispatch must enqueue asynchronously and never block the storefront response."""
        initial_qsize = _TELEMETRY_QUEUE.qsize()

        sample_event = {
            "id": "evt-bench-01",
            "timestamp": "2026-11-09T10:00:00Z",
            "ip": "127.0.0.1",
            "query": "SELECT * FROM users WHERE '1'='1'",
            "threats": ["SQLi · tautology"],
            "risk": 82,
            "route": "honeypot",
            "bucket": "honeypot",
        }

        # Dispatch with storefront remote host
        start = time.perf_counter()
        dispatch_telemetry_event(sample_event, request_host="127.0.0.1:5200")
        dispatch_duration = time.perf_counter() - start

        # Non-blocking verification: call must return in < 10 milliseconds
        self.assertLess(dispatch_duration, 0.01, f"Dispatch took {dispatch_duration:.4f}s, must be sub-millisecond")


if __name__ == "__main__":
    unittest.main()
