import logging
import os
import time
from pathlib import Path
from pinecone import Pinecone, ServerlessSpec
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_text_splitters import MarkdownHeaderTextSplitter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

BUSSINES_INDEX_NAME = os.getenv("BUSSINES_INDEX_NAME")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")

if not BUSSINES_INDEX_NAME or not EMBEDDING_MODEL:
    raise ValueError("BUSSINES_INDEX_NAME and EMBEDDING_MODEL must be specified")

pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))

existing_indexes = [idx.name for idx in pc.list_indexes()]
if BUSSINES_INDEX_NAME in existing_indexes:
    logger.info(f"Deleting existing index '{BUSSINES_INDEX_NAME}'...")
    pc.delete_index(BUSSINES_INDEX_NAME)
    
    while BUSSINES_INDEX_NAME in [idx.name for idx in pc.list_indexes()]:
        time.sleep(2)
    logger.info(f"Index '{BUSSINES_INDEX_NAME}' successfully deleted.")

logger.info(f"Creating classic serverless index '{BUSSINES_INDEX_NAME}'...")
pc.create_index(
    name=BUSSINES_INDEX_NAME,
    dimension=1536,
    metric="cosine",
    spec=ServerlessSpec(cloud="aws", region="us-east-1")
)

while not pc.describe_index(BUSSINES_INDEX_NAME).status["ready"]:
    time.sleep(2)
logger.info(f"Index '{BUSSINES_INDEX_NAME}' is ready!")

file_path = Path(__file__).parent / "layer.md"
with open(file_path, "r", encoding="utf-8") as f:
    markdown_document = f.read()

headers_to_split_on = [("##", "Seccion")]
markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=headers_to_split_on,
    strip_headers=False
)
md_header_splits = markdown_splitter.split_text(markdown_document)

logger.info(f"Document splitted in {len(md_header_splits)} chunks")
logger.info("Generating embeddings and loading them into Pinecone")

embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)

chunk_ids = [f"chunk_{i}" for i in range(len(md_header_splits))]

vectorstore = PineconeVectorStore.from_documents(
    documents=md_header_splits,
    embedding=embeddings,
    index_name=BUSSINES_INDEX_NAME,
    ids=chunk_ids
)
logger.info("Successfully loaded chunks into Pinecone!")
