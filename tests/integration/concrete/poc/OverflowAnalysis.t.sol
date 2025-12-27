// SPDX-License-Identifier: UNLICENSED
pragma solidity >=0.8.22;

import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import { ud21x18, UD21x18 } from "@prb/math/src/UD21x18.sol";
import { console2 } from "forge-std/src/console2.sol";

import { Integration_Test } from "../../Integration.t.sol";

/// @title OverflowAnalysis_POC
/// @notice Deep dive into the overflow mechanism
contract OverflowAnalysis_POC is Integration_Test {
    uint256 internal streamId;

    function setUp() public override {
        Integration_Test.setUp();
    }

    /// @notice Show the exact overflow in hex and decimal
    function test_OverflowAnalysis_HexValues() public {
        console2.log("=== OVERFLOW ANALYSIS: Hex and Decimal Values ===");
        console2.log("");

        // Create stream
        UD21x18 rate = ud21x18(1e15);
        streamId = flow.create({
            sender: users.sender,
            recipient: users.recipient,
            ratePerSecond: rate,
            startTime: 0,
            token: usdc,
            transferable: true
        });

        // Deposit
        uint128 depositAmount = 1e6;
        deal({ token: address(usdc), to: users.sender, give: depositAmount });
        usdc.approve(address(flow), depositAmount);
        flow.deposit(streamId, depositAmount, users.sender, users.recipient);

        // Warp to 2^41
        uint256 extremeTimestamp = 2 ** 41;
        vm.warp(extremeTimestamp);

        // Get values
        uint256 snapshotTime = flow.getSnapshotTime(streamId);
        uint256 currentTime = block.timestamp;
        uint256 elapsedTime = currentTime - snapshotTime;
        uint256 ratePerSecond = flow.getRatePerSecond(streamId).unwrap();
        uint256 snapshotDebtScaled = flow.getSnapshotDebtScaled(streamId);

        console2.log("Raw Values:");
        console2.log("  snapshotTime (dec):", snapshotTime);
        console2.log("  snapshotTime (hex):");
        console2.logBytes32(bytes32(snapshotTime));
        console2.log("  currentTime (dec):", currentTime);
        console2.log("  currentTime (hex):");
        console2.logBytes32(bytes32(currentTime));
        console2.log("  elapsedTime (dec):", elapsedTime);
        console2.log("  elapsedTime (hex):");
        console2.logBytes32(bytes32(elapsedTime));
        console2.log("  ratePerSecond (dec):", ratePerSecond);
        console2.log("  ratePerSecond (hex):");
        console2.logBytes32(bytes32(ratePerSecond));
        console2.log("");

        // Calculate ongoing debt
        uint256 ongoingDebtScaled = elapsedTime * ratePerSecond;
        console2.log("Calculation:");
        console2.log("  ongoingDebtScaled = elapsedTime * ratePerSecond");
        console2.log("  ongoingDebtScaled (dec):", ongoingDebtScaled);
        console2.log("  ongoingDebtScaled (hex):");
        console2.logBytes32(bytes32(ongoingDebtScaled));
        console2.log("");

        // Check max uint256
        uint256 maxUint256 = type(uint256).max;
        console2.log("Bounds Check:");
        console2.log("  max uint256 (dec):", maxUint256);
        console2.log("  ongoingDebtScaled < maxUint256?", ongoingDebtScaled < maxUint256);
        console2.log("  ongoingDebtScaled == maxUint256?", ongoingDebtScaled == maxUint256);
        console2.log("  ongoingDebtScaled > maxUint256?", ongoingDebtScaled > maxUint256);
        console2.log("");

        // Before pause
        console2.log("Before pause():");
        console2.log("  snapshotDebtScaled (dec):", snapshotDebtScaled);
        console2.log("  snapshotDebtScaled (hex):");
        console2.logBytes32(bytes32(snapshotDebtScaled));
        console2.log("  ongoingDebtScaled (dec):", ongoingDebtScaled);
        console2.log("  ongoingDebtScaled (hex):");
        console2.logBytes32(bytes32(ongoingDebtScaled));
        console2.log("");

        // Simulate addition
        uint256 newSnapshotDebtScaled;
        unchecked {
            newSnapshotDebtScaled = snapshotDebtScaled + ongoingDebtScaled;
        }
        console2.log("Simulated addition (unchecked):");
        console2.log("  newSnapshotDebtScaled = snapshotDebtScaled + ongoingDebtScaled");
        console2.log("  newSnapshotDebtScaled (dec):", newSnapshotDebtScaled);
        console2.log("  newSnapshotDebtScaled (hex):");
        console2.logBytes32(bytes32(newSnapshotDebtScaled));
        console2.log("  Overflow check (new < old):", newSnapshotDebtScaled < snapshotDebtScaled);
        console2.log("");

        // Actually pause
        flow.pause(streamId);
        uint256 actualSnapshotDebtAfter = flow.getSnapshotDebtScaled(streamId);
        console2.log("After pause():");
        console2.log("  Actual snapshotDebtScaled stored (dec):", actualSnapshotDebtAfter);
        console2.log("  Actual snapshotDebtScaled stored (hex):");
        console2.logBytes32(bytes32(actualSnapshotDebtAfter));
        console2.log("  Expected (dec):", newSnapshotDebtScaled);
        console2.log("  Match?", actualSnapshotDebtAfter == newSnapshotDebtScaled);
        console2.log("");

        // Check if it's a wrapping issue
        if (actualSnapshotDebtAfter != newSnapshotDebtScaled) {
            console2.log("*** OVERFLOW DETECTED ***");
            console2.log("  The stored value differs from expected!");
            console2.log("  This indicates an overflow occurred during the addition");
        }
    }

    /// @notice Test with smaller values to see where overflow starts
    function test_OverflowAnalysis_FindThreshold() public {
        console2.log("=== FINDING OVERFLOW THRESHOLD ===");
        console2.log("");

        // Try different timestamps to find where overflow occurs
        uint256[] memory timestamps = new uint256[](10);
        timestamps[0] = 2 ** 30;  // ~34 years
        timestamps[1] = 2 ** 35;  // ~1088 years
        timestamps[2] = 2 ** 38;  // ~8704 years
        timestamps[3] = 2 ** 39;  // ~17408 years
        timestamps[4] = 2 ** 40;  // ~34816 years
        timestamps[5] = 2 ** 41;  // ~69632 years (Certora example)
        timestamps[6] = 2 ** 42;  // ~139264 years
        timestamps[7] = 2 ** 43;  // ~278528 years
        timestamps[8] = 2 ** 44;  // ~557056 years
        timestamps[9] = 2 ** 45;  // ~1114112 years

        UD21x18 rate = ud21x18(1e15);
        
        for (uint256 i = 0; i < timestamps.length; i++) {
            // Create new stream for each test
            streamId = flow.create({
                sender: users.sender,
                recipient: users.recipient,
                ratePerSecond: rate,
                startTime: 0,
                token: usdc,
                transferable: true
            });

            // Deposit
            uint128 depositAmount = 1e6;
            deal({ token: address(usdc), to: users.sender, give: depositAmount });
            usdc.approve(address(flow), depositAmount);
            flow.deposit(streamId, depositAmount, users.sender, users.recipient);

            // Warp
            vm.warp(timestamps[i]);

            // Get values
            uint256 snapshotTime = flow.getSnapshotTime(streamId);
            uint256 elapsedTime = timestamps[i] - snapshotTime;
            uint256 ratePerSecond = flow.getRatePerSecond(streamId).unwrap();
            uint256 ongoingDebtScaled = elapsedTime * ratePerSecond;
            uint256 snapshotDebtScaled = flow.getSnapshotDebtScaled(streamId);

            // Check debt before
            uint256 debtBefore = flow.totalDebtOf(streamId);

            // Pause
            flow.pause(streamId);

            // Check debt after
            uint256 debtAfter = flow.totalDebtOf(streamId);
            uint256 actualSnapshotAfter = flow.getSnapshotDebtScaled(streamId);

            console2.log("Timestamp 2^%d:", 30 + i);
            console2.log("  elapsedTime:", elapsedTime);
            console2.log("  ongoingDebtScaled:", ongoingDebtScaled);
            console2.log("  debtBefore:", debtBefore);
            console2.log("  debtAfter:", debtAfter);
            console2.log("  snapshotDebtScaled before:", snapshotDebtScaled);
            console2.log("  snapshotDebtScaled after:", actualSnapshotAfter);
            
            if (debtAfter < debtBefore) {
                console2.log("  *** OVERFLOW OCCURRED AT THIS TIMESTAMP ***");
            }
            console2.log("");
        }
    }
}
