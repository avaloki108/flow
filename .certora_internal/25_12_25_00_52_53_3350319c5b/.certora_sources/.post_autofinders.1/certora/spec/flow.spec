methods {
    function comptroller() external returns (address) envfree;
    function setComptroller(address newComptroller) external;
    function withdraw(uint256 streamId, uint128 amount, address to) external;
    function withdrawableAmountOf(uint256 streamId) external returns (uint128) envfree;
    function refundableAmountOf(uint256 streamId) external returns (uint128) envfree;
    function refund(uint256 streamId, uint128 amount) external;
}

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

// Withdraw bound: cannot withdraw more than withdrawableAmountOf
rule withdrawBound(env e, uint256 streamId, uint128 amount, address to) {
    uint128 before = withdrawableAmountOf(streamId);
    withdraw@withrevert(e, streamId, amount, to);
    assert !lastReverted => amount <= before, "withdraw amount must be <= withdrawable";
    assert lastReverted => withdrawableAmountOf(streamId) == before, "withdrawable should not change on revert";
}

// Refund bound: cannot refund more than refundableAmountOf
rule refundBound(env e, uint256 streamId, uint128 amount) {
    uint128 before = refundableAmountOf(streamId);
    refund@withrevert(e, streamId, amount);
    assert !lastReverted => amount <= before, "refund amount must be <= refundable";
    assert lastReverted => refundableAmountOf(streamId) == before, "refundable should not change on revert";
}
