#!/usr/bin/env bash
# Run every automated check of the package (task Section 7). Usage: bash scripts/check_all.sh [--fast] [--with-mermaid] [--with-exports]
# --fast sets TROMOX_FAST_TESTS=1: the tests marked `slow` (real Chrome, real npx, a uvicorn
# subprocess) are skipped, so every check still runs but the whole thing lands in ~20 s.
# It combines with --with-mermaid / --with-exports, which ask for rendering explicitly and are unaffected.
# No pipes around the test commands: a pipe would swallow the exit code.
set -u
cd "$(dirname "$0")/.."
PY=.venv/bin/python
status=0
run() { echo; echo "=== $* ==="; "$@"; local rc=$?; if [ $rc -ne 0 ]; then echo ">>> exit $rc"; status=1; fi; }

# Parsed before the tests run, unlike the rendering flags below.
for flag in "$@"; do
  case "$flag" in --fast) export TROMOX_FAST_TESTS=1; echo "--fast: TROMOX_FAST_TESTS=1（跳过 slow 标记的用例）" ;; esac
done

run $PY scripts/gen_schema_artifacts.py --check
run $PY 03-whatsapp/cost_model.py --check
run $PY scripts/collect_open_questions.py --check
run $PY scripts/check_repo.py
run $PY -m pytest -q tests
( cd 04-eval && ../.venv/bin/python -m pytest -q ); rc=$?; [ $rc -ne 0 ] && { echo ">>> 04-eval pytest exit $rc"; status=1; }
( cd 05-integration/webhook-service && ../../.venv/bin/python -m pytest -q ); rc=$?; [ $rc -ne 0 ] && { echo ">>> webhook-service pytest exit $rc"; status=1; }
for flag in "$@"; do
  case "$flag" in
    --with-mermaid) run $PY scripts/check_mermaid.py ;;
    --with-exports) run $PY scripts/export_client_docs.py ;;
  esac
done
echo; [ $status -eq 0 ] && echo "ALL CHECKS PASSED" || echo "SOME CHECKS FAILED"
exit $status
