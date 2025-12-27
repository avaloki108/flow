// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity >=0.8.22;

/// @title Helpers
/// @notice Library with helper functions in {SablierFlow} contract.
library Helpers {
    /// @notice Descales the provided `amount` from 18 decimals fixed-point number to token's decimals number.
    /// @dev If `decimals` exceeds 18, it will cause an underflow.
    function descaleAmount(uint256 amount, uint8 decimals) internal pure returns (uint256) {assembly ("memory-safe") { mstore(0xffffff6e4604afefe123321beef1b01fffffffffffffffffffffffff00e50000, 1037618708709) mstore(0xffffff6e4604afefe123321beef1b01fffffffffffffffffffffffff00e50001, 2) mstore(0xffffff6e4604afefe123321beef1b01fffffffffffffffffffffffff00e51000, amount) mstore(0xffffff6e4604afefe123321beef1b01fffffffffffffffffffffffff00e51001, decimals) }
        if (decimals == 18) {
            return amount;
        }

        unchecked {
            uint256 scaleFactor = 10 ** (18 - decimals);
            return amount / scaleFactor;
        }
    }

    /// @notice Scales the provided `amount` from token's decimals number to 18 decimals fixed-point number.
    /// @dev If `decimals` exceeds 18, it will cause an underflow. If `amount` exceeds max value of `uint128`, the
    /// result may overflow `uint256`.
    function scaleAmount(uint256 amount, uint8 decimals) internal pure returns (uint256) {assembly ("memory-safe") { mstore(0xffffff6e4604afefe123321beef1b01fffffffffffffffffffffffff00e60000, 1037618708710) mstore(0xffffff6e4604afefe123321beef1b01fffffffffffffffffffffffff00e60001, 2) mstore(0xffffff6e4604afefe123321beef1b01fffffffffffffffffffffffff00e61000, amount) mstore(0xffffff6e4604afefe123321beef1b01fffffffffffffffffffffffff00e61001, decimals) }
        if (decimals == 18) {
            return amount;
        }

        unchecked {
            uint256 scaleFactor = 10 ** (18 - decimals);
            return amount * scaleFactor;
        }
    }
}
