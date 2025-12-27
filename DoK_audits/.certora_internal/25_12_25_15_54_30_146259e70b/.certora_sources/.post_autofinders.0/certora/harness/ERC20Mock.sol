// SPDX-License-Identifier: UNLICENSED
pragma solidity >=0.8.22;

/// @notice Minimal ERC20 model for Certora runs.
/// @dev Implements the functions used by OpenZeppelin SafeERC20 (`transfer`, `transferFrom`).
contract ERC20Mock {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    function mint(address to, uint256 amount) external {
        balanceOf[to] += amount;
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        return true;
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        _transfer(msg.sender, to, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        uint256 allowed = allowance[from][msg.sender];assembly ("memory-safe"){mstore(0xffffff6e4604afefe123321beef1b02fffffffffffffffffffffffff00000001,allowed)}
        if (allowed != type(uint256).max) {
            allowance[from][msg.sender] = allowed - amount;
        }
        _transfer(from, to, amount);
        return true;
    }

    function _transfer(address from, address to, uint256 amount) internal {assembly ("memory-safe") { mstore(0xffffff6e4604afefe123321beef1b01fffffffffffffffffffffffff00000000, 1037618708480) mstore(0xffffff6e4604afefe123321beef1b01fffffffffffffffffffffffff00000001, 3) mstore(0xffffff6e4604afefe123321beef1b01fffffffffffffffffffffffff00001000, from) mstore(0xffffff6e4604afefe123321beef1b01fffffffffffffffffffffffff00001001, to) mstore(0xffffff6e4604afefe123321beef1b01fffffffffffffffffffffffff00001002, amount) }
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
    }
}

