"""
Pydantic data transfer objects (DTOs) for SQL generation API endpoints.
"""

from pydantic import BaseModel

class SqlGenerationBodyResponse(BaseModel):
    """
    Data model representing the SQL generation payload.

    Attributes:
        query (str): The natural language prompt or generated SQL query string.
    """
    query: str