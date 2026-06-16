#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/path/to/lab-data-collector"
BRANCH_NAME="hybrid-github-pages-api"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python"

cd "$PROJECT_DIR"

git checkout "$BRANCH_NAME"
git pull origin "$BRANCH_NAME"

"$VENV_PYTHON" manage.py export_static_site

git add docs

if git diff --cached --quiet; then
    echo "No static snapshot changes to commit."
    exit 0
fi

STAMP="$(date '+%Y-%m-%d %H:%M:%S')"
git commit -m "Daily read-only LabVault snapshot: $STAMP"
git push origin "$BRANCH_NAME"

echo "Daily static snapshot pushed successfully."
