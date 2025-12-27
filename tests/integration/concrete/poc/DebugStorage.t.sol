// SPDX-License-Identifier: UNLICENSED
pragma solidity >=0.8.22;

import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import { ud21x18, UD21x18 } from "@prb/math/src/UD21x18.sol";
import { console2 } from "forge-std/src/console2.sol";

import { Integration_Test } from "../../Integration.t.sol";

/// @title DebugStorage_POC
/// @notice Debug the actual storage operations
contract DebugStorage_POC is Integration_Test {
    uint256 internal streamId;

    function setUp() public override {
        Integration_Test.setUp();
    }

    /// @notice Trace through the exact code path
    function test_DebugStorage_CodePath() public {
        console2.log("=== DEBUGGING STORAGE OPERATIONS ===");
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

        // Get state before pause
        uint256 snapshotTime = flow.getSnapshotTime(streamId);
        uint256 blockTimestamp = block.timestamp;
        uint256 snapshotDebtScaled = flow.getSnapshotDebtScaled(streamId);
        
        console2.log("State before pause():");
        console2.log("  snapshotTime:", snapshotTime);
        console2.log("  blockTimestamp:", blockTimestamp);
        console2.log("  snapshotTime < blockTimestamp?", snapshotTime < blockTimestamp);
        console2.log("  snapshotDebtScaled:", snapshotDebtScaled);
        console2.log("");

        // Calculate ongoing debt manually
        uint256 elapsedTime = blockTimestamp - snapshotTime;
        uint256 ratePerSecond = flow.getRatePerSecond(streamId).unwrap();
        uint256 ongoingDebtScaled = elapsedTime * ratePerSecond;
        
        console2.log("Calculated values:");
        console2.log("  elapsedTime:", elapsedTime);
        console2.log("  ratePerSecond:", ratePerSecond);
        console2.log("  ongoingDebtScaled:", ongoingDebtScaled);
        console2.log("  ongoingDebtScaled > 0?", ongoingDebtScaled > 0);
        console2.log("");

        // Simulate the exact code path
        console2.log("Simulating _adjustRatePerSecond code path:");
        console2.log("  Line 719: if (snapshotTime < blockTimestamp) {");
        if (snapshotTime < blockTimestamp) {
            console2.log("    -> TRUE: Entering block");
            console2.log("  Line 720: ongoingDebtScaled = _ongoingDebtScaledOf(streamId);");
            console2.log("    -> ongoingDebtScaled =", ongoingDebtScaled);
            console2.log("  Line 723: if (ongoingDebtScaled > 0) {");
            if (ongoingDebtScaled > 0) {
                console2.log("    -> TRUE: Entering block");
                console2.log("  Line 725: snapshotDebtScaled += ongoingDebtScaled;");
                uint256 newSnapshotDebtScaled;
                unchecked {
                    newSnapshotDebtScaled = snapshotDebtScaled + ongoingDebtScaled;
                }
                console2.log("    -> newSnapshotDebtScaled =", newSnapshotDebtScaled);
                console2.log("    -> This should be stored, but let's check...");
            } else {
                console2.log("    -> FALSE: Would skip update");
            }
        } else {
            console2.log("    -> FALSE: Would skip update");
        }
        console2.log("");

        // Actually pause
        console2.log("Executing pause():");
        uint256 debtBefore = flow.totalDebtOf(streamId);
        console2.log("  debtBefore:", debtBefore);
        
        flow.pause(streamId);
        
        uint256 debtAfter = flow.totalDebtOf(streamId);
        uint256 actualSnapshotAfter = flow.getSnapshotDebtScaled(streamId);
        console2.log("  debtAfter:", debtAfter);
        console2.log("  actualSnapshotAfter:", actualSnapshotAfter);
        console2.log("");

        // Check what happened
        if (actualSnapshotAfter == 0 && debtAfter == 0) {
            console2.log("*** MYSTERY: Value is 0 but calculation shows it should be non-zero ***");
            console2.log("  This suggests:");
            console2.log("    1. The addition overflowed (but our check shows it shouldn't)");
            console2.log("    2. There's a type conversion issue");
            console2.log("    3. There's another code path we're missing");
            console2.log("    4. The storage slot is being overwritten elsewhere");
        }
    }

    /// @notice Check if there's a casting issue with uint40
    function test_DebugStorage_TypeCasting() public {
        console2.log("=== CHECKING TYPE CASTING ===");
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

        // Check if block.timestamp casting to uint40 causes issues
        uint256 blockTimestamp = block.timestamp;
        uint40 blockTimestamp40 = uint40(block.timestamp);
        
        console2.log("Type casting check:");
        console2.log("  block.timestamp (uint256):", blockTimestamp);
        console2.log("  block.timestamp (uint40):", blockTimestamp40);
        console2.log("  Casting loss?", blockTimestamp != uint256(blockTimestamp40));
        console2.log("");

        // The issue might be that when we cast block.timestamp to uint40 in _adjustRatePerSecond,
        // and then use it in _ongoingDebtScaledOf, there's a mismatch
        uint256 snapshotTime = flow.getSnapshotTime(streamId);
        console2.log("Snapshot time check:");
        console2.log("  snapshotTime (uint40):", snapshotTime);
        console2.log("  blockTimestamp (uint256):", blockTimestamp);
        console2.log("  blockTimestamp40 (uint40):", blockTimestamp40);
        console2.log("  elapsedTime (uint256 - uint40):", blockTimestamp - snapshotTime);
        console2.log("  elapsedTime (uint40 - uint40):", blockTimestamp40 - uint40(snapshotTime));
        console2.log("");

        // But wait, _ongoingDebtScaledOf uses block.timestamp (uint256), not uint40
        // So that should be fine...
    }
}
