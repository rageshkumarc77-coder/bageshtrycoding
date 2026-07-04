# Running the Nous Research Hermes Agent Locally on macOS

A step-by-step guide covering the **two main deployment paths**:

- **Path 1 — Official Hermes Agent** (`NousResearch/hermes-agent`): Nous Research's open-source terminal agent (released Feb 2026), wired to a local Hermes model via Ollama for a fully-local, zero-API-cost setup.
- **Path 2 — Hermes LLM + agent framework**: Run Hermes 3 / Hermes 4 weights locally via **Ollama** or **LM Studio**, and drive them with **CrewAI**, **AutoGen**, or **LangChain**.

> **TL;DR:** If you want "the Hermes agent," use **Path 1** — it's the real, native Nous Research agent (TUI + messaging gateway). Use **Path 2** if you want to build your own agents on top of Hermes model weights.

---

## Hardware Quick Reference (Apple Silicon)

Ollama/LM Studio use Metal GPU acceleration automatically on M-series Macs. Rule of thumb: the model file should be **≤ ~⅔ of your unified memory**, leaving headroom for the context window.

| Unified RAM | Recommended model | Approx. size (Q4) |
|---|---|---|
| 8 GB | `hermes3:8b` (tight — close other apps) | ~4.7 GB |
| 16 GB | `hermes3:8b` | ~4.7 GB |
| 24–36 GB | Hermes 4 14B (GGUF/MLX) | ~9 GB |
| 48–64 GB+ | `hermes3:70b` / Hermes 4 70B | ~40 GB |

Agentic tool-calling works noticeably better with the larger models; 8B is fine for testing the plumbing.

---

# Path 1 — Official Hermes Agent (NousResearch/hermes-agent)

The official agent from Nous Research: a full terminal UI (multiline editing, slash commands, streaming tool output) plus an optional gateway for Telegram, Discord, Slack, WhatsApp, Signal, and Email.

- Repo: <https://github.com/NousResearch/hermes-agent>
- Docs: <https://hermes-agent.nousresearch.com/docs/>

### 1. Prerequisites

