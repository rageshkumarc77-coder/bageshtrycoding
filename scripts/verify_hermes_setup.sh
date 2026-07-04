#!/usr/bin/env bash
#
# verify_hermes_setup.sh — post-install health check for the local Hermes stack.
# Safe to run any time; makes no changes.
#
set -uo pipefail

PASS=0; FAIL=0
ok()   { printf '  \033[32m✔\033[0m %s\n' "$*"; PASS=$((PASS+1)); }
bad()  { printf '  \033[31m✘\033[0m %s\n' "$*"; FAIL=$((FAIL+1)); }

echo "Hermes local stack — health check"
echo "─────────────────────────────────"

# 1. Ollama binary + server
if command -v ollama >/dev/null 2>&1; then ok "ollama installed ($(ollama --version 2>/dev/null | head -n1))"; else bad "ollama not installed (brew install ollama)"; fi

if curl -fsS http://localhost:11434/v1/models >/dev/null 2>&1; then
  ok "Ollama server responding on :11434"
  MODELS="$(curl -fsS http://localhost:11434/api/tags | python3 -c 'import sys,json;print(", ".join(m["name"] for m in json.load(sys.stdin).get("models",[])) or "none")' 2>/dev/null)"
  if [[ -n "${MODELS:-}" && "$MODELS" != "none" ]]; then ok "Models available: $MODELS"; else bad "No models pulled yet (ollama pull hermes3:8b)"; fi
else
  bad "Ollama server not reachable (brew services start ollama; check: lsof -i :11434)"
fi

# 2. Context window env (agents need >= 64K)
CTX="$(launchctl getenv OLLAMA_CONTEXT_LENGTH 2>/dev/null || true)"
if [[ -n "$CTX" && "$CTX" -ge 65536 ]] 2>/dev/null; then
  ok "OLLAMA_CONTEXT_LENGTH=$CTX"
else
  bad "OLLAMA_CONTEXT_LENGTH not set to >=65536 (launchctl setenv OLLAMA_CONTEXT_LENGTH 65536; brew services restart ollama)"
fi

# 3. Generation smoke test
MODEL="${HERMES_MODEL:-hermes3:8b}"
if command -v ollama >/dev/null 2>&1 && curl -fsS http://localhost:11434/v1/models >/dev/null 2>&1; then
  if OUT="$(ollama run "$MODEL" "Reply with exactly: HERMES-OK" 2>/dev/null)" && [[ "$OUT" == *HERMES-OK* ]]; then
    ok "Model '$MODEL' generates correctly"
  else
    bad "Model '$MODEL' failed to generate (is it pulled? HERMES_MODEL env var set correctly?)"
  fi
fi

# 4. Official Hermes Agent
if command -v hermes >/dev/null 2>&1; then
  ok "hermes agent installed ($(command -v hermes))"
  hermes doctor >/dev/null 2>&1 && ok "hermes doctor: clean" || bad "hermes doctor reported issues (run: hermes doctor)"
else
  bad "hermes agent not on PATH (new terminal, or: bash scripts/setup_hermes_macos.sh --path1)"
fi

# 5. Python venv + frameworks
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
  ok "venv present at .venv"
  for pkg in crewai autogen_agentchat langchain_ollama; do
    if "$REPO_ROOT/.venv/bin/python" -c "import $pkg" >/dev/null 2>&1; then ok "python package: $pkg"; else bad "python package missing: $pkg"; fi
  done
else
  bad "no venv at .venv (bash scripts/setup_hermes_macos.sh --path2)"
fi

echo "─────────────────────────────────"
echo "Result: $PASS passed, $FAIL failed"
exit "$(( FAIL > 0 ? 1 : 0 ))"
