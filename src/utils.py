"""
Utility functions and shared resources for loading database schema files, 
environment configurations, and initializing the LangSmith tracking client.
"""

import os
from uuid import UUID
from pathlib import Path
from langsmith import Client
from langsmith.schemas import Feedback

# Resolve the base directory of the current module and the default SQL schema path
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_PATH = BASE_DIR / "schema" / "schema.sql"


def get_schema(file_path: Path | str = DEFAULT_PATH) -> str:
    """
    Read and return the contents of a SQL schema file.

    Args:
        file_path (Path | str): Path to the SQL schema file. Defaults to DEFAULT_PATH.

    Returns:
        str: The raw SQL schema definition as a string.
    """
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


def get_langsmith_project_name() -> str:
    """
    Retrieve the LangSmith project name from the environment variables.

    Returns:
        str: The configured LangSmith project name.

    Raises:
        ValueError: If the 'LANGSMITH_PROJECT' environment variable is missing or empty.
    """
    langsmith_project_name = os.getenv("LANGSMITH_PROJECT", None)
    if not langsmith_project_name:
        raise ValueError("A valid Langsmith project is required")

    return langsmith_project_name


# Initialize the LangSmith client and ensure the target project exists (create or retrieve UUID)
client = Client()
PROJECT_UUID = client.create_project(
    project_name=get_langsmith_project_name(), 
    upsert=True
).id

def report_metric(run_id: UUID | str, key: str, score: float | int) -> Feedback:
    """
    Log a feedback metric or latency score to LangSmith for a specific trace run.

    Args:
        run_id (UUID | str): The unique identifier of the LangSmith run/trace.
        key (str): The name of the feedback metric (e.g., latency or evaluation key).
        score (float | int): The numerical value or duration to record.

    Returns:
        Feedback: The created LangSmith Feedback object.
    """
    return client.create_feedback(
        run_id=run_id,
        key=key,
        score=score,
        session_id=PROJECT_UUID,
        trace_id=run_id
    )