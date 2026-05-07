#!/usr/bin/env python3
"""
Services Orchestrator.
Combines Jules, GitHub, and Gemini APIs for complex workflows.
"""

from typing import List, Dict, Any, Optional

from jules_client import get_jules_client, JulesClient
from github_client import GitHubClient
from gemini_client import GeminiClient
from common_config import setup_logging, JULES_DEFAULT_SOURCE

logger = setup_logging("orchestrator")


class ServicesOrchestrator:
    """Orchestrates interactions between Jules, GitHub, and Gemini."""

    def __init__(self):
        self.jules = get_jules_client()
        self.github = GitHubClient()
        self.gemini = GeminiClient()

    def review_pr(self, pr_number: int) -> bool:
        """
        Fetches PR diff, uses Gemini to analyze it, and posts a review comment.
        """
        logger.info(f"Starting review for PR #{pr_number}")

        pr_data = self.github.get_pr(pr_number)
        if not pr_data:
            logger.error(f"Could not fetch PR #{pr_number}")
            return False

        base_branch = pr_data.get("baseRefName")
        head_branch = pr_data.get("headRefName")

        # Ensure we have the latest branches
        self.github.fetch()

        # Get changed files
        changed_files = self.github.get_changed_files(f"origin/{base_branch}", f"origin/{head_branch}")
        if not changed_files:
            logger.warning(f"No changed files found for PR #{pr_number}")
            return False

        logger.info(f"Found {len(changed_files)} changed files.")

        review_comments = []
        for file in changed_files:
            # We skip non-code files for simplicity
            if not file.endswith(('.py', '.ts', '.tsx', '.js', '.jsx')):
                continue

            diff = self.github.get_diff(f"origin/{base_branch}", f"origin/{head_branch}", file)
            if not diff:
                continue

            logger.info(f"Analyzing {file}...")
            prompt = f"""
You are an expert code reviewer. Review the following diff for {file}.
Focus on:
1. Bugs and logic errors.
2. Security vulnerabilities.
3. Performance issues.
4. Readability and best practices.

Diff:
```diff
{diff}
```

If you find issues, provide concise, constructive feedback. If the code looks good, reply with "Looks good."
"""
            review = self.gemini.generate_content(prompt)
            if review and "Looks good." not in review:
                review_comments.append(f"### `{file}`\n{review}")

        if review_comments:
            body = "## Automated Code Review\n\n" + "\n\n".join(review_comments)
        else:
            body = "## Automated Code Review\n\n✅ Code looks good! No major issues found by the automated reviewer."

        # Add pre-publish checklist as per memory requirements
        body += "\n\n### Pre-Publish Checklist\n- [ ] Resolve merge conflicts\n- [ ] Verify build (`pnpm run build`)\n- [ ] Verify lint (`pnpm lint`)\n- [ ] Verify tests (`pnpm test:all`)"

        return self.github.post_pr_comment(pr_number, body)

    def dispatch_jules_for_issue(self, issue_number: int, branch_name: Optional[str] = None) -> Optional[str]:
        """
        Fetches an issue and creates a Jules session to resolve it.
        """
        logger.info(f"Dispatching Jules for Issue #{issue_number}")

        issue_data = self.github.get_issue(issue_number)
        if not issue_data:
            logger.error(f"Could not fetch Issue #{issue_number}")
            return None

        title = issue_data.get("title", "")
        body = issue_data.get("body", "")
        url = issue_data.get("url", "")

        prompt = (
            f"Task: {title}\n\n"
            f"Context from Issue #{issue_number}:\n"
            f"{body}\n\nReference: {url}"
        )

        target_branch = branch_name or f"feature/issue-{issue_number}"
        session_title = f"Fix: {title} (#{issue_number})"

        logger.info(f"Target Branch: {target_branch}")

        session_name = self.jules.create_session(
            prompt=prompt,
            source=JULES_DEFAULT_SOURCE,
            branch=target_branch,
            title=session_title
        )

        return session_name

    def fix_merge_conflict(self, target_branch: str) -> bool:
        """
        Attempts to resolve merge conflicts using Gemini.
        Note: This is a complex operation; this implements a basic stub/framework.
        """
        logger.info(f"Attempting to fix merge conflicts on {target_branch}...")

        current_branch = self.github.current_branch()
        if not current_branch:
             logger.error("Could not determine current branch.")
             return False

        # Attempt to merge
        success = self.github.merge(target_branch, abort_on_conflict=False)
        if success:
             logger.info("Merged successfully without conflicts.")
             return True

        logger.warning("Merge conflict detected. Aborting for safety in this stub.")
        self.github.run_cmd(["git", "merge", "--abort"], check=False)

        # A full implementation would:
        # 1. Identify conflicted files (git diff --name-only --diff-filter=U)
        # 2. For each file, extract the conflict markers (<<<<<<<, =======, >>>>>>>)
        # 3. Send the file content to Gemini and ask it to resolve the conflict.
        # 4. Write the resolved content back to the file.
        # 5. git add <file>
        # 6. git commit

        logger.info("Automated conflict resolution requires more complex file parsing. Use manual resolution for now.")
        return False

    def summarize_sessions(self) -> List[Dict[str, Any]]:
        """
        Combines Jules sessions with GitHub PR and Issue data.
        """
        logger.info("Summarizing active sessions...")

        # Need to import jules_ops to reuse its correlation logic
        # Or, we can re-implement the core mapping here to make orchestrator independent
        sessions = self.jules.list_sessions()

        # Basic summarization just returning the raw sessions for now
        # Integration with jules_ops correlation logic will be handled in the CLI/jules_ops layer
        return sessions
