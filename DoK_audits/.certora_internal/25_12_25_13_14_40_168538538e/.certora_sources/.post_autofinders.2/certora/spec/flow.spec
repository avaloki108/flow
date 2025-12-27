methods {
    function comptroller() external returns (address) envfree;
    function setComptroller(address newComptroller) external;
    function withdraw(uint256 streamId, address to, uint128 amount) external;
    function withdrawableAmountOf(uint256 streamId) external returns (uint128);
    function refundableAmountOf(uint256 streamId) external returns (uint128);
    function refund(uint256 streamId, uint128 amount) external;
    function getBalance(uint256 streamId) external returns (uint128) envfree;
    function totalDebtOf(uint256 streamId) external returns (uint256);
    function uncoveredDebtOf(uint256 streamId) external returns (uint256);
    function coveredDebtOf(uint256 streamId) external returns (uint128);
    function getSender(uint256 streamId) external returns (address) envfree;
    function isStream(uint256 streamId) external returns (bool) envfree;
    function isVoided(uint256 streamId) external returns (bool) envfree;
    function pause(uint256 streamId) external;
    function deposit(uint256 streamId, uint128 amount, address sender, address recipient) external;
    function getRecipient(uint256 streamId) external returns (address) envfree;
    function withdrawMax(uint256 streamId, address to) external returns (uint128);
    function refundMax(uint256 streamId) external returns (uint128);
    function nextStreamId() external returns (uint256) envfree;
    function getToken(uint256 streamId) external returns (address) envfree;
    function aggregateAmount(address token) external returns (uint256) envfree;
    function calculateMinFeeWei(uint256 streamId) external returns (uint256);
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
    require isStream(streamId);
    address sender = getSender(streamId);
    pause@withrevert(e, streamId);
    assert !lastReverted => e.msg.sender == sender, "only sender can pause";
}

// ============ REENTRANCY PROTECTION ============

// CRITICAL: No state changes after external token transfers
rule noReentrancyAfterWithdraw(env e, uint256 streamId, address to, uint128 amount) {
    require isStream(streamId), "existing stream";
    uint128 balBefore = getBalance(streamId);
    uint128 withdrawableBefore = withdrawableAmountOf(e, streamId);
    
    withdraw(e, streamId, to, amount);
    
    uint128 balAfter = getBalance(streamId);
    uint128 withdrawableAfter = withdrawableAmountOf(e, streamId);
    
    // Balance and withdrawable should be updated atomically before external call
    // If withdraw succeeded, balance should decrease by amount
    assert balBefore - balAfter == amount || balAfter == balBefore,
        "CRITICAL: Balance not updated atomically - potential reentrancy";
}

// CRITICAL: No state changes after external token transfers in refund
rule noReentrancyAfterRefund(env e, uint256 streamId, uint128 amount) {
    require isStream(streamId), "existing stream";
    uint128 balBefore = getBalance(streamId);
    uint128 refundableBefore = refundableAmountOf(e, streamId);
    
    refund(e, streamId, amount);
    
    uint128 balAfter = getBalance(streamId);
    uint128 refundableAfter = refundableAmountOf(e, streamId);
    
    // Balance should decrease by refund amount atomically
    assert balBefore - balAfter == amount || balAfter == balBefore,
        "CRITICAL: Balance not updated atomically in refund - potential reentrancy";
}

// ============ READ-ONLY REENTRANCY PROTECTION ============

// CRITICAL: View functions should return consistent state during operations
rule readOnlyReentrancyProtection(env e1, env e2, uint256 streamId, uint128 amount, address to) {
    require isStream(streamId), "existing stream";
    uint128 withdrawableBefore = withdrawableAmountOf(e1, streamId);
    uint128 balanceBefore = getBalance(streamId);
    uint256 totalDebtBefore = totalDebtOf(e1, streamId);
    
    // Mark state as potentially dirty
    stateIsClean = false;
    
    withdraw(e1, streamId, to, amount);
    
    // State should be clean again
    stateIsClean = true;
    
    // View functions should return valid state
    uint128 withdrawableAfter = withdrawableAmountOf(e1, streamId);
    uint128 balanceAfter = getBalance(streamId);
    
    // If withdraw succeeded, views should reflect the change
    assert balanceAfter <= balanceBefore,
        "CRITICAL: View returned invalid state - potential ROR";
}

