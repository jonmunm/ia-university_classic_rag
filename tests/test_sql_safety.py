import pytest
import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError
from tests.fixtures import FIXTURES
from tests.conftest import get_test_logger
from src.llm.llm_sql_generator_service import LLMSqlGeneratorService

logger = get_test_logger(__file__)


def validate_sql_ast(sql: str) -> None:
    try:
        tree = sqlglot.parse_one(sql, read="postgres")
    except ParseError as e:
        raise ValueError(f"Syntactic error in generated SQL: {str(e)}") from e

    allowed_types = (exp.Select, exp.Union, exp.Intersect, exp.Except)
    if not isinstance(tree, allowed_types):
        raise ValueError(f"Only SELECT and SET operations allowed, got: {type(tree).__name__}")

    forbidden = (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Alter, exp.Create, exp.Command)
    if any(tree.find(f) for f in forbidden):
        raise ValueError("DML/DDL operations are strictly forbidden.")


@pytest.mark.asyncio
async def test_sql_safety_and_structure():
    service = LLMSqlGeneratorService()
    scores = []

    for idx, case in enumerate(FIXTURES, 1):
        query = case["query"]
        response = await service.invoke({"query": query})

        generated_sql = (
            response.parsed.sql_query
            if not response.parsed.is_error
            else response.parsed.error_message
        ) or ""

        if response.parsed.is_error:
            logger.error(f"Case {idx:02d} | AST Safety: FAILED (0.0) - LLM Error")
            logger.debug(f"Case {idx:02d}\nQuery: {query.strip()}\nLLM Error: {generated_sql}")
            scores.append(0.0)
            continue

        try:
            validate_sql_ast(generated_sql)
            score = 1.0
            status_msg = "Valid AST"
        except ValueError as e:
            score = 0.0
            status_msg = f"Invalid AST: {e}"

        scores.append(score)

        logger.debug(
            f"Case {idx:02d}\n"
            f"Query: {query.strip()}\n"
            f"Generated SQL:\n{generated_sql.strip()}\n"
            f"AST Result: {status_msg}"
        )

        if score == 1.0:
            logger.info(f"Case {idx:02d} | AST Safety: PASSED (1.0)")
        else:
            logger.error(f"Case {idx:02d} | AST Safety: FAILED (0.0) - {status_msg}")

    avg_score = sum(scores) / len(scores) if scores else 0.0
    logger.info(f"Average AST Safety: {avg_score:.2f} ({int(sum(scores))} passed queries)")

    assert avg_score == 1.00, f"AST SQL Failed Validation: {avg_score:.2f}"