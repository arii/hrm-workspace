This finalized plan establishes a clean separation of concerns using **Git Submodules**, where the application logic (`hrm`) is decoupled from the automation and environment control (`hrm-workspace`). This structure provides the necessary revision control for both the application and the tooling.

## 1\. Finalized Architecture: Parent/Submodule Structure

The project will be split into two distinct, version-controlled repositories:

| Repository | Role (Parent/Child) | Primary Responsibility | Key Files Kept Here |
| :--- | :--- | :--- | :--- |
| **`hrm-workspace`** | **Parent (Operational/Tooling)** | **Revision control** for automation, testing agents, session management scripts, and the unified development environment configuration. | `github-ops/`, `agent-requests/`, `.devcontainer/`, `process_pr.py`, `pyproject.toml` |
| **`hrm`** | **Submodule (Application)** | **Application Logic and Local Lifecycle.** Includes source code, local testing, deployment scripts, and configuration for a standalone Next.js/Node.js app. | `app/`, `components/`, `server.ts`, `playwright.config.ts`, `tests/`, `Dockerfile` |

The `hrm-workspace` repository will contain the `hrm` application as a **submodule** in a dedicated subdirectory named `hrm/`.

-----

## 2\. Comprehensive Restructuring Plan

### Phase A: Repository Renaming and Tooling Organization

1.  **Rename Git Repository:** Rename the existing **`hrm-scripts`** repository to **`hrm-workspace`** in your Git hosting service (e.g., GitHub).
2.  **Establish Tooling Structure:** In the local clone of `hrm-workspace`, create the new, organized directory structure for your scripts:
    ```bash
    cd hrm-workspace
    mkdir .devcontainer  # For the workspace development environment
    mkdir agent-requests # For AI/Agentic scripts (e.g., Jules/Gemini analysis)
    mkdir github-ops     # For CI/PR processing (e.g., process_pr.py)
    mkdir session-ops    # For session data management (e.g., publish_old_sessions.py)
    mkdir local-dev      # For local environment verification (e.g., verify_oauth_local.py)
    ```
3.  **Relocate Scripts:** Move all existing Python and Shell scripts (from the original `hrm-scripts` root) into their appropriate new subdirectories.
4.  **Update Internal References:** Globally replace all instances of `"hrm-scripts"` with `"hrm-workspace"` in all relocated scripts and the `README.md`.
5.  **Commit:** Commit the new folder structure and file relocation to `hrm-workspace`.

### Phase B: Submodule Integration and Path Adjustments

1.  **Add `hrm` as Submodule:** From the root of **`hrm-workspace`**, link the core application repository:

    ```bash
    git submodule add <url_of_hrm_repo> hrm
    ```

    *(This creates the `hrm/` folder containing the application code and the `.gitmodules` file at the root of `hrm-workspace`)*

2.  **Commit Submodule Link:** Commit the new submodule pointer to the `hrm-workspace` history.

3.  **Update Script Pathing (Crucial):** Modify all scripts within `hrm-workspace` to access application files using the **`hrm/` prefix**.

    | Script Task | Old Path (in `process_pr.py`) | New Path (in `github-ops/process_pr.py`) |
    | :--- | :--- | :--- |
    | Access application code | `os.path.join(os.getcwd(), '..', 'package.json')` | `os.path.join(os.getcwd(), 'hrm', 'package.json')` |
    | Run Playwright tests | `npx playwright test` | `cd hrm && npx playwright test` |
    | Access build assets | `./build/server.js` | `./hrm/build/server.js` |

4.  **Application Repository (`hrm`) Integrity:** Verify that the `hrm` repository contains all its local lifecycle files (testing, bring-up scripts, Dockerfile). No internal file paths within the `hrm` repository should need changing, as they remain relative to their own root.

### Phase C: Environment Setup

1.  **Workspace Dev Container:** Create the **`.devcontainer/`** folder in the **`hrm-workspace` root**. This environment must include both **Node.js/npm** (to interact with the app) and **Python/Poetry** (for the automation scripts).
2.  **Submodule Initialization Command:** Configure the Dev Container to automatically initialize the submodule upon creation:
      * In `hrm-workspace/.devcontainer/devcontainer.json`, ensure the `postCreateCommand` includes:
        ```json
        "postCreateCommand": "git submodule update --init --recursive && cd hrm && npm install" 
        ```

-----

## 3\. Enforcing the Correct Layout (Updated Strategy)

Layout enforcement is now centralized in the **`hrm-workspace`** repository's scripts, ensuring the `hrm` submodule always conforms to project standards.

### A. Pre-Execution Validation (The Gatekeeper)

A mandatory check script will run before any significant automation (like CI/PR processing) is executed.

1.  **Create Validation Script:** Create a new script, e.g., `hrm-workspace/local-dev/validate_hrm_layout.py`.
2.  **Define Required Layout:** This script will assert the existence of critical files and directories within the `./hrm/` submodule folder.
      * **Core App Files:** Check for `./hrm/package.json`, `./hrm/server.ts`, `./hrm/next.config.js`.
      * **Architecture Files:** Check for the Next.js App Router structure: `./hrm/app/api/auth/[...nextauth]/route.ts`, `./hrm/app/client/control/page.tsx`.
      * **Local Lifecycle Files:** Check for `./hrm/playwright.config.ts`, `./hrm/tests/`, `./hrm/Dockerfile` (if applicable).
3.  **Execution and Failure:** The script should exit with a non-zero status and print a detailed error message if any critical file is missing or misplaced, immediately halting any dependent process (e.g., `process_pr.py`).

### B. Automation Enforcement (CI/CD Pipeline)

The Continuous Integration (CI) pipeline for the **`hrm-workspace`** repository becomes the primary enforcement mechanism.

1.  **Initial Step:** The pipeline must first ensure the `hrm` submodule is initialized (`git submodule update --init --recursive`).
2.  **Mandatory Check:** The very next step must execute the validation script:
    ```bash
    # Example CI step for hrm-workspace
    python local-dev/validate_hrm_layout.py
    ```
    If this script fails, the entire CI pipeline (including running agentic tests or deploying) fails, forcing the developer to fix the `hrm` repository's structure and update the submodule pointer.

### C. Continuous Code Quality Enforcement

Utilize existing and extended tools to enforce code style and structural integrity continuously.

1.  **Pre-Commit Hooks (Submodule Level):** The `hrm` submodule can retain its own local `.pre-commit-config.yaml` to enforce formatting (e.g., using its internal `.prettierrc` and `eslint.config.mjs`) on its codebase.
2.  **Agentic Structure Review:** Extend scripts in `hrm-workspace/agent-requests/` (e.g., a new `analyze_structure.py`) to use AI models to perform high-level structural checks beyond simple file existence. For example, ensuring all API routes adhere to a consistent naming convention or that all components use MUI imports.
