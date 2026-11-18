import logging
from datetime import datetime
from pathlib import Path
import pytest

NOISY_LOGGERS = (
    "httpx",
    "httpcore",
    "openai",
    "openai._base_client",
    "urllib3",
    "ragas",
    "langchain",
)


def silence_external_loggers() -> None:
    for name in NOISY_LOGGERS:
        ext_logger = logging.getLogger(name)
        ext_logger.setLevel(logging.WARNING)
        ext_logger.propagate = False


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    """Se ejecuta justo antes de cada test y bloquea el ruido HTTP en consola."""
    silence_external_loggers()


def get_test_logger(file_path: str) -> logging.Logger:
    """
    Escribe todo el detalle (DEBUG) en logs/{nombre_test}_{YYYY_MM_DD_HH_MM_SS}.log
    y deja en consola solo lo que sea INFO o ERROR.
    """
    silence_external_loggers()

    log_dir = Path("tests/logs")
    log_dir.mkdir(exist_ok=True)

    file_stem = Path(file_path).stem
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    log_filename = f"{file_stem}_{timestamp}.log"

    logger = logging.getLogger(file_stem)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        file_handler = logging.FileHandler(log_dir / log_filename, mode="w", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger