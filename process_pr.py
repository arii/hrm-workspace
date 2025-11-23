#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
import sys
import time

# Attempt to import JulesClient from existing ops script
try:
    from jules_ops import JulesClient

    JULES_AVAILABLE = True
except ImportError:
    JULES_AVAILABLE = False

# Configuration
REPO_DIR = "/home/ari/workspace/leader"
WORKTREES_BASE = "/home/ari/workspace/worktrees"


def run(cmd, cwd=None, check=True, capture_output=False, env=None):
    """
    Run a subprocess command.
    If capture_output is True, it streams output to the console AND captures it
    to return to the caller (useful for logs).
    """
    cmd_str = " ".join(cmd)
    print(f"[CMD] {cmd_str}")

    # Use the passed env or default to current environment
    run_env = env if env is not None else os.environ.copy()

    if capture_output:
        # Use Popen to stream stdout while capturing it
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr into stdout
            text=True,
            bufsize=1,  # Line buffered
            env=run_env,
        )

        captured_lines = []

        # Read stream line by line
        with process.stdout:
            for line in iter(process.stdout.readline, ""):
                print(line, end="")  # Stream to console immediately
                captured_lines.append(line)

        process.wait()
        returncode = process.returncode
        stdout_content = "".join(captured_lines)

        if check and returncode != 0:
            # Raise error with captured output attached
            raise subprocess.CalledProcessError(
                returncode, cmd, output=stdout_content
            )

        # Return object compatible with subprocess.CompletedProcess
        return type(
            "CompletedProcess",
            (object,),
            {
                "stdout": stdout_content,
                "stderr": "",  # Merged into stdout
                "returncode": returncode,
            },
        )

    else:
        # Standard run: Output goes directly to console, no capturing
        try:
            result = subprocess.run(
                cmd, cwd=cwd, check=check, text=True, env=run_env
            )
            return result
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Command failed: {cmd_str}")
            raise e


def get_pr_details(pr_number):
    """Fetch PR branch name and status using gh CLI."""
    try:
        cmd = [
            "gh",
            "pr",
            "view",
            str(pr_number),
            "--json",
            "headRefName,url,isDraft,state,title",
            "--repo",
            "arii/hrm",
        ]
        res = run(cmd, check=True, capture_output=True)
        return json.loads(res.stdout)
    except Exception:
        print(
            f"[ERROR] Failed to fetch PR #{pr_number}. " "Is gh CLI installed?"
        )
        sys.exit(1)


def setup_worktree(branch_name):
    """Creates a worktree for the branch."""
    worktree_path = os.path.join(WORKTREES_BASE, branch_name)

    # Prune existing worktrees first to be safe
    run(["git", "worktree", "prune"], cwd=REPO_DIR, check=False)

    if os.path.exists(worktree_path):
        print(f"[WARN] Worktree path {worktree_path} exists. " "Removing it.")
        shutil.rmtree(worktree_path)
        run(["git", "worktree", "prune"], cwd=REPO_DIR, check=False)

    print(f"[INFO] Creating worktree for branch: {branch_name}")
    # Fetch latest to ensure we know about the branch
    run(["git", "fetch", "origin"], cwd=REPO_DIR)

    try:
        # Try checking out existing branch
        run(
            ["git", "worktree", "add", worktree_path, branch_name],
            cwd=REPO_DIR,
        )
    except subprocess.CalledProcessError:
        # If local branch doesn't match remote or doesn't exist, try tracking
        try:
            run(
                [
                    "git",
                    "worktree",
                    "add",
                    "--track",
                    "-b",
                    branch_name,
                    worktree_path,
                    f"origin/{branch_name}",
                ],
                cwd=REPO_DIR,
            )
        except subprocess.CalledProcessError:
            print("[ERROR] Failed to create worktree. Does branch exist?")
            sys.exit(1)

    return worktree_path


