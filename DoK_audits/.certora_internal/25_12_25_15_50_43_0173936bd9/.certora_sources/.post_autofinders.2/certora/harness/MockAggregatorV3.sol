// SPDX-License-Identifier: UNLICENSED
pragma solidity >=0.8.22;

/// @notice Minimal Chainlink AggregatorV3Interface model for Certora runs.
contract MockAggregatorV3 {
    function decimals() external pure returns (uint8) {
        return 8;
    }

    /// @dev Matches Chainlink's AggregatorV3Interface signature.
    function latestRoundData()
        external
        view
        returns (uint80 roundId, int256 answer, uint256 startedAt, uint256 updatedAt, uint80 answeredInRound)
    {
        // Non-zero, positive price; updated "now" so Comptroller's staleness checks pass.
        return (1, int256(1e8), 0, block.timestamp, 1);
    }
}

