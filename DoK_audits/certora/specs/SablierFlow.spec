import "certora/specs/common/Env.spec";
import "certora/specs/common/ERC20Helpers.spec";

/**
 * Audit-grade starter spec for SablierFlow.
 * 
 * Flow Protocol: Open-ended debt tracking with rate-per-second streaming.
 * Key features: top-ups, pause, void, refund, withdraw.
 * 
 * Core invariants:
 * - Debt monotonicity when running (increases linearly with time)
 * - Pause stops accrual
 * - Withdraw <= covered debt (insolvency protection)
 * - Refund correctness
 */
spec SablierFlowSpec {

  // ============ METHODS ============
  // Add method declarations as needed. Example:
  // function withdraw(uint256 streamId, address to, uint128 amount) external;
  // function coveredDebtOf(uint256 streamId) external returns (uint128);
  // function totalDebtOf(uint256 streamId) external returns (uint256);
  // function pause(uint256 streamId) external;
  // function deposit(uint256 streamId, uint128 amount, address sender, address recipient) external;
  // function getRecipient(uint256 streamId) external returns (address);
  // function isPaused(uint256 streamId) external returns (bool);

  // ============ INVARIANTS ============

  // CRITICAL: Withdraw amount must not exceed covered debt
  // invariant invariant_withdraw_bounded_by_covered_debt:
  //   forall uint256 streamId, address to, uint128 amount.
  //     withdraw(streamId, to, amount) =>
  //     amount <= coveredDebtOf(streamId);

  // CRITICAL: Total debt must be >= covered debt
  // invariant invariant_total_debt_ge_covered:
  //   forall uint256 streamId.
  //     totalDebtOf(streamId) >= coveredDebtOf(streamId);

  // ============ RULES ============

  // CRITICAL: Withdraw must not exceed covered debt
  rule rule_withdraw_does_not_exceed_covered_debt(env e, uint256 streamId, address to, uint128 amount) {
    require amount > 0;
    require isStream(streamId); // Add isStream method if available
    uint128 preCovered = coveredDebtOf(streamId);
    withdraw@withrevert(e, streamId, to, amount);
    assert !lastReverted => amount <= preCovered,
      "CRITICAL: withdraw amount exceeds covered debt";
  }

  // CRITICAL: Pause must stop debt accrual
  rule rule_pause_stops_debt_accrual(env e1, env e2, uint256 streamId) {
    require e1.block.timestamp < e2.block.timestamp;
    require isStream(streamId);
    require !isPaused(streamId);
    uint256 debtBefore = totalDebtOf(e1, streamId);
    pause(e1, streamId);
    uint256 debtAfterPause = totalDebtOf(e1, streamId);
    // Time advances, but stream is paused
    uint256 debtAfterTime = totalDebtOf(e2, streamId);
    assert debtAfterTime == debtAfterPause,
      "CRITICAL: Debt increased while paused";
  }

  // HIGH: Debt monotonicity when running (not paused)
  rule rule_debt_monotonicity_when_running(env e1, env e2, uint256 streamId) {
    require e1.block.timestamp <= e2.block.timestamp;
    require isStream(streamId);
    require !isPaused(streamId);
    uint256 debt1 = totalDebtOf(e1, streamId);
    uint256 debt2 = totalDebtOf(e2, streamId);
    assert to_mathint(debt2) >= to_mathint(debt1),
      "HIGH: Debt decreased over time when running";
  }

  // HIGH: Public withdraw restriction (to == recipient OR caller is recipient/approved)
  rule rule_withdraw_public_restriction(env e, uint256 streamId, address to, uint128 amount) {
    require isStream(streamId);
    require amount > 0;
    address recipient = getRecipient(streamId);
    withdraw@withrevert(e, streamId, to, amount);
    // If to != recipient, caller must be recipient or approved
    assert !lastReverted => (to == recipient || e.msg.sender == recipient || isApprovedForAll(recipient, e.msg.sender)),
      "HIGH: Public withdraw restriction violated";
  }

  // MEDIUM: Refund correctness (doesn't steal owed amounts)
  rule rule_refund_correctness(env e, uint256 streamId, uint128 amount) {
    require isStream(streamId);
    require amount > 0;
    uint128 coveredBefore = coveredDebtOf(streamId);
    uint256 totalDebtBefore = totalDebtOf(streamId);
    refund@withrevert(e, streamId, amount);
    if (!lastReverted) {
      uint128 coveredAfter = coveredDebtOf(streamId);
      uint256 totalDebtAfter = totalDebtOf(streamId);
      // Refund should not affect covered debt incorrectly
      assert to_mathint(coveredAfter) + to_mathint(amount) <= to_mathint(coveredBefore) + to_mathint(totalDebtBefore - totalDebtAfter),
        "MEDIUM: Refund accounting error";
    }
  }

}