def rebase_and_push(worktree_path, branch_name):
    """
    Attempts to rebase onto origin/leader.
    If rebase fails, it aborts the rebase and performs a MERGE instead.
    It deliberately commits the conflict markers so they can be pushed
    and analyzed by the agent.
    """
    print("[INFO] Fetching origin/leader...")
    run(["git", "fetch", "origin", "leader"], cwd=worktree_path)

    print(f"[INFO] Attempting rebase of {branch_name}...")
    try:
        run(
            ["git", "rebase", "origin/leader"],
            cwd=worktree_path,
            capture_output=True,
        )
        print("[OK] Rebase successful.")
    except subprocess.CalledProcessError:
        print("[WARN] Rebase failed due to conflicts.")
        print("[INFO] Aborting rebase to fallback to Merge strategy...")
        # Abort the rebase to get back to clean state
        run(["git", "rebase", "--abort"], cwd=worktree_path, check=False)

        print("[INFO] Falling back to Merge to capture conflicts...")
        try:
            # Attempt merge
            run(
                ["git", "merge", "origin/leader"],
                cwd=worktree_path,
                capture_output=True,
            )
        except subprocess.CalledProcessError:
            print("[WARN] Merge conflicts detected. Committing markers...")
            # 1. Stage all files (including those with <<<< markers)
            run(["git", "add", "."], cwd=worktree_path, check=False)

            # 2. Commit the conflicts.
            # We use --no-edit to accept default merge message or -m
            run(
                [
                    "git",
                    "commit",
                    "-m",
                    "Merge origin/leader (with unresolved conflicts)",
                ],
                cwd=worktree_path,
                check=False,
            )

    print("[INFO] Force pushing changes (including potential conflicts)...")
    run(
        ["git", "push", "origin", branch_name, "--force"],
        cwd=worktree_path,
        check=False,
    )
    return True


def run_checks(worktree_path):
    """Runs the suite of checks and returns a list of results."""
    # We apply robust flags here to prevent hangs and ensure
    # correct exit codes.
    # --ci: Tells Jest to run in non-interactive mode.
    # --reporter=list: Tells Playwright to output text only.
    checks = [
        {"name": "Lint", "cmd": ["npm", "run", "lint"]},
        {"name": "Build", "cmd": ["npm", "run", "build"]},
        {"name": "Unit Tests", "cmd": ["npm", "run", "test", "--", "--ci"]},
        {
            "name": "Visual Tests",
            "cmd": ["npm", "run", "test:visual", "--", "--reporter=list"],
        },
    ]

    # Setup CI environment as an extra layer of safety
    ci_env = os.environ.copy()
    ci_env["CI"] = "true"

    results = []
    failure_details = None

    for check in checks:
        print(f"\n[RUN] Running: {check['name']}")
        start_time = time.time()
        try:
            # Command output is streamed to console via run()
            run(
                check["cmd"],
                cwd=worktree_path,
                check=True,
                capture_output=True,
                env=ci_env,
            )

            duration = round(time.time() - start_time, 2)
            results.append(
                {
                    "name": check["name"],
                    "status": "[PASS]",
                    "duration": f"{duration}s",
                }
            )
        except subprocess.CalledProcessError as e:
            duration = round(time.time() - start_time, 2)
            results.append(
                {
                    "name": check["name"],
                    "status": "[FAIL]",
                    "duration": f"{duration}s",
                }
            )

            # Capture failure info
            stdout = e.output if hasattr(e, "output") else str(e)
            failure_details = {
                "step": check["name"],
                "cmd": " ".join(check["cmd"]),
                "log": stdout,
            }
            print(f"[ERROR] {check['name']} Failed!")
            break  # Stop at first failure

    return results, failure_details


