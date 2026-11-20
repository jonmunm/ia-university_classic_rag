import argparse
import hashlib
import logging
import psycopg
from pathlib import Path
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_text_splitters import MarkdownHeaderTextSplitter

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


def is_collection_up_to_date(
    *,
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
    collection_name: str,
    expected_hash: str,
    expected_count: int,
) -> bool:
    """Check whether the vector store already holds the exact collection hash and chunk count."""
    with psycopg.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT to_regclass('public.langchain_pg_collection'), "
                "to_regclass('public.langchain_pg_embedding');"
            )
            col_table, emb_table = cur.fetchone()
            if not col_table or not emb_table:
                return False

            cur.execute(
                """
                SELECT e.cmetadata->>'source_hash', COUNT(*)
                FROM langchain_pg_embedding e
                JOIN langchain_pg_collection c ON e.collection_id = c.uuid
                WHERE c.name = %s
                GROUP BY e.cmetadata->>'source_hash';
                """,
                (collection_name,),
            )
            rows = cur.fetchall()

    return len(rows) == 1 and rows[0][0] == expected_hash and rows[0][1] == expected_count


def run_chunker(force: bool = False) -> None:
    business_index_name = get_env("BUSSINES_INDEX_NAME")
    embedding_model = get_env("EMBEDDING_MODEL")
    vector_host = get_env("VECTOR_STORE_HOST")
    vector_port = int(get_env("VECTOR_STORE_PORT"))
    vector_user = get_env("VECTOR_STORE_USER")
    vector_password = get_env("VECTOR_STORE_PASSWORD")
    vector_db = get_env("VECTOR_STORE_DB")

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

    if not force and is_collection_up_to_date(
        host=vector_host,
        port=vector_port,
        dbname=vector_db,
        user=vector_user,
        password=vector_password,
        collection_name=business_index_name,
        expected_hash=content_hash,
        expected_count=len(md_header_splits),
    ):
        logger.info(
            "Collection '%s' is already up to date (hash=%s, chunks=%d). Skipping indexing.",
            business_index_name,
            content_hash[:12],
            len(md_header_splits),
        )
        return

    logger.info("Document split into %d chunks (hash=%s)", len(md_header_splits), content_hash[:12])
    logger.info("Recreating collection '%s' and loading embeddings into vector store...", business_index_name)

    vector_store_connection = (
        f"postgresql+psycopg://{vector_user}:{vector_password}@{vector_host}:{vector_port}/{vector_db}"
    )
    embeddings = OpenAIEmbeddings(model=embedding_model)
    chunk_ids = [f"chunk_{i}" for i in range(len(md_header_splits))]

    PGVector.from_documents(
        documents=md_header_splits,
        embedding=embeddings,
        collection_name=business_index_name,
        connection=vector_store_connection,
        ids=chunk_ids,
        pre_delete_collection=True,
        use_jsonb=True,
    )
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