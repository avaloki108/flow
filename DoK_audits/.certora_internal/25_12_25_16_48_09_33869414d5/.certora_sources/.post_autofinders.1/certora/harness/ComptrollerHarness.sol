// SPDX-License-Identifier: UNLICENSED
pragma solidity >=0.8.22;

/// @notice Minimal comptroller model for Certora runs.
/// @dev We deliberately omit generic admin entrypoints like `execute` and fee-sweeping functions,
/// because they introduce huge over-approximation in induction (they can call arbitrary targets).
contract ComptrollerHarness {
    enum Protocol {
        Airdrops,
        Flow,
        Lockup,
        Staking
    }

    function calculateMinFeeWeiFor(Protocol, address) external pure returns (uint256) {
        return 0;
    }
}


