methods {
    function comptroller() external returns (address) envfree;
    function setComptroller(address newComptroller) external;
    function withdraw(uint256 streamId, address to, uint128 amount) external payable;
    function withdrawableAmountOf(uint256 streamId) external returns (uint128) envfree;
    function refundableAmountOf(uint256 streamId) external returns (uint128) envfree;
    function refund(uint256 streamId, uint128 amount) external payable;
    function getBalance(uint256 streamId) external returns (uint128) envfree;
    function totalDebtOf(uint256 streamId) external returns (uint256) envfree;
    function uncoveredDebtOf(uint256 streamId) external returns (uint256) envfree;
    function coveredDebtOf(uint256 streamId) external returns (uint128) envfree;
    function getSender(uint256 streamId) external returns (address) envfree;
    function isVoided(uint256 streamId) external returns (bool) envfree;
    function pause(uint256 streamId) external payable;
    function void(uint256 streamId) external payable;
    function deposit(uint256 streamId, uint128 amount, address sender, address recipient) external payable;
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
    withdraw@withrevert(e, streamId, to, amount);
    uint128 after = withdrawableAmountOf(streamId);
    assert !lastReverted => after + amount <= before, "withdrawable must decrease by at least amount";
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
    refund@withrevert(e, streamId, amount);
    uint128 after = refundableAmountOf(streamId);
    assert !lastReverted => after + amount <= before, "refundable must decrease by at least amount";
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