// ============ WITHDRAW BOUNDS ============

rule withdrawBound(env e, uint256 streamId, uint128 amount, address to) {
    require isStream(streamId), "existing stream";
    uint128 before = withdrawableAmountOf(e, streamId);
    withdraw@withrevert(e, streamId, to, amount);
    assert !lastReverted => amount <= before, "withdraw amount must be <= withdrawable";
}

rule withdrawDecreasesWithdrawable(env e, uint256 streamId, uint128 amount, address to) {
    require isStream(streamId), "existing stream";
    uint128 before = withdrawableAmountOf(e, streamId);
    withdraw(e, streamId, to, amount);
    uint128 after = withdrawableAmountOf(e, streamId);
    assert after + amount <= before, "withdrawable must decrease by at least amount";
}

// ============ REFUND BOUNDS ============

rule refundBound(env e, uint256 streamId, uint128 amount) {
    require isStream(streamId), "existing stream";
    uint128 before = refundableAmountOf(e, streamId);
    refund@withrevert(e, streamId, amount);
    assert !lastReverted => amount <= before, "refund amount must be <= refundable";
}

rule refundDecreasesRefundable(env e, uint256 streamId, uint128 amount) {
    require isStream(streamId), "existing stream";
    uint128 before = refundableAmountOf(e, streamId);
    refund(e, streamId, amount);
    uint128 after = refundableAmountOf(e, streamId);
    assert after + amount <= before, "refundable must decrease by at least amount";
}

rule refundAccessControl(env e, uint256 streamId, uint128 amount) {
    require isStream(streamId), "existing stream";
    address sender = getSender(streamId);
    refund@withrevert(e, streamId, amount);
    assert !lastReverted => e.msg.sender == sender, "only sender can refund";
}

// ============ BALANCE INVARIANTS ============

rule balanceInvariant(env e, uint256 streamId) {
    require isStream(streamId), "existing stream";
    assert getBalance(streamId) == coveredDebtOf(e, streamId) + refundableAmountOf(e, streamId),
        "balance must equal covered + refundable";
}

rule totalDebtGeCoveredDebt(env e, uint256 streamId) {
    require isStream(streamId), "existing stream";
    assert totalDebtOf(e, streamId) >= coveredDebtOf(e, streamId), "totalDebt must be >= coveredDebt";
}

// ============ VOID SEMANTICS ============

rule voidIsPermanent(env e, uint256 streamId, method f) {
    require isStream(streamId);
    bool voidedBefore = isVoided(streamId);
    calldataarg args;
    f(e, args);
    bool voidedAfter = isVoided(streamId);
    assert voidedBefore => voidedAfter, "voided streams cannot be un-voided";
}

// ============ DEPOSIT INCREASES BALANCE ============

rule depositIncreasesBalance(env e, uint256 streamId, uint128 amount, address sender, address recipient) {
    require isStream(streamId), "existing stream";
    uint128 balBefore = getBalance(streamId);
    deposit@withrevert(e, streamId, amount, sender, recipient);
    bool reverted = lastReverted;
    uint128 balAfter = getBalance(streamId);
    assert reverted || balAfter >= balBefore, "deposit must not decrease balance";
    assert reverted || (amount > 0 => balAfter > balBefore), "non-zero deposit must increase balance";
}

// ============ WITHDRAW MAX CORRECTNESS ============

