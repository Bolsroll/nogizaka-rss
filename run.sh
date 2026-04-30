#!/bin/bash

set -e  # エラーで即停止（重要）

# -----------------------
# 設定
# -----------------------
BASE_DIR="/Users/dig/nogi-rss"
LOG_FILE="$BASE_DIR/cron.log"
PYTHON="/Library/Frameworks/Python.framework/Versions/3.11/bin/python3"

# 環境固定（超重要）
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export LANG="ja_JP.UTF-8"
export LC_ALL="ja_JP.UTF-8"

# -----------------------
# ログ初期化
# -----------------------
: > "$LOG_FILE"

echo "==============================" >> "$LOG_FILE"
echo "START: $(date)" >> "$LOG_FILE"

# -----------------------
# 環境ログ
# -----------------------
echo "[ENV] which python: $(which python3)" >> "$LOG_FILE"
echo "[ENV] using python: $PYTHON" >> "$LOG_FILE"
$PYTHON --version >> "$LOG_FILE" 2>&1

echo "[ENV] pwd before cd: $(pwd)" >> "$LOG_FILE"

# -----------------------
# ディレクトリ移動
# -----------------------
cd "$BASE_DIR" || {
    echo "❌ cd失敗" >> "$LOG_FILE"
    exit 1
}

echo "[ENV] pwd after cd: $(pwd)" >> "$LOG_FILE"

# -----------------------
# Playwright確認（軽量チェックに変更）
# -----------------------
echo "[INIT] playwright check" >> "$LOG_FILE"
$PYTHON -m playwright --version >> "$LOG_FILE" 2>&1 || {
    echo "⚠️ playwright再インストール" >> "$LOG_FILE"
    $PYTHON -m playwright install >> "$LOG_FILE" 2>&1
}

# -----------------------
# スクレイピング
# -----------------------
echo "[RUN] main.py" >> "$LOG_FILE"
$PYTHON main.py >> "$LOG_FILE" 2>&1

# -----------------------
# XML生成
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