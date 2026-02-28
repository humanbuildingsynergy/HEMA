#!/usr/bin/env python
# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
"""CLI for managing the RAG knowledge base.

Usage:
    python -m scripts.manage_rag build [--force]     Build/rebuild the vector index
    python -m scripts.manage_rag add <files...>      Add documents to the index
    python -m scripts.manage_rag query <query>       Test a search query
    python -m scripts.manage_rag status              Show index status
    python -m scripts.manage_rag clear               Clear the entire index
    python -m scripts.manage_rag download            Download sample documents
"""

import argparse
import sys
from pathlib import Path


def cmd_build(args):
    """Build or rebuild the vector index."""
    from agents.tools.knowledge_tools.rag import build_index, get_index_stats

    print("Building vector index...")
    try:
        build_index(force_rebuild=args.force)
        stats = get_index_stats()
        print(f"\nIndex built successfully!")
        print(f"  Total chunks: {stats.get('total_chunks', 0)}")
        print(f"  Sources: {len(stats.get('sources', []))}")
        for source in stats.get("sources", []):
            print(f"    - {source}")
    except Exception as e:
        print(f"Error building index: {e}")
        sys.exit(1)


def cmd_add(args):
    """Add documents to the index."""
    from agents.tools.knowledge_tools.rag import add_documents

    paths = [Path(f) for f in args.files]
    missing = [p for p in paths if not p.exists()]

    if missing:
        print("Error: Files not found:")
        for p in missing:
            print(f"  - {p}")
        sys.exit(1)

    print(f"Adding {len(paths)} document(s)...")
    try:
        count = add_documents(paths)
        print(f"Successfully added {count} chunks to the index.")
    except Exception as e:
        print(f"Error adding documents: {e}")
        sys.exit(1)


def cmd_query(args):
    """Test a search query."""
    from agents.tools.knowledge_tools.rag import retrieve

    print(f"Searching for: {args.query}\n")

    try:
        results = retrieve(args.query, top_k=args.top_k)

        if not results:
            print("No results found.")
            return

        print(f"Found {len(results)} result(s):\n")
        for i, result in enumerate(results, 1):
            source = result["source"]
            page = f", page {result['page']}" if result.get("page") else ""
            score = result["score"]

            print(f"--- Result {i} ({source}{page}) [score: {score:.2f}] ---")
            # Truncate content for display
            content = result["content"]
            if len(content) > 500:
                content = content[:500] + "..."
            print(content)
            print()

    except Exception as e:
        print(f"Error during search: {e}")
        sys.exit(1)


def cmd_status(args):
    """Show index status."""
    from agents.tools.knowledge_tools.rag import get_index_stats
    from agents.tools.knowledge_tools.rag.config import RAG_CONFIG

    stats = get_index_stats()

    print("Knowledge Base Status")
    print("=" * 50)
    print(f"Status: {stats.get('status', 'unknown')}")
    print(f"Total chunks indexed: {stats.get('total_chunks', 0)}")
    print(f"Documents directory: {RAG_CONFIG.documents_dir}")
    print(f"Index directory: {RAG_CONFIG.index_dir}")

    sources = stats.get("sources", [])
    if sources:
        print(f"\nIndexed documents ({len(sources)}):")
        for source in sources:
            print(f"  - {source}")
    else:
        print("\nNo documents indexed yet.")
        print("\nTo add documents:")
        print(f"  1. Place PDF/markdown files in: {RAG_CONFIG.documents_dir}")
        print("  2. Run: python -m scripts.manage_rag build")

    if stats.get("error"):
        print(f"\nError: {stats['error']}")


def cmd_clear(args):
    """Clear the entire index."""
    from agents.tools.knowledge_tools.rag.indexer import clear_index

    if not args.yes:
        response = input("Are you sure you want to clear the entire index? [y/N] ")
        if response.lower() != "y":
            print("Cancelled.")
            return

    print("Clearing index...")
    if clear_index():
        print("Index cleared successfully.")
    else:
        print("Error clearing index.")
        sys.exit(1)


def cmd_download(args):
    """Download sample documents for the knowledge base."""
    import urllib.request
    from agents.tools.knowledge_tools.rag.config import RAG_CONFIG

    # Sample documents to download
    documents = [
        {
            "url": "https://www.energy.gov/sites/default/files/2022-08/energy-saver-guide-2022.pdf",
            "filename": "energy-saver-guide-2022.pdf",
            "subdir": "guides",
            "description": "DOE Energy Saver Guide",
        },
    ]

    print("Downloading sample documents...\n")

    for doc in documents:
        target_dir = RAG_CONFIG.documents_dir / doc["subdir"]
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / doc["filename"]

        if target_path.exists() and not args.force:
            print(f"  [skip] {doc['description']} (already exists)")
            continue

        print(f"  Downloading {doc['description']}...")
        try:
            urllib.request.urlretrieve(doc["url"], target_path)
            print(f"    -> {target_path}")
        except Exception as e:
            print(f"    Error: {e}")

    print("\nDownload complete!")
    print("\nTo build the index, run:")
    print("  python -m scripts.manage_rag build")


def main():
    parser = argparse.ArgumentParser(
        description="Manage the RAG knowledge base for HEMA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Build command
    build_parser = subparsers.add_parser("build", help="Build/rebuild the vector index")
    build_parser.add_argument(
        "--force", "-f", action="store_true", help="Force rebuild even if index exists"
    )

    # Add command
    add_parser = subparsers.add_parser("add", help="Add documents to the index")
    add_parser.add_argument("files", nargs="+", help="PDF or markdown files to add")

    # Query command
    query_parser = subparsers.add_parser("query", help="Test a search query")
    query_parser.add_argument("query", help="Search query")
    query_parser.add_argument(
        "--top-k", "-k", type=int, default=4, help="Number of results (default: 4)"
    )

    # Status command
    subparsers.add_parser("status", help="Show index status")

    # Clear command
    clear_parser = subparsers.add_parser("clear", help="Clear the entire index")
    clear_parser.add_argument(
        "--yes", "-y", action="store_true", help="Skip confirmation prompt"
    )

    # Download command
    download_parser = subparsers.add_parser(
        "download", help="Download sample documents"
    )
    download_parser.add_argument(
        "--force", "-f", action="store_true", help="Overwrite existing files"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Route to command handler
    commands = {
        "build": cmd_build,
        "add": cmd_add,
        "query": cmd_query,
        "status": cmd_status,
        "clear": cmd_clear,
        "download": cmd_download,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
