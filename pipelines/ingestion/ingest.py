import argparse
import logging
import os
import tempfile
from typing import Any, Generator

import boto3
from langchain_community.document_loaders import (
    PyPDFLoader,
    UnstructuredMarkdownLoader,
    WikipediaLoader,
)
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter
from markitdown import MarkItDown

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ingest")

parser = argparse.ArgumentParser(
    description="Ingest & embed documents into vector store"
)
parser.add_argument(
    "--input-directory",
    type=str,
    help="Directory containing documents to ingest (local)",
)
parser.add_argument("--chunk-size", type=int, help="Chunk size for splitting")
parser.add_argument("--chunk-overlap", type=int, help="Chunk overlap for splitting")
parser.add_argument(
    "--collection-name",
    type=str,
    help="Name of collection to store documents",
    required=True,
)
parser.add_argument(
    "--embedding-model-name",
    type=str,
    help="Name of embedding model to use",
    required=True,
)
parser.add_argument(
    "--recreate-collection",
    type=bool,
    default=False,
    help="Recreate collection",
)
parser.add_argument(
    "--s3-bucket",
    type=str,
    help="Name of the S3 bucket containing PDF documents",
)
parser.add_argument(
    "--s3-prefix",
    type=str,
    help="Prefix (subdirectory) in the S3 bucket to filter PDFs",
    default="",
)
parser.add_argument(
    "--convert-to-markdown",
    type=bool,
    help="Convert PDFs to Markdown",
    default=False,
)
parser.add_argument(
    "--disable-chunking",
    type=bool,
    help="Disable chunking of documents",
    default=False,
)
parser.add_argument(
    "--enable-full-documents",
    type=bool,
    help="Enable full documents to be stored in the vector store",
    default=False,
)
parser.add_argument(
    "--wikipedia-query", type=str, help="Query to search for Wikipedia articles"
)
args = parser.parse_args()

logger.info(f"Args: {args}")

# Initalize DB information
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")

if not DB_USER:
    logger.error("DB_USER is not set")
    raise Exception("DB_USER is not set")

if not DB_PASSWORD:
    logger.error("DB_PASSWORD is not set")
    raise Exception("DB_PASSWORD is not set")

if not DB_HOST:
    logger.error("DB_HOST is not set")
    raise Exception("DB_HOST is not set")

if not DB_NAME:
    logger.error("DB_NAME is not set")
    raise Exception("DB_NAME is not set")

md = MarkItDown() if args.convert_to_markdown else None


def chunk_list(lst: list[Any], chunk_size: int = 500) -> Generator[Any, Any, Any]:
    """Yield successive chunk_size-sized chunks from a list."""
    for i in range(0, len(lst), chunk_size):
        yield lst[i : i + chunk_size]


def fetch_pdfs_from_local_directory(directory: str) -> list[str]:
    """
    Fetch .pdf file paths from local directory.
    """
    pdf_paths = []
    for file_name in os.listdir(directory):
        if file_name.lower().endswith(".pdf"):
            pdf_paths.append(os.path.join(directory, file_name))
    return pdf_paths


def convert_pdfs_to_markdown(file_list: list[str]) -> list[str]:
    """
    Convert PDF files to Markdown.
    """
    markdown_paths = []
    for pdf_file in file_list:
        logger.info(f"Converting {pdf_file} to Markdown")
        result = md.convert(pdf_file)
        local_temp_path = os.path.join(
            tempfile.gettempdir(), os.path.basename(pdf_file) + ".md"
        )
        with open(local_temp_path, "w") as f:
            f.write(result.text_content)
        markdown_paths.append(local_temp_path)
    return markdown_paths


def fetch_pdfs_from_s3(bucket_name: str, prefix: str = "") -> list[str]:
    """
    Fetch .pdf files from an S3 bucket (optionally with a prefix).
    Downloads each PDF to a temporary file and returns a list of local file paths.
    """
    s3 = boto3.client("s3")
    pdf_paths = []

    paginator = s3.get_paginator("list_objects_v2")
    page_iterator = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

    for page in page_iterator:
        if "Contents" not in page:
            continue
        for obj in page["Contents"]:
            key = obj["Key"]
            if key.lower().endswith(".pdf"):
                local_temp_path = os.path.join(
                    tempfile.gettempdir(), os.path.basename(key)
                )
                logger.info(
                    f"Downloading s3://{bucket_name}/{key} -> {local_temp_path}"
                )
                s3.download_file(bucket_name, key, local_temp_path)
                pdf_paths.append(local_temp_path)

    return pdf_paths


def ingest() -> None:
    """Ingest documents into the vector store."""
    input_directory: str | None = args.input_directory
    s3_bucket: str | None = args.s3_bucket
    s3_prefix: str = args.s3_prefix
    wikipedia_query: str | None = args.wikipedia_query

    chunk_size: int = args.chunk_size
    chunk_overlap: int = args.chunk_overlap
    collection_name: str = args.collection_name
    embedding_model_name: str = args.embedding_model_name
    recreate_collection: bool = args.recreate_collection

    embeddings = OpenAIEmbeddings(model=embedding_model_name)

    vector_store = PGVector(
        embeddings=embeddings,
        collection_name=collection_name,
        connection=f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}",
    )

    if recreate_collection:
        logger.info(f"Recreating collection '{collection_name}'...")
        vector_store.delete_collection()
        vector_store.create_collection()
        logger.info("Collection recreated successfully")

    pdf_file_paths = []

    if s3_bucket:
        logger.info(f"Fetching PDFs from S3 bucket: {s3_bucket}, prefix: {s3_prefix}")
        pdf_file_paths = fetch_pdfs_from_s3(s3_bucket, s3_prefix)
    elif input_directory:
        logger.info(f"Fetching PDFs from local directory: {input_directory}")
        pdf_file_paths = fetch_pdfs_from_local_directory(input_directory)
    elif wikipedia_query:
        pass
    else:
        logger.error("No input directory or S3 bucket specified. Exiting.")
        exit(1)

    if len(pdf_file_paths) == 0 and not args.wikipedia_query:
        logger.warning("No PDF files found")
        return

    if args.convert_to_markdown:
        logger.info(
            f"Converting PDFs to Markdown in local directory: {input_directory}"
        )
        markdown_file_paths = convert_pdfs_to_markdown(pdf_file_paths)

    all_documents = []
    if not args.convert_to_markdown and not wikipedia_query:
        for pdf_path in pdf_file_paths:
            pdf_loader = PyPDFLoader(pdf_path)
            docs = pdf_loader.load()
            all_documents.extend(docs)
    elif wikipedia_query:
        wikipedia_loader = WikipediaLoader(query=wikipedia_query)
        all_documents = wikipedia_loader.load()
    else:
        for markdown_path in markdown_file_paths:
            markdown_loader = UnstructuredMarkdownLoader(markdown_path)
            docs = markdown_loader.load()
            all_documents.extend(docs)

    logger.info(f"Loaded {len(all_documents)} total documents/pages from PDFs")

    if not args.disable_chunking:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        chunked_documents = text_splitter.split_documents(all_documents)
        logger.info(f"Generated {len(chunked_documents)} chunks.")

        for chunk in chunk_list(chunked_documents):
            vector_store.add_documents(chunk)

        logger.info("Document chunks loaded successfully into the vector store")

    if args.enable_full_documents:
        for documents in chunk_list(all_documents):
            vector_store.add_documents(documents)

        logger.info("Non-chunked documents loaded successfully into the vector store")


if __name__ == "__main__":
    ingest()
