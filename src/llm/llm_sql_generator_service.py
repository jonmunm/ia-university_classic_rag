import asyncio
import time
from langchain_openai import ChatOpenAI
from langsmith import traceable
from langsmith.run_helpers import get_current_run_tree
from src.llm.utils import (
    LLMSqlGeneratorSchema,
    LLMSqlGeneratorServiceResponse,
    format_docs,
    validate_safe_select,
)
from src.prompts.prompts import get_messages_prompt
from src.retriever import VectorRetriever
from src.utils import get_env, get_observability_project_name, report_metric

MAIN_MODEL_NAME = get_env("MAIN_MODEL_NAME")

llm = ChatOpenAI(model=MAIN_MODEL_NAME, temperature=0)
structured_llm = llm.with_structured_output(LLMSqlGeneratorSchema, include_raw=True)


class LLMSqlGeneratorService:
    def __init__(self, retriever: VectorRetriever | None = None) -> None:
        self._retriever = retriever or VectorRetriever()

    @traceable(name="3_SQL_Validation", project_name=get_observability_project_name())
    def _validate_safe_select(self, sql: str) -> None:
        validate_safe_select(sql)

    @traceable(name="LLMSqlGeneratorService.invoke", project_name=get_observability_project_name())
    async def invoke(self, inputs: dict) -> LLMSqlGeneratorServiceResponse:
        run_id = get_current_run_tree().id
        query = inputs["query"]

        t0 = time.perf_counter()
        docs = await self._retriever.retrieve(query)
        t_service_retrieval = time.perf_counter() - t0
        asyncio.create_task(
            asyncio.to_thread(
                report_metric,
                run_id=run_id,
                key="service_retrieval_duration",
                score=t_service_retrieval,
            )
        )

        context = format_docs(docs)
        messages = get_messages_prompt(context, query)

        t0 = time.perf_counter()
        out = await structured_llm.ainvoke(messages, config={"run_name": "2_Generation"})
        t_service_duration = time.perf_counter() - t0
        asyncio.create_task(
            asyncio.to_thread(
                report_metric,
                run_id=run_id,
                key="service_generation_duration",
                score=t_service_duration,
            )
        )

        result = out["parsed"]

        if result is None:
            parsed_error = LLMSqlGeneratorSchema(
                is_error=True,
                error_message=f"Structured parsing failed: {out.get('parsing_error')}",
                sql_query=None,
            )
            return LLMSqlGeneratorServiceResponse(parsed=parsed_error, contexts=docs)

        t0 = time.perf_counter()
        if result.sql_query:
            try:
                self._validate_safe_select(result.sql_query)
            except ValueError as e:
                result.sql_query = None
                result.is_error = True
                result.error_message = f"Validation blocked the query: {str(e)}"
        t_sql_validation = time.perf_counter() - t0
        asyncio.create_task(
            asyncio.to_thread(
                report_metric,
                run_id=run_id,
                key="sql_validation_duration",
                score=t_sql_validation,
            )
        )

        return LLMSqlGeneratorServiceResponse(parsed=result, contexts=docs)