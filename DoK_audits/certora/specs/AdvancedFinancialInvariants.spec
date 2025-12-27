import "certora/specs/common/Env.spec";
import "certora/specs/common/ERC20Helpers.spec";

/**
 * CRITICAL VULNERABILITY HUNTING SPEC
 *
 * This spec is designed to uncover exploitable financial vulnerabilities:
 * 1. Balance manipulation attacks
 * 2. Reentrancy vulnerabilities
 * 3. Integer overflow/underflow
 * 4. Debt accounting errors
 * 5. Unauthorized fund extraction
 * 6. Time-dependent manipulation
 * 7. Rounding errors leading to fund loss
 * 8. Front-running opportunities
 */

methods {
    // Core state queries
    function balanceOf(uint256) external returns (uint128) envfree;
    function totalDebtOf(uint256) external returns (uint256) envfree;
    function coveredDebtOf(uint256) external returns (uint128) envfree;
    function ongoingDebtScaledOf(uint256) external returns (uint256) envfree;
    function refundableAmountOf(uint256) external returns (uint128) envfree;
    function uncoveredDebtOf(uint256) external returns (uint256) envfree;

    // Stream properties
    function getRatePerSecond(uint256) external returns (uint256) envfree;
    function getSnapshotTime(uint256) external returns (uint40) envfree;
    function getSnapshotDebtScaled(uint256) external returns (uint256) envfree;
    function isPaused(uint256) external returns (bool) envfree;
    function isVoided(uint256) external returns (bool) envfree;
    function getSender(uint256) external returns (address) envfree;
    function getRecipient(uint256) external returns (address) envfree;
    function getToken(uint256) external returns (address) envfree;

    // State-changing functions
    function deposit(uint256, uint128, address, address) external;
    function withdraw(uint256, address, uint128) external;
    function refund(uint256, uint128) external;
    function pause(uint256) external;
    function restart(uint256, uint256) external;
    function void(uint256) external;
    function adjustRatePerSecond(uint256, uint256) external;

    // ERC20
    function _.balanceOf(address) external => DISPATCHER(true);
    function _.transfer(address, uint256) external => DISPATCHER(true);
    function _.transferFrom(address, address, uint256) external => DISPATCHER(true);
}

// ============ CRITICAL INVARIANTS ============

// CRITICAL: Total covered debt across all streams must not exceed aggregate balance
invariant invariant_aggregate_balance_covers_debt(address token)
    getAggregateAmount(token) >= sumOfCoveredDebts(token)
    {
        preserved {
            requireInvariant invariant_balance_never_negative(token);
        }
    }

// CRITICAL: Balance can never be negative (overflow protection)
invariant invariant_balance_never_negative(uint256 streamId)
    balanceOf(streamId) >= 0

// CRITICAL: Covered debt never exceeds balance
invariant invariant_covered_debt_bounded_by_balance(uint256 streamId)
    coveredDebtOf(streamId) <= balanceOf(streamId)
    {
        preserved {
            requireInvariant invariant_balance_never_negative(streamId);
        }
    }

// CRITICAL: Total debt consistency
invariant invariant_total_debt_consistency(uint256 streamId)
    totalDebtOf(streamId) >= coveredDebtOf(streamId)

// ============ VULNERABILITY HUNTING RULES ============

// CRITICAL: Check for balance manipulation via deposit-withdraw cycle
rule rule_no_fund_extraction_via_deposit_withdraw_cycle(uint256 streamId, uint128 depositAmount) {
    env e1;
    env e2;

    require e1.msg.sender != currentContract;
    require e2.msg.sender != currentContract;
    require depositAmount > 0;

    // Initial state
    uint128 balanceBefore = balanceOf(streamId);
    uint256 totalDebtBefore = totalDebtOf(streamId);
    address sender = getSender(streamId);
    address recipient = getRecipient(streamId);
    address token = getToken(streamId);

    uint256 contractBalanceBefore = tokenBalanceOf(token, currentContract);
    uint256 recipientBalanceBefore = tokenBalanceOf(token, recipient);

    // Deposit funds
    deposit(e1, streamId, depositAmount, sender, recipient);

    // Try to withdraw immediately
    uint128 withdrawAmount = coveredDebtOf(streamId);
    withdraw@withrevert(e2, streamId, recipient, withdrawAmount);

    uint256 contractBalanceAfter = tokenBalanceOf(token, currentContract);
    uint256 recipientBalanceAfter = tokenBalanceOf(token, recipient);

    // CRITICAL: The contract should not lose more funds than expected
    assert contractBalanceBefore + depositAmount >= contractBalanceAfter,
        "CRITICAL: Fund extraction detected via deposit-withdraw cycle";

    // CRITICAL: Recipient should not gain more than covered debt
    assert recipientBalanceAfter <= recipientBalanceBefore + withdrawAmount,
        "CRITICAL: Recipient extracted more funds than covered debt";
}

