import csv
import subprocess
import os
import time
import argparse # Import argparse
from datetime import datetime, timedelta

# --- Configuration ---
CONSOLIDATED_WORKSTREAMS_CSV = "consolidated_workstreams.csv"
JULES_OPS_SCRIPT = "jules_ops.py"
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
JULES_OPS_PATH = os.path.join(SCRIPTS_DIR, JULES_OPS_SCRIPT)
CONSOLIDATED_WORKSTREAMS_PATH = os.path.join(
    SCRIPTS_DIR, CONSOLIDATED_WORKSTREAMS_CSV
)

def run_jules_ops_export():
    """Runs jules_ops.py export to regenerate CSV files."""
    print("Regenerating CSV data from Jules and GitHub...")
    command = [
        "python3",
        JULES_OPS_PATH,
        "export",
        "--format",
        "csv"
    ]
    try:
        # Execute jules_ops.py from the workspace root
        result = subprocess.run(
            command,
            cwd="/home/ari/workspace", # Assuming /home/ari/workspace is the root
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            print("✅ CSV data regenerated successfully.")
        else:
            print(f"❌ Failed to regenerate CSV data. Exit code: {result.returncode}")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
    except FileNotFoundError:
        print(f"Error: '{JULES_OPS_PATH}' not found. Make sure jules_ops.py is in the 'scripts' directory.")
    except Exception as e:
        print(f"An unexpected error occurred during CSV regeneration: {e}")


def get_unpublished_sessions(csv_path):
    """
    Reads the consolidated_workstreams.csv and returns a list of completed sessions
    that do not have an associated PR.
    """
    sessions_to_publish = []
    try:
        with open(csv_path, mode="r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Assuming session_id is not '-' (which indicates an orphaned PR)
                """
                if (
                    row["session_state"] == "COMPLETED"
                    and not row["pr_id"].strip()
                    and row["session_id"].strip() != "-"
                ):
                """
                sessions_to_publish.append(
                    {
                        "session_id": row["session_id"],
                        "session_title": row["session_title"],
                    }
                )
    except FileNotFoundError:
        print(f"Error: {csv_path} not found.")
    except Exception as e:
        print(f"Error reading CSV: {e}")
    return sessions_to_publish


def publish_session_with_timeout(session_id, timeout_seconds=60):
    """
    Attempts to publish a single Jules session with a specified timeout.
    """
    print(
        f"\nAttempting to publish session: {session_id} with a {timeout_seconds}s timeout..."
    )
    command = [
        "timeout",
        str(timeout_seconds),
        "python3",
        os.path.join("scripts", JULES_OPS_SCRIPT),
        "publish",
        session_id,
    ]

    try:
        result = subprocess.run(
            command,
            cwd="/home/ari/workspace",
            capture_output=True,
            text=True,
            check=False,
        )

        print(f"--- Output for session {session_id} ---")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        print(f"--- End Output for session {session_id} ---")

        if result.returncode == 0:
            print(
                f"✅ Publish request for session {session_id} completed (or initiated)."
            )
            return True
        elif result.returncode == 124:  # Timeout exit code
            print(
                f"❌ Publish request for session {session_id} timed out after {timeout_seconds} seconds."
            )
            return False
        else:
            print(
                f"❌ Publish request for session {session_id} failed with exit code {result.returncode}."
            )
            return False

    except FileNotFoundError:
        print(
            f"Error: '{os.path.join('scripts', JULES_OPS_SCRIPT)}' or 'timeout' command not found."
        )
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Collects and publishes old Jules sessions without associated PRs."
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Regenerate consolidated_workstreams.csv before processing sessions.",
    )
    args = parser.parse_args()

    if args.update:
        run_jules_ops_export()
        # Give a moment for files to be written
        time.sleep(2)

    print("Collecting unpublished Jules sessions...")

    sessions = get_unpublished_sessions(CONSOLIDATED_WORKSTREAMS_PATH)

    if not sessions:
        print("No completed, unpublished sessions found.")
        return

    print(f"Found {len(sessions)} completed, unpublished sessions.")

    for session in sessions:
        session_id = session["session_id"]
        session_title = session["session_title"]
        print(f"\nProcessing session ID: {session_id}, Title: {session_title}")
        publish_session_with_timeout(session_id)
        time.sleep(1)  # Small delay to prevent overwhelming the API


if __name__ == "__main__":
    main()
