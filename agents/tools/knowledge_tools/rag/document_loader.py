# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/tools/knowledge_tools/rag/document_loader.py
"""Document loading and chunking for RAG system."""

from pathlib import Path
from typing import List, Optional

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from utils.logger import setup_logger
from .config import RAG_CONFIG

logger = setup_logger()


def load_pdf(file_path: Path) -> List[Document]:
    """Load a PDF file and return documents."""
    try:
        from langchain_community.document_loaders import PyPDFLoader

        loader = PyPDFLoader(str(file_path))
        docs = loader.load()

        # Add source metadata
        for doc in docs:
            doc.metadata["source"] = file_path.name
            doc.metadata["source_path"] = str(file_path)
            doc.metadata["file_type"] = "pdf"

        logger.info(f"Loaded PDF: {file_path.name} ({len(docs)} pages)")
        return docs

    except ImportError:
        logger.error("pypdf not installed. Run: pip install pypdf")
        return []
    except Exception as e:
        logger.error(f"Error loading PDF {file_path}: {e}")
        return []


def load_markdown(file_path: Path) -> List[Document]:
    """Load a markdown file and return documents."""
    try:
        from langchain_community.document_loaders import UnstructuredMarkdownLoader

        loader = UnstructuredMarkdownLoader(str(file_path))
        docs = loader.load()

        # Add source metadata
        for doc in docs:
            doc.metadata["source"] = file_path.name
            doc.metadata["source_path"] = str(file_path)
            doc.metadata["file_type"] = "markdown"

        logger.info(f"Loaded Markdown: {file_path.name}")
        return docs

    except ImportError:
        # Fallback to simple text loading
        logger.warning("unstructured not installed, using simple text loader")
        return load_text(file_path)
    except Exception as e:
        logger.error(f"Error loading markdown {file_path}: {e}")
        return []


def load_text(file_path: Path) -> List[Document]:
    """Load a plain text file and return documents."""
    try:
        content = file_path.read_text(encoding="utf-8")
        doc = Document(
            page_content=content,
            metadata={
                "source": file_path.name,
                "source_path": str(file_path),
                "file_type": "text",
            },
        )
        logger.info(f"Loaded text file: {file_path.name}")
        return [doc]

    except Exception as e:
        logger.error(f"Error loading text file {file_path}: {e}")
        return []


def load_document(file_path: Path) -> List[Document]:
    """Load a document based on its file type."""
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        return load_pdf(file_path)
    elif suffix == ".md":
        return load_markdown(file_path)
    elif suffix == ".txt":
        return load_text(file_path)
    else:
        logger.warning(f"Unsupported file type: {suffix} for {file_path}")
        return []


def load_documents(
    source_dir: Optional[Path] = None,
    recursive: bool = True,
) -> List[Document]:
    """
    Load all supported documents from a directory.

    Args:
        source_dir: Directory to load from (default: RAG_CONFIG.documents_dir)
        recursive: Whether to search subdirectories

    Returns:
        List of Document objects
    """
    source_dir = source_dir or RAG_CONFIG.documents_dir

    if not source_dir.exists():
        logger.warning(f"Documents directory does not exist: {source_dir}")
        return []

    documents = []
    pattern = "**/*" if recursive else "*"

    for ext in RAG_CONFIG.supported_extensions:
        for file_path in source_dir.glob(f"{pattern}{ext}"):
            if file_path.is_file():
                docs = load_document(file_path)
                documents.extend(docs)

    logger.info(f"Loaded {len(documents)} documents from {source_dir}")
    return documents


def chunk_documents(
    documents: List[Document],
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> List[Document]:
    """
    Split documents into smaller chunks for embedding.

    Args:
        documents: List of documents to chunk
        chunk_size: Size of each chunk (default: RAG_CONFIG.chunk_size)
        chunk_overlap: Overlap between chunks (default: RAG_CONFIG.chunk_overlap)

    Returns:
        List of chunked Document objects
    """
    chunk_size = chunk_size or RAG_CONFIG.chunk_size
    chunk_overlap = chunk_overlap or RAG_CONFIG.chunk_overlap

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", ", ", " ", ""],
        length_function=len,
    )

    chunks = splitter.split_documents(documents)

    logger.info(
        f"Split {len(documents)} documents into {len(chunks)} chunks "
        f"(size={chunk_size}, overlap={chunk_overlap})"
    )

    return chunks


def load_and_chunk(
    source_dir: Optional[Path] = None,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> List[Document]:
    """
    Convenience function to load and chunk documents in one step.

    Args:
        source_dir: Directory to load from
        chunk_size: Size of each chunk
        chunk_overlap: Overlap between chunks

    Returns:
        List of chunked Document objects ready for embedding
    """
    documents = load_documents(source_dir)
    if not documents:
        return []
    return chunk_documents(documents, chunk_size, chunk_overlap)
