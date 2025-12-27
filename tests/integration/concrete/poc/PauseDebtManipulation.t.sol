// SPDX-License-Identifier: UNLICENSED
pragma solidity >=0.8.22;

import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import { ud21x18, UD21x18 } from "@prb/math/src/UD21x18.sol";

import { Integration_Test } from "../../Integration.t.sol";

/// @title PauseDebtManipulation_POC
/// @notice Proof of Concept for the critical vulnerability found by Certora Prover
/// @dev This test demonstrates that calling pause() can manipulate/decrease total debt
contract PauseDebtManipulation_POC is Integration_Test {
    uint256 internal streamId;

    function setUp() public override {
        Integration_Test.setUp();
    }

    /// @notice Demonstrates the pause debt manipulation vulnerability
    /// @dev Certora found: totalDebtBefore = 0xa0000000020, debtAfterPause = 12
    function test_POC_PauseDecreaseDebt() public {
        // Step 1: Create a stream with a high rate per second
        UD21x18 highRate = ud21x18(1e18); // 1 token per second (18 decimals)
        streamId = flow.create({
            sender: users.sender,
            recipient: users.recipient,
            ratePerSecond: highRate,
            startTime: ZERO, // Start immediately
            token: usdc,
            transferable: TRANSFERABLE
        });

        // Step 2: Deposit a large amount
        uint128 depositAmount = 1_000_000e6; // 1M USDC (6 decimals)
        deal({ token: address(usdc), to: users.sender, give: depositAmount });
        usdc.approve(address(flow), depositAmount);
        flow.deposit(streamId, depositAmount, users.sender, users.recipient);

        // Step 3: Let time pass to accumulate debt
        uint256 timeJump = 1 days; // 1 day
        vm.warp(block.timestamp + timeJump);

        // Step 4: Record debt BEFORE pause
        uint256 totalDebtBefore = flow.totalDebtOf(streamId);

        // Step 5: Sender calls pause()
        flow.pause(streamId);

        // Step 6: Record debt AFTER pause
        uint256 totalDebtAfter = flow.totalDebtOf(streamId);

        // Assert: Total debt should NOT decrease after pause
        assertGe(totalDebtAfter, totalDebtBefore, "EXPLOIT: Pause decreased total debt!");
    }

    /// @notice Test with extreme time values (similar to Certora counterexample)
    /// @dev Certora used e1.block.timestamp = 2^41
    function test_POC_PauseDebtWithExtremeTimestamp() public {
        // Create stream
        UD21x18 rate = ud21x18(1e15); // Lower rate to avoid overflow
        streamId = flow.create({
            sender: users.sender,
            recipient: users.recipient,
            ratePerSecond: rate,
            startTime: ZERO,
            token: usdc,
            transferable: TRANSFERABLE
        });

        // Deposit
        uint128 depositAmount = 100_000e6;
        deal({ token: address(usdc), to: users.sender, give: depositAmount });
        usdc.approve(address(flow), depositAmount);
        flow.deposit(streamId, depositAmount, users.sender, users.recipient);

        // Warp to extreme timestamp (2^41 as in Certora counterexample)
        uint256 extremeTimestamp = 2 ** 41;
        vm.warp(extremeTimestamp);

        uint256 totalDebtBefore = flow.totalDebtOf(streamId);

        // Pause
        flow.pause(streamId);

        uint256 totalDebtAfter = flow.totalDebtOf(streamId);

        assertGe(totalDebtAfter, totalDebtBefore, "EXPLOIT: Pause with extreme timestamp decreased debt!");
    }

    /// @notice Test the specific Certora counterexample values
    /// @dev streamId=2, e1.block.timestamp=2^41, totalDebtBefore=0xa0000000020, debtAfterPause=12
    function test_POC_CertoraCounterexample() public {
        // Create streams to get streamId = 2
        flow.create({
            sender: users.sender,
            recipient: users.recipient,
            ratePerSecond: ud21x18(1),
            startTime: ZERO,
            token: usdc,
            transferable: TRANSFERABLE
        });
        
        streamId = flow.create({
            sender: users.sender,
            recipient: users.recipient,
            ratePerSecond: ud21x18(1e15),
            startTime: ZERO,
            token: usdc,
            transferable: TRANSFERABLE
        });

        // Deposit minimal
        uint128 depositAmount = 1e6;
        deal({ token: address(usdc), to: users.sender, give: depositAmount });
        usdc.approve(address(flow), depositAmount);
        flow.deposit(streamId, depositAmount, users.sender, users.recipient);

        // Warp to 2^41
        vm.warp(2 ** 41);

        uint256 debtBefore = flow.totalDebtOf(streamId);

        // Pause
        flow.pause(streamId);

        uint256 debtAfter = flow.totalDebtOf(streamId);

        // Check if debt decreased
        assertGe(debtAfter, debtBefore, "EXPLOIT: Certora counterexample replicated!");
    }

    /// @notice Test rapid pause/unpause cycles
    function test_POC_RapidPauseUnpauseCycles() public {
        UD21x18 rate = ud21x18(1e18);
        streamId = flow.create({
            sender: users.sender,
            recipient: users.recipient,
            ratePerSecond: rate,
            startTime: ZERO,
            token: usdc,
            transferable: TRANSFERABLE
        });

        uint128 depositAmount = 1_000_000e6;
        deal({ token: address(usdc), to: users.sender, give: depositAmount });
        usdc.approve(address(flow), depositAmount);
        flow.deposit(streamId, depositAmount, users.sender, users.recipient);

        // Initial debt
        vm.warp(block.timestamp + 1 hours);
        uint256 initialDebt = flow.totalDebtOf(streamId);

        // Rapid cycles
        for (uint i = 0; i < 5; i++) {
            uint256 debtBeforePause = flow.totalDebtOf(streamId);
            
            flow.pause(streamId);
            uint256 debtAfterPause = flow.totalDebtOf(streamId);
            
            assertGe(debtAfterPause, debtBeforePause, "EXPLOIT: Debt decreased in pause cycle!");
            
            vm.warp(block.timestamp + 1); // Minimal time
            
            flow.restart(streamId, rate);
            vm.warp(block.timestamp + 10 minutes);
        }

        uint256 finalDebt = flow.totalDebtOf(streamId);

        // Final debt should be >= initial since time only increased
        assertGe(finalDebt, initialDebt, "EXPLOIT: Debt manipulation via pause cycles!");
    }

    /// @notice Test pause at boundary conditions
    function test_POC_PauseAtSnapshotBoundary() public {
        UD21x18 rate = ud21x18(1e12); // Small rate
        
        // Create stream starting in the future
        uint40 futureStart = uint40(block.timestamp + 1 hours);
        streamId = flow.create({
            sender: users.sender,
            recipient: users.recipient,
            ratePerSecond: rate,
            startTime: futureStart,
            token: usdc,
            transferable: TRANSFERABLE
        });

        uint128 depositAmount = 100_000e6;
        deal({ token: address(usdc), to: users.sender, give: depositAmount });
        usdc.approve(address(flow), depositAmount);
        flow.deposit(streamId, depositAmount, users.sender, users.recipient);

        // Warp to exactly when stream starts
        vm.warp(futureStart);

        // Warp just 1 second
        vm.warp(block.timestamp + 1);
        uint256 debtAfter1Sec = flow.totalDebtOf(streamId);

        // Now pause immediately
        flow.pause(streamId);
        uint256 debtAfterPause = flow.totalDebtOf(streamId);

        assertGe(debtAfterPause, debtAfter1Sec, "EXPLOIT: Pause at boundary decreased debt!");
    }
}
