#!/usr/bin/env bash
# 日干特化版アプリを起動する
# 既存のフル機能版（run_web.sh）と別ポートで動作
set -euo pipefail
cd "$(dirname "$0")"
exec .venv/bin/streamlit run web_app_nikkan.py --server.port "${PORT:-8502}"
