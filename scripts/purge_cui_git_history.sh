#!/bin/bash
# Purge NASA RDRE CUI blobs from local git history. Safe: only .git is rewritten;
# working-tree files are never deleted. Full .git backup taken for rollback.
set -euo pipefail
cd /Users/exomac/.openclaw/workspace

TS=$(date +%Y%m%d-%H%M%S)
BK="/tmp/exomac-git-backup-${TS}.tar"
F1="references/nasa-rdre-data-usage-agreement.doc"
F2="references/teasley-nasa-rdre-dev-2025.pdf"
B1="7a3602b66761896f59db037558265cf8a1c51be5"
B2="fc392899fe434ee743e537356dd39e286b9abf5e"

echo "=== 1) backup .git -> $BK ==="
tar -cf "$BK" .git
echo "backup size: $(du -h "$BK" | cut -f1)"

echo "=== 2) checkpoint commit of TRACKED changes only (clean tree for rewrite; skips unreadable untracked files) ==="
git commit -a -q --no-verify -m "WIP checkpoint before CUI git-history purge (${TS})" || echo "(nothing to commit)"

echo "=== 3) strip CUI paths from ALL history ==="
FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch --force --index-filter \
  "git rm -q --cached --ignore-unmatch '$F1' '$F2'" \
  --prune-empty --tag-name-filter cat -- --all

echo "=== 4) expire refs/reflog + gc (physically delete blobs) ==="
rm -rf .git/refs/original/
git reflog expire --expire=now --all
git gc --prune=now --aggressive 2>&1 | tail -2

echo "=== 5) VERIFY blobs gone ==="
FAIL=0
git cat-file -e "$B1" 2>/dev/null && { echo "BLOB1 STILL PRESENT - FAIL"; FAIL=1; } || echo "blob1 (usage-agreement) purged - OK"
git cat-file -e "$B2" 2>/dev/null && { echo "BLOB2 STILL PRESENT - FAIL"; FAIL=1; } || echo "blob2 (teasley-pdf) purged - OK"
git rev-list --all --objects 2>/dev/null | grep -iE "nasa-rdre-data-usage|teasley-nasa-rdre" && { echo "PATH STILL IN HISTORY - FAIL"; FAIL=1; } || echo "paths absent from all history - OK"

echo "=== 6) restore your uncommitted working state ==="
git reset --mixed HEAD~1 >/dev/null 2>&1
echo "working tree restored; uncommitted entries: $(git status --short | wc -l | tr -d ' ')"
ls "$F1" "$F2" 2>&1 | sed 's/.*No such file.*/NASA files absent from disk - OK/' | sort -u

if [ "$FAIL" = "0" ]; then
  rm -f "$BK"
  echo "=== SUCCESS: CUI fully purged from exomac (incl. git history). Backup deleted. ==="
else
  echo "=== VERIFICATION FAILED — .git backup KEPT at $BK for rollback. ==="
  exit 1
fi
