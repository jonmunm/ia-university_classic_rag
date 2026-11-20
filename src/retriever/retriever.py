from functools import lru_cache

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from src.utils import get_env

DEFAULT_TOP_K = 10

def get_vector_store_connection() -> str:
    """Build the SQLAlchemy connection URI for the configured vector store."""
    host = get_env("VECTOR_STORE_HOST")
    port = get_env("VECTOR_STORE_PORT")
    user = get_env("VECTOR_STORE_USER")
    password = get_env("VECTOR_STORE_PASSWORD")
    db = get_env("VECTOR_STORE_DB")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"


@lru_cache(maxsize=1)
def get_vector_store() -> PGVector:
    """Return a cached async PGVector instance to reuse a single connection pool."""
    embeddings = OpenAIEmbeddings(model=get_env("EMBEDDING_MODEL"))
    return PGVector(
        embeddings=embeddings,
        collection_name=get_env("BUSSINES_INDEX_NAME"),
        connection=get_vector_store_connection(),
        use_jsonb=True,
        async_mode=True,
    )


class VectorRetriever:
    """Encapsulates semantic document retrieval from the vector store."""

    def __init__(
        self,
        k: int = DEFAULT_TOP_K,
        vector_store: PGVector | None = None,
    ) -> None:
        store = vector_store or get_vector_store()
        self._retriever = store.as_retriever(search_kwargs={"k": k})

    async def retrieve(self, query: str) -> list[Document]:
        """Retrieve the top-k relevant metadata chunks for a natural language query."""
        return await self._retriever.ainvoke(query, config={"run_name": "1_Retrieval"})