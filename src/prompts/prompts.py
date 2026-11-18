from src.utils import get_schema
from langchain_core.messages import HumanMessage
from langchain_core.messages import SystemMessage
from langchain_core.messages import BaseMessage

STATIC_SYSTEM_TEMPLATE = """
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
"""

STATIC_SYSTEM_PROMPT = STATIC_SYSTEM_TEMPLATE.format(
    schema=get_schema()
)

def get_messages_prompt(context: str, query: str) -> list[BaseMessage]:
    """
    Construct the system and human message payload for the LLM, 
    including an ephemeral prompt cache breakpoint on the system prompt.

    Args:
        context (str): The formatted retrieved context documents.
        query (str): The user's natural language question.

    Returns:
        list[BaseMessage]: The list of messages ready to be passed to the chat model.
    """
    return [
        SystemMessage(content=[
            {
                "type": "text",
                "text": STATIC_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},  # <-- CACHE BREAKPOINT
            },
        ]),
        HumanMessage(content=[
            {
                "type": "text",
                "text": (
                    "==== OTHER METADATA CONTEXT (retrieved, query-specific) ====\n"
                    f"{context}\n\n"
                    "==== USER REQUEST ====\n"
                    f"Query: {query}"
                ),
            },
        ]),
    ]