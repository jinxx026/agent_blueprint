#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$project_root/backend"
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
test -f .env || cp .env.example .env

cd "$project_root/frontend"
npm ci
test -f .env.local || cp .env.example .env.local

printf '%s\n' 'Setup complete. Run scripts/dev.sh from the project root.'
