#!/usr/bin/env python3
import argparse
import csv
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime

import requests

# Optional Pandas Import
try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

# --- Configuration ---
API_BASE_URL = "https://jules.googleapis.com/v1alpha"
DEFAULT_SOURCE = "sources/github/arii/hrm"
GIT_REPO_PATH = "/home/ari/workspace/leader"
LOG_FORMAT = "%(asctime)s - %(message)s"
DATE_FORMAT = "%H:%M:%S"

# Configure Logging
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, datefmt=DATE_FORMAT)
logger = logging.getLogger("jules_ops")


# -------------------------------------------------------------------------
# 1. JULES CLIENT
# -------------------------------------------------------------------------
class JulesClient:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("JULES_API_KEY")

        if not self.api_key:
            logger.error(
                "No API key found. Set JULES_API_KEY "
                "env var or pass --api-key."
            )
            sys.exit(1)

        self.headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
        }

    def _request(self, method, endpoint, data=None):
        url = f"{API_BASE_URL}/{endpoint}"
        try:
            response = requests.request(
                method, url, headers=self.headers, json=data
            )
            response.raise_for_status()
            if response.status_code == 204 or not response.content:
                return {}
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(
                f"HTTP Error: {e.response.status_code} - {e.response.text}"
            )
            return None
        except Exception as exc:
            logger.error(f"Request Failed: {exc}")
            return None

    def list_sources(self, filter_str=None):
        endpoint = "sources"
        if filter_str:
            endpoint += f"?filter={filter_str}"
        response = self._request("GET", endpoint)
        return response.get("sources", []) if response else []

    def list_sessions(self):
        all_sessions = []
        next_page_token = None
        while True:
            endpoint = "sessions"
            if next_page_token:
                endpoint += f"?pageToken={next_page_token}"

            response = self._request("GET", endpoint)
            if response:
                all_sessions.extend(response.get("sessions", []))
                next_page_token = response.get("nextPageToken")
                if not next_page_token:
                    break  # No more pages
            else:
                break  # Error or empty response, stop.
        return all_sessions

    def create_session(
        self, prompt, source=DEFAULT_SOURCE, branch=None, title=None
    ):
        if source.startswith("sources/"):
            source_id = source
        else:
            sources = self.list_sources(f'name="{source}"')
            if not sources:
                logger.error(
                    f"Source '{source}' not found. "
                    "Use 'list-sources' to see available options."
                )
                return None
            source_id = sources[0]["id"]

        # UPDATED: Payload structure matches Jules API v1alpha Session resource
        payload = {
            "prompt": prompt,
            "sourceContext": {
                "source": source_id,
                "githubRepoContext": {
                    # 'startingBranch' is required by the API.
                    # Default to 'main' if no specific branch is provided.
                    "startingBranch": branch
                    or "main"
                },
            },
        }

        if title:
            payload["title"] = title

        logger.info(f"🚀 Launching session using source: {source_id}")
        logger.info(f"📝 Title: {title or 'Untitled'}")

        response = self._request("POST", "sessions", payload)

        if response and "name" in response:
            return response["name"]
        return None

    def create_session_deprecated(
        self, prompt, source=DEFAULT_SOURCE, branch=None, title=None
    ):
        if source.startswith("sources/"):
            source_id = source
        else:
            sources = self.list_sources(f'name="{source}"')
            if not sources:
                logger.error(
                    f"Source '{source}' not found. "
                    "Use 'list-sources' to see available options."
                )
                return None
            source_id = sources[0]["id"]

        payload = {"source": source_id, "prompt": prompt}

        config_overrides = {}
        if branch:
            config_overrides["branch"] = branch
        if config_overrides:
            payload["config"] = config_overrides

        if title:
            payload["title"] = title

        logger.info(f"🚀 Launching session using source: {source_id}")
        logger.info(f"📝 Title: {title or 'Untitled'}")

        response = self._request("POST", "sessions", payload)

        if response and "name" in response:
            return response["name"]
        return None

    def get_session(self, session_name):
        return self._request("GET", f"sessions/{session_name}")

    def send_message_deprecated(self, session_name, text):
        payload = {"text": text}
        response = self._request(
            "POST", f"sessions/{session_name}:message", payload
        )
        return response is not None

    def send_message(self, session_name, text):
        # UPDATED: API expects 'prompt' instead of 'text'
        payload = {"prompt": text}
        # UPDATED: Endpoint is ':sendMessage' instead of ':message'
        response = self._request(
            "POST", f"sessions/{session_name}:sendMessage", payload
        )
        return response is not None

    def delete_session(self, session_name):
        logger.info(f"🗑️ Deleting session {session_name}...")
        self._request("DELETE", f"sessions/{session_name}")

    def monitor_session(self, session_name, timeout_minutes=30):
        logger.info(f"👀 Watching session: {session_name}")
        end_time = time.time() + (timeout_minutes * 60)

        while time.time() < end_time:
            status = self.get_session(session_name)
            if not status:
                time.sleep(30)
                continue

            state = status.get("state", "UNKNOWN")

            if state == "SUCCEEDED":
                logger.info("✅ Session SUCCEEDED.")
                self._print_pr_link(status)
                return True

            elif state in ["FAILED", "CANCELLED", "TERMINATED"]:
                logger.error(f"❌ Session ended with state: {state}")
                if "error" in status:
                    logger.error(f"Error details: {status['error']}")
                return False

            else:
                logger.info(f"⏳ Status: {state}... waiting 30s")
                time.sleep(30)

        logger.error("⏱️ Monitoring timed out.")
        return False

    def _print_pr_link(self, status_json):
        """Extracts and prints the PR link if available."""
        outputs = status_json.get("outputs", [])
        found_pr = False
        for output in outputs:
            if "pullRequest" in output:
                pr_url = output["pullRequest"].get("url")
                print(f"\n{'-'*40}")
                print(f"🚀 PULL REQUEST CREATED: {pr_url}")
                print(f"{'-'*40}\n")
                found_pr = True

        if not found_pr:
            logger.warning(
                "Session succeeded, but no PR URL found in outputs."
            )


