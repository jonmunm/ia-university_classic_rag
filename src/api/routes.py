import time
from fastapi import FastAPI, HTTPException
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from src.utils import init_telemetry

# Inicializar antes de importar el servicio para instrumentar LangChain
init_telemetry()

from src.api.utils import SqlGenerationBodyResponse
from src.llm.llm_sql_generator_service import LLMSqlGeneratorService

app = FastAPI()
tracer = trace.get_tracer(__name__)

async def _generate_sql(body: SqlGenerationBodyResponse):
    with tracer.start_as_current_span(
        "SQL_Generation",
        attributes={
            "openinference.span.kind": "CHAIN",
            "input.value": body.query,
        },
    ) as span:
        t0 = time.perf_counter()
        service_response = await LLMSqlGeneratorService().invoke({
            "query": body.query,
        })
        span.set_attribute("metrics.endpoint_generation_duration_s", time.perf_counter() - t0)

        result = service_response.parsed

        if result.is_error or result.sql_query is None:
            error_detail = (
                result.error_message
                or "Please, provide a valid prompt. The generated SQL was invalid or unsafe."
            )
            span.set_attribute("output.value", error_detail)
            span.set_status(Status(StatusCode.ERROR, error_detail))
            raise HTTPException(
                status_code=400,
                detail=f"There has been some issues generating the query: {error_detail}",
            )

        span.set_attribute("output.value", result.sql_query)
        span.set_status(Status(StatusCode.OK))
        return {
            "sql_query": result.sql_query,
            "is_error": result.is_error,
            "error_message": result.error_message,
            "sql_observations": None,
        }


@app.api_route("/v1/sqlgen", methods=["POST", "HEAD"])
async def generate_sql(body: SqlGenerationBodyResponse):
    return await _generate_sql(body)