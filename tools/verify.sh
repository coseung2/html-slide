#!/usr/bin/env bash
# verify.sh — run everything that must pass before a deck is delivered.
#
#   1. every shipped deck passes the linter
#   2. the linter still detects what it claims (fixture self-test)
#   3. the motion behaviour checks pass in a live browser
#
# Usage: bash tools/verify.sh    (exit 0 = all green)
set -u
cd "$(dirname "$0")/.." || exit 2
PY=~/.venvs/pw/bin/python
[ -x "$PY" ] || PY=python3

fail=0

echo "== 1/3 deck lint =="
bash tools/lint_all.sh || fail=1

echo
echo "== 2/3 linter self-test =="
"$PY" tests/linter_selftest.py || fail=1

echo
echo "== 3/3 motion behaviour =="
"$PY" tests/motion_check.py || fail=1

echo
if [ "$fail" -eq 0 ]; then
  echo "ALL GREEN"
else
  echo "FAILURES PRESENT"
fi
exit "$fail"
