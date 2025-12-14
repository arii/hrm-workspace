# Self-Hosted GitHub Actions Runner

This directory contains the infrastructure for running a self-hosted GitHub Actions runner in a Docker container.

## Setup

1.  Navigate to this directory:
    ```bash
    cd infra/github-runner
    ```

2.  Create a `.env` file from the example:
    ```bash
    cp .env.example .env
    ```

3.  Configure `.env`:
    *   **REPO_URL**: The URL of your GitHub repository.
    *   **Authentication**: You must provide either a `RUNNER_TOKEN` or a `GH_TOKEN` (PAT).
        *   **Recommended**: Provide a `GH_TOKEN` (Personal Access Token) with `repo` scope. This allows the container to dynamically fetch a valid registration token on startup.
        *   **Alternative**: Provide a static `RUNNER_TOKEN` obtained from *Settings -> Actions -> Runners -> New Runner*. Note that these tokens expire quickly.

## Running the Runner

Use Docker Compose to build and start the runner:

```bash
docker compose up -d --build
```

To view logs:

```bash
docker compose logs -f
```

To stop the runner:

```bash
docker compose down
```

## Architecture

*   **Dockerfile**: Extends `ubuntu:22.04` and installs:
    *   GitHub CLI (`gh`)
    *   Node.js (LTS)
    *   Playwright dependencies (browsers and system libs)
    *   GitHub Actions Runner agent
*   **entrypoint.sh**: Handles configuration and registration. It supports dynamic token fetching using the `gh` CLI.
