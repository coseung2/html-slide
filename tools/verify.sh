#!/usr/bin/env bash
# verify.sh — run everything that must pass before a deck is delivered.
#
#   1. every shipped deck passes the linter
#   2. the linter still detects what it claims (fixture self-test)
#   3. the motion behaviour checks pass in a live browser
#   4. sports media geometry and shared presenter regressions pass
#   5. Korean-copy linter self-tests pass
#
# Usage: bash tools/verify.sh    (exit 0 = all green)
set -u
cd "$(dirname "$0")/.." || exit 2
PY=${PYTHON:-$HOME/.venvs/pw/bin/python}
[ -x "$PY" ] || PY=python3
export PYTHON="$PY"

fail=0

echo "== 1/5 deck lint =="
bash tools/lint_all.sh || fail=1

echo
echo "== 2/5 linter self-test =="
"$PY" tests/linter_selftest.py || fail=1

echo
echo "== 3/5 motion behaviour =="
"$PY" tests/motion_check.py || fail=1

echo
echo "== 4/5 sports and presenter regressions =="
"$PY" tests/sports_check.py || fail=1

echo
echo "== 5/5 Korean copy lint self-test =="
"$PY" tests/copy_lint_selftest.py || fail=1

echo
if [ "$fail" -eq 0 ]; then
  echo "ALL GREEN"
else
  echo "FAILURES PRESENT"
fi
exit "$fail"
