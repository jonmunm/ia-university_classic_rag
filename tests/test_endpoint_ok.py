import pytest
import httpx
from tests.conftest import get_test_logger
from tests.fixtures import FIXTURES

logger = get_test_logger(__file__)

BASE_URL = "http://localhost:8000"
ENDPOINT = "/v1/sqlgen"

@pytest.mark.asyncio
async def test_success_code():

    for idx, case in enumerate(FIXTURES, 1):
        query = case["query"]
        payload = { "query" : query }
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            response = await client.post(ENDPOINT, json=payload)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"

        data = response.json()
        assert "sql_query" in data, "The response does not contain the 'sql_query' key."

        if response.status_code == 200:
            logger.info(f"Case {idx} PASSED")
        else:
            logger.warning(f"Case {idx} FAILED")