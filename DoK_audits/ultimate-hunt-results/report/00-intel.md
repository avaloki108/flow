# Recon — SablierFlow

## Scope
- Target: `flow/src/SablierFlow.sol` plus supporting contracts/interfaces.
- Excluded build/artifacts and node_modules.

## Inventory
- Solidity files: 91 (excluding `node_modules`/`out`).
- Total Solidity LOC: 10,285.
- Largest sources: `SablierFlow.sol` (1,067 LOC), `ISablierFlow.sol` (520 LOC), `SablierFlowState.sol` (167 LOC), `FlowNFTDescriptor.sol` (37 LOC), `Helpers.sol` (33 LOC), `Errors.sol` (103 LOC).
- Artifacts: `flow/ultimate-hunt-results/recon/solidity-files.txt`, `flow/ultimate-hunt-results/recon/solidity-loc.txt`, `flow/ultimate-hunt-results/recon/tree-L4.txt`.

## Inheritance / Architecture
- `SablierFlow` ← `Batch`, `Comptrollerable`, `ERC721`, `ISablierFlow`, `NoDelegateCall`, `SablierFlowState`.
- `SablierFlowState` (abstract) ← `ISablierFlowState`; holds stream storage, aggregate balances, NFT descriptor pointer.
- `FlowNFTDescriptor` implements `IFlowNFTDescriptor`.

## External Value Transfer Surfaces
- ERC20 interactions via `SafeERC20`:
  - Deposits: `_deposit` uses `safeTransferFrom` into contract.
  - Withdrawals: `_withdraw` uses `safeTransfer` to recipient after state updates and fee check.
  - Refunds: `_refund` uses `safeTransfer` back to sender.
  - Recover: `recover` transfers surplus to comptroller-chosen address.
  - Utility: `transferTokens` exposes arbitrary `safeTransferFrom(msg.sender, to, amount)`.
- No `call{value}`/`transfer`/`send`/`delegatecall`/`assembly` in `flow/src`.

## Control Flows (pause / restart / void)
- `pause`: ensures stream started, then sets `ratePerSecond` to zero via `_adjustRatePerSecond`.
- `restart`: requires paused/not voided; sets new `ratePerSecond`.
- `void`: callable by sender or approved recipient; writes off uncovered debt (or snapshots ongoing debt), zeros rate, sets `isVoided`, updates snapshot time.
- `withdraw`: requires `msg.value >= comptroller.calculateMinFeeWeiFor(sender)`, bounds amount to withdrawable debt, updates debt/balance before transferring tokens.

## Reentrancy / Surfaces
- No `nonReentrant` guard; ERC20 transfers happen after state updates but remain externally callable (malicious ERC777-style tokens could reenter read paths). `NoDelegateCall` only blocks delegatecall.
- `transferTokens` is unconstrained (any caller can move their own tokens to arbitrary `to`), primarily a helper but increases interaction surface.

## Static Analysis (initial)
- Slither run (config fixed) emits IR generation errors (`NoneType` during IR) yet produced JSON: `flow/ultimate-hunt-results/static/slither.json`; exit code 255. Findings include likely false positives: uninitialized storage (mappings), unused private helpers, const/immutable suggestions, interface implementation warning on `aggregateAmount`.
- Slitheryn run mirrored IR issues + noisy AI heuristics; JSON at `flow/ultimate-hunt-results/static/slitheryn.json`; exit code 255.

## Next Steps
- Deep-dive debt accounting invariants (`_totalDebtOf`, `_ongoingDebtScaledOf`, `_refundableAmountOf`).
- Run remaining static tools (Securify2.5, Aderyn2.0) and symbolic (Mythril/Oyente), then fuzzing (Foundry/Echidna/Medusa) per plan.
