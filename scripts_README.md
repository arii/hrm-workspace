# hrm-workspace Scripts

This directory contains unified Python scripts for managing the HRM project workspace, including Jules AI sessions, GitHub operations, and data management.

## Unified Architecture

### Common Configuration (`common_config.py`)
- Provides consistent paths and workspace detection
- Standardized logging configuration
- Python path management for imports
- Data directory management

### Unified Jules Client (`jules_client.py`)
- Single, robust implementation for Jules API interactions
- Consistent error handling and logging
- Timeout support and retry logic
- Used by all scripts that interact with Jules

## Core Scripts

### `jules_ops.py`
Main operations script for Jules and GitHub integration:
- **Status**: `python jules_ops.py status` - View workstreams dashboard
- **Export**: `python jules_ops.py export` - Export data to CSV/JSON (saved to `data/`)
- **Create**: `python jules_ops.py create --prompt "..."` - Create new session
- **Work-on**: `python jules_ops.py work-on 123` - Create session from GitHub issue
- **Delete**: `python jules_ops.py delete sessions/123` - Delete specific session
- **Monitor**: `python jules_ops.py watch sessions/123` - Monitor session progress

### Session Management
- **`delete_failed_sessions.py`** - Delete all Jules sessions (cleanup tool)
- **`close_jules_sessions.py`** - Close sessions associated with specific PR numbers

### GitHub Operations
- **`github_client.py`** - Robust client for Git and GitHub CLI operations
- **`scripts/update_priority_prs.py`** - Update high-priority PRs from leader (replaces shell script)
- **`scripts/update_prs_with_test_fixes.py`** - Batch update PRs with fixes (replaces shell script)

### GitHub Ops Directory (`github-ops/`)
- **`process_pr.py`** - Process and integrate PRs with Jules sessions
- **`check_branch_session.py`** - Check branch/session relationships

### Session Operations (`session-ops/`)
- **`publish_old_sessions.py`** - Publish stalled sessions that haven't created PRs
- **`secrets_ops.py`** - Manage secrets across environments

## Data Management

### Export Directory
All CSV/JSON exports are saved to the `data/` directory:
- `data/jules_sessions.csv` - Session details
- `data/github_issues.csv` - GitHub issues
- `data/github_prs.csv` - GitHub PRs
- `data/consolidated_workstreams.csv` - Correlated workstream data

### Configuration
Scripts automatically detect the workspace environment and use:
- **Workspace Root**: `/home/ari/hrm-workspace`
- **HRM Repository**: `/home/ari/hrm-workspace/hrm`
- **Worktrees**: `/home/ari/hrm-workspace/worktrees`

## Environment Setup

### Required Environment Variables
```bash
export JULES_API_KEY="your-jules-api-key"
```

### Optional Configuration
```bash
export SKIP_JULES_INTEGRATION=1        # Disable Jules integration
export COMMENT_JULES=1                 # Enable Jules mentions in GitHub
export SKIP_REBASE_INTEGRATION=1       # Disable rebase operations
```

## Usage Examples

### Daily Workflow
```bash
# Check current status
python jules_ops.py status

# Export data for analysis
python jules_ops.py export --format csv

# Create session from GitHub issue
python jules_ops.py work-on 456

# Update priority PRs
python scripts/update_priority_prs.py

# Clean up completed sessions
python delete_failed_sessions.py
```

### Development Integration
```bash
# Process a new PR
python github-ops/process_pr.py --pr-number 123

# Publish stalled sessions
python session-ops/publish_old_sessions.py --update
```

## Dependencies

Core requirements:
- `requests` - HTTP client for API calls
- `pandas` (optional) - Enhanced data processing for exports

GitHub CLI:
- `gh` command must be available and authenticated

## Migration Notes

This unified system replaces the previous scattered approach with:
- ✅ Consistent path management across all scripts
- ✅ Single Jules client implementation
- ✅ Standardized logging and error handling
- ✅ Centralized data export location
- ✅ Reduced code duplication
- ✅ Better error messages and debugging

All scripts now use the shared configuration and client, making the system more maintainable and reliable.