#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$project_root/backend"
.venv/bin/python -m ruff check app tests
.venv/bin/python -m ruff format --check app tests
.venv/bin/python -m pytest

cd "$project_root/frontend"
npm run lint
npm run build
