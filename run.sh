#!/bin/bash

# -----------------------
# 設定
# -----------------------
LOG_FILE="/Users/dig/nogi-rss/cron.log"
PYTHON="/Library/Frameworks/Python.framework/Versions/3.11/bin/python3"

# PATH問題対策
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# -----------------------
# ログ初期化（毎回上書き）
# -----------------------
: > "$LOG_FILE"

# -----------------------
# 開始ログ
# -----------------------
echo "==============================" >> "$LOG_FILE"
echo "START: $(date)" >> "$LOG_FILE"

# -----------------------
# 環境ログ（重要）
# -----------------------
echo "[ENV] which python: $(which python3)" >> "$LOG_FILE"
echo "[ENV] using python: $PYTHON" >> "$LOG_FILE"
$PYTHON --version >> "$LOG_FILE" 2>&1

# -----------------------
# ディレクトリ移動
# -----------------------
cd /Users/dig/nogi-rss || {
    echo "❌ cd失敗" >> "$LOG_FILE"
    exit 1
}

# -----------------------
# Playwright確認（自動修復）
# -----------------------
echo "[INIT] playwright install check" >> "$LOG_FILE"
$PYTHON -m playwright install >> "$LOG_FILE" 2>&1

# -----------------------
# スクレイピング
# -----------------------
echo "[RUN] main.py" >> "$LOG_FILE"
$PYTHON main.py >> "$LOG_FILE" 2>&1

# -----------------------
# メンバーXML生成
# -----------------------
echo "[RUN] make_member_xml.py" >> "$LOG_FILE"
$PYTHON make_member_xml.py >> "$LOG_FILE" 2>&1

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