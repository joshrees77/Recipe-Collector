#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configure Git User Info ---
# Use environment variables set in Render dashboard
if [ -z "$GIT_USER_NAME" ] || [ -z "$GIT_USER_EMAIL" ]; then
  echo "Git user name or email not set. Skipping Git config."
else
  git config user.name "$GIT_USER_NAME"
  git config user.email "$GIT_USER_EMAIL"
  echo "Git user configured."
fi

# --- Configure Git Remote with PAT (REQUIRED for pushing to private repo) ---
# Use environment variable set in Render dashboard
if [ -z "$GITHUB_PAT" ]; then
  echo "GitHub PAT not set ($GITHUB_PAT). Cannot configure remote for pushing."
else
  REPO_URL=$(git config --get remote.origin.url)
  # Replace the original HTTPS URL with one that includes the PAT
  # Assumes the original remote is HTTPS
  AUTH_REPO_URL=$(echo "$REPO_URL" | sed "s/https:\/\/github.com/https:\/\/$GITHUB_PAT@github.com/")

  if [ "$REPO_URL" != "$AUTH_REPO_URL" ]; then
      git remote set-url origin "$AUTH_REPO_URL"
      echo "Configured Git remote URL with PAT."
  else
      echo "Could not configure Git remote URL with PAT. Is the remote URL already set?"
  fi
fi

# --- Ensure recipes.db is not ignored (if you added it to .gitignore) ---
# This might be tricky to automate reliably if .gitignore is complex
# Ensure your .gitignore does NOT ignore recipes.db before pushing code

# --- Start the Gunicorn server ---
echo "Starting Gunicorn server..."
exec gunicorn app:app