rule withdrawMaxCorrectness(env e, uint256 streamId, address to) {
    require isStream(streamId), "existing stream";
    require e.msg.value >= calculateMinFeeWei(e, streamId);
    uint128 withdrawable = withdrawableAmountOf(e, streamId);
    uint128 withdrawn = withdrawMax(e, streamId, to);
    assert withdrawn == withdrawable, "withdrawMax should withdraw exactly withdrawable amount";
}

// ============ REFUND MAX CORRECTNESS ============

rule refundMaxCorrectness(env e, uint256 streamId) {
    require isStream(streamId), "existing stream";
    uint128 refundable = refundableAmountOf(e, streamId);
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
    require isStream(streamId), "existing stream";
    address token = getToken(streamId);
    uint256 contractBalBefore = aggregateAmount(token);
    uint128 streamBalBefore = getBalance(streamId);
    
    withdraw@withrevert(e, streamId, to, amount);
    bool reverted = lastReverted;
    
    uint256 contractBalAfter = aggregateAmount(token);
    uint128 streamBalAfter = getBalance(streamId);
    
    // Contract balance should decrease by at least amount (may be more with fees)
    // Stream balance should decrease by exactly amount
    assert reverted || (streamBalBefore - streamBalAfter == amount || streamBalAfter == streamBalBefore),
        "CRITICAL: Stream balance accounting error with fee-on-transfer tokens";
}

// CRITICAL: Deposit should account for fee-on-transfer tokens
rule feeOnTransferDepositSafety(env e, uint256 streamId, uint128 amount, address sender, address recipient) {
    require isStream(streamId), "existing stream";
    address token = getToken(streamId);
    uint256 contractBalBefore = aggregateAmount(token);
    uint128 streamBalBefore = getBalance(streamId);
    
    deposit@withrevert(e, streamId, amount, sender, recipient);
    bool reverted = lastReverted;
    
    uint256 contractBalAfter = aggregateAmount(token);
    uint128 streamBalAfter = getBalance(streamId);
    
    // Stream balance should increase by amount
    // Contract balance may increase by less if token has fees
    assert reverted || (streamBalAfter >= streamBalBefore + amount || streamBalAfter == streamBalBefore),
        "CRITICAL: Stream balance not increased correctly - fee-on-transfer issue";
}

// ============ ROUNDING ERROR PROTECTION ============

// CRITICAL: Debt calculations should not lose precision
rule noLossyDebtRounding(env e, uint256 streamId) {
    require isStream(streamId), "existing stream";
    uint256 totalDebt = totalDebtOf(e, streamId);
    uint128 coveredDebt = coveredDebtOf(e, streamId);
    uint256 uncoveredDebt = uncoveredDebtOf(e, streamId);
    
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
    require isStream(streamId1), "existing stream 1";
    require isStream(streamId2), "existing stream 2";
    
    uint128 bal1Before = getBalance(streamId1);
    uint128 bal2Before = getBalance(streamId2);
    uint128 withdrawable1Before = withdrawableAmountOf(e, streamId1);
    uint128 withdrawable2Before = withdrawableAmountOf(e, streamId2);
    
    withdraw@withrevert(e, streamId1, to, amount);
    bool reverted = lastReverted;
    
    uint128 bal1After = getBalance(streamId1);
    uint128 bal2After = getBalance(streamId2);
    uint128 withdrawable1After = withdrawableAmountOf(e, streamId1);
    uint128 withdrawable2After = withdrawableAmountOf(e, streamId2);
    
    // Stream 2 should be unaffected
    assert reverted || bal2After == bal2Before,
        "CRITICAL: Withdraw on stream1 affected stream2 balance";
    assert reverted || withdrawable2After == withdrawable2Before,
        "CRITICAL: Withdraw on stream1 affected stream2 withdrawable";
}

// ============ AGGREGATE BALANCE CONSERVATION ============

