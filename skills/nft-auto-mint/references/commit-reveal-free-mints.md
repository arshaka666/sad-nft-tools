# Commit-Reveal Free Mint Pattern (Disclosure Visitors-style)

Use this for free mints that are not single-call `mint()`, but require a two-step commit/reveal flow.

## Signals

ABI/source includes functions like:
- `commit(bytes32 commitment)`
- `revealAndMint(bytes32 salt, uint256 cellId)`
- `commitmentFor(address account, bytes32 salt)`
- `commits(address) -> (bytes32 commitment, uint64 commitBlock, uint64 targetBlock)`
- constants such as `MIN_DELAY` and `REVEAL_WINDOW`
- per-wallet guard such as `minted(address)` / `AlreadyMinted()`

Example contract logic:
```solidity
commitment = keccak256(abi.encode(account, salt, block.chainid, address(this)))
targetBlock = block.number + MIN_DELAY
// later:
revealAndMint(salt, cellId)
```

## Workflow

1. Fetch verified source/ABI (Blockscout/Sourcify) and confirm mint is open.
2. For every wallet, check:
   - ETH balance
   - `minted(wallet)`
   - existing `commits(wallet)`
   - `balanceOf(wallet)`
   - `totalMinted() < MAX_SUPPLY()`
3. Generate a random 32-byte `salt` per wallet and save it to a local state file before broadcasting commit.
4. Compute commitment exactly as the contract expects. For Solidity `abi.encode`, use `eth_abi.encode`, not packed encoding:
   ```python
   from eth_abi import encode
   commitment = Web3.keccak(encode(
       ['address','bytes32','uint256','address'],
       [account, salt, chain_id, contract]
   ))
   ```
5. Broadcast `commit(commitment)` and wait for receipt `status == 1`.
6. Read `targetBlock` from `commits(wallet)`. Wait until `block.number > targetBlock`.
7. Reveal before `targetBlock + REVEAL_WINDOW`; otherwise the commit expires and gas is wasted.
8. If the reveal requires a selectable slot/cell/lane, compute the lane off-chain for candidate cells and pick a currently-free lane.
9. Estimate `revealAndMint(salt, cellId)` and broadcast only if wallet has enough ETH for the reveal gas.
10. Wait for receipt and verify `minted(wallet) == true` and/or `balanceOf(wallet) > 0` before reporting success.

## Cell/lane selection pattern

For contracts that derive a lane/slot from blockhash + wallet + salt + cell id:
```python
from eth_abi import encode

def lane_for(target_seed, account, salt, cell_id):
    h = Web3.keccak(encode(
        ['bytes32','address','bytes32','uint256'],
        [target_seed, account, salt, cell_id]
    ))
    return int.from_bytes(h, 'big') % LANES
```

Scan cells with `cellStatus(cellId)` and choose a cell where `laneMask & (1 << lane) == 0`.

## Gas/balance pitfalls

Commit-reveal mints can look “free” but require two transactions. Tiny burner wallets need enough ETH for both:
- `commit()` can be ~75k gas.
- `revealAndMint()` can be ~250k+ gas.
- Type-2 transactions lock `gasLimit * maxFeePerGas`, not just expected gas used.

When balances are tiny:
- Use a tight but valid EIP-1559 max fee, e.g. `maxFeePerGas = baseFee * 1.05–1.15 + small priority`, rather than a broad 2x multiplier.
- Estimate reveal with fee fields omitted or with `gasPrice: 0` if RPC simulation complains about insufficient funds.
- Top up before committing or immediately after commit receipt; do not wait until near the reveal expiry.
- Do not claim the wallet minted after commit only; commit is not mint success.
- If a wallet has committed but not revealed, warn about the remaining reveal window and top-up requirement.

## Expired commit pitfall

Some commit-reveal contracts do **not** expose a clear/reset/cancel commit function. If `commit()` checks `commits[msg.sender].commitment != 0` and reverts `AlreadyCommitted()`, an expired unrevealed commit can permanently lock that wallet out of minting: `revealAndMint()` reverts expired, while `commit()` cannot be called again.

Before trying to recover expired commit wallets:
1. Fetch source/ABI (Sourcify often works when explorer APIs are blocked).
2. Search for clear/reset/cancel commit functions.
3. If no such function exists, report the wallet as expired/locked instead of attempting recommit.

For Disclosure Visitors-specific selectors and source notes, see `references/disclosure-visitors-commit-reveal.md`.

## Reporting rule

Report wallets in three buckets:
- Confirmed minted: receipt `status == 1` plus on-chain `minted/balanceOf` verification.
- Committed but not revealed: include target/reveal window and exact blocker, usually insufficient gas.
- Not attempted/skipped: include balance/eligibility reason.
