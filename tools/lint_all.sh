#!/usr/bin/env bash
# Lint every shipped deck and report a single pass/fail total.
set -u
cd "$(dirname "$0")/.." || exit 2
PY=~/.venvs/pw/bin/python
fail=0
for f in examples/*.html motion/patterns/*.html; do
  out=$("$PY" tools/slide_lint.py "$f" 2>&1)
  rc=$?
  printf '%-42s rc=%s %s\n' "$(basename "$f")" "$rc" \
    "$(printf '%s' "$out" | grep -E 'PASS|FAIL' | tail -1)"
  [ "$rc" -ne 0 ] && fail=$((fail + 1))
done
echo "TOTAL_FAILING=$fail"
exit "$fail"
