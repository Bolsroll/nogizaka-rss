#!/bin/bash

cd /Users/dig/nogi-rss

echo "=== START ==="
date

python3 main.py

# Git自動push
git add .
git commit -m "auto update" || echo "no changes"
git push origin main

echo "=== END ==="
