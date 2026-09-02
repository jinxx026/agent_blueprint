#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root/backend"
.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 &
backend_pid=$!
trap 'kill "$backend_pid" 2>/dev/null || true' EXIT INT TERM

cd "$project_root"
backend/.venv/bin/python -m streamlit run frontend/app.py --server.port 8501
