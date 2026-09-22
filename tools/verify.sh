#!/usr/bin/env bash
# verify.sh — run everything that must pass before a deck is delivered.
#
#   1. every shipped deck passes the linter
#   2. the linter still detects what it claims (fixture self-test)
#   3. the motion behaviour checks pass in a live browser
#   4. shared presenter and template regressions pass
#   5. Korean-copy linter self-tests pass
#   6. modular compiler, runtime and generated-deck checks pass
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
echo "== 4/5 presenter and template regressions =="
"$PY" tests/template_runtime_check.py || fail=1

echo
echo "== 5/5 Korean copy lint self-test =="
"$PY" tests/copy_lint_selftest.py || fail=1

echo
echo "== 6/6 modular composition and browser QA =="
bash tools/verify_modular.sh || fail=1

echo
if [ "$fail" -eq 0 ]; then
  echo "ALL GREEN"
else
  echo "FAILURES PRESENT"
fi
exit "$fail"
