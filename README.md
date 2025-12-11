# hrm-workspace

Operational workspace for HRM automation, tooling, and local development.

This workspace contains unified Python scripts for managing agentic workflows and integrates the `hrm` application as a Git submodule.

## Unified Script Architecture

All scripts now use a consistent, unified architecture with:
- **Common Configuration**: Centralized path management and logging
- **Unified Jules Client**: Single, robust API client with proper error handling
- **Data Management**: All exports saved to `data/` directory
- **Consistent Error Handling**: Standardized logging and timeout support

See [`scripts_README.md`](./scripts_README.md) for detailed documentation.

## Key Scripts

### `jules_ops.py`
Main operations script for Jules AI and GitHub integration.

**Features:**
- **Unified Dashboard:** View active workstreams correlating Jules sessions, PRs, and Issues
- **Smart Start (`work-on`):** Start a Jules session from a GitHub Issue ID with automatic branch creation
- **Data Export:** Export comprehensive data to CSV/JSON in the `data/` directory
- **Session Management:** Create, monitor, delete, and publish Jules sessions
- **Zero-Config:** Automatically detects workspace environment and paths

**Typical Usage:**
```bash
# Show dashboard of sessions, PRs, and issues
python jules_ops.py status

# Start a Jules session from a GitHub Issue
python jules_ops.py work-on <issue_id>

# Export data for analysis (saved to data/)
python jules_ops.py export --format csv

# Create a session manually
python jules_ops.py create --prompt "Refactor login" --branch "refactor/login" --title "Login Refactor"

# Publish a PR for a session
python jules_ops.py publish <session_id>

# Monitor a session
python jules_ops.py watch <session_id>

# Delete a specific session
python jules_ops.py delete sessions/<session_id>
```

### Session Management Tools
- **`delete_failed_sessions.py`**: Clean up all Jules sessions (bulk deletion)
- **`close_jules_sessions.py`**: Close sessions associated with specific PR numbers

**Setup:**
- Set API key: `export JULES_API_KEY="your-api-key"`
- Install dependencies: `pip install requests pandas` (pandas optional but recommended)
- Authenticate GitHub CLI: `gh auth login`

### GitHub Operations (`github-ops/`)
- **`process_pr.py`**: Process and integrate PRs with Jules sessions
- **`check_branch_session.py`**: Map branches/PRs/Issues to Jules sessions

**Usage:**
```bash
# Find session for a branch, PR, or issue
python github-ops/check_branch_session.py <branch|#pr|issue>

# Process a specific PR
python github-ops/process_pr.py --pr-number 123
```

### Session Operations (`session-ops/`)
- **`publish_old_sessions.py`**: Publish stalled sessions that haven't created PRs
- **`secrets_ops.py`**: Manage secrets across environments

**Usage:**
```bash
# Publish stalled sessions
python session-ops/publish_old_sessions.py --update
```

---

## Data Management

All script outputs are now organized in the `data/` directory:
- `data/jules_sessions.csv`: Session details and metadata
- `data/github_issues.csv`: GitHub issues data
- `data/github_prs.csv`: GitHub pull requests data  
- `data/consolidated_workstreams.csv`: Correlated workstream data

Configuration files:
- `pyproject.toml`, `.pre-commit-config.yaml`: Formatting and linting configuration
- `common_config.py`, `jules_client.py`: Unified script architecture

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
# Process specific PR(s)
python github-ops/process_pr.py <pr_number>

# Update priority PRs
python scripts/update_priority_prs.py

# Update all PRs with fixes
python scripts/update_prs_with_test_fixes.py

# Process specific PRs or all open PRs (if no args)
bash scripts/verify-pr.sh [pr_number ...]

# Quick workspace validation
bash scripts/check-workspace.sh

# Clean up all worktrees
bash scripts/clean-worktrees.sh
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
