"""CrewAI agent backed by a local Hermes model on Ollama.

Usage:
    source .venv/bin/activate
    HERMES_MODEL=hermes3:8b python examples/agent_crewai.py
"""

import os

from crewai import LLM, Agent, Crew, Task

MODEL = os.environ.get("HERMES_MODEL", "hermes3:8b")
BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

llm = LLM(model=f"ollama/{MODEL}", base_url=BASE_URL)

researcher = Agent(
    role="Research Analyst",
    goal="Answer questions accurately and concisely",
    backstory="A meticulous analyst who verifies claims before stating them.",
    llm=llm,
    verbose=True,
)

task = Task(
    description=(
        "Explain in 3 bullet points why unified memory matters for "
        "local LLMs on Apple Silicon."
    ),
    expected_output="Three concise bullet points.",
    agent=researcher,
)

crew = Crew(agents=[researcher], tasks=[task])
print(crew.kickoff())
