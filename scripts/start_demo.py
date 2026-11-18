"""Cross-platform, robust service launcher for Sentinel DB demo."""
import os
import sys
import time
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

SERVICES = [
    {"name": "Sentinel DB", "port": 3000, "role": "sentinel"},
    {"name": "Storefront", "port": 5200, "role": "storefront"},
    {"name": "Honeypot", "port": 5300, "role": "honeypot"},
]

def check_port_free(port: int):
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) != 0

def stop_services():
    # Use taskkill on Windows to ensure clean shutdown of existing listeners
    if os.name == "nt":
        for s in SERVICES:
            try:
                out = subprocess.check_output(f"netstat -ano | findstr :{s['port']}", shell=True, text=True)
                for line in out.strip().splitlines():
                    parts = line.split()
                    if len(parts) >= 5 and "LISTENING" in parts:
                        pid = parts[-1]
                        subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
    time.sleep(1)

def start_services():
    print("Checking ports and stopping any stale processes...")
    stop_services()

    for s in SERVICES:
        if not check_port_free(s["port"]):
            print(f"Port {s['port']} is still busy! Forcing stop...")
            stop_services()
            break

    processes = []
    creation_flags = 0
    if os.name == "nt":
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

    for s in SERVICES:
        stdout_file = open(DATA_DIR / f"service-{s['port']}.log", "w", encoding="utf-8")
        stderr_file = open(DATA_DIR / f"service-{s['port']}.err", "w", encoding="utf-8")
        
        cmd = [
            sys.executable,
            "-u",
            str(ROOT / "app.py"),
            "--port", str(s["port"]),
            "--role", s["role"]
        ]
        
        proc = subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            stdin=subprocess.DEVNULL,
            stdout=stdout_file,
            stderr=stderr_file,
            creationflags=creation_flags,
        )
        processes.append((s, proc))
        print(f"Spawned {s['name']} (role: {s['role']}) on port {s['port']} [PID {proc.pid}]")

    print("\nWaiting for service health checks...")
    deadline = time.time() + 30
    all_ready = False
    
    while time.time() < deadline:
        ready_count = 0
        for s in SERVICES:
            try:
                req = urllib.request.urlopen(f"http://127.0.0.1:{s['port']}/api/health", timeout=1.5)
                if req.status == 200:
                    ready_count += 1
            except Exception:
                pass
        if ready_count == len(SERVICES):
            all_ready = True
            break
        time.sleep(0.5)

    if not all_ready:
        print("\nERROR: One or more services failed to report healthy:")
        for s in SERVICES:
            print(f"\n--- Port {s['port']} Logs ---")
            err_path = DATA_DIR / f"service-{s['port']}.err"
            if err_path.exists():
                print(err_path.read_text(encoding="utf-8", errors="replace")[-500:])
        sys.exit(1)

    print("\n==================================================================")
    print(" ALL 3 DEMO SERVICES ARE RUNNING AND READY!")
    print("==================================================================")
    print(" 1. Sentinel SOC Analyst Dashboard : http://127.0.0.1:3000/")
    print(" 2. Storefront (Harbor & Pine)     : http://127.0.0.1:5200/")
    print(" 3. Honeypot (Northstar Workspace) : http://127.0.0.1:5300/")
    print("==================================================================")
    print("\n[INFO] Press Ctrl+C at any time to stop all services cleanly.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down demo services...")
        for _, proc in processes:
            try:
                proc.terminate()
            except Exception:
                pass
        stop_services()
        print("Demo services stopped.")

if __name__ == "__main__":
    start_services()
