# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/tools/knowledge_tools/rag/retriever.py
"""Document retrieval for RAG system."""

from typing import Dict, List, Any, Optional

from utils.logger import setup_logger
from .config import RAG_CONFIG
from .indexer import build_index

logger = setup_logger()


def retrieve(
    query: str,
    top_k: Optional[int] = None,
    score_threshold: Optional[float] = None,
    filter_source: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve relevant documents for a query.

    Args:
        query: The search query
        top_k: Number of results to return (default: RAG_CONFIG.top_k)
        score_threshold: Minimum relevance score (default: RAG_CONFIG.score_threshold)
        filter_source: Only return results from this source file

    Returns:
        List of dictionaries with keys: content, source, page, score
    """
    top_k = top_k or RAG_CONFIG.top_k
    score_threshold = score_threshold or RAG_CONFIG.score_threshold

    try:
        vector_store = build_index()
    except Exception as e:
        logger.error(f"Failed to load index: {e}")
        return []

    # Build filter if source specified
    where_filter = None
    if filter_source:
        where_filter = {"source": filter_source}

    try:
        # Retrieve with relevance scores
        if where_filter:
            results = vector_store.similarity_search_with_relevance_scores(
                query,
                k=top_k,
                filter=where_filter,
            )
        else:
            results = vector_store.similarity_search_with_relevance_scores(
                query,
                k=top_k,
            )
    except Exception as e:
        logger.error(f"Error during retrieval: {e}")
        return []

    # Format and filter results
    formatted = []
    for doc, score in results:
        # Skip results below threshold
        if score < score_threshold:
            continue

        formatted.append({
            "content": doc.page_content,
            "source": doc.metadata.get("source", "unknown"),
            "source_path": doc.metadata.get("source_path"),
            "page": doc.metadata.get("page"),
            "file_type": doc.metadata.get("file_type"),
            "score": round(score, 3),
        })

    logger.info(
        f"Retrieved {len(formatted)} relevant chunks for query: {query[:50]}..."
    )

    return formatted


def retrieve_with_context(
    query: str,
    top_k: Optional[int] = None,
) -> str:
    """
    Retrieve documents and format them as context for LLM.

    Args:
        query: The search query
        top_k: Number of results to return

    Returns:
        Formatted string with retrieved context
    """
    results = retrieve(query, top_k=top_k)

    if not results:
        return ""

    context_parts = []
    for i, result in enumerate(results, 1):
        source = result["source"]
        page_info = f", page {result['page']}" if result.get("page") else ""

        context_parts.append(
            f"[Source {i}: {source}{page_info}]\n{result['content']}"
        )

    return "\n\n---\n\n".join(context_parts)


def search_by_category(
    query: str,
    category: str,
    top_k: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Search with category-specific query enhancement.

    Args:
        query: The base search query
        category: Category to search - "rates", "rebates", "equipment", "efficiency", "solar"
        top_k: Number of results to return

    Returns:
        List of result dictionaries
    """
    # Category-specific query enhancement
    category_context = {
        "rates": "utility rate schedule TOU time-of-use pricing tier",
        "rebates": "rebate incentive program tax credit savings",
        "equipment": "appliance HVAC efficiency SEER rating specification",
        "efficiency": "energy efficiency home improvement weatherization",
        "solar": "solar panel net metering battery storage photovoltaic",
        "general": "",
    }

    enhancement = category_context.get(category.lower(), "")
    enhanced_query = f"{query} {enhancement}".strip()

    logger.info(f"Category search: {category} -> {enhanced_query[:50]}...")

    return retrieve(enhanced_query, top_k=top_k)
