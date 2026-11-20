"""
Pydantic schemas and response models for the LLM SQL generation service.
"""
import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError
from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.documents import Document


class LLMSqlGeneratorSchema(BaseModel):
    """
    Structured output schema for natural language to SQL (NL-to-SQL) generation.

    Attributes:
        is_error (bool): Flag indicating whether the user's request cannot be 
            satisfied using the available database schema.
        error_message (Optional[str]): Concise explanation of why the query could not 
            be generated (e.g., missing columns, ambiguity, or granularity issues). 
            Populated strictly when is_error is True; otherwise None.
        sql_query (Optional[str]): The generated, executable SQL query string. 
            Populated strictly when is_error is False; otherwise None.
    """

    is_error: bool = Field(
        description="True ONLY if the request is impossible to fulfill with the given schema."
    )

    error_message: Optional[str] = Field(
        default=None,
        description="Populate ONLY when is_error=True: one or two sentences on the missing column, ambiguity, or grain issue and how to fix the request. MUST be null when is_error=False."
    )

    sql_query: Optional[str] = Field(
        default=None,
        description="The executable Oracle SQL query. Null when is_error is True."
    )


class LLMSqlGeneratorServiceResponse(BaseModel):
    """
    Internal service response wrapper combining the structured LLM output 
    with the retrieved vector store context documents.

    Attributes:
        parsed (LLMSqlGeneratorSchema): The structured SQL generation result or error details.
        contexts (list[Document]): The list of retrieved LangChain Document chunks 
            used as context during generation.
    """
    parsed: LLMSqlGeneratorSchema
    contexts: list[Document]

def validate_safe_select(sql: str) -> None:
    """
    Validate that the SQL query is syntactically valid PostgreSQL and strictly read-only.

    Ensures the top-level statement is a SELECT or set operation (UNION, INTERSECT, EXCEPT)
    and verifies that the abstract syntax tree (AST) contains no destructive DML or DDL 
    nodes (INSERT, UPDATE, DELETE, DROP, ALTER).

    Args:
        sql (str): The raw SQL query string to validate.

    Raises:
        ValueError: If the SQL has syntax errors, is not a read-only SELECT/SET 
            statement, or contains forbidden DML/DDL operations.
    """
    if not sql:
        return

    try:
        tree = sqlglot.parse_one(sql, read="postgres")
    except ParseError as e:
        raise ValueError(f"Syntactic error in generated SQL: {str(e)}")

    allowed_types = (exp.Select, exp.Union, exp.Intersect, exp.Except)
    if not isinstance(tree, allowed_types):
        raise ValueError("Only SELECT and SET operations allowed")

    forbidden = (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Alter)
    if any(tree.find(f) for f in forbidden):
        raise ValueError("DML/DDL operations are strictly forbidden.")

def format_docs(docs: list[Document]) -> str:
    """
    Concatenate the text content of retrieved documents into a single string.

    Args:
        docs (list[Document]): A list of retrieved LangChain Document objects.

    Returns:
        str: The combined page content of all documents, separated by double newlines.
    """
    return "\n\n".join(doc.page_content for doc in docs)