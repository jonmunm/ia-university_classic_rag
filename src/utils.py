"""
Utility functions and shared resources for loading environment variables,
database schema files, and initializing OpenTelemetry tracing.
"""

import os
from pathlib import Path
from phoenix.otel import register

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_PATH = BASE_DIR / "schema" / "schema.sql"

_telemetry_initialized = False


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


def init_telemetry() -> None:
    """Initialize observability tracing and auto-instrument LangChain once."""
    global _telemetry_initialized
    if _telemetry_initialized:
        return

    endpoint = get_env("OBSERVABILITY_ENDPOINT").rstrip("/")
    if not endpoint.endswith("/v1/traces"):
        endpoint = f"{endpoint}/v1/traces"

    register(
        project_name=get_env("OBSERVABILITY_PROJECT_NAME"),
        endpoint=endpoint,
        protocol="http/protobuf",
        auto_instrument=True,
        batch=True,
    )
    _telemetry_initialized = True