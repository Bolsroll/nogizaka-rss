#!/bin/bash

cd /Users/dig/nogi-rss

echo "=== START ==="
date

# 実行
python3 main.py

# Git反映
git add .
git commit -m "auto update"
git push origin main

echo "=== END ==="
