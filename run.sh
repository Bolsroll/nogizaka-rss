#!/bin/bash

# 環境変数（これ超重要）
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin

cd /Users/dig/nogi-rss || exit 1

echo "=== START ==="
date

/usr/bin/python3 main.py
/usr/bin/python3 make_member_xml.py

/usr/bin/git add .
/usr/bin/git commit -m "auto update" || echo "no changes"
/usr/bin/git push

echo "=== END ==="
date
