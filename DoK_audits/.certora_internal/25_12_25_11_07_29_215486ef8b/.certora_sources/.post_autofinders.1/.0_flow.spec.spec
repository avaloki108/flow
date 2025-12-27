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

// Pause access control: only sender can pause
rule pauseAccessControl(env e, uint256 streamId) {
    address sender = getSender(streamId);
    pause@withrevert(e, streamId);
    assert !lastReverted => e.msg.sender == sender, "only sender can pause";
}

// ============ WITHDRAW BOUNDS ============

// Withdraw bound: cannot withdraw more than withdrawableAmountOf
rule withdrawBound(env e, uint256 streamId, uint128 amount, address to) {
    uint128 before = withdrawableAmountOf(streamId);
    withdraw@withrevert(e, streamId, to, amount);
    assert !lastReverted => amount <= before, "withdraw amount must be <= withdrawable";
}

// Withdraw decreases withdrawable by at least the withdrawn amount
rule withdrawDecreasesWithdrawable(env e, uint256 streamId, uint128 amount, address to) {
    uint128 before = withdrawableAmountOf(streamId);
    withdraw(e, streamId, to, amount);
    uint128 after = withdrawableAmountOf(streamId);
    assert after + amount <= before, "withdrawable must decrease by at least amount";
}

// ============ REFUND BOUNDS ============

// Refund bound: cannot refund more than refundableAmountOf
rule refundBound(env e, uint256 streamId, uint128 amount) {
    uint128 before = refundableAmountOf(streamId);
    refund@withrevert(e, streamId, amount);
    assert !lastReverted => amount <= before, "refund amount must be <= refundable";
}

// Refund decreases refundable by at least the refunded amount
rule refundDecreasesRefundable(env e, uint256 streamId, uint128 amount) {
    uint128 before = refundableAmountOf(streamId);
    refund(e, streamId, amount);
    uint128 after = refundableAmountOf(streamId);
    assert after + amount <= before, "refundable must decrease by at least amount";
}

// Refund access control: only sender can refund
rule refundAccessControl(env e, uint256 streamId, uint128 amount) {
    address sender = getSender(streamId);
    refund@withrevert(e, streamId, amount);
    assert !lastReverted => e.msg.sender == sender, "only sender can refund";
}

// ============ BALANCE INVARIANTS ============

// Balance = coveredDebt + refundable (fundamental accounting identity)
invariant balanceInvariant(uint256 streamId)
    getBalance(streamId) == coveredDebtOf(streamId) + refundableAmountOf(streamId);

// totalDebt >= coveredDebt (covered debt is capped by balance)
invariant totalDebtGeCoveredDebt(uint256 streamId)
    totalDebtOf(streamId) >= coveredDebtOf(streamId);

// ============ VOID SEMANTICS ============

// Once voided, stream stays voided (no un-voiding)
rule voidIsPermanent(env e, uint256 streamId, method f) {
    bool voidedBefore = isVoided(streamId);
    calldataarg args;
    f(e, args);
    bool voidedAfter = isVoided(streamId);
    assert voidedBefore => voidedAfter, "voided streams cannot be un-voided";
}

// ============ DEPOSIT INCREASES BALANCE ============

// Deposit should increase stream balance
rule depositIncreasesBalance(env e, uint256 streamId, uint128 amount, address sender, address recipient) {
    uint128 balBefore = getBalance(streamId);
    deposit(e, streamId, amount, sender, recipient);
    uint128 balAfter = getBalance(streamId);
    assert balAfter >= balBefore, "deposit must not decrease balance";
    assert amount > 0 => balAfter > balBefore, "non-zero deposit must increase balance";
}

// ============ WITHDRAW MAX CORRECTNESS ============

// withdrawMax should withdraw exactly the withdrawable amount
rule withdrawMaxCorrectness(env e, uint256 streamId, address to) {
    uint128 withdrawable = withdrawableAmountOf(streamId);
    uint128 withdrawn = withdrawMax(e, streamId, to);
    assert withdrawn == withdrawable, "withdrawMax should withdraw exactly withdrawable amount";
}

// ============ REFUND MAX CORRECTNESS ============

// refundMax should refund exactly the refundable amount
rule refundMaxCorrectness(env e, uint256 streamId) {
    uint128 refundable = refundableAmountOf(streamId);
    uint128 refunded = refundMax(e, streamId);
    assert refunded == refundable, "refundMax should refund exactly refundable amount";
}

// ============ NO FUNDS DRAIN ============

// Balance should never go negative (implicit in uint128, but let's verify logic)
rule balanceNeverNegative(env e, uint256 streamId, method f) {
    uint128 balBefore = getBalance(streamId);
    calldataarg args;
    f(e, args);
    uint128 balAfter = getBalance(streamId);
    // If balance decreased, it should be by a legitimate withdraw amount
    assert balAfter <= balBefore || f.selector == sig:deposit(uint256,uint128,address,address).selector, 
        "balance can only increase via deposit";
}

// ============ STREAM ID MONOTONICITY ============

// nextStreamId should only increase
rule streamIdMonotonicity(env e, method f) {
    uint256 idBefore = nextStreamId();
    calldataarg args;
    f(e, args);
    uint256 idAfter = nextStreamId();
    assert idAfter >= idBefore, "nextStreamId should never decrease";
}