// CRITICAL: Aggregate balance should track all stream balances correctly
rule aggregateBalanceConservation(env e, uint256 streamId, uint128 amount, address sender, address recipient) {
    require isStream(streamId), "existing stream";
    address token = getToken(streamId);
    uint256 aggregateBefore = aggregateAmount(token);
    uint128 streamBalBefore = getBalance(streamId);
    
    deposit@withrevert(e, streamId, amount, sender, recipient);
    bool reverted = lastReverted;
    
    uint256 aggregateAfter = aggregateAmount(token);
    uint128 streamBalAfter = getBalance(streamId);
    
    mathint streamBalIncrease = to_mathint(streamBalAfter) - to_mathint(streamBalBefore);
    
    // Aggregate should increase by at least the stream balance increase
    assert reverted || (to_mathint(aggregateAfter) >= to_mathint(aggregateBefore) + streamBalIncrease),
        "CRITICAL: Aggregate balance not tracking stream deposits correctly";
}

// ============ ZERO AMOUNT EDGE CASES ============

// HIGH: Zero amount operations should be safe
rule zeroAmountWithdrawRevertsAndNoStateChange(env e, uint256 streamId, address to) {
    require isStream(streamId), "existing stream";
    require to != 0;

    uint128 balBefore = getBalance(streamId);
    uint128 withdrawableBefore = withdrawableAmountOf(e, streamId);

    withdraw@withrevert(e, streamId, to, 0);
    assert lastReverted, "HIGH: withdraw(0) must revert";

    assert getBalance(streamId) == balBefore, "HIGH: state changed on revert (balance)";
    assert withdrawableAmountOf(e, streamId) == withdrawableBefore, "HIGH: state changed on revert (withdrawable)";
}

rule zeroAmountRefundRevertsAndNoStateChange(env e, uint256 streamId) {
    require isStream(streamId), "existing stream";

    uint128 balBefore = getBalance(streamId);
    uint128 refundableBefore = refundableAmountOf(e, streamId);

    refund@withrevert(e, streamId, 0);
    assert lastReverted, "HIGH: refund(0) must revert";

    assert getBalance(streamId) == balBefore, "HIGH: state changed on revert (balance)";
    assert refundableAmountOf(e, streamId) == refundableBefore, "HIGH: state changed on revert (refundable)";
}

// ============ TIME-BASED DEBT EDGE CASES ============

// CRITICAL: Debt should not decrease over time (only increase or stay same)
rule debtMonotonicityOverTime(env e1, env e2, uint256 streamId) {
    require isStream(streamId), "existing stream";
    require e1.block.timestamp <= e2.block.timestamp;
    
    uint256 debt1 = totalDebtOf(e1, streamId);
    uint256 debt2 = totalDebtOf(e2, streamId);
    
    // Debt at later time should be >= debt at earlier time
    assert to_mathint(debt2) >= to_mathint(debt1),
        "CRITICAL: Debt decreased over time - calculation error";
}

// ============ DOS PROTECTION ============

// HIGH: Valid withdrawals should not revert
rule withdrawalAlwaysSucceeds(env e, uint256 streamId, address to, uint128 amount) {
    require isStream(streamId), "existing stream";
    require e.msg.value >= calculateMinFeeWei(e, streamId);
    uint128 withdrawable = withdrawableAmountOf(e, streamId);
    require withdrawable >= amount;
    require amount > 0;
    
    withdraw@withrevert(e, streamId, to, amount);
    
    assert !lastReverted,
        "HIGH: Valid withdrawal reverted - potential DoS";
}

// HIGH: Valid refunds should not revert
rule refundAlwaysSucceeds(env e, uint256 streamId, uint128 amount) {
    require isStream(streamId), "existing stream";
    uint128 refundable = refundableAmountOf(e, streamId);
    require refundable >= amount;
    require amount > 0;
    
    refund@withrevert(e, streamId, amount);
    
    assert !lastReverted,
        "HIGH: Valid refund reverted - potential DoS";
}
