#!/usr/bin/env python3
"""
Test script for the LangGraph workflow.
Usage: python test_langgraph.py --folder ./sample_docs --request "All emails about Project Blue Sky"
"""

import argparse
import os
from pathlib import Path
from typing import Any, cast

from dotenv import load_dotenv

from src.langgraph.state import DocumentState
from src.langgraph.workflow import process_document
from src.models.document import Document

# Load environment variables from .env file
load_dotenv()


def print_separator():
    print("=" * 80)


def print_document_result(filename: str, result: dict[str, Any]) -> None:
    """Pretty print the results for a document."""
    print(f"\nFile: {filename}")
    print(f"Classification: {result.get('classification', 'N/A')}")
    print(f"Confidence: {result.get('confidence', 0):.2f}")
    print(f"Justification: {result.get('justification', 'N/A')}")

    exemptions = result.get("exemptions", [])
    if exemptions:
        print(f"Exemptions found: {len(exemptions)}")
        for ex in exemptions[:3]:  # Show first 3 exemptions
            print(f"  - {ex['type']}: {ex['text']} (b{ex['exemption_code'][1:]})")
        if len(exemptions) > 3:
            print(f"  ... and {len(exemptions) - 3} more")
    else:
        print("No exemptions found")

    if result.get("error"):
        print(f"ERROR: {result['error']}")


def main():
    parser = argparse.ArgumentParser(description="Test FOIA document classification")
    parser.add_argument(
        "--folder",
        type=str,
        default="./sample_docs",
        help="Folder containing documents to process",
    )
    parser.add_argument(
        "--request",
        type=str,
        default="All emails about Project Blue Sky",
        help="FOIA request text",
    )

    args = parser.parse_args()

    # Check if folder exists
    folder_path = Path(args.folder)
    if not folder_path.exists():
        print(f"Error: Folder {args.folder} does not exist")
        return

    # Get all .txt files
    txt_files = list(folder_path.glob("*.txt"))
    if not txt_files:
        print(f"No .txt files found in {args.folder}")
        return

    print(f"FOIA Request: {args.request}")
    print(f"Processing {len(txt_files)} documents from {args.folder}")
    print_separator()

    # Process each document
    results = []
    for txt_file in txt_files:
        try:
            print(f"\nProcessing: {txt_file.name}")
            result = process_document(str(txt_file), args.request)
            results.append((txt_file.name, result))
            print_document_result(txt_file.name, cast(dict[str, Any], result))
        except Exception as e:
            print(f"Error processing {txt_file.name}: {e!s}")
        print_separator()

    # Summary
    print("\nSUMMARY")
    print("-------")
    responsive = sum(1 for _, r in results if r.get("classification") == "responsive")
    non_responsive = sum(
        1 for _, r in results if r.get("classification") == "non_responsive"
    )
    uncertain = sum(1 for _, r in results if r.get("classification") == "uncertain")

    print(f"Total documents: {len(results)}")
    print(f"Responsive: {responsive}")
    print(f"Non-responsive: {non_responsive}")
    print(f"Uncertain: {uncertain}")

    # List responsive documents
    if responsive > 0:
        print("\nResponsive documents:")
        for filename, result in results:
            if result.get("classification") == "responsive":
                print(f"  - {filename}")


if __name__ == "__main__":
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Please run: export OPENAI_API_KEY='your-key-here'")
        exit(1)

    main()
