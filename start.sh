#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Enable xtrace to debug command execution
set -x

# --- Change directory to the project root ---
# Render clones the project into /opt/render/project/src/
cd /opt/render/project/src/ || { echo "Failed to change directory to project root." >&2; exit 1; }

# --- Configure Git User Info ---
# Use environment variables set in Render dashboard
if [ -z "$GIT_USER_NAME" ] || [ -z "$GIT_USER_EMAIL" ]; then
  echo "Git user name or email not set. Skipping Git config." >&2
else
  git config user.name "$GIT_USER_NAME"
  git config user.email "$GIT_USER_EMAIL"
  echo "Git user configured." >&2
fi

# --- Configure Git Remote with PAT (REQUIRED for pushing to private repo via HTTPS) ---
# Ensure the origin remote exists and points to the authenticated URL
# Use environment variable set in Render dashboard
if [ -z "$GITHUB_PAT" ]; then
  echo "GitHub PAT not set. Cannot configure remote for pushing." >&2
  # If PAT is mandatory for the workflow, you might want to exit here:
  # exit 1
else
  echo "GITHUB_PAT is set. Attempting to configure remote URL." >&2

  GITHUB_HOST="github.com"
  GITHUB_USER="joshrees77" # Your GitHub username
  REPO_NAME="Recipe-Collector" # Your repository name

  # Safely format the PAT for inclusion in the URL
  PAT_ESCAPED=$(echo -n "$GITHUB_PAT" | jq -sRr @uri)

  AUTHENTICATED_REMOTE_URL="https://${PAT_ESCAPED}@${GITHUB_HOST}/${GITHUB_USER}/${REPO_NAME}.git"

  echo "Constructed Authenticated Remote URL: $AUTHENTICATED_REMOTE_URL" >&2 # Debug print
  echo "Checking if 'origin' remote exists..." >&2 # Debug print

  # Check if 'origin' remote exists
  if git remote get-url origin > /dev/null 2>&1; then
    # If origin exists, set its URL (forcefully in case it's wrong)
    echo "'origin' remote exists. Setting URL..." >&2 # Debug print
    printf -v GIT_REMOTE_CMD 'git remote set-url origin %q --force' "$AUTHENTICATED_REMOTE_URL"
    eval "$GIT_REMOTE_CMD"
    echo "Git remote 'origin' URL set successfully." >&2
  else
    # If origin does not exist, add it
    echo "'origin' remote does not exist. Adding remote..." >&2 # Debug print
    printf -v GIT_REMOTE_CMD 'git remote add origin %q' "$AUTHENTICATED_REMOTE_URL"
    eval "$GIT_REMOTE_CMD"
    echo "Git remote 'origin' added successfully." >&2
  fi

  echo "Git remote configuration finished." >&2

fi

# Disable xtrace before starting the app
set +x

# --- Ensure recipes.db is not ignored (if you added it to .gitignore) ---
# This might be tricky to automate reliably if .gitignore is complex
# Make sure your .gitignore does NOT ignore recipes.db before pushing code to Render

# --- Start the Gunicorn server ---
echo "Starting Gunicorn server..." >&2
exec gunicorn app:app
