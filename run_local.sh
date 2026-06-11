#!/usr/bin/env bash
# ローカルでBotを起動する。別ターミナルで `ngrok http 8000` を立ち上げ、
# 表示された https URL + /callback を LINE Developers の Webhook URL に設定。
set -euo pipefail
cd "$(dirname "$0")"
PORT="${PORT:-8000}"
exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --reload
