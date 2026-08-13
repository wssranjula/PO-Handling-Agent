$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv")) {
    py -3.12 -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

# Some Windows application-control policies reject downloaded native wheels.
# Building xxhash locally produces an equivalent extension trusted by that policy.
& .\.venv\Scripts\python.exe -c "import xxhash" 2>$null
if ($LASTEXITCODE -ne 0) {
    .\.venv\Scripts\python.exe -m pip install --force-reinstall --no-binary xxhash "xxhash>=3.5,<4"
}

docker compose up -d postgres
Write-Output "Setup complete. Activate with: .\.venv\Scripts\Activate.ps1"
