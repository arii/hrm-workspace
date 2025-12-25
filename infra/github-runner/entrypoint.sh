#!/bin/bash
set -e

# Validate required environment variables
if [ -z "${REPO_URL}" ]; then
  echo "Error: REPO_URL is not set."
  exit 1
fi

cd /home/runner/actions-runner

# If RUNNER_TOKEN is not provided, try to fetch it using the GitHub CLI and a PAT
if [ -z "${RUNNER_TOKEN}" ]; then
  if [ -z "${GH_TOKEN}" ] && [ -z "${GITHUB_TOKEN}" ]; then
    echo "Error: RUNNER_TOKEN is missing, and no GH_TOKEN or GITHUB_TOKEN provided to fetch it."
    exit 1
  fi

  echo "RUNNER_TOKEN not provided. Attempting to fetch using GitHub CLI..."

  # Extract owner/repo from URL (e.g., https://github.com/arii/hrm -> arii/hrm)
  # Remove 'https://github.com/' or 'http://github.com/' prefix
  REPO_PATH=${REPO_URL#*github.com/}
  # Remove possible .git suffix
  REPO_PATH=${REPO_PATH%.git}

  echo "Fetching registration token for repository: ${REPO_PATH}"

  # Fetch the token
  # Note: The PAT must have 'admin:org' (for org runners) or 'repo' (for repo runners) scope.
  RUNNER_TOKEN=$(gh api --method POST \
    -H "Accept: application/vnd.github+json" \
    "/repos/${REPO_PATH}/actions/runners/registration-token" \
    | jq -r .token)

  if [ -z "${RUNNER_TOKEN}" ] || [ "${RUNNER_TOKEN}" = "null" ]; then
    echo "Error: Failed to fetch RUNNER_TOKEN."
    exit 1
  fi

  echo "Successfully fetched RUNNER_TOKEN."
fi

echo "Configuring GitHub Actions Runner..."

# --unattended: Don't ask for interaction
# --replace: Replace any existing runner with the same name
# --ephemeral: Optional, but good for containers.
# However, the user used standard persistent config. We will stick to their pattern but use --replace.
./config.sh --unattended \
  --url "${REPO_URL}" \
  --token "${RUNNER_TOKEN}" \
  --name "hrm-docker-runner-$(hostname)" \
  --work "_work" \
  --replace \
  --labels "hrm-backend,playwright,docker"

echo "Starting Runner..."
# Runs the listener process
./run.sh
