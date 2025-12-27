// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity >=0.8.22;

import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import { UD21x18 } from "@prb/math/src/UD21x18.sol";

import { IFlowNFTDescriptor } from "./../interfaces/IFlowNFTDescriptor.sol";
import { ISablierFlowState } from "./../interfaces/ISablierFlowState.sol";
import { Errors } from "./../libraries/Errors.sol";
import { Flow } from "./../types/DataTypes.sol";

/// @title SablierFlowState
/// @notice See the documentation in {ISablierFlowState}.
abstract contract SablierFlowState is ISablierFlowState {
    /*//////////////////////////////////////////////////////////////////////////
                                  STATE VARIABLES
    //////////////////////////////////////////////////////////////////////////*/

    /// @inheritdoc ISablierFlowState
    mapping(IERC20 token => uint256 amount) public override aggregateAmount;

    /// @inheritdoc ISablierFlowState
    address public override nativeToken;

    /// @inheritdoc ISablierFlowState
    uint256 public override nextStreamId;

    /// @inheritdoc ISablierFlowState
    IFlowNFTDescriptor public override nftDescriptor;

    /// @dev Sablier Flow streams mapped by unsigned integers.
    mapping(uint256 id => Flow.Stream stream) internal _streams;

    /*//////////////////////////////////////////////////////////////////////////
                                    CONSTRUCTOR
    //////////////////////////////////////////////////////////////////////////*/

    /// @param initialNFTDescriptor The address of the initial NFT descriptor.
    constructor(address initialNFTDescriptor) {
        nextStreamId = 1;
        nftDescriptor = IFlowNFTDescriptor(initialNFTDescriptor);
    }

    /*//////////////////////////////////////////////////////////////////////////
                                     MODIFIERS
    //////////////////////////////////////////////////////////////////////////*/

    /// @dev Checks that `streamId` does not reference a null stream.
    modifier notNull(uint256 streamId) {
        _notNull(streamId);
        _;
    }

    /// @dev Checks that `streamId` does not reference a paused stream. Note that this implicitly checks that the stream
    /// is not voided either.
    modifier notPaused(uint256 streamId) {
        if (_streams[streamId].ratePerSecond.unwrap() == 0) {
            revert Errors.SablierFlowState_StreamPaused(streamId);
        }
        _;
    }

    /// @dev Checks that `streamId` does not reference a voided stream.
    modifier notVoided(uint256 streamId) {
        if (_streams[streamId].isVoided) {
            revert Errors.SablierFlowState_StreamVoided(streamId);
        }
        _;
    }

    /// @dev Checks the `msg.sender` is the stream's sender.
    modifier onlySender(uint256 streamId) {
        if (msg.sender != _streams[streamId].sender) {
            revert Errors.SablierFlowState_Unauthorized(streamId, msg.sender);
        }
        _;
    }

    /*//////////////////////////////////////////////////////////////////////////
                          USER-FACING READ-ONLY FUNCTIONS
    //////////////////////////////////////////////////////////////////////////*/

    /// @inheritdoc ISablierFlowState
    function getBalance(uint256 streamId) external view override notNull(streamId) returns (uint128 balance) {
        balance = _streams[streamId].balance;uint128 certora_local58 = balance;assembly ("memory-safe"){mstore(0xffffff6e4604afefe123321beef1b02fffffffffffffffffffffffff0000003a,certora_local58)}
    }

    /// @inheritdoc ISablierFlowState
    function getRatePerSecond(uint256 streamId)
        external
        view
        override
        notNull(streamId)
        returns (UD21x18 ratePerSecond)
    {
        ratePerSecond = _streams[streamId].ratePerSecond;assembly ("memory-safe"){mstore(0xffffff6e4604afefe123321beef1b02fffffffffffffffffffffffff0002003b,0)}
    }

    /// @inheritdoc ISablierFlowState
    function getSender(uint256 streamId) external view override notNull(streamId) returns (address sender) {
        sender = _streams[streamId].sender;assembly ("memory-safe"){mstore(0xffffff6e4604afefe123321beef1b02fffffffffffffffffffffffff0000003c,sender)}
    }

    /// @inheritdoc ISablierFlowState
    function getSnapshotDebtScaled(uint256 streamId)
        external
        view
        override
        notNull(streamId)
        returns (uint256 snapshotDebtScaled)
    {
        snapshotDebtScaled = _streams[streamId].snapshotDebtScaled;assembly ("memory-safe"){mstore(0xffffff6e4604afefe123321beef1b02fffffffffffffffffffffffff0000003d,snapshotDebtScaled)}
    }

    /// @inheritdoc ISablierFlowState
    function getSnapshotTime(uint256 streamId) external view override notNull(streamId) returns (uint40 snapshotTime) {
        snapshotTime = _streams[streamId].snapshotTime;assembly ("memory-safe"){mstore(0xffffff6e4604afefe123321beef1b02fffffffffffffffffffffffff0000003e,snapshotTime)}
    }

    /// @inheritdoc ISablierFlowState
    function getStream(uint256 streamId) external view override notNull(streamId) returns (Flow.Stream memory stream) {
        stream = _streams[streamId];assembly ("memory-safe"){mstore(0xffffff6e4604afefe123321beef1b02fffffffffffffffffffffffff0002003f,0)}
    }

    /// @inheritdoc ISablierFlowState
    function getToken(uint256 streamId) external view override notNull(streamId) returns (IERC20 token) {
        token = _streams[streamId].token;assembly ("memory-safe"){mstore(0xffffff6e4604afefe123321beef1b02fffffffffffffffffffffffff00020040,0)}
    }

    /// @inheritdoc ISablierFlowState
    function getTokenDecimals(uint256 streamId)
        external
        view
        override
        notNull(streamId)
        returns (uint8 tokenDecimals)
    {
        tokenDecimals = _streams[streamId].tokenDecimals;assembly ("memory-safe"){mstore(0xffffff6e4604afefe123321beef1b02fffffffffffffffffffffffff00000041,tokenDecimals)}
    }

    /// @inheritdoc ISablierFlowState
    function isStream(uint256 streamId) external view override returns (bool result) {
        result = _streams[streamId].isStream;assembly ("memory-safe"){mstore(0xffffff6e4604afefe123321beef1b02fffffffffffffffffffffffff00000042,result)}
    }

    /// @inheritdoc ISablierFlowState
    function isTransferable(uint256 streamId) external view override notNull(streamId) returns (bool result) {
        result = _streams[streamId].isTransferable;assembly ("memory-safe"){mstore(0xffffff6e4604afefe123321beef1b02fffffffffffffffffffffffff00000043,result)}
    }

    /// @inheritdoc ISablierFlowState
    function isVoided(uint256 streamId) external view override notNull(streamId) returns (bool result) {
        result = _streams[streamId].isVoided;assembly ("memory-safe"){mstore(0xffffff6e4604afefe123321beef1b02fffffffffffffffffffffffff00000044,result)}
    }

    /*//////////////////////////////////////////////////////////////////////////
                            PRIVATE READ-ONLY FUNCTIONS
    //////////////////////////////////////////////////////////////////////////*/

    /// @dev A private function is used instead of inlining this logic in a modifier because Solidity copies modifiers
    /// into every function that uses them.
    function _notNull(uint256 streamId) private view {assembly ("memory-safe") { mstore(0xffffff6e4604afefe123321beef1b01fffffffffffffffffffffffff00e30000, 1037618708707) mstore(0xffffff6e4604afefe123321beef1b01fffffffffffffffffffffffff00e30001, 1) mstore(0xffffff6e4604afefe123321beef1b01fffffffffffffffffffffffff00e31000, streamId) }
        if (!_streams[streamId].isStream) {
            revert Errors.SablierFlowState_Null(streamId);
        }
    }
}
