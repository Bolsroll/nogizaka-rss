#!/bin/bash

cd /Users/dig/nogi-rss || exit 1

echo "=== START ==="
date

# -----------------------
# スクレイピング
# -----------------------
python3 main.py
python3 make_member_xml.py

# -----------------------
# Git（強制上書き方式）
# -----------------------

rm -f .git/index.lock
rm -rf .git/rebase-merge

git add .

git commit -m "auto update $(date '+%Y-%m-%d %H:%M:%S')" || echo "no commit"

# 👇これが最重要
git push -f origin main

echo "=== END ==="