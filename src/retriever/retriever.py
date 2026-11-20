from functools import lru_cache

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

from src.utils import get_env

DEFAULT_TOP_K = 10

@lru_cache(maxsize=1)
def get_vector_store() -> PineconeVectorStore:
    """Return a cached PineconeVectorStore instance to reuse a single client."""
    embeddings = OpenAIEmbeddings(model=get_env("EMBEDDING_MODEL"))
    return PineconeVectorStore(
        embedding=embeddings,
        index_name=get_env("VECTOR_STORE_INDEX_NAME"),
        pinecone_api_key=get_env("VECTOR_STORE_API_KEY"),
    )


class VectorRetriever:
    """Encapsulates semantic document retrieval from the vector store."""

    def __init__(
        self,
        k: int = DEFAULT_TOP_K,
        vector_store: PineconeVectorStore | None = None,
    ) -> None:
        store = vector_store or get_vector_store()
        self._retriever = store.as_retriever(search_kwargs={"k": k})

    async def retrieve(self, query: str) -> list[Document]:
        """Retrieve the top-k relevant metadata chunks for a natural language query."""
        return await self._retriever.ainvoke(query, config={"run_name": "1_Retrieval"})