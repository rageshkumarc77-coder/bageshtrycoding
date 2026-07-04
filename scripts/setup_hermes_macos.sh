#!/usr/bin/env bash
#
# setup_hermes_macos.sh — one-command setup for running Nous Research Hermes locally on macOS.
#
# Path 1: official NousResearch/hermes-agent + local Ollama backend
# Path 2: Python venv + agent frameworks (CrewAI / AutoGen / LangChain) with runnable examples
#
# Usage:
#   bash scripts/setup_hermes_macos.sh                # interactive: asks which path(s)
#   bash scripts/setup_hermes_macos.sh --all          # everything
#   bash scripts/setup_hermes_macos.sh --path1        # official Hermes Agent + Ollama only
#   bash scripts/setup_hermes_macos.sh --path2        # frameworks + examples only
#   bash scripts/setup_hermes_macos.sh --model hermes3:70b   # override auto-picked model
#
set -euo pipefail

MODEL_OVERRIDE=""
DO_PATH1=false
DO_PATH2=false
INTERACTIVE=true

while [[ $# -gt 0 ]]; do
  case "$1" in
    --all)    DO_PATH1=true; DO_PATH2=true; INTERACTIVE=false ;;
    --path1)  DO_PATH1=true; INTERACTIVE=false ;;
    --path2)  DO_PATH2=true; INTERACTIVE=false ;;
    --model)  MODEL_OVERRIDE="${2:?--model needs a value}"; shift ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown option: $1 (see --help)"; exit 1 ;;
  esac
  shift
done

bold()  { printf '\033[1m%s\033[0m\n' "$*"; }
info()  { printf '\033[36m==>\033[0m %s\n' "$*"; }
warn()  { printf '\033[33m[warn]\033[0m %s\n' "$*"; }
die()   { printf '\033[31m[error]\033[0m %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- guards ----
[[ "$(uname -s)" == "Darwin" ]] || die "This script is for macOS. Run it on your MacBook, not a Linux box."

ARCH="$(uname -m)"
RAM_BYTES="$(sysctl -n hw.memsize)"
RAM_GB=$(( RAM_BYTES / 1024 / 1024 / 1024 ))
bold "Detected: macOS on ${ARCH}, ${RAM_GB} GB unified memory"

if $INTERACTIVE; then
  echo
  echo "What do you want to set up?"
  echo "  1) Official Hermes Agent + local Ollama  (recommended)"
  echo "  2) Hermes model + agent frameworks (CrewAI/AutoGen/LangChain)"
  echo "  3) Both"
  read -r -p "Choice [1/2/3, default 3]: " choice
  case "${choice:-3}" in
    1) DO_PATH1=true ;;
    2) DO_PATH2=true ;;
    3) DO_PATH1=true; DO_PATH2=true ;;
    *) die "Invalid choice." ;;
  esac
fi

# ---------------------------------------------------------- pick a model ----
pick_model() {
  if [[ -n "$MODEL_OVERRIDE" ]]; then
    echo "$MODEL_OVERRIDE"
  elif (( RAM_GB >= 64 )); then
    echo "hermes3:70b"
  elif (( RAM_GB >= 24 )); then
    echo "hf.co/NousResearch/Hermes-4-14B-GGUF:Q4_K_M"
  else
    echo "hermes3:8b"
  fi
}
MODEL="$(pick_model)"
(( RAM_GB >= 16 )) || warn "${RAM_GB} GB RAM is tight for local LLMs — close other apps while running ${MODEL}."
info "Model selection: ${MODEL} (override with --model <tag>)"

# -------------------------------------------------------------- homebrew ----
if ! command -v brew >/dev/null 2>&1; then
  info "Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  if [[ "$ARCH" == "arm64" ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  else
    eval "$(/usr/local/bin/brew shellenv)"
  fi
else
  info "Homebrew already installed."
fi

# ---------------------------------------------------------------- ollama ----
if ! command -v ollama >/dev/null 2>&1; then
  info "Installing Ollama..."
  brew install ollama
else
  info "Ollama already installed."
fi

info "Raising Ollama context window to 64K (agents need it for tool schemas)..."
launchctl setenv OLLAMA_CONTEXT_LENGTH 65536
launchctl setenv OLLAMA_KEEP_ALIVE 1h

info "Starting Ollama service..."
brew services restart ollama >/dev/null

info "Waiting for Ollama to come up on :11434..."
for i in $(seq 1 30); do
  if curl -fsS http://localhost:11434/v1/models >/dev/null 2>&1; then break; fi
  [[ $i -eq 30 ]] && die "Ollama didn't start. Check port conflicts: lsof -i :11434"
  sleep 1
done
info "Ollama is up."

info "Pulling ${MODEL} (this can take a while — multi-GB download)..."
ollama pull "$MODEL"

info "Smoke-testing the model..."
ollama run "$MODEL" "Reply with exactly: HERMES-OK" | head -n 2

# ------------------------------------------------- path 1: hermes-agent -----
if $DO_PATH1; then
  echo
  bold "── Path 1: Official Hermes Agent ──────────────────────────────"
  if ! command -v hermes >/dev/null 2>&1; then
    info "Installing NousResearch/hermes-agent..."
    curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
    # Pick up the PATH change the installer wrote to the shell rc
    export PATH="$HOME/.hermes/bin:$HOME/.local/bin:$PATH"
  else
    info "hermes already installed ($(command -v hermes))."
  fi

  if command -v hermes >/dev/null 2>&1; then
    info "Running hermes doctor..."
    hermes doctor || warn "hermes doctor reported issues — usually fixed by 'hermes setup'."
    echo
    bold "Final manual step (interactive wizard):"
    cat <<EOF
    Run:            hermes setup
    Provider:       custom / OpenAI-compatible endpoint
    Base URL:       http://localhost:11434/v1
    API key:        ollama          (any placeholder; Ollama ignores it)
    Model:          ${MODEL}

    Then launch:    hermes
EOF
  else
    warn "hermes not on PATH yet — open a NEW terminal (or 'source ~/.zshrc') and run: hermes setup"
  fi
fi

# ------------------------------------------- path 2: python frameworks ------
if $DO_PATH2; then
  echo
  bold "── Path 2: Agent frameworks (CrewAI / AutoGen / LangChain) ────"
  if ! command -v python3.12 >/dev/null 2>&1; then
    info "Installing Python 3.12..."
    brew install python@3.12
  fi

  REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
  VENV="$REPO_ROOT/.venv"
  info "Creating virtual environment at ${VENV}..."
  python3.12 -m venv "$VENV"
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
  python -m pip install --upgrade pip -q

  info "Installing CrewAI, AutoGen, LangChain (a few minutes)..."
  python -m pip install -q crewai "autogen-agentchat" "autogen-ext[ollama]" langchain langchain-ollama

  export HERMES_MODEL="$MODEL"
  info "Verifying with the LangChain example (fastest)..."
  python "$REPO_ROOT/examples/agent_langchain.py" \
    && info "LangChain example: OK" \
    || warn "LangChain example failed — is Ollama running and the model pulled?"

  echo
  bold "Run the examples any time:"
  cat <<EOF
    source ${VENV}/bin/activate
    export HERMES_MODEL="${MODEL}"
    python examples/agent_langchain.py
    python examples/agent_crewai.py
    python examples/agent_autogen.py
EOF
fi

echo
bold "✅ Setup finished. Verify everything with: bash scripts/verify_hermes_setup.sh"
