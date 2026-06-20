# Disclosure Visitors commit-reveal operational notes

Contract: `0x40f8fC27712c32fCCD77026ED7F71E58E63d1136` (Ethereum mainnet)

## Durable lessons from multi-wallet minting

### Expired commits are permanent wallet locks

Disclosure Visitors has:
- `commit(bytes32)`
- `revealAndMint(bytes32 salt, uint256 cellId)`
- `commits(address) -> (commitment, commitBlock, targetBlock)`
- `MIN_DELAY = 12`
- `REVEAL_WINDOW = 180`
- `AlreadyCommitted()` selector: `0xbfec5558`

Source behavior:
- `commit()` reverts if `commits[msg.sender].commitment != bytes32(0)`.
- `revealAndMint()` reverts if `block.number > targetBlock + REVEAL_WINDOW`.
- There is no public `clear`, `reset`, `cancel`, or overwrite path for expired commits.

Therefore, if a wallet commits but misses the reveal window, that wallet is effectively stuck for this mint: it cannot reveal and cannot commit again. Do not try to “recommit” after expiry; it will revert with `AlreadyCommitted()` and waste time/gas if sent.

### Fund before committing, not after

Because the reveal window is finite, tiny-wallet workflows must ensure enough ETH for both steps before broadcasting commits.

Recommended sequence:
1. Check wallet balance against a full budget for commit + reveal + safety buffer.
2. Top up all candidate wallets before sending any `commit()` tx.
3. Commit wallets.
4. Read each wallet’s `targetBlock` immediately after receipt.
5. Wait only until `max(targetBlock)+1` if batching; then reveal quickly.
6. Avoid slow sequential topups inside the reveal window — topup waits can cause early wallets to expire.

Practical budget observed during this session:
- Commit: ~75,214 gas.
- Reveal: ~254k–280k gas on successful mints; estimate can be ~270k–297k.
- Failed expired reveal can still burn ~38k gas.
- Type-2 tx locks `gasLimit * maxFeePerGas`, so set a tight max fee but leave enough balance headroom. During 0.5–0.7 gwei base-fee periods, tiny balances around `0.00010–0.00014 ETH` were not enough for reveal lock; `~0.00022 ETH` was sometimes borderline. Prefer funding closer to `0.00035–0.00045 ETH` per wallet before committing when base fee is volatile.

### Lane/cell selection

Use target block hash and scan cells for a free derived lane:

```python
from eth_abi import encode
from web3 import Web3

def lane_for(target_seed, account, salt, cell_id):
    h = Web3.keccak(encode(
        ['bytes32','address','bytes32','uint256'],
        [target_seed, account, salt, cell_id]
    ))
    return int.from_bytes(h, 'big') % 8
```

Then call `cellStatus(cellId)` and pick a `cellId` where `laneMask & (1 << lane) == 0`. Under high activity, scan deeper than the first few cells (e.g. up to 1000).

### Verification/reporting

- Count “minted” using `minted(address) == true`, not only `balanceOf(address)`, because NFTs may later be transferred away.
- After consolidation, `balanceOf(source) == 0` is expected; use `ownerOf(tokenId)` for each token to verify destination ownership.
- Immediate `ownerOf()` reads right after a receipt may be stale on some public RPCs; do a final verification pass after all transfers and treat that as authoritative.
- If tokens later leave the main wallet via unrelated outgoing transfers, `balanceOf(main)` will be lower than the number minted/consolidated. For PnL, distinguish mint/transfer gas from subsequent unrelated token movements.

### Gas/PnL accounting pattern

For exact gas fee accounting, use receipt fields:

```python
receipt = w3.eth.get_transaction_receipt(tx_hash)
gas_fee_wei = receipt.gasUsed * receipt.effectiveGasPrice
```

Group by action class:
- commit tx gas
- successful reveal tx gas
- failed reveal tx gas
- NFT transfer/consolidation gas
- topup transfer gas (gas only, exclude the ETH value transferred because unspent value remains in wallets)

For this Disclosure Visitors run, total gas across 74 known txs was `0.001843593274606793 ETH` (~$3.68 at $1,998.17/ETH). This is a reference point, not a fixed estimate.
