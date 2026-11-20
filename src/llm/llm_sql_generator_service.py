import time
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from langchain_openai import ChatOpenAI
from src.prompts.prompts import get_messages_prompt
from src.llm.utils import (
    LLMSqlGeneratorSchema,
    LLMSqlGeneratorServiceResponse,
    format_docs,
    validate_safe_select,
)
from src.retriever import VectorRetriever
from src.utils import get_env

MAIN_MODEL_NAME = get_env("MAIN_MODEL_NAME")

tracer = trace.get_tracer(__name__)

llm = ChatOpenAI(model=MAIN_MODEL_NAME, temperature=0)

structured_llm = llm.with_structured_output(
    LLMSqlGeneratorSchema,
    include_raw=True,
)


class LLMSqlGeneratorService:
    def __init__(self, retriever: VectorRetriever | None = None) -> None:
        self._retriever = retriever or VectorRetriever()

    def _validate_safe_select(self, sql: str) -> None:
        validate_safe_select(sql)

    async def invoke(self, inputs: dict) -> LLMSqlGeneratorServiceResponse:
        query = inputs["query"]

        with tracer.start_as_current_span(
            "LLMSqlGeneratorService.invoke",
            attributes={
                "openinference.span.kind": "CHAIN",
                "input.value": query,
            },
        ) as span:
            t0 = time.perf_counter()
            docs = await self._retriever.retrieve(query)
            span.set_attribute("metrics.service_retrieval_duration_s", time.perf_counter() - t0)

            context = format_docs(docs)
            messages = get_messages_prompt(context, query)

            t0 = time.perf_counter()
            out = await structured_llm.ainvoke(messages, config={"run_name": "2_Generation"})
            span.set_attribute("metrics.service_generation_duration_s", time.perf_counter() - t0)

            result = out["parsed"]

            if result is None:
                parsed_error = LLMSqlGeneratorSchema(
                    is_error=True,
                    error_message=f"Structured parsing failed: {out.get('parsing_error')}",
                    sql_query=None,
                )
                span.set_attribute("output.value", parsed_error.error_message)
                span.set_status(Status(StatusCode.ERROR, parsed_error.error_message))
                return LLMSqlGeneratorServiceResponse(parsed=parsed_error, contexts=docs)

            with tracer.start_as_current_span(
                "3_SQL_Validation",
                attributes={
                    "openinference.span.kind": "GUARDRAIL",
                    "input.value": result.sql_query or "",
                },
            ) as val_span:
                t0 = time.perf_counter()
                if result.sql_query:
                    try:
                        self._validate_safe_select(result.sql_query)
                        val_span.set_attribute("output.value", "VALID")
                        val_span.set_status(Status(StatusCode.OK))
                    except ValueError as e:
                        result.sql_query = None
                        result.is_error = True
                        result.error_message = f"Validation blocked the query: {str(e)}"
                        val_span.set_attribute("output.value", result.error_message)
                        val_span.set_status(Status(StatusCode.ERROR, result.error_message))
                span.set_attribute("metrics.sql_validation_duration_s", time.perf_counter() - t0)

            span.set_attribute("output.value", result.sql_query or result.error_message or "")
            span.set_status(
                Status(StatusCode.ERROR, result.error_message or "Error")
                if result.is_error
                else Status(StatusCode.OK)
            )
            return LLMSqlGeneratorServiceResponse(parsed=result, contexts=docs)