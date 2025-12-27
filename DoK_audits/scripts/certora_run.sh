#!/usr/bin/env bash
set -euo pipefail

CONF="${1:-}"
if [[ -z "$CONF" ]]; then
  echo "Usage: $0 path/to/run.conf [--rule RULE_NAME] [--method METHOD_NAME]"
  exit 1
fi

# Parse optional arguments
RULE_ARG=""
METHOD_ARG=""
shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --rule)
      RULE_ARG="--rule $2"
      shift 2
      ;;
    --method)
      METHOD_ARG="--method $2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Require secrets from .env.local (never inline)
if [[ -f ".env.local" ]]; then
  set -a
  source ".env.local"
  set +a
fi

: "${CERTORAKEY:?CERTORAKEY not set (put it in .env.local)}"

mkdir -p certora/out
LOG_FILE="certora/out/$(basename "$CONF" .conf).log"
echo "[*] certoraRun $CONF $RULE_ARG $METHOD_ARG"
certoraRun "$CONF" $RULE_ARG $METHOD_ARG | tee "$LOG_FILE"

# Generate summary if there are failures
if grep -q "FAILED\|VIOLATED" "$LOG_FILE" 2>/dev/null; then
  echo "[*] Generating triage summary..."
  ./scripts/certora_triage.sh "$LOG_FILE" > "certora/out/summary.md" 2>/dev/null || true
fi