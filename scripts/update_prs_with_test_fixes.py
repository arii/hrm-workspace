#!/usr/bin/env python3
"""
Update all open PRs with changes from the leader branch.
Replaces update-prs-with-test-fixes.sh
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import common modules
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from common_config import HRM_REPO_DIR, setup_logging, setup_python_path
from github_client import GitHubClient

setup_python_path()
logger = setup_logging("update_test_fixes")

# Branches to exclude
EXCLUDE_BRANCHES = {
    "fix/test-json-errors",
    "dependabot" # Will match if branch name contains this
}

def update_all_open_prs():
    client = GitHubClient(repo_path=HRM_REPO_DIR)

    logger.info("🚀 Updating all open PRs with test timeout fixes...")

    # Ensure we're on leader
    logger.info("Switching to leader branch...")
    if not client.checkout("leader"):
        logger.error("Failed to checkout leader branch. Aborting.")
        return

    logger.info("Pulling latest leader...")
    if not client.pull("origin", "leader"):
        logger.warning("Could not pull latest leader")

    logger.info("Getting list of open PR branches...")
    open_prs = client.list_prs(state="open", limit=200)

    # Filter branches
    branches_to_update = []
    for pr in open_prs:
        branch = pr["headRefName"]
        should_exclude = False
        for exclude in EXCLUDE_BRANCHES:
            if exclude in branch:
                should_exclude = True
                break

        if not should_exclude:
            branches_to_update.append(branch)

    if not branches_to_update:
        logger.warning("No open PR branches found to update.")
        return

    total = len(branches_to_update)
    logger.info(f"Found {total} open PR branches to update")

    updated = 0
    failed = 0

    for i, branch in enumerate(branches_to_update, 1):
        logger.info(f"[{i}/{total}] Updating branch: {branch}")

        # Check if remote branch exists
        if not client.branch_exists(branch, remote=True):
             logger.warning(f"  Remote branch {branch} does not exist, skipping...")
             failed += 1
             continue

        # Checkout
        if client.branch_exists(branch):
            logger.info(f"  Switching to existing branch {branch}")
            if not client.checkout(branch):
                logger.error(f"  Failed to checkout {branch}")
                failed += 1
                continue
            client.pull("origin", branch)
        else:
             logger.info(f"  Creating local branch {branch} from remote")
             if not client.checkout(branch, create=True, source=f"origin/{branch}"):
                 logger.error(f"  Failed to create local branch {branch}")
                 failed += 1
                 continue

        # Merge leader
        logger.info(f"  Merging leader into {branch}...")
        if client.merge("leader"):
            logger.info(f"  Merge successful, pushing to remote...")
            if client.push("origin", branch):
                logger.info(f"  ✅ Updated {branch} successfully")
                updated += 1
            else:
                logger.error(f"  ❌ Failed to push {branch}")
                failed += 1
        else:
            logger.warning(f"  ⚠️  Merge conflicts in {branch} - requires manual resolution")
            logger.warning(f"     Skipping {branch} - will need manual update")
            failed += 1

    # Return to leader
    client.checkout("leader")

    logger.info("==================== SUMMARY ====================")
    logger.info(f"Total branches processed: {total}")
    logger.info(f"Successfully updated: {updated}")
    if failed > 0:
        logger.error(f"Failed/Skipped: {failed}")
        logger.warning("Branches that need manual attention: Run 'gh pr list --state open' to see which PRs might have conflicts")

    logger.info("🎉 PR update process completed!")

if __name__ == "__main__":
    update_all_open_prs()