# -------------------------------------------------------------------------
# 2. GITHUB UTILITIES
# -------------------------------------------------------------------------


def check_gh_dependencies():
    if not shutil.which("gh"):
        logger.error("❌ GitHub CLI ('gh') is not installed.")
        sys.exit(1)


def run_gh_cmd(cmd_list):
    try:
        result = subprocess.run(
            cmd_list,
            capture_output=True,
            text=True,
            check=True,
            cwd=GIT_REPO_PATH,
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError:
        logger.error(f"❌ GH Command failed: {' '.join(cmd_list)}")
        return None


def fetch_issue_context(issue_number):
    logger.info(f"📥 Fetching context from Issue #{issue_number}...")
    check_gh_dependencies()
    data = run_gh_cmd(
        ["gh", "issue", "view", str(issue_number), "--json", "title,body,url"]
    )
    if data:
        return {
            "title": data["title"],
            "prompt": (
                f"Task: {data['title']}\n\n"
                f"Context from Issue #{issue_number}:\n"
                f"{data['body']}\n\nReference: {data['url']}"
            ),
        }
    return None


def format_time(iso_str):
    """Converts ISO string to granular relative time."""
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        delta = datetime.now(dt.tzinfo) - dt
        if delta.days > 365:
            return f"{delta.days // 365}y ago"
        if delta.days > 0:
            return f"{delta.days}d ago"
        hours = delta.seconds // 3600
        if hours > 0:
            return f"{hours}h ago"
        minutes = (delta.seconds % 3600) // 60
        return f"{minutes}m ago"
    except ValueError:
        return iso_str


def get_state_icon(state, created_at_iso):
    """Returns an icon based on state and staleness."""
    if state == "SUCCEEDED":
        return "✅"
    if state in ["FAILED", "CANCELLED", "TERMINATED"]:
        return "🔴"

    # Check for stale running sessions (> 24 hours)
    if state == "RUNNING":
        try:
            dt = datetime.fromisoformat(created_at_iso.replace("Z", "+00:00"))
            delta = datetime.now(dt.tzinfo) - dt
            if delta.days >= 1:
                return "🐢"  # Stale/Slow
        except Exception:
            pass
        return "🏃"

    return "⚪"


# -------------------------------------------------------------------------
# 3. DATA PROCESSING & CORRELATION
# -------------------------------------------------------------------------


def extract_issue_id(text):
    """Heuristic to find Issue ID in branches/titles."""
    if not text:
        return None
    match = re.search(r"#(\d+)", text)
    if match:
        return match.group(1)
    match = re.search(r"issue[-/](\d+)", text, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def normalize_sessions(sessions):
    data = []
    for s in sessions:
        outputs = s.get("outputs", [])
        pr_url = None
        for o in outputs:
            if "pullRequest" in o:
                pr_url = o["pullRequest"].get("url")
                break

        sid = (
            s.get("name", "").split("/")[-1]
            if "/" in s.get("name", "")
            else s.get("name", "N/A")
        )

        # Extract branch directly from session sourceContext
        session_branch = (
            s.get("sourceContext", {})
            .get("githubRepoContext", {})
            .get("startingBranch")
        )

        data.append(
            {
                "id": sid,
                "full_name": s.get("name"),
                "state": s.get("state"),
                "created_at": s.get("createTime"),
                "title": s.get("title", "").split("\n")[0],
                "pr_url": pr_url,
                "branch": session_branch,  # Add the branch here
            }
        )
    return data


def normalize_issues(issues):
    data = []
    for i in issues:
        assignees = [a["login"] for a in i.get("assignees", [])]
        data.append(
            {
                "id": str(i.get("number")),
                "title": i.get("title"),
                "assignees": ", ".join(assignees),
                "updated_at": i.get("updatedAt"),
                "url": i.get("url"),
            }
        )
    return data


def normalize_prs(prs):
    data = []
    for p in prs:
        data.append(
            {
                "id": str(p.get("number")),
                "title": p.get("title"),
                "branch": p.get("headRefName"),
                "review": p.get("reviewDecision"),
                "updated_at": p.get("updatedAt"),
                "url": p.get("url"),
            }
        )
    return data


def correlate_data(sessions, issues, prs):
    """Groups data into Workstreams."""
    normalized_sessions = normalize_sessions(sessions)
    normalized_issues = normalize_issues(issues)
    normalized_prs = normalize_prs(prs)

    issue_map = {i["id"]: i for i in normalized_issues}
    pr_map_by_url = {p["url"]: p for p in normalized_prs}

    workstreams = []

    # 1. Start with Sessions
    for s in normalized_sessions:
        row = {
            "session_id": s["id"],
            "session_state": s["state"],
            "session_title": s["title"],
            "session_created": s["created_at"],
            "last_activity": s["created_at"],  # default
            "pr_id": None,
            "pr_status": None,
            "branch": s["branch"],  # Initialize branch from session data
            "issue_id": None,
            "issue_title": None,
        }

        # Link PR
        if s["pr_url"] and s["pr_url"] in pr_map_by_url:
            pr = pr_map_by_url[s["pr_url"]]
            row["pr_id"] = f"#{pr['id']}"
            row["pr_status"] = pr["review"]
            row["branch"] = pr["branch"]
            row["last_activity"] = pr[
                "updated_at"
            ]  # PR update is newer than session create

            # Link Issue via PR
            found_issue = extract_issue_id(pr["branch"]) or extract_issue_id(
                pr["title"]
            )
            if found_issue:
                row["issue_id"] = f"#{found_issue}"
                if found_issue in issue_map:
                    row["issue_title"] = issue_map[found_issue]["title"]

        # Link Issue via Session Title
        if not row["issue_id"]:
            found_issue = extract_issue_id(s["title"])
            if found_issue:
                row["issue_id"] = f"#{found_issue}"
                if found_issue in issue_map:
                    row["issue_title"] = issue_map[found_issue]["title"]

        workstreams.append(row)

    # 2. Catch Orphan PRs
    linked_pr_urls = {s["pr_url"] for s in normalized_sessions if s["pr_url"]}
    for p in normalized_prs:
        if p["url"] not in linked_pr_urls:
            iid = extract_issue_id(p["branch"]) or extract_issue_id(p["title"])
            workstreams.append(
                {
                    "session_id": "-",
                    "session_state": "-",
                    "session_title": "-",
                    "session_created": "-",
                    "last_activity": p["updated_at"],
                    "pr_id": f"#{p['id']}",
                    "pr_status": p["review"],
                    "branch": p["branch"],
                    "issue_id": f"#{iid}" if iid else None,
                    "issue_title": (
                        issue_map[iid]["title"]
                        if (iid and iid in issue_map)
                        else None
                    ),
                }
            )

    # Sort by last_activity
    workstreams.sort(key=lambda x: x.get("last_activity") or "", reverse=True)
    return workstreams


# -------------------------------------------------------------------------
# 4. DASHBOARD & EXPORT
# -------------------------------------------------------------------------


def print_pandas_dashboard(sessions, issues, prs):
    workstreams = correlate_data(sessions, issues, prs)
    df_ws = pd.DataFrame(workstreams)

    print("\n" + "=" * 100)
    print(" 🔗 ACTIVE WORKSTREAMS (Grouped)")
    print("=" * 100)
    if not df_ws.empty:
        view = df_ws[
            [
                "issue_id",
                "issue_title",
                "session_id",
                "session_state",
                "pr_id",
                "pr_status",
                "last_activity",
            ]
        ].copy()
        view["last_activity"] = view["last_activity"].apply(format_time)

        # Rename for display
        view.rename(
            columns={
                "issue_id": "Issue",
                "issue_title": "Task",
                "session_id": "Jules ID",
                "session_state": "State",
                "pr_id": "PR",
                "pr_status": "Review",
                "last_activity": "Updated",
            },
            inplace=True,
        )

        view["Task"] = view["Task"].apply(
            lambda x: (str(x)[:30] + "..") if x and len(str(x)) > 30 else x
        )
        print(view.to_string(index=False))
    else:
        print("No active workstreams found.")

    print("\n" + "-" * 100)
    print(" 📢 BACKLOG (Unassigned Issues)")
    print("-" * 100)

    assigned_ids = set()
    for w in workstreams:
        if w["issue_id"]:
            assigned_ids.add(w["issue_id"].replace("#", ""))

    norm_issues = normalize_issues(issues)
    backlog = [i for i in norm_issues if i["id"] not in assigned_ids]

    df_bl = pd.DataFrame(backlog)
    if not df_bl.empty:
        view_bl = df_bl[["id", "title", "updated_at"]].copy()
        view_bl["updated_at"] = view_bl["updated_at"].apply(format_time)
        print(view_bl.to_string(index=False))
    else:
        print("No orphaned issues.")


def print_dashboard(sessions, issues, prs):
    workstreams = correlate_data(sessions, issues, prs)

    print("\nACTIVE WORKSTREAMS (Correlated)")
    print(
        f"{'UPDATED':<9} {'ISSUE':<8} {'SESSION':<18} {'ST':<4} "
        f"{'PR':<6} {'REV':<4} {'TASK'}"
    )
    print("-" * 100)

    for w in workstreams[:25]:
        updated = format_time(w["last_activity"])[:9]
        issue = w["issue_id"] or "-"
        sess = w["session_id"][:16] or "-"

        # Use Icon for state
        state_icon = get_state_icon(w["session_state"], w["session_created"])

        pr = w["pr_id"] or "-"

        # Review Icon
        rev = w["pr_status"] or ""
        rev_icon = (
            "✅"
            if rev == "APPROVED"
            else (
                "🚫"
                if rev == "CHANGES_REQUESTED"
                else "👀" if rev == "REVIEW_REQUIRED" else "-"
            )
        )

        task = w["issue_title"] or w["session_title"] or ""

        print(
            f"{updated:<9} {issue:<8} {sess:<18} "
            f"{state_icon:<4} {pr:<6} {rev_icon:<4} {task[:35]}"
        )

    print("\n📢 OPEN ISSUES (Raw List)")
    print(f"{'ID':<6} {'UPDATED':<10} {'TITLE'}")
    print("-" * 80)
    for i in issues[:10]:
        print(
            f"#{i['number']:<5} {format_time(i['updatedAt']):<10} "
            f"{i['title'][:60]}"
        )


def export_data(sessions, issues, prs, fmt="csv"):
    """Exports data to files, using Pandas if available."""
    workstreams = correlate_data(sessions, issues, prs)

    datasets = {
        "jules_sessions": normalize_sessions(sessions),
        "github_issues": normalize_issues(issues),
        "github_prs": normalize_prs(prs),
        "consolidated_workstreams": workstreams,
    }

    logger.info(f"💾 Exporting data in {fmt.upper()} format...")

    for name, data in datasets.items():
        filename = f"{name}.{fmt}"
        if not data:
            continue

        try:
            if HAS_PANDAS:
                # Use Pandas for robust export
                df = pd.DataFrame(data)
                if fmt == "csv":
                    df.to_csv(filename, index=False)
                elif fmt == "json":
                    df.to_json(filename, orient="records", indent=2)
            else:
                # Fallback to standard library
                if fmt == "csv":
                    with open(
                        filename, "w", newline="", encoding="utf-8"
                    ) as f:
                        writer = csv.DictWriter(f, fieldnames=data[0].keys())
                        writer.writeheader()
                        writer.writerows(data)
                elif fmt == "json":
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)

            logger.info(f"  ✅ Saved {filename}")
        except Exception as e:
            logger.error(f"  ❌ Failed to save {filename}: {e}")


def generate_markdown_summary(sessions):
    filename = "jules_sessions_summary.md"
    sessions.sort(key=lambda s: s.get("createTime", ""), reverse=True)

    header = "| Session Name | State | Age | Title | PR Link |\n"
    separator = "|---|---|---|---|---|\n"

    try:
        with open(filename, "w") as f:
            f.write(
                f"# Jules Session Summary\nGenerated: {datetime.now()}\n\n"
            )
            f.write(header)
            f.write(separator)

            for session in sessions:
                name = session.get("name", "N/A").split("/")[-1]
                state = session.get("state", "N/A")
                created = session.get("createTime", "")
                age = format_time(created)
                title = session.get("title", "N/A")

                pr_link = ""
                outputs = session.get("outputs", [])
                for output in outputs:
                    if "pullRequest" in output:
                        pr_url = output["pullRequest"].get("url", "")
                        pr_link = f"[PR]({pr_url})"
                        break

                f.write(
                    f"| {name} | {state} | {age} | {title} | {pr_link} |\n"
                )
        logger.info(f"📄 Summary generated: {filename}")
    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")


# -------------------------------------------------------------------------
# 5. MAIN CLI
# -------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Jules Ops & GitHub Sync Tool"
    )
    parser.add_argument(
        "--api-key", help="Jules API Key (or set JULES_API_KEY env)"
    )

    subparsers = parser.add_subparsers(
        dest="command", help="Available commands"
    )

    # Status
    p_status = subparsers.add_parser("status", help="Show unified Dashboard")
    p_status.add_argument(
        "--style",
        choices=["table", "pandas"],
        default="table",
        help="Output style",
    )

    # Export
    p_export = subparsers.add_parser("export", help="Export data to files")
    p_export.add_argument(
        "--format",
        choices=["csv", "json"],
        default="csv",
        help="Export format",
    )

    # Create / Work-on
    p_create = subparsers.add_parser(
        "create", help="Create session from prompt"
    )
    p_create.add_argument("--prompt", required=True, help="Instruction text")
    p_create.add_argument("--branch", help="Target branch")
    p_create.add_argument("--title", help="Session title")
    p_create.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
        help="Source name (default: github/arii/hrm)",
    )
    p_create.add_argument(
        "--no-watch", action="store_true", help="Don't watch after creating"
    )

    p_work = subparsers.add_parser(
        "work-on", help="Create session from GitHub Issue"
    )
    p_work.add_argument("issue_id", type=int, help="GitHub Issue Number")
    p_work.add_argument("--branch", help="Target branch (optional)")

    # Session Management
    p_watch = subparsers.add_parser("watch", help="Monitor a session")
    p_watch.add_argument("session_name", help="Session ID/Name")

    p_msg = subparsers.add_parser("message", help="Send message to session")
    p_msg.add_argument("session_name", help="Session ID/Name")
    p_msg.add_argument("text", help="Message text")

    p_pub = subparsers.add_parser("publish", help="Tell Jules to publish PR")
    p_pub.add_argument("session_name", help="Session ID/Name")

    p_del = subparsers.add_parser("delete", help="Delete a session")
    p_del.add_argument("session_name", help="Session ID/Name")

    subparsers.add_parser("list-sources", help="List available Jules sources")
    subparsers.add_parser(
        "summary", help="Generate Markdown summary of sessions"
    )

    args = parser.parse_args()

    # --- Execution ---
    if args.command is None:
        parser.print_help()
        return

    # Initialize Client
    client = JulesClient(api_key=args.api_key)

    # Common Fetch Logic for Status and Export
    if args.command in ["status", "export"]:
        logger.info("🔄 Refreshing data from Jules and GitHub...")
        sessions = client.list_sessions()
        check_gh_dependencies()
        issues = (
            run_gh_cmd(
                [
                    "gh",
                    "issue",
                    "list",
                    "--state",
                    "open",
                    "--limit",
                    "100",
                    "--json",
                    "number,title,assignees,updatedAt,url",
                ]
            )
            or []
        )
        prs = (
            run_gh_cmd(
                [
                    "gh",
                    "pr",
                    "list",
                    "--state",
                    "open",
                    "--limit",
                    "100",
                    "--json",
                    "number,title,headRefName,reviewDecision,url,updatedAt",
                ]
            )
            or []
        )

        if args.command == "status":
            if args.style == "pandas":
                if HAS_PANDAS:
                    print_pandas_dashboard(sessions, issues, prs)
                else:
                    logger.warning(
                        "Pandas is not installed. Falling back to table view."
                    )
                    print_dashboard(sessions, issues, prs)
            else:
                print_dashboard(sessions, issues, prs)

        elif args.command == "export":
            export_data(sessions, issues, prs, fmt=args.format)

    elif args.command == "create":
        session_name = client.create_session(
            args.prompt, args.source, args.branch, args.title
        )
        if session_name:
            print(f"✅ Session started: {session_name}")
            if not args.no_watch:
                client.monitor_session(session_name)

    elif args.command == "work-on":
        data = fetch_issue_context(args.issue_id)
        if not data:
            logger.error("Could not fetch issue data.")
            sys.exit(1)

        branch_name = args.branch or f"feature/issue-{args.issue_id}"
        logger.info(
            f"Assigning Jules  Issue #{args.issue_id} -> Branch: {branch_name}"
        )
        session_name = client.create_session(
            prompt=data["prompt"],
            source=DEFAULT_SOURCE,
            branch=branch_name,
            title=f"Fix: {data['title']} (#{args.issue_id})",
        )

        if session_name:
            print(f"✅ Session started: {session_name}")
            client.monitor_session(session_name)

    elif args.command == "watch":
        client.monitor_session(args.session_name)

    elif args.command == "message":
        if client.send_message(args.session_name, args.text):
            logger.info("📨 Message sent.")
            client.monitor_session(args.session_name)

    elif args.command == "publish":
        if client.send_message(
            args.session_name,
            "Please publish the branch and create the Pull Request now.",
        ):
            logger.info("📨 Publish request sent to Jules.")
            logger.info("   Monitoring for PR link...")
            client.monitor_session(args.session_name)

    elif args.command == "delete":
        client.delete_session(args.session_name)

    elif args.command == "list-sources":
        sources = client.list_sources()
        print(f"\nFound {len(sources)} sources:")
        for s in sources:
            print(f"- {s.get('name')} (ID: {s.get('id')})")

    elif args.command == "summary":
        sessions = client.list_sessions()
        generate_markdown_summary(sessions)


if __name__ == "__main__":
    main()
