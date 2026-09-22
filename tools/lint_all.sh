#!/usr/bin/env bash
# Lint every shipped deck and report a single pass/fail total.
set -u
cd "$(dirname "$0")/.." || exit 2
PY=${PYTHON:-$HOME/.venvs/pw/bin/python}
[ -x "$PY" ] || PY=python3
fail=0
for f in examples/*.html motion/patterns/*.html templates/*.html; do
  # Modular decks have a separate contract and are verified by verify_modular.sh.
  if grep -q 'data-engine="html-slide-modular-v1"' "$f"; then
    continue
  fi
  out=$("$PY" tools/slide_lint.py "$f" 2>&1)
  rc=$?
  printf '%-42s rc=%s %s\n' "$(basename "$f")" "$rc" \
    "$(printf '%s' "$out" | grep -E 'PASS|FAIL' | tail -1)"
  [ "$rc" -ne 0 ] && fail=$((fail + 1))
done
echo "TOTAL_FAILING=$fail"
exit "$fail"
