#!/usr/bin/env bash
# Verify critical financial rules for SablierFlow
set -euo pipefail

cd "$(dirname "$0")/.."

CRITICAL_RULES=(
    "withdrawBound"
    "refundBound"
    "balanceInvariant"
    "totalDebtGeCoveredDebt"
    "noReentrancyAfterWithdraw"
    "noReentrancyAfterRefund"
    "debtMonotonicityOverTime"
    "aggregateBalanceConservation"
    "noLossyDebtRounding"
    "noCrossStreamInterference"
)

echo "=== Running Critical Financial Rules Verification ==="
echo ""

for rule in "${CRITICAL_RULES[@]}"; do
    echo "[*] Verifying rule: $rule"
    ./scripts/certora_run.sh certora/confs/SablierFlow.conf --rule "$rule" 2>&1 | tee "certora/out/critical-${rule}.log" | tail -5
    echo ""
done

echo "=== Critical Rules Verification Complete ==="
