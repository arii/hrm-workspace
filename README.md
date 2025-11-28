# hrm-workspace

Operational workspace for HRM automation, tooling, and local development.

This workspace contains Python scripts for managing agentic workflows and integrates the `hrm` application as a Git submodule.

## Key Scripts

### `jules_ops.py`
A unified CLI tool for interacting with Jules AI sessions and GitHub Issues/PRs.

**Features:**
- **Unified Dashboard:** View active Jules sessions, open PRs, and assigned Issues.
- **Smart Start (`work-on`):** Start a Jules session from a GitHub Issue ID. Automatically creates a feature branch and sends the issue context to Jules.
- **Session Lifecycle Automation:** Create, monitor, and publish Jules sessions and PRs.
- **Zero-Config:** Only requires Python 3, `requests`, and authenticated GitHub CLI (`gh`).

**Typical Usage:**
```bash
# Show dashboard of sessions, PRs, and issues
./jules_ops.py status

# Start a Jules session from a GitHub Issue
./jules_ops.py work-on <issue_id>

# Create a session manually
./jules_ops.py create --prompt "Refactor login" --branch "refactor/login" --title "Login Refactor"

# Publish a PR for a session
./jules_ops.py publish <session_id>

# Monitor a session
./jules_ops.py watch <session_id>
```

**Setup:**
- Make executable: `chmod +x jules_ops.py`
- Set API key: `export JULES_API_KEY="your-api-key"`
- Install dependencies: `pip install requests`
- Authenticate GitHub CLI: `gh auth login`

---

### `check_branch_session.py`
A utility within `github-ops/` to map a branch, PR, or Issue to its corresponding Jules session using the consolidated CSV artifact.

**Features:**
- **Lookup:** Find the Jules session linked to a branch, PR, or Issue.
- **Messaging:** Send a message to the session (if `jules_ops.py` is available).
- **Deletion:** Delete a session after confirmation.

**Typical Usage (from workspace root):**
```bash
# Find session for a branch, PR, or issue
./github-ops/check_branch_session.py <branch|#pr|issue>

# Send a message to the session
./github-ops/check_branch_session.py <identifier> --message "Ping from dev"

# Delete a session
./github-ops/check_branch_session.py <identifier> --delete
```

**Notes:**
- Uses `consolidated_workstreams.csv` for lookups.
- Requires `jules_ops.py` for messaging/deletion features.

---

## Other Files

- `consolidated_workstreams.csv`: Artifact mapping branches/PRs/issues to Jules sessions.
- `pyproject.toml`, `.pre-commit-config.yaml`: Formatting and linting configuration.
- `jules_sessions.csv`, `github_issues.csv`, `github_prs.csv`: Data exports.

---

## Developer Workflow (Submodule Setup)

This workspace tracks the `hrm` application as a Git submodule inside `hrm/`.

- Clone the workspace:

```bash
git clone <url_of_hrm-workspace>
cd hrm-workspace
```

- Initialize and fetch the application submodule:

```bash
git submodule update --init --recursive
```

- Run workspace automation (examples):

```bash
python github-ops/process_pr.py <pr_number>
```

- Work inside the app:

```bash
cd hrm
npm install
npm run test

- Preferred local-first verification:

```bash
cd hrm
npm run verify
```

This executes the app’s full local verification flow and posts results directly (no GitHub Actions runners). The PR processor uses this by default.
```

### Dev Container

If you use VS Code Dev Containers, this workspace will automatically initialize submodules via the post-create command defined in `.devcontainer/devcontainer.json`.

## Developer Tips

- All scripts are Python 3.x and require minimal dependencies.
- For full automation, ensure your API key and GitHub CLI are configured.
- Use the dashboard (`jules_ops.py status`) to track all active workstreams.

### Cross-References

- App testing and conventions: see `hrm/TESTING.md` and `hrm/README.md`.
- The workspace enforces a local-first process; prefer `npm run verify` inside `hrm/` instead of CI runners.

---

## Troubleshooting

- Layout validation fails:
	- Ensure submodule is initialized: `git submodule update --init --recursive`
	- Verify expected paths exist in `hrm/`:
		- `hrm/package.json`, `hrm/server.ts`, `hrm/next.config.js`
		- `hrm/app/api/auth/[...nextauth]/route.ts`
		- `hrm/app/client/control/page.tsx`
		- `hrm/playwright.config.ts`, `hrm/tests/`, `hrm/Dockerfile`
- Local verification issues (`npm run verify`):
	- Run `npm install` in `hrm/` and re-run.
	- Check environment variables and secrets expected by the app.
	- Review PR comment for attached logs and structure analyzer output.
