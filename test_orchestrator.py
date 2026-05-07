#!/usr/bin/env python3
"""
Test script for the orchestrator.
"""

from orchestrator import ServicesOrchestrator
import logging

logging.basicConfig(level=logging.INFO)

def main():
    print("Testing ServicesOrchestrator Initialization...")
    orchestrator = ServicesOrchestrator()
    print("✅ Initialized successfully.")

    print("\nTesting jules_list...")
    sessions = orchestrator.jules.list_sessions()
    print(f"✅ Found {len(sessions)} sessions.")

if __name__ == "__main__":
    main()
