#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$project_root/backend"
.venv/bin/python -m ruff check app tests ../frontend
.venv/bin/python -m ruff format --check app tests ../frontend
.venv/bin/python -m pytest
