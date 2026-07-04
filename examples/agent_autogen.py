"""AutoGen assistant backed by a local Hermes model on Ollama.

Usage:
    source .venv/bin/activate
    HERMES_MODEL=hermes3:8b python examples/agent_autogen.py
"""

import asyncio
import os

from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.ollama import OllamaChatCompletionClient

MODEL = os.environ.get("HERMES_MODEL", "hermes3:8b")


async def main() -> None:
    model_client = OllamaChatCompletionClient(model=MODEL)
    agent = AssistantAgent("hermes", model_client=model_client)
    result = await agent.run(task="List three practical uses of a local LLM agent.")
    print(f"[{MODEL}] {result.messages[-1].content}")
    await model_client.close()


asyncio.run(main())
