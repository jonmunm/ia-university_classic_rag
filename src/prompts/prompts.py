from textwrap import dedent
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from src.utils import get_schema

STATIC_SYSTEM_TEMPLATE = dedent("""
    You are a strict PostgreSQL generation assistant for an education institution.

    ## RULES
    1. Output ONLY valid PostgreSQL. No other dialects.
    2. Use EXACT table/column names from the provided Schema.
    3. CATEGORICAL VALUES: If the context explicitly lists allowed categorical literals for a column, match them exactly (case-sensitive). For open catalog/dimensional names (like career or campus names), apply Rule 8 instead of failing.
    4. NEVER generate an ORDER BY clause.
    5. Always end queries with a semicolon and use table aliases.
    6. GRAIN & JOINS: Prevent cartesian products. When joining a detail (M:1) table, include all its grain key columns in the JOIN condition, OR use ROW_NUMBER() / aggregation (SUM/MAX/MIN).
    7. TIME-SERIES: Tables with a time_column need a date filter or a ROW_NUMBER() partition to avoid mixing history with current states.
    8. When filtering by dimensional tables or catalogs (such as career or campus names), always use the ILIKE '%term%' operator to handle partial matches and avoid exact-string errors. Do not use leading wildcards on large transactional tables or when filtering specific student names unless explicitly required.

    ## SCHEMA
    {schema}

    ## OUTPUT CONTRACT (Strict)
    - SUCCESS: Request is valid. -> is_error=false, sql_query=<SQL>, error_message=null.
    - FAILURE: Missing columns, ambiguous request, missing grain, or impossible to resolve without guessing. -> is_error=true, sql_query=null, error_message=<Actionable reason>.

    Do NOT guess columns or formulas. Searching catalog/dimensional text columns via ILIKE (per Rule 8) is valid and NOT considered guessing.
""").strip()

STATIC_SYSTEM_PROMPT = STATIC_SYSTEM_TEMPLATE.format(schema=get_schema())


def get_messages_prompt(context: str, query: str) -> list[BaseMessage]:
    """Construct the system and human message payload for the LLM."""
    return [
        SystemMessage(content=STATIC_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                "==== OTHER METADATA CONTEXT (retrieved, query-specific) ====\n"
                f"{context}\n\n"
                "==== USER REQUEST ====\n"
                f"Query: {query}"
            )
        ),
    ]