# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# main.py
"""CLI entry point for the LangGraph-based energy analysis system."""
import os
import sys
from dotenv import load_dotenv

from agents.graph.builder import HEMAGraphRunner
from utils.logger import setup_logger

# Set up logging
logger = setup_logger()

# Load environment variables
load_dotenv()


def main():
    """Demo mode: run test queries through the energy analysis graph."""
    try:
        # Check for API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Warning: OPENAI_API_KEY not set. LLM features will use fallback responses.")

        # Create the graph runner
        logger.info("Initializing HEMAGraphRunner...")
        runner = HEMAGraphRunner(use_persistence=True)

        # Test queries demonstrating the workflow
        test_queries = [
            "Hello, what can you help me with?",
            "Analyze my energy consumption patterns",  # Should redirect - no data loaded
            "Load data from data/home_power/energy_data_sample.csv",
            "Now analyze my energy consumption patterns",
            "What are my peak usage hours?",
            "Give me recommendations to reduce energy costs",
        ]

        print("\n" + "=" * 60)
        print("ENERGY ANALYSIS SYSTEM - DEMO MODE (LangGraph)")
        print("=" * 60)

        session_id = "demo-session"

        for i, query in enumerate(test_queries, 1):
            print(f"\nQuery {i}: {query}")
            print("-" * 50)

            try:
                result = runner.invoke(query, session_id=session_id)
                response = result.get("final_response", "No response generated")
                query_type = result.get("query_type", "unknown")
                workflow_step = result.get("workflow_step", "unknown")

                print(f"Response:\n{response}")
                print(f"\n[Query Type: {query_type} | Workflow Step: {workflow_step}]")

                # Show data/analysis status
                data_loaded = result.get("data_loaded", False)
                analysis_done = result.get("analysis_completed", False)
                print(f"[Data Loaded: {data_loaded} | Analysis Done: {analysis_done}]")

            except Exception as e:
                logger.error(f"Error processing query: {str(e)}")
                print(f"Error: {str(e)}")

            print("\n" + "=" * 60)

    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        print(f"An error occurred: {str(e)}")
        raise


def interactive_mode():
    """Interactive mode for testing the energy analysis system."""
    try:
        # Check for API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Warning: OPENAI_API_KEY not set. LLM features will use fallback responses.")

        # Create the graph runner with persistence
        runner = HEMAGraphRunner(use_persistence=True)

        print("\nEnergy Analysis Assistant - Interactive Mode (LangGraph)")
        print("=" * 55)
        print("Commands:")
        print("  'status' - Show current session status")
        print("  'reset'  - Reset session state")
        print("  'quit'   - Exit the assistant")
        print("=" * 55)

        session_id = "interactive-session"

        while True:
            try:
                user_input = input("\nYou: ").strip()

                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("Goodbye! Thanks for using Energy Analysis Assistant.")
                    break

                if user_input.lower() == 'status':
                    state = runner.get_state(session_id)
                    if state:
                        print("\nCurrent Status:")
                        print(f"  Data Loaded: {state.get('data_loaded', False)}")
                        print(f"  Analysis Done: {state.get('analysis_completed', False)}")
                        print(f"  Last Query Type: {state.get('query_type', 'N/A')}")
                        print(f"  Workflow Step: {state.get('workflow_step', 'N/A')}")
                        if state.get('energy_data_path'):
                            print(f"  Data File: {state.get('energy_data_path')}")
                    else:
                        print("\nNo session state available.")
                    continue

                if user_input.lower() == 'reset':
                    runner.reset_session(session_id)
                    print("\nSession has been reset.")
                    continue

                if not user_input:
                    continue

                # Process the query
                result = runner.invoke(user_input, session_id=session_id)
                response = result.get("final_response", "No response generated")

                print(f"\nAssistant:\n{response}")

            except KeyboardInterrupt:
                print("\n\nGoodbye! Thanks for using Energy Analysis Assistant.")
                break
            except Exception as e:
                logger.error(f"Error processing input: {str(e)}")
                print(f"\nError: {str(e)}")

    except Exception as e:
        logger.error(f"Error in interactive mode: {str(e)}")
        print(f"Failed to start interactive mode: {str(e)}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_mode()
    else:
        main()
