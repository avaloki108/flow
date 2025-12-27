methods {
    function comptroller() external returns (address) envfree;
    function setComptroller(address newComptroller) external;
}

rule setComptrollerAccessControl(env e, address newComptroller) {
    address current = comptroller();
    e.msg.value = 0;
    setComptroller@withrevert(e, newComptroller);
    assert !lastReverted => e.msg.sender == current, "only comptroller can succeed";
}

rule setComptrollerNoChangeOnRevert(env e, address newComptroller) {
    address before = comptroller();
    e.msg.value = 0;
    setComptroller@withrevert(e, newComptroller);
    assert lastReverted => comptroller() == before, "comptroller should not change on revert";
}
