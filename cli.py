#!/usr/bin/env python3
"""
Unified CLI for the HRM Workspace.
Provides access to Jules, GitHub, and orchestrator workflows.
"""

import argparse
import sys
import logging

from orchestrator import ServicesOrchestrator
from jules_client import get_jules_client
from common_config import setup_logging

logger = setup_logging("cli", level=logging.INFO)

def main():
    parser = argparse.ArgumentParser(description="HRM Workspace Unified CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- Orchestrator Workflows ---

    p_review = subparsers.add_parser("review", help="Review a Pull Request using Gemini")
    p_review.add_argument("pr_number", type=int, help="The PR number to review")

    p_dispatch = subparsers.add_parser("dispatch", help="Dispatch a Jules session for a GitHub Issue")
    p_dispatch.add_argument("issue_number", type=int, help="The Issue number to solve")
    p_dispatch.add_argument("--branch", help="Optional target branch name")
    p_dispatch.add_argument("--no-watch", action="store_true", help="Don't watch the session after creation")

    p_fix_conflicts = subparsers.add_parser("fix-conflicts", help="Attempt to fix merge conflicts (Stub)")
    p_fix_conflicts.add_argument("branch", help="The branch to merge from")

    p_status = subparsers.add_parser("status", help="Show unified session/issue dashboard")

    # --- Raw Jules Workflows (subset for utility) ---

    p_jules_list = subparsers.add_parser("jules-list", help="List active Jules sessions")

    p_jules_watch = subparsers.add_parser("jules-watch", help="Watch a Jules session")
    p_jules_watch.add_argument("session_name", help="Session ID/Name")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    orchestrator = ServicesOrchestrator()

    if args.command == "review":
        success = orchestrator.review_pr(args.pr_number)
        if success:
            logger.info(f"✅ Successfully posted review for PR #{args.pr_number}")
        else:
            logger.error(f"❌ Failed to review PR #{args.pr_number}")
            sys.exit(1)

    elif args.command == "dispatch":
        session_name = orchestrator.dispatch_jules_for_issue(args.issue_number, args.branch)
        if session_name:
            logger.info(f"✅ Created Jules session: {session_name}")
            if not args.no_watch:
                orchestrator.jules.monitor_session(session_name)
        else:
            logger.error("❌ Failed to create Jules session.")
            sys.exit(1)

    elif args.command == "fix-conflicts":
        orchestrator.fix_merge_conflict(args.branch)

    elif args.command == "status":
        # For full status we delegate to the existing robust jules_ops logic,
        # or implement a simpler view here.
        # Here we just show sessions.
        sessions = orchestrator.summarize_sessions()
        logger.info(f"Found {len(sessions)} active sessions.")
        for s in sessions[:10]:
            name = s.get("name", "").split("/")[-1]
            state = s.get("state", "UNKNOWN")
            title = s.get("title", "")
            print(f"- {name} [{state}]: {title[:50]}")

    elif args.command == "jules-list":
        sessions = orchestrator.jules.list_sessions()
        for s in sessions:
            name = s.get("name", "").split("/")[-1]
            print(f"{name} - {s.get('state')}")

    elif args.command == "jules-watch":
        orchestrator.jules.monitor_session(args.session_name)

if __name__ == "__main__":
    main()