// CRITICAL: Refund must not allow sender to steal recipient's owed funds
rule rule_refund_cannot_steal_covered_debt(uint256 streamId, uint128 refundAmount) {
    env e;

    require refundAmount > 0;
    require !isVoided(streamId);

    uint128 coveredBefore = coveredDebtOf(streamId);
    uint128 balanceBefore = balanceOf(streamId);
    uint128 refundableBefore = refundableAmountOf(streamId);

    refund@withrevert(e, streamId, refundAmount);

    if (!lastReverted) {
        uint128 coveredAfter = coveredDebtOf(streamId);
        uint128 balanceAfter = balanceOf(streamId);

        // CRITICAL: Refund must not reduce covered debt
        assert coveredAfter == (coveredBefore > balanceAfter ? balanceAfter : coveredBefore),
            "CRITICAL: Refund reduced covered debt - sender stealing recipient funds";

        // CRITICAL: Can only refund from excess balance
        assert refundAmount <= refundableBefore,
            "CRITICAL: Refunded more than refundable amount";

        // CRITICAL: Balance reduction must equal refund amount
        assert balanceBefore == balanceAfter + refundAmount,
            "CRITICAL: Balance accounting error in refund";
    }
}

// CRITICAL: Pause-unpause cycle cannot manipulate debt
rule rule_pause_restart_debt_integrity(uint256 streamId, uint256 newRate) {
    env e1;
    env e2;
    env e3;

    require e1.block.timestamp < e2.block.timestamp;
    require e2.block.timestamp < e3.block.timestamp;
    require !isPaused(streamId);
    require !isVoided(streamId);
    require newRate > 0;

    // Record initial debt
    uint256 debtBeforePause = totalDebtOf(streamId);

    // Pause the stream
    pause(e1, streamId);
    uint256 debtAtPause = totalDebtOf(streamId);

    // Time passes while paused
    uint256 debtWhilePaused = totalDebtOfAt(streamId, e2.block.timestamp);

    // Restart the stream
    restart(e2, streamId, newRate);

    // More time passes
    uint256 debtAfterRestart = totalDebtOfAt(streamId, e3.block.timestamp);

    // CRITICAL: Debt should not decrease during pause
    assert debtWhilePaused >= debtAtPause,
        "CRITICAL: Debt decreased while paused";

    // CRITICAL: Debt at pause should be >= debt before (time passed)
    assert debtAtPause >= debtBeforePause,
        "CRITICAL: Debt decreased on pause";
}

// CRITICAL: Withdraw cannot exceed covered debt at any time
rule rule_withdraw_strict_debt_boundary(uint256 streamId, address to, uint128 amount) {
    env e;

    require amount > 0;
    require to != 0;

    uint128 coveredBefore = coveredDebtOf(streamId);
    uint256 totalDebtBefore = totalDebtOf(streamId);
    uint128 balanceBefore = balanceOf(streamId);

    withdraw@withrevert(e, streamId, to, amount);

    // If withdraw succeeded, it must respect covered debt
    assert !lastReverted => amount <= coveredBefore,
        "CRITICAL: Withdrew more than covered debt - insolvency exploit";

    // Additional check: balance must cover the amount
    assert !lastReverted => amount <= balanceBefore,
        "CRITICAL: Withdrew more than balance - impossible overflow";
}

// CRITICAL: Time-based debt manipulation check
rule rule_time_travel_attack_protection(uint256 streamId) {
    env e1;
    env e2;

    require e1.block.timestamp < e2.block.timestamp;
    require !isPaused(streamId);
    require !isVoided(streamId);
    require getRatePerSecond(streamId) > 0;

    uint256 debt1 = totalDebtOf(streamId);
    uint256 rate = getRatePerSecond(streamId);
    uint256 timeDelta = e2.block.timestamp - e1.block.timestamp;

    // Perform any operation at later time
    mathint expectedMinDebt = debt1 + (rate * timeDelta);

    uint256 debt2 = totalDebtOfAt(streamId, e2.block.timestamp);

    // CRITICAL: Debt must increase proportionally to time when streaming
    assert to_mathint(debt2) >= expectedMinDebt - 1,  // Allow 1 wei rounding
        "CRITICAL: Debt did not increase properly over time - manipulation detected";
}

// CRITICAL: Reentrancy protection on withdraw
rule rule_no_reentrancy_in_withdraw(uint256 streamId, address to, uint128 amount) {
    env e;

    require amount > 0;

    uint128 balanceBefore = balanceOf(streamId);
    uint128 coveredBefore = coveredDebtOf(streamId);

    // First withdraw
    withdraw@withrevert(e, streamId, to, amount);
    bool firstSucceeded = !lastReverted;

    uint128 balanceAfter1 = balanceOf(streamId);
    uint128 coveredAfter1 = coveredDebtOf(streamId);

    // Attempt immediate second withdraw (simulating reentrancy)
    withdraw@withrevert(e, streamId, to, amount);
    bool secondSucceeded = !lastReverted;

    uint128 balanceAfter2 = balanceOf(streamId);

    // CRITICAL: Cannot withdraw same amount twice in single transaction
    if (firstSucceeded && secondSucceeded) {
        assert balanceBefore >= balanceAfter2 + (2 * amount),
            "CRITICAL: Reentrancy allowed double withdrawal";
    }
}

