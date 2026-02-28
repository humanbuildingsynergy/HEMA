# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/tools/knowledge_tools/rag/indexer.py
"""Vector store indexing for RAG system using ChromaDB."""

from pathlib import Path
from typing import Dict, List, Optional, Any

from langchain_core.documents import Document

from utils.logger import setup_logger
from .config import RAG_CONFIG
from .document_loader import load_and_chunk, load_document, chunk_documents

logger = setup_logger()

# Singleton vector store instance
_vector_store = None


def get_embeddings():
    """Get the embedding model based on configuration."""
    if RAG_CONFIG.embedding_provider == "openai":
        try:
            from langchain_openai import OpenAIEmbeddings

            return OpenAIEmbeddings(model=RAG_CONFIG.embedding_model)
        except ImportError:
            logger.error("langchain-openai not installed. Run: pip install langchain-openai")
            raise
    else:
        raise ValueError(f"Unsupported embedding provider: {RAG_CONFIG.embedding_provider}")


def build_index(force_rebuild: bool = False) -> Any:
    """
    Build or load the vector index.

    Args:
        force_rebuild: If True, rebuild index even if it exists

    Returns:
        ChromaDB vector store instance
    """
    global _vector_store

    try:
        from langchain_chroma import Chroma
    except ImportError:
        logger.error("langchain-chroma not installed. Run: pip install langchain-chroma")
        raise

    index_path = RAG_CONFIG.index_dir

    # Return cached instance if available and not forcing rebuild
    if _vector_store is not None and not force_rebuild:
        return _vector_store

    # Check if existing index exists
    chroma_db_path = index_path / "chroma.sqlite3"
    index_exists = chroma_db_path.exists()

    if index_exists and not force_rebuild:
        logger.info(f"Loading existing index from {index_path}")
        _vector_store = Chroma(
            persist_directory=str(index_path),
            embedding_function=get_embeddings(),
            collection_name="energy_knowledge",
        )
        return _vector_store

    # Build new index
    logger.info("Building new vector index...")

    # Load and chunk documents
    chunks = load_and_chunk()

    if not chunks:
        logger.warning("No documents found to index. Creating empty index.")
        _vector_store = Chroma(
            persist_directory=str(index_path),
            embedding_function=get_embeddings(),
            collection_name="energy_knowledge",
        )
        return _vector_store

    logger.info(f"Indexing {len(chunks)} chunks...")

    _vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=get_embeddings(),
        persist_directory=str(index_path),
        collection_name="energy_knowledge",
    )

    logger.info(f"Index built and saved to {index_path}")
    return _vector_store


def add_documents(file_paths: List[Path]) -> int:
    """
    Add new documents to the existing index.

    Args:
        file_paths: List of file paths to add

    Returns:
        Number of chunks added
    """
    global _vector_store

    if _vector_store is None:
        _vector_store = build_index()

    # Load documents
    all_docs = []
    for path in file_paths:
        path = Path(path)
        if path.exists():
            docs = load_document(path)
            all_docs.extend(docs)
        else:
            logger.warning(f"File not found: {path}")

    if not all_docs:
        logger.warning("No documents loaded")
        return 0

    # Chunk documents
    chunks = chunk_documents(all_docs)

    # Add to index
    _vector_store.add_documents(chunks)

    logger.info(f"Added {len(chunks)} chunks from {len(file_paths)} files")
    return len(chunks)


def delete_source(source_name: str) -> int:
    """
    Delete all chunks from a specific source.

    Args:
        source_name: Name of the source file to delete

    Returns:
        Number of chunks deleted
    """
    global _vector_store

    if _vector_store is None:
        _vector_store = build_index()

    # Get documents with matching source
    results = _vector_store.get(where={"source": source_name})

    if not results or not results.get("ids"):
        logger.info(f"No documents found for source: {source_name}")
        return 0

    ids_to_delete = results["ids"]
    _vector_store.delete(ids=ids_to_delete)

    logger.info(f"Deleted {len(ids_to_delete)} chunks from source: {source_name}")
    return len(ids_to_delete)


def get_index_stats() -> Dict[str, Any]:
    """
    Get statistics about the current index.

    Returns:
        Dictionary with index statistics
    """
    global _vector_store

    if _vector_store is None:
        try:
            _vector_store = build_index()
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "total_chunks": 0,
                "sources": [],
            }

    try:
        # Get collection info
        collection = _vector_store._collection
        count = collection.count()

        # Get unique sources
        results = _vector_store.get(include=["metadatas"])
        sources = set()
        if results and results.get("metadatas"):
            for metadata in results["metadatas"]:
                if metadata and "source" in metadata:
                    sources.add(metadata["source"])

        return {
            "status": "ready",
            "total_chunks": count,
            "sources": sorted(list(sources)),
            "index_path": str(RAG_CONFIG.index_dir),
            "documents_path": str(RAG_CONFIG.documents_dir),
        }

    except Exception as e:
        logger.error(f"Error getting index stats: {e}")
        return {
            "status": "error",
            "error": str(e),
            "total_chunks": 0,
            "sources": [],
        }


def clear_index() -> bool:
    """
    Clear the entire index.

    Returns:
        True if successful
    """
    global _vector_store

    import shutil

    try:
        # Remove the index directory
        if RAG_CONFIG.index_dir.exists():
            shutil.rmtree(RAG_CONFIG.index_dir)
            RAG_CONFIG.index_dir.mkdir(parents=True, exist_ok=True)

        _vector_store = None
        logger.info("Index cleared successfully")
        return True

    except Exception as e:
        logger.error(f"Error clearing index: {e}")
        return False
