// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity >=0.8.22 <0.9.0;

import { Script } from "forge-std/src/Script.sol";

import { FlowNFTDescriptor } from "../../src/FlowNFTDescriptor.sol";
import { SablierFlow } from "../../src/SablierFlow.sol";

/// @notice Deploys Flow Protocol to local testnet with provided comptroller address.
contract LocalDeploy is Script {
    function run(address comptroller)
        public
        returns (SablierFlow flow, FlowNFTDescriptor nftDescriptor)
    {
        vm.startBroadcast();

        nftDescriptor = new FlowNFTDescriptor();
        flow = new SablierFlow(comptroller, address(nftDescriptor));

        vm.stopBroadcast();
    }
}
