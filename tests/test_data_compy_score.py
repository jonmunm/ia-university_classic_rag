import pytest
import asyncpg
import pandas as pd
from tests.fixtures import FIXTURES
from tests.conftest import get_test_logger
from src.llm.llm_sql_generator_service import LLMSqlGeneratorService
from src.utils import get_env

logger = get_test_logger(__file__)

OLTP_STORE_USER = get_env("OLTP_STORE_USER")
OLTP_STORE_PASSWORD = get_env("OLTP_STORE_PASSWORD")
OLTP_STORE_DB = get_env("OLTP_STORE_DB")
OLTP_STORE_HOST = get_env("OLTP_STORE_HOST")
OLTP_STORE_PORT = get_env("OLTP_STORE_PORT")

DB_DSN = (
    f"postgresql://{OLTP_STORE_USER}:{OLTP_STORE_PASSWORD}"
    f"@{OLTP_STORE_HOST}:{OLTP_STORE_PORT}/{OLTP_STORE_DB}"
)

@pytest.mark.asyncio
async def test_sql_execution_accuracy():
    service = LLMSqlGeneratorService()
    conn = await asyncpg.connect(DB_DSN)

    try:
        for idx, case in enumerate(FIXTURES, 1):

            query = case["query"]
            expected_sql = case["expected_sql"]

            response = await service.invoke({"query": query})
            generated_sql = (
                response.parsed.sql_query
                if not response.parsed.is_error
                else response.parsed.error_message
            ) or ""

            logger.debug(
                f"Case {idx:02d}\n"
                f"Query: {query.strip()}\n"
                f"Expected SQL:\n{expected_sql.strip()}\n"
                f"Generated SQL:\n{generated_sql.strip()}"
            )

            if response.parsed.is_error:
                logger.error(f"Case {idx:02d} | Execution Accuracy: FAILED (0.0) - LLM Error")
                logger.debug(f"LLM Error Details (Case {idx}): {generated_sql}")
                continue

            try:
                async with conn.transaction():
                    exp_rows = await conn.fetch(expected_sql)
                    exp_columns = list(exp_rows[0].keys()) if exp_rows else []
                    exp_df = pd.DataFrame([dict(row) for row in exp_rows], columns=exp_columns)
                    raise asyncpg.exceptions.InternalServerError("Rollback expected")
            except asyncpg.exceptions.InternalServerError:
                pass

            gen_df = pd.DataFrame()
            exec_error = False
            try:
                async with conn.transaction():
                    gen_rows = await conn.fetch(generated_sql)
                    gen_columns = list(gen_rows[0].keys()) if gen_rows else []
                    gen_df = pd.DataFrame([dict(row) for row in gen_rows], columns=gen_columns)
                    raise asyncpg.exceptions.InternalServerError("Rollback generated")
            except asyncpg.exceptions.InternalServerError:
                pass
            except Exception as db_err:
                exec_error = True
                logger.error(f"Case {idx:02d} | Execution Accuracy: FAILED (0.0) - DB Error: {db_err}")
                logger.debug(f"Generated SQL Execution Error (Case {idx}): {db_err}")

            match = False
            discrepancy_msg = ""
            try:
                if len(exp_df.columns) == len(gen_df.columns):
                    gen_df.columns = exp_df.columns

                exp_sorted = exp_df.sort_values(by=list(exp_df.columns)).reset_index(drop=True)
                gen_sorted = gen_df.sort_values(by=list(gen_df.columns)).reset_index(drop=True)

                pd.testing.assert_frame_equal(exp_sorted, gen_sorted, check_dtype=False)
                match = True
            except AssertionError as ae:
                discrepancy_msg = str(ae)
                logger.debug(f"Discrepancy on data on case {idx}:\n{discrepancy_msg}")

            assert match, f"Discrepancy on data on case {idx}"

            if match:
                logger.info(f"Case {idx:02d} | Execution Accuracy: PASSED (1.0)")
            else:
                logger.error(f"Case {idx:02d} | Execution Accuracy: FAILED (0.0) - Dataframes differ")

    finally:
        await conn.close()