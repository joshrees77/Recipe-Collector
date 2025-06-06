#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

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
# Use environment variable set in Render dashboard
if [ -z "$GITHUB_PAT" ]; then
  echo "GitHub PAT not set. Cannot configure remote for pushing." >&2
else
  REPO_URL=$(git config --get remote.origin.url)

  if [[ "$REPO_URL" == git@github.com:* ]]; then
    # If using SSH format, attempt to change to HTTPS with PAT
    AUTH_REPO_URL=$(echo "$REPO_URL" | sed "s/git@github.com:/https:\/\/$GITHUB_PAT@github.com\/\")
    echo "Detected SSH remote URL, converting to HTTPS with PAT." >&2
    git remote set-url origin "$AUTH_REPO_URL"
    echo "Configured Git remote URL with PAT." >&2
  elif [[ "$REPO_URL" == https://github.com/* ]]; then
    # If already using HTTPS format, update with PAT if not already there
    # This sed command handles if PAT is already in the URL or not
    AUTH_REPO_URL=$(echo "$REPO_URL" | sed "s/https:\/\/.*@github.com/https:\/\/$GITHUB_PAT@github.com/" | sed "s/https:\/\/github.com/https:\/\/$GITHUB_PAT@github.com/")

    if [ "$REPO_URL" != "$AUTH_REPO_URL" ]; then
        git remote set-url origin "$AUTH_REPO_URL"
        echo "Configured Git remote URL with PAT." >&2
    else
        echo "Git remote URL already configured correctly with PAT." >&2
    fi
  else
    echo "Could not configure Git remote URL with PAT. Unsupported format: $REPO_URL" >&2
  fi
fi

# --- Ensure recipes.db is not ignored (if you added it to .gitignore) ---
# This might be tricky to automate reliably if .gitignore is complex
# Make sure your .gitignore does NOT ignore recipes.db before pushing code to Render

# --- Start the Gunicorn server ---
echo "Starting Gunicorn server..." >&2
exec gunicorn app:app
