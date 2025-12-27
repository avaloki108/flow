#!/usr/bin/env bash
# Triage helper for Certora counterexamples
# Usage: ./scripts/certora_triage.sh certora/out/<conf>.log

LOG_FILE="${1:-}"
[[ -z "$LOG_FILE" ]] && {
  echo "Usage: $0 <log_file>"
  exit 1
}

[[ -f "$LOG_FILE" ]] || {
  echo "Error: $LOG_FILE not found"
  exit 1
}

echo "# Certora Triage Summary"
echo ""
echo "Generated from: $(basename "$LOG_FILE")"
echo "Date: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
echo ""

# Extract failing rules
FAILING_RULES=$(grep -E "FAILED|VIOLATED" "$LOG_FILE" | grep -oE "rule [a-zA-Z0-9_]+" | sort -u || true)

if [[ -z "$FAILING_RULES" ]]; then
  echo "✅ No failing rules found."
  exit 0
fi

echo "## Failing Rules"
echo ""
for rule in $FAILING_RULES; do
  rule_name=$(echo "$rule" | awk '{print $2}')
  echo "### $rule_name"
  echo ""
  echo "- **Status**: ❌ FAILED"
  echo "- **Classification**: ⚠️  Needs triage"
  echo ""
  echo "#### Triage Steps:"
  echo "1. Reproduce: \`certoraRun certora/confs/<Contract>.conf --rule $rule_name\`"
  echo "2. Classify:"
  echo "   - [ ] Real bug (exploit path exists)"
  echo "   - [ ] Missing assumption (ERC20/token behavior)"
  echo "   - [ ] Model mismatch (time/pause semantics)"
  echo "3. Fix:"
  echo "   - [ ] Add require precondition"
  echo "   - [ ] Adjust spec assumptions"
  echo "   - [ ] Generate Foundry PoC (if real bug)"
  echo ""
done

echo "## Recommendations"
echo ""
echo "- Rerun failing rules individually: \`--rule <rule_name>\`"
echo "- Focus on CRITICAL rules first"
echo "- Check counterexamples in Certora dashboard"
echo "- Update spec assumptions if needed"