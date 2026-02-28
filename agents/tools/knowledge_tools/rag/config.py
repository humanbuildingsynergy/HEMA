# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/tools/knowledge_tools/rag/config.py
"""Configuration for RAG system."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


def _get_project_root() -> Path:
    """Get the project root directory."""
    # Navigate up from this file to find project root
    current = Path(__file__).resolve()
    # Go up: rag -> knowledge_tools -> tools -> agents -> project_root
    return current.parents[4]


@dataclass
class RAGConfig:
    """RAG system configuration."""

    # Paths (relative to project root)
    documents_dir: Path = field(default_factory=lambda: _get_project_root() / "data" / "knowledge_base")
    index_dir: Path = field(default_factory=lambda: _get_project_root() / "data" / "vector_index")

    # Chunking parameters
    chunk_size: int = 1000  # characters per chunk
    chunk_overlap: int = 200  # overlap between chunks

    # Retrieval parameters
    top_k: int = 4  # number of results to return
    score_threshold: float = 0.3  # minimum relevance score (0-1)

    # Embedding model
    # OpenAI embeddings (requires OPENAI_API_KEY)
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"

    # Supported file types
    supported_extensions: List[str] = field(
        default_factory=lambda: [".pdf", ".md", ".txt"]
    )

    def __post_init__(self):
        """Ensure directories exist."""
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        self.index_dir.mkdir(parents=True, exist_ok=True)


# Global config instance
RAG_CONFIG = RAGConfig()
