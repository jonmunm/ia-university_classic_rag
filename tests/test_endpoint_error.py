import pytest
import httpx
from tests.conftest import get_test_logger

logger = get_test_logger(__file__)

BASE_URL = "http://localhost:8000"
ENDPOINT = "/v1/sqlgen"

@pytest.mark.asyncio
async def test_non_successful_codes():
    queries = [
        "None",
        "",
        "error",
        "Dame columnas",
        "Lo que sea"
    ]

    for idx, query in enumerate(queries, 1):

        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            response = await client.post(ENDPOINT, json={ "query" : query })

        assert response.status_code == 400, f"Expected 200, got {response.status_code}. Response: {response.text}"

        data = response.json()
        assert "detail" in data, "The response does not contain the 'detail' key."

        if response.status_code == 400:
            logger.info(f"Case {idx} PASSED")
        else:
            logger.warning(f"Case {idx} FAILED")
