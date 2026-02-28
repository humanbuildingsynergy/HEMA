# agents/tools/knowledge_tools/rag/__init__.py
"""RAG (Retrieval-Augmented Generation) module for Knowledge Agent.

This module provides document retrieval capabilities using vector embeddings
to enhance the Knowledge Agent with specific information from PDFs and other
documents about utility rates, rebates, and energy efficiency guides.
"""

from .config import RAG_CONFIG
from .indexer import build_index, add_documents, get_index_stats
from .retriever import retrieve
from .rag_tool import search_energy_documents, get_knowledge_base_status

__all__ = [
    "RAG_CONFIG",
    "build_index",
    "add_documents",
    "get_index_stats",
    "retrieve",
    "search_energy_documents",
    "get_knowledge_base_status",
]
