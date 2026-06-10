param(
    [string]$Python = "python",
    [string]$Model = "qwen2.5:3b-instruct",
    [switch]$SkipOllama,
    [switch]$RunApp
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Test-Command {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Step "Checking Python"
if (-not (Test-Command $Python)) {
    throw "Python command '$Python' was not found. Install Python 3.10+ first, then rerun this script."
}

& $Python --version

Write-Step "Creating virtual environment"
if (-not (Test-Path ".venv")) {
    & $Python -m venv .venv
}

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    throw "Virtual environment was not created correctly: $VenvPython"
}

Write-Step "Installing Python dependencies"
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r requirements.txt

Write-Step "Preparing .env"
if (-not (Test-Path ".env") -and (Test-Path ".env.example")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example"
}

if (-not $SkipOllama) {
    Write-Step "Checking Ollama"
    if (-not (Test-Command "ollama")) {
        if (Test-Command "winget") {
            Write-Host "Ollama was not found. Installing with winget..."
            winget install --id Ollama.Ollama --exact --accept-source-agreements --accept-package-agreements
        }
        else {
            throw "Ollama was not found and winget is unavailable. Install Ollama from https://ollama.com/download, then rerun this script."
        }
    }

    if (-not (Test-Command "ollama")) {
        Write-Warning "Ollama was installed but is not available in this terminal yet. Open a new terminal and run: ollama pull $Model"
    }
    else {
        Write-Step "Starting Ollama server"
        try {
            $tags = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 2
            if ($tags.StatusCode -eq 200) {
                Write-Host "Ollama is already running."
            }
        }
        catch {
            Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
            Start-Sleep -Seconds 5
        }

        Write-Step "Pulling local AI model: $Model"
        & ollama pull $Model
    }
}

Write-Step "Verifying project imports"
& $VenvPython -m py_compile src/config.py src/llm_services.py src/indexer.py src/searcher.py src/app.py

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Activate the environment with:"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "Run the app with:"
Write-Host "  streamlit run src/app.py"

if ($RunApp) {
    Write-Step "Starting Streamlit"
    & (Join-Path $ProjectRoot ".venv\Scripts\streamlit.exe") run src/app.py
}
