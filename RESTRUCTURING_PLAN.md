That's an excellent architectural choice. Using a **Git Submodule** for the `hrm` application inside the **`hrm-workspace`** repository provides a clean separation of concerns while ensuring that the automation scripts can easily access the application code at a *specific, version-controlled commit*.

The `hrm-workspace` becomes the operational layer, and the `hrm` submodule remains the self-contained application layer.

Here is the comprehensive set of instructions for implementing this structure:

## Restructuring Plan: Git Submodule Integration

### Phase 1: Repository Renaming and Initialization

1.  **Rename Repository (External):** In your Git provider (GitHub, etc.), rename the **`hrm-scripts`** repository to **`hrm-workspace`**.
2.  **Clone and Update Local References:** Clone the new repository locally.
    ```bash
    git clone <url_of_hrm-workspace>
    cd hrm-workspace
    ```
3.  **Update Internal References:** Globally replace all instances of `"hrm-scripts"` with `"hrm-workspace"` in all existing Python/Shell scripts and the `README.md` within this repository.
4.  **Organize Automation Scripts:** Organize the existing utility scripts into logical directories within the root of `hrm-workspace`:
    ```bash
    # Create the structure for your specialized tooling
    mkdir agent-requests  # For your agentic scripts
    mkdir github-ops
    mkdir session-ops
    mkdir local-dev

    # Move existing scripts into the new structure
    mv process_pr.py github-ops/
    mv verify_oauth_local.py local-dev/
    # etc.
    ```

-----

### Phase 2: Integrating the Application Submodule

The `hrm` application will be added as a subdirectory controlled by its own Git history.

1.  **Add `hrm` as a Submodule:** From the root of your new **`hrm-workspace`** repository, run the following command, using the URL of your independent `hrm` application repository:

    ```bash
    git submodule add <url_of_hrm_repo> hrm
    ```

    *This creates the `hrm` subdirectory, clones the `hrm` repository into it, and creates the `.gitmodules` file in `hrm-workspace`.*

2.  **Commit the Submodule:** Commit the addition of the submodule to the `hrm-workspace` repository:

    ```bash
    git add hrm .gitmodules
    git commit -m "feat: Add core hrm application as a submodule"
    git push
    ```

    The `hrm-workspace` repository now tracks a specific commit SHA of the `hrm` repository.

-----

### Phase 3: Path and Configuration Adjustments

Since the application and all its self-contained files (`playwright.config.ts`, `tests/`, `Dockerfile`, etc.) now live under the `hrm/` directory, the automation scripts need to be updated.

1.  **Update Automation Scripts (Python/Shell):**
    All scripts in `hrm-workspace` must now access the application files through the **`hrm/` prefix**.

    | Old Reference (in a script) | New Reference (in a script) |
    | :--- | :--- |
    | `./package.json` | `./hrm/package.json` |
    | `cd ../hrm` | `cd hrm` |
    | `open-project-file.py` | `hrm/open-project-file.py` |

    *Example (`github-ops/process_pr.py`):*

    ```python
    # Before: 
    # with open('package.json', 'r') as f:
    # After: 
    with open('hrm/package.json', 'r') as f:
        # ... logic to read HRM application dependencies
    ```

2.  **Define Workspace Dev Container (Optional but Recommended):**
    If you use a Dev Container for the `hrm-workspace` tooling (Python, Agent dependencies), the configuration must initialize the submodule.

      * **In `.devcontainer/devcontainer.json`:** Add the `initializeCommand` to handle the submodule checkout:
        ```json
        {
          "name": "HRM Agent/Workspace Tooling",
          // ... other config
          "postCreateCommand": "git submodule update --init --recursive",
          "workspaceFolder": "/workspaces/hrm-workspace"
        }
        ```

3.  **Update Application Scripts (No Change Needed in `hrm`):**
    Crucially, since you are keeping the testing, bringup scripts, and Dockerfile *within* the `hrm` repository, they will still run relative to the `hrm/` directory. No internal path changes are needed within the `hrm` submodule itself, preserving its standalone nature.

-----

### Phase 4: Updated Developer Workflow

The process for anyone cloning the **`hrm-workspace`** repository now includes one extra step:

1.  **Initial Clone:**
    ```bash
    git clone <url_of_hrm-workspace>
    cd hrm-workspace
    ```
2.  **Initialize Submodule:** This fetches the actual application code.
    ```bash
    git submodule update --init --recursive
    ```
3.  **Start Development/Automation:**
      * To run an agentic script: `python github-ops/process_pr.py`
      * To run a test on the application: `cd hrm && npm install && npm run test`
