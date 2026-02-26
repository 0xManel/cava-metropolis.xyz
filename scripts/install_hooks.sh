#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

git config core.hooksPath .githooks
chmod +x scripts/update_project_logs.sh
chmod +x .githooks/post-commit

echo "Hooks enabled: core.hooksPath=.githooks"
