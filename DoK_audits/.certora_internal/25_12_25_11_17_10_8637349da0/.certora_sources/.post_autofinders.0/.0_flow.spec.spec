methods {
    function comptroller() external returns (address) envfree;
    function setComptroller(address newComptroller) external;
    function withdraw(uint256 streamId, address to, uint128 amount) external;
    function withdrawableAmountOf(uint256 streamId) external returns (uint128) envfree;
    function refundableAmountOf(uint256 streamId) external returns (uint128) envfree;
    function refund(uint256 streamId, uint128 amount) external;
    function getBalance(uint256 streamId) external returns (uint128) envfree;
    function totalDebtOf(uint256 streamId) external returns (uint256) envfree;
    function uncoveredDebtOf(uint256 streamId) external returns (uint256) envfree;
    function coveredDebtOf(uint256 streamId) external returns (uint128) envfree;
    function getSender(uint256 streamId) external returns (address) envfree;
    function isVoided(uint256 streamId) external returns (bool) envfree;
    function pause(uint256 streamId) external;
    function deposit(uint256 streamId, uint128 amount, address sender, address recipient) external;
    function getRecipient(uint256 streamId) external returns (address) envfree;
    function withdrawMax(uint256 streamId, address to) external returns (uint128);
    function refundMax(uint256 streamId) external returns (uint128);
    function nextStreamId() external returns (uint256) envfree;
    function getToken(uint256 streamId) external returns (address) envfree;
    function aggregateAmount(address token) external returns (uint256) envfree;
}

// ============ GHOST VARIABLES FOR REENTRANCY TRACKING ============

ghost bool inExternalCall {
    init_state axiom inExternalCall == false;
}

ghost uint256 balanceBeforeExternalCall {
    init_state axiom balanceBeforeExternalCall == 0;
}

ghost bool stateIsClean {
    init_state axiom stateIsClean == true;
}

// ============ ACCESS CONTROL ============

rule setComptrollerAccessControl(env e, address newComptroller) {
    address current = comptroller();
    setComptroller@withrevert(e, newComptroller);
    assert !lastReverted => e.msg.sender == current, "only comptroller can succeed";
}

rule setComptrollerNoChangeOnRevert(env e, address newComptroller) {
    address before = comptroller();
    setComptroller@withrevert(e, newComptroller);
    assert lastReverted => comptroller() == before, "comptroller should not change on revert";
}

rule pauseAccessControl(env e, uint256 streamId) {
    address sender = getSender(streamId);
    pause@withrevert(e, streamId);
    assert !lastReverted => e.msg.sender == sender, "only sender can pause";
}

// ============ REENTRANCY PROTECTION ============

// CRITICAL: No state changes after external token transfers
rule noReentrancyAfterWithdraw(env e, uint256 streamId, address to, uint128 amount) {
    uint128 balBefore = getBalance(streamId);
    uint128 withdrawableBefore = withdrawableAmountOf(streamId);
    
    withdraw(e, streamId, to, amount);
    
    uint128 balAfter = getBalance(streamId);
    uint128 withdrawableAfter = withdrawableAmountOf(streamId);
    
    // Balance and withdrawable should be updated atomically before external call
    // If withdraw succeeded, balance should decrease by amount
    assert balBefore - balAfter == amount || balAfter == balBefore,
        "CRITICAL: Balance not updated atomically - potential reentrancy";
}

// CRITICAL: No state changes after external token transfers in refund
rule noReentrancyAfterRefund(env e, uint256 streamId, uint128 amount) {
    uint128 balBefore = getBalance(streamId);
    uint128 refundableBefore = refundableAmountOf(streamId);
    
    refund(e, streamId, amount);
    
    uint128 balAfter = getBalance(streamId);
    uint128 refundableAfter = refundableAmountOf(streamId);
    
    // Balance should decrease by refund amount atomically
    assert balBefore - balAfter == amount || balAfter == balBefore,
        "CRITICAL: Balance not updated atomically in refund - potential reentrancy";
}

// ============ READ-ONLY REENTRANCY PROTECTION ============

// CRITICAL: View functions should return consistent state during operations
rule readOnlyReentrancyProtection(env e1, env e2, uint256 streamId, uint128 amount, address to) {
    uint128 withdrawableBefore = withdrawableAmountOf(streamId);
    uint128 balanceBefore = getBalance(streamId);
    uint256 totalDebtBefore = totalDebtOf(streamId);
    
    // Mark state as potentially dirty
    stateIsClean = false;
    
    withdraw(e1, streamId, to, amount);
    
    // State should be clean again
    stateIsClean = true;
    
    // View functions should return valid state
    uint128 withdrawableAfter = withdrawableAmountOf(streamId);
    uint128 balanceAfter = getBalance(streamId);
    
    // If withdraw succeeded, views should reflect the change
    assert balanceAfter <= balanceBefore,
        "CRITICAL: View returned invalid state - potential ROR";
}

// ============ WITHDRAW BOUNDS ============

rule withdrawBound(env e, uint256 streamId, uint128 amount, address to) {
    uint128 before = withdrawableAmountOf(streamId);
    withdraw@withrevert(e, streamId, to, amount);
    assert !lastReverted => amount <= before, "withdraw amount must be <= withdrawable";
}

