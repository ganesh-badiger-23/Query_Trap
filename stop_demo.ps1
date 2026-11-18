$ports = @(3000, 5100, 5200, 5300)

foreach ($port in $ports) {
    try {
        $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        foreach ($conn in $conns) {
            Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    } catch {}
}

try {
    $pattern = 'app.py.*--port (' + ($ports -join '|') + ')'
    $services = Get-Process -Name python, python3 -ErrorAction SilentlyContinue | Where-Object {
        try { $_.CommandLine -match $pattern } catch { $false }
    }
    foreach ($service in $services) {
        try { Stop-Process -Id $service.Id -Force -ErrorAction SilentlyContinue } catch {}
    }
} catch {}

Write-Output 'Stopped Sentinel DB demo services on ports 3000, 5200, and 5300.'
