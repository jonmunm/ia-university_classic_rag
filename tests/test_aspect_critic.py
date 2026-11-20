import pytest
from openai import AsyncOpenAI
from ragas.llms import llm_factory
from ragas.dataset_schema import SingleTurnSample
from ragas.metrics import AspectCritic

from tests.fixtures import FIXTURES
from tests.conftest import get_test_logger
from src.utils import get_env, get_schema
from src.llm.llm_sql_generator_service import LLMSqlGeneratorService

logger = get_test_logger(__file__)

TEST_MODEL_NAME = get_env("TEST_MODEL_NAME")

@pytest.mark.asyncio
async def test_sql_generator_aspect_critic():
    service = LLMSqlGeneratorService()

    openai_client = AsyncOpenAI()
    ragas_llm = llm_factory(TEST_MODEL_NAME, client=openai_client, temperature=0.0)

    scorer = AspectCritic(
        name="sql_logical_equivalence",
        definition=(
            "Evaluate whether the generated SQL query ('response') is logically equivalent to the "
            "Reference SQL provided in the context and accurately answers the 'user_input' according to the Database Schema. "
            "You MUST treat the following syntactic variations as 100% EQUIVALENT (Return 1): "
            "1. Using Common Table Expressions (CTEs / WITH clauses) or subqueries vs flat JOINs. "
            "2. Using LEFT JOIN vs INNER JOIN when the WHERE clause filters on the joined tables (null-rejecting predicates). "
            "3. Using ILIKE '%value%' vs '=' for string matching. "
            "4. Evaluating 'alumno antiguo' dynamically via 'ic.semestre_ingreso_id < ms.semestre_id' vs hardcoding previous semesters like ('2018-1', '2019-1'). "
            "5. Filtering dates using 'EXTRACT(YEAR FROM fecha) = 2021' vs '>= 2021-01-01 AND <= 2021-12-31'. "
            "6. If the Reference SQL includes an extra filter NOT requested in 'user_input' (e.g., filtering by a career not mentioned in the prompt), DO NOT penalize the response for omitting that unrequested filter. "
            "Return 0 ONLY if the response has a genuine business logic error, queries the wrong tables, misses a requested filter, or hallucinates an unrequested WHERE condition (such as filtering hic.motivo when not asked)."
        ),
        llm=ragas_llm,
    )

    base_schema = get_schema()
    scores = []

    for idx, case in enumerate(FIXTURES, 1):

        query = case["query"]
        expected_sql = case["expected_sql"]
        response = await service.invoke({"query": query})

        generated_sql = (
            response.parsed.sql_query
            if not response.parsed.is_error
            else response.parsed.error_message
        ) or ""

        if response.parsed.is_error:
            logger.error(f"Case {idx:02d} | AspectCritic: Failed (0.0) - LLM Error")
            logger.debug(f"Case {idx:02d}\nQuery: {query.strip()}\nLLM Error: {generated_sql}")
            scores.append(0.0)
            continue

        eval_contexts = [
            f"Database Schema (DDL): \n {base_schema} \n",
            f"Reference SQL (Ground Truth): \n {expected_sql}",
        ] + [doc.page_content for doc in response.contexts]

        sample = SingleTurnSample(
            user_input=query,
            response=generated_sql,
            reference=expected_sql,
            retrieved_contexts=eval_contexts,
        )

        result = await scorer.single_turn_ascore(sample)
        score = float(result.value) if hasattr(result, "value") else float(result)
        scores.append(score)

        logger.debug(
            f"Case {idx:02d}\n"
            f"Query: {query.strip()}\n"
            f"Expected SQL:\n{expected_sql.strip()}\n"
            f"Generated SQL:\n{generated_sql.strip()}\n"
            f"AspectCritic Score: {score}"
        )

        if score == 1.0:
            logger.info(f"Case {idx:02d} | AspectCritic: PASSED ({score:.1f})")
        else:
            logger.warning(f"Case {idx:02d} | AspectCritic: FAILED ({score:.1f})")

    avg_score = sum(scores) / len(scores) if scores else 0.0
    logger.info(f"Average AspectCritic: {avg_score:.2f} ({sum(scores)/len(scores)} passed)")

    assert avg_score >= 0.70, f"Insufficient logical equivalence average: {avg_score:.2f}"