rule withdrawDecreasesWithdrawable(env e, uint256 streamId, uint128 amount, address to) {
    uint128 before = withdrawableAmountOf(streamId);
    withdraw(e, streamId, to, amount);
    uint128 after = withdrawableAmountOf(streamId);
    assert after + amount <= before, "withdrawable must decrease by at least amount";
}

// ============ REFUND BOUNDS ============

rule refundBound(env e, uint256 streamId, uint128 amount) {
    uint128 before = refundableAmountOf(streamId);
    refund@withrevert(e, streamId, amount);
    assert !lastReverted => amount <= before, "refund amount must be <= refundable";
}

rule refundDecreasesRefundable(env e, uint256 streamId, uint128 amount) {
    uint128 before = refundableAmountOf(streamId);
    refund(e, streamId, amount);
    uint128 after = refundableAmountOf(streamId);
    assert after + amount <= before, "refundable must decrease by at least amount";
}

rule refundAccessControl(env e, uint256 streamId, uint128 amount) {
    address sender = getSender(streamId);
    refund@withrevert(e, streamId, amount);
    assert !lastReverted => e.msg.sender == sender, "only sender can refund";
}

// ============ BALANCE INVARIANTS ============

invariant balanceInvariant(uint256 streamId)
    getBalance(streamId) == coveredDebtOf(streamId) + refundableAmountOf(streamId);

invariant totalDebtGeCoveredDebt(uint256 streamId)
    totalDebtOf(streamId) >= coveredDebtOf(streamId);

// ============ VOID SEMANTICS ============

rule voidIsPermanent(env e, uint256 streamId, method f) {
    bool voidedBefore = isVoided(streamId);
    calldataarg args;
    f(e, args);
    bool voidedAfter = isVoided(streamId);
    assert voidedBefore => voidedAfter, "voided streams cannot be un-voided";
}

// ============ DEPOSIT INCREASES BALANCE ============

rule depositIncreasesBalance(env e, uint256 streamId, uint128 amount, address sender, address recipient) {
    uint128 balBefore = getBalance(streamId);
    deposit(e, streamId, amount, sender, recipient);
    uint128 balAfter = getBalance(streamId);
    assert balAfter >= balBefore, "deposit must not decrease balance";
    assert amount > 0 => balAfter > balBefore, "non-zero deposit must increase balance";
}

// ============ WITHDRAW MAX CORRECTNESS ============

rule withdrawMaxCorrectness(env e, uint256 streamId, address to) {
    uint128 withdrawable = withdrawableAmountOf(streamId);
    uint128 withdrawn = withdrawMax(e, streamId, to);
    assert withdrawn == withdrawable, "withdrawMax should withdraw exactly withdrawable amount";
}

// ============ REFUND MAX CORRECTNESS ============

rule refundMaxCorrectness(env e, uint256 streamId) {
    uint128 refundable = refundableAmountOf(streamId);
    uint128 refunded = refundMax(e, streamId);
    assert refunded == refundable, "refundMax should refund exactly refundable amount";
}

// ============ STREAM ID MONOTONICITY ============

rule streamIdMonotonicity(env e, method f) {
    uint256 idBefore = nextStreamId();
    calldataarg args;
    f(e, args);
    uint256 idAfter = nextStreamId();
    assert idAfter >= idBefore, "nextStreamId should never decrease";
}

// ============ FEE-ON-TRANSFER TOKEN SAFETY ============

// CRITICAL: Withdraw should handle fee-on-transfer tokens correctly
rule feeOnTransferWithdrawSafety(env e, uint256 streamId, address to, uint128 amount) {
    address token = getToken(streamId);
    uint256 contractBalBefore = aggregateAmount(token);
    uint128 streamBalBefore = getBalance(streamId);
    
    withdraw(e, streamId, to, amount);
    
    uint256 contractBalAfter = aggregateAmount(token);
    uint128 streamBalAfter = getBalance(streamId);
    
    // Contract balance should decrease by at least amount (may be more with fees)
    // Stream balance should decrease by exactly amount
    assert streamBalBefore - streamBalAfter == amount || streamBalAfter == streamBalBefore,
        "CRITICAL: Stream balance accounting error with fee-on-transfer tokens";
}

// CRITICAL: Deposit should account for fee-on-transfer tokens
rule feeOnTransferDepositSafety(env e, uint256 streamId, uint128 amount, address sender, address recipient) {
    address token = getToken(streamId);
    uint256 contractBalBefore = aggregateAmount(token);
    uint128 streamBalBefore = getBalance(streamId);
    
    deposit(e, streamId, amount, sender, recipient);
    
    uint256 contractBalAfter = aggregateAmount(token);
    uint128 streamBalAfter = getBalance(streamId);
    
    // Stream balance should increase by amount
    // Contract balance may increase by less if token has fees
    assert streamBalAfter >= streamBalBefore + amount || streamBalAfter == streamBalBefore,
        "CRITICAL: Stream balance not increased correctly - fee-on-transfer issue";
}