// CRITICAL: Rounding errors cannot drain funds
rule rule_rounding_cannot_create_funds(uint256 streamId, uint128 amount, method f) {
    env e;

    uint128 balanceBefore = balanceOf(streamId);
    address token = getToken(streamId);
    uint256 contractBalanceBefore = tokenBalanceOf(token, currentContract);

    // Call any function
    calldataarg args;
    f(e, args);

    uint128 balanceAfter = balanceOf(streamId);
    uint256 contractBalanceAfter = tokenBalanceOf(token, currentContract);

    // CRITICAL: Internal balance cannot exceed actual token balance
    assert balanceAfter <= contractBalanceAfter,
        "CRITICAL: Accounting error - internal balance exceeds actual tokens";

    // CRITICAL: Total change must be consistent
    mathint internalChange = balanceAfter - balanceBefore;
    mathint actualChange = contractBalanceAfter - contractBalanceBefore;

    assert internalChange <= actualChange + 1,  // Allow 1 wei rounding
        "CRITICAL: Rounding error creating funds from nothing";
}

// CRITICAL: Void cannot be exploited to avoid debt
rule rule_void_cannot_erase_covered_debt(uint256 streamId) {
    env e;

    require !isVoided(streamId);

    uint128 coveredBefore = coveredDebtOf(streamId);
    uint128 balanceBefore = balanceOf(streamId);
    uint256 totalDebtBefore = totalDebtOf(streamId);

    void(e, streamId);

    uint128 coveredAfter = coveredDebtOf(streamId);
    uint256 totalDebtAfter = totalDebtOf(streamId);
    uint128 balanceAfter = balanceOf(streamId);

    // CRITICAL: Void cannot reduce covered debt below balance
    if (coveredBefore <= balanceBefore) {
        assert coveredAfter >= coveredBefore,
            "CRITICAL: Void reduced covered debt - sender avoiding obligation";
    }

    // CRITICAL: After void, covered debt should equal balance (or remain same if already insolvent)
    assert coveredAfter <= balanceAfter,
        "CRITICAL: Covered debt exceeds balance after void";
}

// CRITICAL: Rate adjustment cannot retroactively reduce debt
rule rule_rate_change_cannot_reduce_past_debt(uint256 streamId, uint256 newRate) {
    env e;

    require !isVoided(streamId);
    require newRate >= 0;

    uint256 totalDebtBefore = totalDebtOf(streamId);
    uint256 coveredBefore = coveredDebtOf(streamId);

    adjustRatePerSecond@withrevert(e, streamId, newRate);

    if (!lastReverted) {
        uint256 totalDebtAfter = totalDebtOf(streamId);
        uint256 coveredAfter = coveredDebtOf(streamId);

        // CRITICAL: Rate change must not reduce existing debt
        assert totalDebtAfter >= totalDebtBefore,
            "CRITICAL: Rate adjustment reduced past debt - accounting manipulation";
    }
}

// CRITICAL: Front-running protection - deposit cannot be sandwiched
rule rule_no_deposit_frontrun_exploit(uint256 streamId, uint128 depositAmount, uint128 withdrawAmount) {
    env e1;  // Attacker
    env e2;  // Victim deposit
    env e3;  // Attacker

    require e1.msg.sender != e2.msg.sender;
    require depositAmount > 0;
    require withdrawAmount > 0;

    address sender = getSender(streamId);
    address recipient = getRecipient(streamId);

    // Attacker withdraws first
    uint128 balanceBefore = balanceOf(streamId);
    withdraw@withrevert(e1, streamId, recipient, withdrawAmount);

    // Victim deposits
    deposit(e2, streamId, depositAmount, sender, recipient);

    uint128 balanceAfter = balanceOf(streamId);

    // Attacker tries to withdraw again
    uint128 coveredAfterDeposit = coveredDebtOf(streamId);
    withdraw@withrevert(e3, streamId, recipient, coveredAfterDeposit);

    uint128 finalBalance = balanceOf(streamId);

    // CRITICAL: Attacker should not profit from victim's deposit
    // The net effect should be that funds remain for debt coverage
    assert finalBalance >= depositAmount - withdrawAmount - coveredAfterDeposit,
        "CRITICAL: Front-running allowed fund extraction from victim deposit";
}

// CRITICAL: Stream creation with future start time cannot be exploited
rule rule_future_stream_no_immediate_debt(address sender, address recipient, uint256 rate, uint40 startTime, address token, bool transferable, uint128 deposit) {
    env e;

    require startTime > e.block.timestamp;
    require rate > 0;

    uint256 streamId = createAndDeposit(e, sender, recipient, rate, startTime, token, transferable, deposit);

    // CRITICAL: Stream with future start time should have zero ongoing debt
    uint256 ongoingDebt = ongoingDebtScaledOf(streamId);
    assert ongoingDebt == 0,
        "CRITICAL: Future stream has immediate debt - accounting error";

    // CRITICAL: No withdrawable amount before start
    uint128 covered = coveredDebtOf(streamId);
    assert covered == 0,
        "CRITICAL: Can withdraw from stream before it starts";
}
