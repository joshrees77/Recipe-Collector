#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Enable xtrace to debug command execution
set -x

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
# Explicitly set the remote URL using the PAT
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

  # Construct the full authenticated HTTPS URL
  # Safely format the PAT for inclusion in the URL
  PAT_ESCAPED=$(echo -n "$GITHUB_PAT" | jq -sRr @uri)

  NEW_REMOTE_URL="https://${PAT_ESCAPED}@${GITHUB_HOST}/${GITHUB_USER}/${REPO_NAME}.git"

  echo "Constructed NEW_REMOTE_URL: $NEW_REMOTE_URL" >&2 # Debug print
  echo "Setting git remote origin URL..." >&2 # Debug print

  # Use printf %q with eval for safer command execution
  printf -v GIT_SET_URL_CMD 'git remote set-url origin %q' "$NEW_REMOTE_URL"
  eval "$GIT_SET_URL_CMD"

  echo "Git remote origin URL configured successfully for pushing." >&2

fi

# Disable xtrace before starting the app
set +x

# --- Ensure recipes.db is not ignored (if you added it to .gitignore) ---
# This might be tricky to automate reliably if .gitignore is complex
# Make sure your .gitignore does NOT ignore recipes.db before pushing code to Render

# --- Start the Gunicorn server ---
echo "Starting Gunicorn server..." >&2
exec gunicorn app:app
