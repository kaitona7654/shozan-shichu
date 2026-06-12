#!/usr/bin/env bash
# 毎朝 launchd から起動。今日の運勢投稿文を生成し、
# X版をクリップボードにコピーして macOS 通知を出す。
# kaitoさんは通知を見たら X に Cmd+V で貼り付けて投稿するだけ。
# Threads版は output/YYYY-MM-DD.txt 内に併記。
set -euo pipefail
cd "$(dirname "$0")/.."

X_POST=$(.venv/bin/python daily_post/generate_daily_post.py)

# X版をクリップボードへ
printf '%s' "$X_POST" | pbcopy

# macOS 通知
osascript -e 'display notification "X版をクリップボードにコピーしました。Threads版は output フォルダ内。" with title "🔮 今日の運勢 投稿文ができました" sound name "Glass"'

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 生成完了"
