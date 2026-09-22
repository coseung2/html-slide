#!/usr/bin/env bash
# Canonical modular verification; generated reports remain outside source control.
set -eu
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
"$PY" -m unittest discover -s tests -p 'test_modular.py'
"$PY" tests/modular_runtime_check.py
"$PY" tools/compose_deck.py build examples/modular-showcase.json --out dist/modular-showcase.html
"$PY" tools/verify_modular.py dist/modular-showcase.html --out dist/modular-qa
for f in examples/*.html; do
  if grep -q 'data-engine="html-slide-modular-v1"' "$f"; then
    "$PY" tools/verify_modular.py "$f" --out "dist/shipped-qa/$(basename "$f" .html)"
  fi
done
