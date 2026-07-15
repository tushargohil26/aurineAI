$ErrorActionPreference = "Stop"

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
  Write-Host "Python virtual environment is missing. Creating it..." -ForegroundColor Yellow
  python -m venv .venv
  .\.venv\Scripts\python.exe -m pip install -r requirements.txt
}

$ip = (Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" } |
  Select-Object -First 1 -ExpandProperty IPAddress)

if (-not $ip) {
  $ip = "127.0.0.1"
}

Write-Host ""
Write-Host "Aurine desktop URL: http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "Aurine mobile URL:  http://$ip`:8000" -ForegroundColor Cyan
Write-Host "Phone and PC must be on the same Wi-Fi. If Windows Firewall asks, allow private network access." -ForegroundColor Yellow
Write-Host ""

.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000


