"""
Utility functions and shared resources for loading database schema files,
environment configurations, and reporting observability metrics to LangSmith.
"""

import os
from functools import lru_cache
from pathlib import Path
from uuid import UUID

from langsmith import Client
from langsmith.schemas import Feedback

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_PATH = BASE_DIR / "schema" / "schema.sql"


def get_env(name: str) -> str:
    """
    Retrieve a required environment variable by name.

    Args:
        name (str): The name of the environment variable to look up.

    Returns:
        str: The non-empty value of the environment variable.

    Raises:
        ValueError: If the environment variable is not set or is empty.
    """
    env = os.getenv(name)
    if not env:
        raise ValueError(f"{name} must be specified")

    return env


def get_schema(file_path: Path | str = DEFAULT_PATH) -> str:
    """Read and return the contents of a SQL schema file."""
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


def get_observability_project_name() -> str:
    """Retrieve the observability project name from environment variables."""
    return get_env("OBSERVABILITY_PROJECT_NAME")


@lru_cache(maxsize=1)
def _get_observability_client() -> Client:
    """Return a cached LangSmith client configured from OBSERVABILITY_* variables."""
    return Client(
        api_url=get_env("OBSERVABILITY_ENDPOINT"),
        api_key=get_env("OBSERVABILITY_API_KEY"),
    )


@lru_cache(maxsize=1)
def _get_project_uuid() -> UUID:
    """Ensure the target observability project exists and cache its UUID."""
    return (
        _get_observability_client()
        .create_project(
            project_name=get_observability_project_name(),
            upsert=True,
        )
        .id
    )


def report_metric(run_id: UUID | str, key: str, score: float | int) -> Feedback:
    """Log a feedback metric or latency score to LangSmith for a specific trace run."""
    return _get_observability_client().create_feedback(
        run_id=run_id,
        key=key,
        score=score,
        session_id=_get_project_uuid(),
        trace_id=run_id,
    )