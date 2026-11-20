import argparse
import hashlib
import logging
import time
from pathlib import Path

from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_text_splitters import MarkdownHeaderTextSplitter
from pinecone import Pinecone, ServerlessSpec

from src.utils import get_env

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def compute_content_hash(embedding_model: str, content: str) -> str:
    """Compute a deterministic SHA-256 hash combining the embedding model and source text."""
    payload = f"{embedding_model}\n{content}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def is_index_up_to_date(
    *,
    pc: Pinecone,
    index_name: str,
    chunk_ids: list[str],
    expected_hash: str,
) -> bool:
    """Check whether the vector index exists and holds the exact chunk count and hash."""
    existing_indexes = [idx.name for idx in pc.list_indexes()]
    if index_name not in existing_indexes:
        return False

    if not pc.describe_index(index_name).status["ready"]:
        return False

    index = pc.Index(index_name)
    stats = index.describe_index_stats()
    total_count = (
        stats.total_vector_count
        if hasattr(stats, "total_vector_count")
        else stats.get("total_vector_count", 0)
    )
    if total_count != len(chunk_ids):
        return False

    fetched = index.fetch(ids=chunk_ids)
    vectors = (
        fetched.vectors
        if hasattr(fetched, "vectors")
        else fetched.get("vectors", {})
    )
    if len(vectors) != len(chunk_ids):
        return False

    for chunk_id in chunk_ids:
        vec = vectors.get(chunk_id)
        if vec is None:
            return False
        metadata = (
            vec.metadata if hasattr(vec, "metadata") else vec.get("metadata", {})
        ) or {}
        if metadata.get("source_hash") != expected_hash:
            return False

    return True


def run_chunker(force: bool = False) -> None:
    index_name = get_env("VECTOR_STORE_INDEX_NAME")
    vector_api_key = get_env("VECTOR_STORE_API_KEY")
    embedding_model = get_env("EMBEDDING_MODEL")

    file_path = Path(__file__).parent / "layer.md"
    markdown_document = file_path.read_text(encoding="utf-8")
    content_hash = compute_content_hash(embedding_model, markdown_document)

    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("##", "Seccion")],
        strip_headers=False,
    )
    md_header_splits = markdown_splitter.split_text(markdown_document)

    for doc in md_header_splits:
        doc.metadata["source_hash"] = content_hash

    chunk_ids = [f"chunk_{i}" for i in range(len(md_header_splits))]
    pc = Pinecone(api_key=vector_api_key)

    if not force and is_index_up_to_date(
        pc=pc,
        index_name=index_name,
        chunk_ids=chunk_ids,
        expected_hash=content_hash,
    ):
        logger.info(
            "Index '%s' is already up to date (hash=%s, chunks=%d). Skipping indexing.",
            index_name,
            content_hash[:12],
            len(md_header_splits),
        )
        return

    existing_indexes = [idx.name for idx in pc.list_indexes()]
    if index_name in existing_indexes:
        logger.info("Deleting existing index '%s'...", index_name)
        pc.delete_index(index_name)

        while index_name in [idx.name for idx in pc.list_indexes()]:
            time.sleep(2)
        logger.info("Index '%s' successfully deleted.", index_name)

    logger.info("Creating serverless index '%s'...", index_name)
    pc.create_index(
        name=index_name,
        dimension=1536,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )

    while not pc.describe_index(index_name).status["ready"]:
        time.sleep(2)
    logger.info("Index '%s' is ready!", index_name)

    logger.info("Document split into %d chunks (hash=%s)", len(md_header_splits), content_hash[:12])
    logger.info("Generating embeddings and loading them into vector store...")

    embeddings = OpenAIEmbeddings(model=embedding_model)
    index = pc.Index(index_name)
    vectorstore = PineconeVectorStore(index=index, embedding=embeddings)
    vectorstore.add_documents(documents=md_header_splits, ids=chunk_ids)

    logger.info("Successfully loaded chunks into vector store!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Index layer.md chunks into the vector store.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force full re-indexing even if the content hash has not changed.",
    )
    args = parser.parse_args()
    run_chunker(force=args.force)