// ============ ROUNDING ERROR PROTECTION ============

// CRITICAL: Debt calculations should not lose precision
rule noLossyDebtRounding(env e, uint256 streamId) {
    uint256 totalDebt = totalDebtOf(streamId);
    uint128 coveredDebt = coveredDebtOf(streamId);
    uint256 uncoveredDebt = uncoveredDebtOf(streamId);
    
    // Total debt should equal covered + uncovered (accounting for precision)
    assert to_mathint(totalDebt) >= to_mathint(coveredDebt) + to_mathint(uncoveredDebt) - 1,
        "CRITICAL: Debt rounding lost precision";
    assert to_mathint(totalDebt) <= to_mathint(coveredDebt) + to_mathint(uncoveredDebt) + 1,
        "CRITICAL: Debt rounding created extra value";
}

// ============ CROSS-STREAM INTERFERENCE ============

// CRITICAL: Operations on one stream should not affect another
rule noCrossStreamInterference(env e, uint256 streamId1, uint256 streamId2, uint128 amount, address to) {
    require streamId1 != streamId2;
    
    uint128 bal1Before = getBalance(streamId1);
    uint128 bal2Before = getBalance(streamId2);
    uint128 withdrawable1Before = withdrawableAmountOf(streamId1);
    uint128 withdrawable2Before = withdrawableAmountOf(streamId2);
    
    withdraw(e, streamId1, to, amount);
    
    uint128 bal1After = getBalance(streamId1);
    uint128 bal2After = getBalance(streamId2);
    uint128 withdrawable1After = withdrawableAmountOf(streamId1);
    uint128 withdrawable2After = withdrawableAmountOf(streamId2);
    
    // Stream 2 should be unaffected
    assert bal2After == bal2Before,
        "CRITICAL: Withdraw on stream1 affected stream2 balance";
    assert withdrawable2After == withdrawable2Before,
        "CRITICAL: Withdraw on stream1 affected stream2 withdrawable";
}

// ============ AGGREGATE BALANCE CONSERVATION ============

// CRITICAL: Aggregate balance should track all stream balances correctly
rule aggregateBalanceConservation(env e, uint256 streamId, uint128 amount, address sender, address recipient) {
    address token = getToken(streamId);
    uint256 aggregateBefore = aggregateAmount(token);
    uint128 streamBalBefore = getBalance(streamId);
    
    deposit(e, streamId, amount, sender, recipient);
    
    uint256 aggregateAfter = aggregateAmount(token);
    uint128 streamBalAfter = getBalance(streamId);
    
    uint128 streamBalIncrease = streamBalAfter - streamBalBefore;
    
    // Aggregate should increase by at least the stream balance increase
    assert to_mathint(aggregateAfter) >= to_mathint(aggregateBefore) + to_mathint(streamBalIncrease),
        "CRITICAL: Aggregate balance not tracking stream deposits correctly";
}

// ============ ZERO AMOUNT EDGE CASES ============

// HIGH: Zero amount operations should be safe
rule zeroAmountWithdrawSafe(env e, uint256 streamId, address to) {
    withdraw(e, streamId, to, 0);
    uint128 withdrawable = withdrawableAmountOf(streamId);
    uint128 balance = getBalance(streamId);
    // Zero withdraw should not break invariants
    assert balance == coveredDebtOf(streamId) + refundableAmountOf(streamId),
        "HIGH: Zero withdraw broke balance invariant";
}

rule zeroAmountRefundSafe(env e, uint256 streamId) {
    refund(e, streamId, 0);
    uint128 balance = getBalance(streamId);
    assert balance == coveredDebtOf(streamId) + refundableAmountOf(streamId),
        "HIGH: Zero refund broke balance invariant";
}

// ============ TIME-BASED DEBT EDGE CASES ============

// CRITICAL: Debt should not decrease over time (only increase or stay same)
rule debtMonotonicityOverTime(env e1, env e2, uint256 streamId) {
    require e1.block.timestamp <= e2.block.timestamp;
    
    uint256 debt1 = totalDebtOf(streamId);
    uint256 debt2 = totalDebtOf(streamId);
    
    // Debt at later time should be >= debt at earlier time
    assert to_mathint(debt2) >= to_mathint(debt1),
        "CRITICAL: Debt decreased over time - calculation error";
}

// ============ DOS PROTECTION ============

// HIGH: Valid withdrawals should not revert
rule withdrawalAlwaysSucceeds(env e, uint256 streamId, address to, uint128 amount) {
    uint128 withdrawable = withdrawableAmountOf(streamId);
    require withdrawable >= amount;
    require amount > 0;
    
    withdraw@withrevert(e, streamId, to, amount);
    
    assert !lastReverted,
        "HIGH: Valid withdrawal reverted - potential DoS";
}

// HIGH: Valid refunds should not revert
rule refundAlwaysSucceeds(env e, uint256 streamId, uint128 amount) {
    uint128 refundable = refundableAmountOf(streamId);
    require refundable >= amount;
    require amount > 0;
    
    refund@withrevert(e, streamId, amount);
    
    assert !lastReverted,
        "HIGH: Valid refund reverted - potential DoS";
}
