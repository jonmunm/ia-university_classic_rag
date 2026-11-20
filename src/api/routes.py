import time
import asyncio
from fastapi import FastAPI
from fastapi import HTTPException
from langsmith import traceable
from langsmith.run_helpers import get_current_run_tree
from src.utils import get_observability_project_name
from src.utils import report_metric
from src.llm.llm_sql_generator_service import LLMSqlGeneratorService
from src.api.utils import SqlGenerationBodyResponse

app = FastAPI()

@traceable(name="SQL_Generation", project_name=get_observability_project_name())
async def _generate_sql(body: SqlGenerationBodyResponse):

    run_id = get_current_run_tree().id

    t0 = time.perf_counter()
    service_response = await LLMSqlGeneratorService().invoke({
        "query": body.query
    })
    t_end = time.perf_counter() - t0

    result = service_response.parsed

    asyncio.create_task(
        asyncio.to_thread(
            report_metric,
            run_id=run_id,
            key="endpoint_generation_duration",
            score=t_end
        )
    )    

    if result.is_error or result.sql_query is None:
        error_detail = result.error_message or "Please, provide a valid prompt. The generated SQL was invalid or unsafe."

        raise HTTPException(
            status_code=400,
            detail=f"There has been some issues generating the query: {result.error_message}"
        )

    return {
        "sql_query": result.sql_query,
        "is_error": result.is_error,
        "error_message": result.error_message,
        "sql_observations": None
    }

@app.api_route("/v1/sqlgen", methods=["POST", "HEAD"])
async def generate_sql(body: SqlGenerationBodyResponse):
    return await _generate_sql(body)