#!/bin/bash

# -----------------------
# 設定
# -----------------------
LOG_FILE="/Users/dig/nogi-rss/cron.log"

# PATH問題対策
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# -----------------------
# ログ初期化（これ追加）
# -----------------------
: > "$LOG_FILE"

# -----------------------
# 開始ログ
# -----------------------
echo "==============================" >> "$LOG_FILE"
echo "START: $(date)" >> "$LOG_FILE"

# -----------------------
# ディレクトリ移動
# -----------------------
cd /Users/dig/nogi-rss || {
    echo "❌ cd失敗" >> "$LOG_FILE"
    exit 1
}

# -----------------------
# スクレイピング
# -----------------------
echo "[RUN] main.py" >> "$LOG_FILE"
python3 main.py >> "$LOG_FILE" 2>&1

echo "[RUN] make_member_xml.py" >> "$LOG_FILE"
python3 make_member_xml.py >> "$LOG_FILE" 2>&1

# -----------------------
# Git処理
# -----------------------
echo "[GIT] cleanup" >> "$LOG_FILE"
rm -f .git/index.lock >> "$LOG_FILE" 2>&1
rm -rf .git/rebase-merge >> "$LOG_FILE" 2>&1

echo "[GIT] add" >> "$LOG_FILE"
git add . >> "$LOG_FILE" 2>&1

echo "[GIT] commit" >> "$LOG_FILE"
git commit -m "auto update $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE" 2>&1 || echo "no commit" >> "$LOG_FILE"

echo "[GIT] push" >> "$LOG_FILE"
git push -f origin main >> "$LOG_FILE" 2>&1

# -----------------------
# 終了ログ
# -----------------------
echo "END: $(date)" >> "$LOG_FILE"
echo "==============================" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"