Almost none — the installer bootstraps everything (uv, Python 3.11, Node.js, ripgrep, ffmpeg). You only need macOS with a terminal. Having [Homebrew](https://brew.sh) installed is still recommended for the Ollama step:

```bash
# Install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Xcode command-line tools (git, compilers) — usually already present
xcode-select --install
```

### 2. Install Hermes Agent

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash

# Reload your shell so the `hermes` command is on PATH
source ~/.zshrc    # macOS default shell is zsh
```

> Good practice: download the script first (`curl -fsSL <url> -o install.sh`), skim it, then `bash install.sh`.

Verify:

```bash
hermes --help
hermes doctor      # built-in diagnostics
```

### 3. Set up a local model backend (Ollama)

Hermes Agent talks to any OpenAI-compatible endpoint, so a local Ollama server works out of the box.

```bash
# Install and start Ollama
brew install ollama
brew services start ollama        # runs the server on http://localhost:11434

# Pull a Hermes model with tool-calling support
ollama pull hermes3:8b            # 16 GB Macs
# ollama pull hermes3:70b         # 64 GB+ Macs
```

**Important:** agents need a big context window. Ollama defaults to a small one, so raise it (64K recommended):

```bash
# Persist for the brew service:
launchctl setenv OLLAMA_CONTEXT_LENGTH 65536
brew services restart ollama

# ...or run the server manually instead of via brew services:
OLLAMA_CONTEXT_LENGTH=65536 ollama serve
```

Sanity-check the OpenAI-compatible endpoint:

```bash
curl http://localhost:11434/v1/models
```

### 4. Configure Hermes Agent

Run the wizard and point it at your local endpoint:

```bash
hermes setup
```

- When asked for a provider, choose the **custom / OpenAI-compatible endpoint** option.
- Base URL: `http://localhost:11434/v1`
- API key: any placeholder (Ollama ignores it), e.g. `ollama`
- Model: `hermes3:8b` (or whatever you pulled)

You can change any of this later without re-running setup:

```bash
hermes model            # pick provider/model interactively
hermes config set       # set individual config values
hermes tools            # enable/disable tools
```

Config lives in `~/.hermes/`.

> **Alternative (hosted models):** `hermes setup --portal` signs you into Nous Portal via OAuth and gives access to 300+ models — useful if your Mac can't run a big model, though it's no longer fully local.

### 5. Run it

```bash
hermes
```

You get the interactive TUI. Verify it works end-to-end:

- Ask something simple: `What files are in the current directory?` (exercises tool calling)
- Switch models on the fly with `/model <provider:model>`

Optional — chat with your agent from messaging apps:

```bash
hermes gateway setup    # configure Telegram / Discord / Slack / WhatsApp / Signal
hermes gateway start
```

Keep it updated:

```bash
hermes update
```

### 6. Troubleshooting (Path 1)

| Symptom | Fix |
|---|---|
| `command not found: hermes` | Open a new terminal or `source ~/.zshrc`; the installer adds its bin dir to PATH in your shell rc |
| Anything weird | `hermes doctor` first — it diagnoses config/dependency issues |
| Agent replies but never uses tools | Your model must support function calling (`hermes3`/Hermes 4 do); also raise `OLLAMA_CONTEXT_LENGTH` to ≥ 64K — truncated context breaks tool schemas |
| Connection refused to `localhost:11434` | Ollama isn't running: `brew services start ollama` or `ollama serve` |
| SSL/CA certificate errors after updates | Re-run `hermes doctor`; on corporate networks export `SSL_CERT_FILE` to your CA bundle |

---

# Path 2 — Hermes LLM (Ollama / LM Studio) + Agent Framework

Run Hermes model weights locally and build your own agents with CrewAI, AutoGen, or LangChain.

### 1. Prerequisites

```bash
# Homebrew (if needed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Python 3.12 + git
brew install python@3.12 git

python3.12 --version   # verify
```

### 2A. Model backend option 1 — Ollama

```bash
brew install ollama
brew services start ollama       # server on http://localhost:11434
```

Pull Hermes weights:

```bash
# Hermes 3 (official Ollama library, tool-calling capable)
ollama pull hermes3:8b           # ~4.7 GB — 16 GB Macs
# ollama pull hermes3:70b        # ~40 GB — 64 GB+ Macs

# Hermes 4 — pull GGUF directly from Hugging Face (no Modelfile needed)
ollama pull hf.co/NousResearch/Hermes-4-14B-GGUF:Q4_K_M
```

Verify the model runs:

```bash
ollama run hermes3:8b "Say hello in five words."
ollama ps      # shows loaded model + GPU (Metal) usage
```

### 2B. Model backend option 2 — LM Studio (nicer GUI, Apple-Silicon MLX)

1. Install: `brew install --cask lm-studio` (or download from <https://lmstudio.ai>).
2. In the app's **Discover** tab, search **"Hermes 4"** or **"Hermes 3"**.
   - On M-series Macs, prefer **MLX** builds (e.g. from `mlx-community`) — they're optimized for Apple Silicon and noticeably faster than GGUF.
3. Load the model, then open the **Developer** tab → **Start Server**.
   - Local OpenAI-compatible endpoint: `http://localhost:1234/v1`

Verify:

```bash
curl http://localhost:1234/v1/models
```

> Everything below uses Ollama URLs (`localhost:11434`). For LM Studio, just swap the base URL to `http://localhost:1234/v1` and use the model ID shown in the LM Studio server tab.

### 3. Project + virtual environment

```bash
mkdir ~/hermes-agents && cd ~/hermes-agents
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### 4A. Framework option 1 — CrewAI

```bash
pip install crewai
```

`agent_crewai.py`:

```python
from crewai import Agent, Task, Crew, LLM

llm = LLM(
    model="ollama/hermes3:8b",            # "ollama/" prefix routes to local Ollama
    base_url="http://localhost:11434",
)

researcher = Agent(
    role="Research Analyst",
    goal="Answer questions accurately and concisely",
    backstory="A meticulous analyst who verifies claims before stating them.",
    llm=llm,
    verbose=True,
)

task = Task(
    description="Explain in 3 bullet points why unified memory matters for local LLMs on Apple Silicon.",
    expected_output="Three concise bullet points.",
    agent=researcher,
)

crew = Crew(agents=[researcher], tasks=[task])
print(crew.kickoff())
```

```bash
python agent_crewai.py
```

### 4B. Framework option 2 — AutoGen

```bash
pip install "autogen-agentchat" "autogen-ext[ollama]"
```

`agent_autogen.py`:

```python
import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.ollama import OllamaChatCompletionClient

async def main():
    model_client = OllamaChatCompletionClient(model="hermes3:8b")
    agent = AssistantAgent("hermes", model_client=model_client)
    result = await agent.run(task="List three practical uses of a local LLM agent.")
    print(result.messages[-1].content)

asyncio.run(main())
```

```bash
python agent_autogen.py
```

### 4C. Framework option 3 — LangChain

```bash
pip install langchain langchain-ollama
```

`agent_langchain.py`:

```python
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

llm = ChatOllama(model="hermes3:8b", base_url="http://localhost:11434")
print(llm.invoke([HumanMessage("Give me a one-line summary of the Hermes model family.")]).content)
```

```bash
python agent_langchain.py
```

For tool-using LangChain agents, bind tools as usual (`llm.bind_tools([...])`) — `hermes3`/Hermes 4 support function calling natively.

---

# macOS Troubleshooting Cheat Sheet

### Apple Silicon / performance

- **Metal is automatic** — no CUDA, no flags. Confirm GPU offload with `ollama ps` (should show near-100% GPU).
- **Model too big → swapping/crawling:** keep model size ≤ ~⅔ of unified RAM; drop to a smaller quant (Q4_K_M) or smaller model.
- **Slow first response:** that's model load from disk. Keep it resident: `launchctl setenv OLLAMA_KEEP_ALIVE 1h && brew services restart ollama`.
- **LM Studio:** always prefer **MLX** builds over GGUF on M-series.

### Python path issues

```bash
which python3          # make sure you're not using /usr/bin/python3 (Apple's old one)
source .venv/bin/activate   # ALWAYS activate the venv before pip/python
python -m pip install ...   # use `python -m pip`, never bare pip against the wrong interpreter
```

- Build failures for native packages → `xcode-select --install`.
- Multiple Pythons (pyenv/brew/system) fighting each other → create the venv with an explicit interpreter: `python3.12 -m venv .venv`.

### Port conflicts

```bash
lsof -i :11434         # who owns Ollama's port (LM Studio: 1234)
kill <PID>             # free it, or move Ollama:
OLLAMA_HOST=127.0.0.1:11435 ollama serve
```

If you move the port, update `base_url` everywhere to match.

### Tool calling / agent quality

- The model **must** support function calling — `hermes3` and Hermes 4 do; random fine-tunes often don't.
- Raise the context window (`OLLAMA_CONTEXT_LENGTH=65536`) — small default contexts silently truncate tool schemas and break agent loops.
- If an 8B model loops or ignores tools, that's usually a capability ceiling — try the 14B/70B before debugging your code.

---

## Sources

- [NousResearch/hermes-agent (GitHub)](https://github.com/NousResearch/hermes-agent)
- [Hermes Agent official docs](https://hermes-agent.nousresearch.com/docs/)
- [Hermes Agent — local Ollama setup guide](https://hermes-agent.nousresearch.com/docs/guides/local-ollama-setup)
- [Ollama docs — Hermes integration](https://docs.ollama.com/integrations/hermes)
- [Hermes models on Hugging Face (NousResearch)](https://huggingface.co/NousResearch)
