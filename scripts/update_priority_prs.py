#!/usr/bin/env python3
"""
Update high-priority PRs with changes from the leader branch.
Replaces update-priority-prs.sh
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import common modules
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from typing import List
from common_config import HRM_REPO_DIR, setup_logging, setup_python_path
from github_client import GitHubClient

setup_python_path()
logger = setup_logging("update_priority_prs")

# High-priority branches that should be updated first
HIGH_PRIORITY_BRANCHES = [
    "feat/websocket-command-relay",
    "feature/websocket-reconnect-2-1",
    "feat/api-validation-zod",
    "feat/mobile-ux-improvements-1",
    "feat/rate-limiting",
    "feat/secure-debug-endpoints",
    "feat/health-checks",
    "refactor/spotify-service-singleton",
    "quick-win/dry-fail-fast-fixes",
    "feat/consolidate-volume-hook",
]


def update_priority_prs():
    client = GitHubClient(repo_path=HRM_REPO_DIR)

    logger.info("🎯 Updating HIGH-PRIORITY PRs with test fixes...")

    # Ensure we're on leader
    logger.info("Switching to leader branch...")
    if not client.checkout("leader"):
        logger.error("Failed to checkout leader branch. Aborting.")
        return

    logger.info("Pulling latest leader...")
    if not client.pull("origin", "leader"):
        logger.warning("Could not pull latest leader")

    logger.info(f"Updating {len(HIGH_PRIORITY_BRANCHES)} high-priority branches...")

    # Get status of branches (check if they have open PRs)
    # Optimization: Get all open PRs first to check against
    open_prs = client.list_prs(state="open", limit=200)
    open_branches = {pr["headRefName"] for pr in open_prs}

    for branch in HIGH_PRIORITY_BRANCHES:
        logger.info(f"🔄 Processing {branch}...")

        if branch not in open_branches:
             logger.info(f"ℹ️  {branch} is not associated with an open PR, skipping")
             continue

        # Check if branch exists locally or remotely
        if not client.branch_exists(branch) and not client.branch_exists(branch, remote=True):
             logger.warning(f"⚠️ Branch {branch} not found locally or on remote, skipping")
             continue

        logger.info(f"Checking out {branch}...")
        if not client.checkout(branch):
             # Try creating tracking branch
             if not client.checkout(branch, create=True, source=f"origin/{branch}"):
                 logger.error(f"Could not checkout {branch}")
                 continue

        logger.info(f"Pulling {branch}...")
        client.pull("origin", branch)

        logger.info(f"Merging leader into {branch}...")
        if client.merge("leader"):
            logger.info(f"✅ Merge successful, pushing {branch}...")
            if client.push("origin", branch):
                 logger.info(f"✅ Updated {branch}")
            else:
                 logger.error(f"❌ Failed to push {branch}")
        else:
            logger.warning(f"⚠️  Conflicts in {branch} - skipping")
            # Merge is already aborted by client.merge if it fails

    # Return to leader
    client.checkout("leader")
    logger.info("🎉 High-priority PRs update process completed!")


if __name__ == "__main__":
    update_priority_prs()
