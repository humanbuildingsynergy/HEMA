#!/usr/bin/env python3
# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# scripts/read_session_log.py
"""
Session log reader utility for debugging HEMA interactions.

Reads and displays session replay logs in a human-readable format.

⚠️  IMPORTANT: Session logging is OFF by default for privacy.
    Enable it with: export HEMA_LOG_SESSIONS=true (before running HEMA API)

Usage:
    python scripts/read_session_log.py --latest              # Read most recent session
    python scripts/read_session_log.py --session abc123      # Read specific session
    python scripts/read_session_log.py --errors              # Show only errors
    python scripts/read_session_log.py --tail 10             # Show last N entries
    python scripts/read_session_log.py --list                # List available sessions

Example with evaluation:
    export HEMA_LOG_SESSIONS=true
    python -m evaluation.run_experiment --persona confused_newcomer --scenario understand_utility_rate
    python scripts/read_session_log.py --latest --verbose
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Default log directory
DEFAULT_LOG_DIR = "logs/session_replay"


def list_sessions(log_dir: str = DEFAULT_LOG_DIR) -> List[Dict[str, Any]]:
    """List all available session log files."""
    log_path = Path(log_dir)
    if not log_path.exists():
        return []

    sessions = []
    for file in sorted(log_path.glob("session_*.jsonl"), reverse=True):
        # Parse filename: session_{session_id}_{date}.jsonl
        parts = file.stem.split("_")
        if len(parts) >= 3:
            session_id = "_".join(parts[1:-1])
            date_str = parts[-1]
        else:
            session_id = file.stem
            date_str = "unknown"

        # Get file stats
        stat = file.stat()
        entry_count = sum(1 for _ in open(file))

        sessions.append({
            "file": str(file),
            "session_id": session_id,
            "date": date_str,
            "size_kb": round(stat.st_size / 1024, 2),
            "entries": entry_count,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })

    return sessions


def read_log_file(filepath: str) -> List[Dict[str, Any]]:
    """Read all entries from a JSONL log file."""
    entries = []
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def find_latest_session(log_dir: str = DEFAULT_LOG_DIR) -> Optional[str]:
    """Find the most recently modified session log file."""
    log_path = Path(log_dir)
    if not log_path.exists():
        return None

    files = list(log_path.glob("session_*.jsonl"))
    if not files:
        return None

    # Sort by modification time, most recent first
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return str(files[0])


def find_session_file(session_id: str, log_dir: str = DEFAULT_LOG_DIR) -> Optional[str]:
    """Find log file(s) for a specific session ID."""
    log_path = Path(log_dir)
    if not log_path.exists():
        return None

    # Look for files matching the session ID
    matches = list(log_path.glob(f"session_{session_id}_*.jsonl"))
    if matches:
        # Return most recent
        matches.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        return str(matches[0])

    # Try partial match
    matches = list(log_path.glob(f"session_*{session_id}*.jsonl"))
    if matches:
        matches.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        return str(matches[0])

    return None


def format_entry(entry: Dict[str, Any], verbose: bool = False) -> str:
    """Format a single log entry for display."""
    lines = []
    entry_type = entry.get("type", "unknown")
    timestamp = entry.get("timestamp", "")
    session_id = entry.get("session_id", "")
    turn = entry.get("turn_number", "?")

    # Header
    time_short = timestamp.split("T")[1][:8] if "T" in timestamp else timestamp
    lines.append(f"[{time_short}] Turn {turn} - {entry_type.upper()}")

    if entry_type == "request":
        req = entry.get("request", {})
        message = req.get("message", "")
        lines.append(f"  User: {message}")

    elif entry_type == "classification":
        cls = entry.get("classification", {})
        scope = cls.get("scope", "?")
        intent = cls.get("intent", "?")
        agent = cls.get("agent", "?")
        votes = cls.get("vote_distribution", {})
        needs_clarify = cls.get("needs_clarification", False)

        lines.append(f"  Scope: {scope} | Intent: {intent} | Agent: {agent}")
        if votes:
            vote_str = ", ".join(f"{k}:{v}" for k, v in votes.items())
            lines.append(f"  Votes: {vote_str}")
        if needs_clarify:
            lines.append(f"  [NEEDS CLARIFICATION]")

    elif entry_type == "response":
        resp = entry.get("response", {})
        content = resp.get("content", "")
        latency = resp.get("latency_ms", 0)
        step = resp.get("workflow_step", "?")

        # Truncate long responses
        if len(content) > 200 and not verbose:
            content = content[:200] + "..."

        lines.append(f"  Response ({latency:.0f}ms, step={step}):")
        for line in content.split("\n")[:5]:  # Show first 5 lines
            lines.append(f"    {line}")
        if content.count("\n") > 5 and not verbose:
            lines.append(f"    ... ({content.count(chr(10)) - 5} more lines)")

    elif entry_type == "error":
        err = entry.get("error", {})
        error_type = err.get("type", "Unknown")
        error_msg = err.get("message", "No message")
        lines.append(f"  ERROR [{error_type}]: {error_msg}")
        if verbose and err.get("stack_trace"):
            lines.append(f"  Stack trace:")
            for line in err["stack_trace"].split("\n")[:10]:
                lines.append(f"    {line}")

    return "\n".join(lines)


def display_session(
    entries: List[Dict[str, Any]],
    errors_only: bool = False,
    tail: Optional[int] = None,
    verbose: bool = False,
) -> None:
    """Display session entries."""
    # Filter
    if errors_only:
        entries = [e for e in entries if e.get("type") == "error"]

    # Tail
    if tail and len(entries) > tail:
        entries = entries[-tail:]
        print(f"(Showing last {tail} entries)\n")

    if not entries:
        print("No entries to display.")
        return

    # Group by turn
    current_turn = None
    for entry in entries:
        turn = entry.get("turn_number")
        if turn != current_turn:
            if current_turn is not None:
                print("-" * 50)
            current_turn = turn

        print(format_entry(entry, verbose=verbose))
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Read and display HEMA session replay logs"
    )
    parser.add_argument(
        "--session", "-s",
        type=str,
        help="Session ID to read",
    )
    parser.add_argument(
        "--latest", "-l",
        action="store_true",
        help="Read the most recent session",
    )
    parser.add_argument(
        "--errors", "-e",
        action="store_true",
        help="Show only error entries",
    )
    parser.add_argument(
        "--tail", "-t",
        type=int,
        help="Show only the last N entries",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available sessions",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show full entry details",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default=DEFAULT_LOG_DIR,
        help=f"Log directory (default: {DEFAULT_LOG_DIR})",
    )

    args = parser.parse_args()

    # List sessions
    if args.list:
        sessions = list_sessions(args.log_dir)
        if not sessions:
            print(f"No session logs found in {args.log_dir}")
            return 0

        print("\n" + "=" * 70)
        print("AVAILABLE SESSION LOGS")
        print("=" * 70)
        print(f"{'Session ID':<30} {'Date':<10} {'Entries':<8} {'Size':<10}")
        print("-" * 70)
        for s in sessions:
            print(f"{s['session_id']:<30} {s['date']:<10} {s['entries']:<8} {s['size_kb']:.1f} KB")
        print("=" * 70 + "\n")
        return 0

    # Find log file
    log_file = None
    if args.latest:
        log_file = find_latest_session(args.log_dir)
        if not log_file:
            print(f"No session logs found in {args.log_dir}")
            return 1
    elif args.session:
        log_file = find_session_file(args.session, args.log_dir)
        if not log_file:
            print(f"No session log found for: {args.session}")
            return 1
    else:
        # Default to latest
        log_file = find_latest_session(args.log_dir)
        if not log_file:
            print(f"No session logs found in {args.log_dir}")
            print("Usage: python scripts/read_session_log.py --latest")
            print("       python scripts/read_session_log.py --session SESSION_ID")
            print("       python scripts/read_session_log.py --list")
            return 1

    # Read and display
    print(f"\nReading: {log_file}\n")
    entries = read_log_file(log_file)

    if args.json:
        # Filter and output JSON
        if args.errors:
            entries = [e for e in entries if e.get("type") == "error"]
        if args.tail:
            entries = entries[-args.tail:]
        print(json.dumps(entries, indent=2))
    else:
        print("=" * 70)
        print("SESSION LOG")
        print("=" * 70 + "\n")
        display_session(
            entries,
            errors_only=args.errors,
            tail=args.tail,
            verbose=args.verbose,
        )
        print("=" * 70)
        print(f"Total entries: {len(entries)}")
        print("=" * 70 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
