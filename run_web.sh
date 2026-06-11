#!/usr/bin/env bash
# Streamlit Web版を起動する。
# 別ターミナルで `cp .env.example .env` 後、ANTHROPIC_API_KEY を設定しておくこと。
set -euo pipefail
cd "$(dirname "$0")"
exec .venv/bin/streamlit run web_app.py --server.port "${PORT:-8501}"
