# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/tools/knowledge_tools/rag/rag_tool.py
"""LangChain tool wrapper for RAG retrieval."""

from typing import Optional

from langchain_core.tools import tool

from utils.logger import setup_logger
from .retriever import retrieve, search_by_category
from .indexer import get_index_stats

logger = setup_logger()


@tool
def search_energy_documents(
    query: str,
    category: Optional[str] = None,
) -> str:
    """
    Search the energy knowledge base for relevant information.

    Use this tool to find specific information about:
    - Utility rate schedules and TOU pricing (Austin Energy)
    - Rebate and incentive programs (heat pumps, HVAC, water heaters)
    - Equipment specifications and efficiency ratings
    - Energy efficiency best practices and guides
    - Solar and battery storage information

    This tool searches through official documents including utility rate schedules,
    DOE energy guides, ENERGY STAR resources, and rebate program details.

    Args:
        query: The question or topic to search for. Be specific.
               Examples: "Austin Energy peak hours", "heat pump rebate eligibility",
               "SEER rating recommendations"
        category: Optional filter to narrow search results. Options:
                 - "rates": Utility rate schedules, TOU pricing, tier structures
                 - "rebates": Rebate programs, incentives, tax credits
                 - "equipment": Appliance specs, HVAC efficiency, product guides
                 - "efficiency": Energy saving tips, home improvements
                 - "solar": Solar panels, net metering, battery storage

    Returns:
        Relevant information from the knowledge base with source citations.
        If no relevant information is found, returns a message indicating this.
    """
    logger.info(f"RAG search: query='{query[:50]}...', category={category}")

    # Check if index has any documents
    stats = get_index_stats()
    if stats.get("total_chunks", 0) == 0:
        return (
            "The knowledge base is currently empty. No documents have been indexed yet.\n\n"
            "To add documents, place PDF or markdown files in the data/knowledge_base/ directory "
            "and run: python -m scripts.manage_rag build"
        )

    # Perform search
    if category:
        results = search_by_category(query, category)
    else:
        results = retrieve(query)

    if not results:
        return (
            f"No relevant information found in the knowledge base for: '{query}'\n\n"
            "Try rephrasing your question or using different keywords. "
            "You can also specify a category (rates, rebates, equipment, efficiency, solar) "
            "to narrow the search."
        )

    # Format response
    response_parts = ["## Retrieved Information\n"]

    for i, result in enumerate(results, 1):
        source = result["source"]
        page_info = f", page {result['page']}" if result.get("page") else ""
        relevance = f"{result['score']:.0%}"

        response_parts.append(f"### Source {i}: {source}{page_info}")
        response_parts.append(f"*Relevance: {relevance}*\n")
        response_parts.append(result["content"])
        response_parts.append("")  # Empty line between sources

    # Add citation note
    response_parts.append("---")
    response_parts.append(
        "*Information retrieved from indexed documents. "
        "Verify current rates and program details with official sources.*"
    )

    return "\n".join(response_parts)


@tool
def get_knowledge_base_status() -> str:
    """
    Check the status of the energy knowledge base.

    Use this tool to see what documents are available in the knowledge base
    and whether the index is ready for queries.

    Returns:
        Status information including number of indexed documents and their sources.
    """
    logger.info("Checking knowledge base status")

    stats = get_index_stats()

    if stats.get("status") == "error":
        return f"Knowledge base error: {stats.get('error', 'Unknown error')}"

    response_parts = ["## Knowledge Base Status\n"]

    response_parts.append(f"**Status:** {stats.get('status', 'unknown')}")
    response_parts.append(f"**Total chunks indexed:** {stats.get('total_chunks', 0)}")

    sources = stats.get("sources", [])
    if sources:
        response_parts.append(f"\n**Indexed documents ({len(sources)}):**")
        for source in sources:
            response_parts.append(f"- {source}")
    else:
        response_parts.append("\n**No documents indexed yet.**")
        response_parts.append(
            "\nTo add documents, place PDF or markdown files in:\n"
            f"`{stats.get('documents_path', 'data/knowledge_base/')}`"
        )

    return "\n".join(response_parts)
