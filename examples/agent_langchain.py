"""Minimal LangChain check against a local Hermes model on Ollama.

Usage:
    source .venv/bin/activate
    HERMES_MODEL=hermes3:8b python examples/agent_langchain.py
"""

import os

from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama

MODEL = os.environ.get("HERMES_MODEL", "hermes3:8b")
BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

llm = ChatOllama(model=MODEL, base_url=BASE_URL)
reply = llm.invoke([HumanMessage("Give me a one-line summary of the Hermes model family.")])
print(f"[{MODEL}] {reply.content}")
