#!/usr/bin/env bash
# Verify all financial rules for SablierFlow in organized batches
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== SablierFlow Financial Contracts Verification ==="
echo "Main Contract: src/SablierFlow.sol"
echo "Covered Components:"
echo "  - SablierFlowState (abstract, inherited)"
echo "  - Helpers library (internal functions)"
echo ""

# Batch 1: Access Control
echo "[*] Batch 1: Access Control Rules"
ACCESS_CONTROL_RULES=("setComptrollerAccessControl" "pauseAccessControl" "refundAccessControl")
for rule in "${ACCESS_CONTROL_RULES[@]}"; do
    echo "  - $rule"
done
echo ""

# Batch 2: Reentrancy Protection
echo "[*] Batch 2: Reentrancy Protection (CRITICAL)"
REENTRANCY_RULES=("noReentrancyAfterWithdraw" "noReentrancyAfterRefund" "readOnlyReentrancyProtection")
for rule in "${REENTRANCY_RULES[@]}"; do
    echo "  - $rule"
done
echo ""

# Batch 3: Withdraw/Refund Bounds
echo "[*] Batch 3: Withdraw/Refund Bounds (CRITICAL)"
BOUNDS_RULES=("withdrawBound" "withdrawDecreasesWithdrawable" "refundBound" "refundDecreasesRefundable")
for rule in "${BOUNDS_RULES[@]}"; do
    echo "  - $rule"
done
echo ""

# Batch 4: Balance & Debt Invariants
echo "[*] Batch 4: Balance & Debt Invariants (CRITICAL)"
INVARIANT_RULES=("balanceInvariant" "totalDebtGeCoveredDebt" "debtMonotonicityOverTime")
for rule in "${INVARIANT_RULES[@]}"; do
    echo "  - $rule"
done
echo ""

# Batch 5: Financial Safety
echo "[*] Batch 5: Financial Safety (CRITICAL)"
SAFETY_RULES=("aggregateBalanceConservation" "noLossyDebtRounding" "noCrossStreamInterference" "feeOnTransferWithdrawSafety" "feeOnTransferDepositSafety")
for rule in "${SAFETY_RULES[@]}"; do
    echo "  - $rule"
done
echo ""

echo "=== Running Full Verification ==="
./scripts/certora_run.sh certora/confs/SablierFlow.conf

echo ""
echo "=== Verification Complete ==="
echo "Check results at: certora/out/SablierFlow.log"
echo "Triage failures: ./scripts/certora_triage.sh certora/out/SablierFlow.log"
