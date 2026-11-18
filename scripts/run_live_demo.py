import urllib.request
import urllib.parse
import json
import sys

def probe(url, name, follow_redirects=False):
    print(f"\n======================================================================")
    print(f" DEMO STEP: {name}")
    print(f" URL: {url}")
    print(f"======================================================================")
    
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    opener = urllib.request.build_opener(NoRedirect) if not follow_redirects else urllib.request.build_opener()
    
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DemoBrowser/1.0"})
        resp = opener.open(req)
        body = resp.read().decode('utf-8', errors='replace')
        print(f"STATUS CODE: {resp.status}")
        print(f"HEADERS: {dict(resp.headers)}")
        if "json" in resp.headers.get("Content-Type", ""):
            print("RESPONSE JSON (sample):")
            print(json.dumps(json.loads(body), indent=2)[:1200])
        else:
            print(f"RESPONSE HTML (length {len(body)} chars, sample):")
            lines = [line.strip() for line in body.splitlines() if line.strip()][:15]
            print("\n".join(lines[:8]))
        return resp.status, dict(resp.headers), body
    except urllib.error.HTTPError as e:
        print(f"HTTP ERROR CODE: {e.code}")
        headers = dict(e.headers)
        print(f"LOCATION: {headers.get('Location', 'None')}")
        return e.code, headers, ""
    except Exception as e:
        print(f"ERROR: {e}")
        return None, {}, ""

print("\n--- [1] PROBING HEALTH OF ALL 3 SERVICES ---")
probe("http://127.0.0.1:5100/api/health", "Sentinel SOC Health Check", follow_redirects=True)
probe("http://127.0.0.1:5200/api/health", "Storefront Health Check", follow_redirects=True)
probe("http://127.0.0.1:5300/api/health", "Honeypot Health Check", follow_redirects=True)

print("\n--- [2] ADDRESS BAR SAFE SEARCH: ?q=notebook ---")
probe("http://127.0.0.1:5200/?q=notebook", "Storefront Safe Address-Bar Query", follow_redirects=False)

print("\n--- [3] ADDRESS BAR ATTACK: ?q=' OR '1'='1 ---")
code, headers, _ = probe("http://127.0.0.1:5200/?q=%27+OR+%271%27%3D%271", "Storefront SQLi Address-Bar Attack", follow_redirects=False)
redirect_url = headers.get("Location")

if redirect_url:
    print(f"\n---> Successfully intercepted attack! Redirect issued to: {redirect_url}")
    # Extract token
    token = redirect_url.split("handoff=")[-1]
    print(f"---> Single-use Handoff Token: {token}")
    
    print("\n--- [4] FETCHING HONEYPOT SYNTHETIC DECOY DATA VIA HANDOFF ---")
    probe(f"http://127.0.0.1:5300/api/handoff/{token}", "Honeypot Single-Use Token Consumption", follow_redirects=True)

print("\n--- [5] VERIFYING SENTINEL SOC TELEMETRY ---")
probe("http://127.0.0.1:5100/api/events", "Sentinel SOC Live Telemetry Feed", follow_redirects=True)

