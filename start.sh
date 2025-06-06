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
# Use environment variable set in Render dashboard
if [ -z "$GITHUB_PAT" ]; then
  echo "GitHub PAT not set. Cannot configure remote for pushing." >&2
  # If PAT is mandatory for the workflow, you might want to exit here:
  # exit 1
else
  echo "GITHUB_PAT is set. Attempting to configure remote URL." >&2

  REPO_URL=$(git config --get remote.origin.url)
  echo "Current remote URL: $REPO_URL" >&2

  # Safely format the PAT for inclusion in the URL
  PAT_ESCAPED=$(echo -n "$GITHUB_PAT" | jq -sRr @uri)

  NEW_REPO_URL=""
  GITHUB_HOST="github.com"

  if [[ "$REPO_URL" == git@github.com:* ]]; then
    # Convert SSH to HTTPS, inserting PAT
    # git@github.com:user/repo.git -> https://PAT@github.com/user/repo.git
    REPO_PATH=${REPO_URL#git@github.com:}
    NEW_REPO_URL="https://${PAT_ESCAPED}@${GITHUB_HOST}/${REPO_PATH}"
    echo "Converted SSH remote URL to HTTPS with PAT." >&2

  elif [[ "$REPO_URL" == https://github.com/* ]]; then
    # Handle existing HTTPS, removing any old user@ and inserting PAT
    # https://github.com/user/repo.git -> https://PAT@github.com/user/repo.git
    # https://old_user@github.com/user/repo.git -> https://PAT@github.com/user/repo.git
    # Extract the path part after github.com/
    REPO_PATH=${REPO_URL#https://*/}
    REPO_PATH=${REPO_PATH#*@*/}

    NEW_REPO_URL="https://${PAT_ESCAPED}@${GITHUB_HOST}/${REPO_PATH}"
    echo "Updated HTTPS remote URL with PAT." >&2

  else
    echo "Could not configure Git remote URL with PAT. Unsupported format: $REPO_URL" >&2
    # If unsupported URL format should halt deploy, uncomment below:
    # exit 1
  fi

  # Only update if a new URL was successfully constructed and is non-empty
  if [ -n "$NEW_REPO_URL" ]; then
      echo "Constructed NEW_REPO_URL: $NEW_REPO_URL" >&2 # Debug print
      echo "Setting new remote URL..." >&2 # Debug print
      # Use printf to safely pass the URL string as a single argument to git
      printf -v GIT_SET_URL_CMD 'git remote set-url origin %q' "$NEW_REPO_URL"
      eval "$GIT_SET_URL_CMD"
      echo "Git remote URL configured successfully." >&2
  fi
fi

# Disable xtrace before starting the app
set +x

# --- Ensure recipes.db is not ignored (if you added it to .gitignore) ---
# This might be tricky to automate reliably if .gitignore is complex
# Make sure your .gitignore does NOT ignore recipes.db before pushing code to Render

# --- Start the Gunicorn server ---
echo "Starting Gunicorn server..." >&2
exec gunicorn app:app
