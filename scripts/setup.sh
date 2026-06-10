#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
MODEL="${MODEL:-qwen2.5:3b-instruct}"
SKIP_OLLAMA="${SKIP_OLLAMA:-0}"
RUN_APP="${RUN_APP:-0}"

step() {
    printf '\n==> %s\n' "$1"
}

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

step "Checking Python"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "Python command '$PYTHON_BIN' was not found. Install Python 3.10+ first." >&2
    exit 1
fi
"$PYTHON_BIN" --version

step "Creating virtual environment"
if [ ! -d ".venv" ]; then
    "$PYTHON_BIN" -m venv .venv
fi

VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
if [ ! -x "$VENV_PYTHON" ]; then
    echo "Virtual environment was not created correctly: $VENV_PYTHON" >&2
    exit 1
fi

step "Installing Python dependencies"
"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install -r requirements.txt

step "Preparing .env"
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp ".env.example" ".env"
    echo "Created .env from .env.example"
fi

if [ "$SKIP_OLLAMA" != "1" ]; then
    step "Checking Ollama"
    if ! command -v ollama >/dev/null 2>&1; then
        if [[ "$(uname -s)" == "Darwin" ]] && command -v brew >/dev/null 2>&1; then
            brew install ollama
        elif [[ "$(uname -s)" == "Linux" ]]; then
            curl -fsSL https://ollama.com/install.sh | sh
        else
            echo "Ollama was not found. Install it from https://ollama.com/download, then rerun this script." >&2
            exit 1
        fi
    fi

    step "Starting Ollama server"
    if ! curl -fsS http://localhost:11434/api/tags >/dev/null 2>&1; then
        nohup ollama serve >/tmp/ollama-serve.log 2>&1 &
        sleep 5
    fi

    step "Pulling local AI model: $MODEL"
    ollama pull "$MODEL"
fi

step "Verifying project imports"
"$VENV_PYTHON" -m py_compile src/config.py src/llm_services.py src/indexer.py src/searcher.py src/app.py

printf '\nSetup complete.\n'
printf 'Activate the environment with:\n'
printf '  source .venv/bin/activate\n'
printf 'Run the app with:\n'
printf '  streamlit run src/app.py\n'

if [ "$RUN_APP" = "1" ]; then
    step "Starting Streamlit"
    "$PROJECT_ROOT/.venv/bin/streamlit" run src/app.py
fi