def post_pr_comment(pr_number, results, failure_details, session_url=None):
    """Posts a comment to the PR with the results."""

    body = "### Automated Verification Results\n\n"

    # Table of results
    body += "| Check | Status | Duration |\n"
    body += "|---|---|---|\n"
    for r in results:
        body += f"| {r['name']} | {r['status']} | {r['duration']} |\n"

    if failure_details:
        body += f"\n\n**Verification Failed at: {failure_details['step']}**\n"
        if session_url:
            body += f"Jules session created: {session_url}\n"

        body += "\n<details><summary>Failure Logs</summary>\n\n```\n"
        # Truncate log if too long for comment
        body += failure_details["log"][-2000:]
        body += "\n```\n</details>"
    else:
        body += "\n\nAll checks passed! Ready for review."

    print("[INFO] Posting comment to PR...")
    run(
        [
            "gh",
            "pr",
            "comment",
            str(pr_number),
            "--body",
            body,
            "--repo",
            "arii/hrm",
        ],
        check=False,
    )


def update_pr_status(pr_number):
    """Updates PR to ready for review if it is a draft."""
    print("[INFO] Marking PR as ready for review...")
    run(
        ["gh", "pr", "ready", str(pr_number), "--repo", "arii/hrm"],
        check=False,
    )


def trigger_jules_fix(branch_name, pr_number, pr_title, failure_details):
    """Creates a Jules session to fix the issue."""
    if not JULES_AVAILABLE:
        print("[WARN] Jules integration not available.")
        return None

    print("\n[JULES] Creating Jules Session for Fix...")
    client = JulesClient()

    # Construct prompt
    prompt = (
        f'The verification failed for PR #{pr_number} ("{pr_title}").\n\n'
        f"**Failed Step:** {failure_details['step']}\n"
        f"**Command:** `{failure_details['cmd']}`\n\n"
        f"**Error Log:**\n```\n{failure_details['log']}\n```\n\n"
        f"Please analyze, fix branch `{branch_name}`, and verify with:\n"
        "1. npm run lint\n2. npm run build\n"
        "3. npm run test\n4. npm run test:visual"
    )

    session_title = f"Fix {failure_details['step']} Failure - PR #{pr_number}"

    try:
        session_name = client.create_session(
            prompt=prompt,
            source="sources/github/arii/hrm",  # Default source
            branch=branch_name,
            title=session_title,
        )
        print(f"[OK] Created Session: {session_name}")
        return session_name
    except Exception as e:
        print(f"[ERROR] Failed to create Jules session: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Automated PR Verification & Fix Loop"
    )
    parser.add_argument("pr_number", help="GitHub PR number (e.g. 160)")
    args = parser.parse_args()

    # 1. Get PR Details
    print(f"[INFO] Fetching details for PR #{args.pr_number}...")
    pr_info = get_pr_details(args.pr_number)
    branch_name = pr_info["headRefName"]
    print(f"   Branch: {branch_name}")
    print(f"   Draft:  {pr_info['isDraft']}")

    # 2. Setup Worktree
    worktree_path = setup_worktree(branch_name)

    # 3. Setup Dependencies
    setup_script = os.path.join(worktree_path, "scripts", "setup.sh")
    if os.path.exists(setup_script):
        print("[INFO] Running setup.sh...")
        run([setup_script], cwd=worktree_path)
    else:
        print("[WARN] scripts/setup.sh not found, running npm install.")
        run(["npm", "install"], cwd=worktree_path)

    # 4. Rebase & Force Push
    rebase_and_push(worktree_path, branch_name)

    # 5. Run Checks
    results, failure = run_checks(worktree_path)

    # 6. Handle Outcome
    session_link = None
    if failure:
        # Create Jules Session
        session_id = trigger_jules_fix(
            branch_name, args.pr_number, pr_info["title"], failure
        )
        if session_id:
            session_link = f"Session ID: {session_id}"
    else:
        # Success Action
        if pr_info["isDraft"]:
            update_pr_status(args.pr_number)

    # 7. Post Results
    post_pr_comment(args.pr_number, results, failure, session_link)

    print("\n[DONE] Process Complete.")


if __name__ == "__main__":
    main()
