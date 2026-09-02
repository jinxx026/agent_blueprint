#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$project_root/backend"
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev,ui]'
test -f .env || cp .env.example .env

printf '%s\n' 'Setup complete. Run scripts/dev.sh from the project root.'
