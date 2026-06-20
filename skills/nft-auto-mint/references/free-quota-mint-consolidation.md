# ThreeCH0-style free quota mint + consolidation

Session pattern validated on Ethereum mainnet contract `ThreeCH0` (`0xd0c9ec4f4c92794edac3a5446570200f851b27bc`). Use this as a reusable pattern for ERC721 contracts with a free-per-wallet quota implemented inside `mint(uint256)`.

## Contract signals

ABI/source indicators:

- `mint(uint256 qty) external payable`
- `FREE_PER_WALLET() -> uint256`
- `freeMinted(address) -> uint256`
- `mintOpen() -> bool`
- `mintPrice() -> uint256`
- `tokensOfOwner(address) -> uint256[]`
- `isIdMinted(uint256) -> bool`
- `Minted(address indexed to, uint256 qty, uint256[] ids)`

Source logic shape:

```solidity
uint256 alreadyFree = freeMinted[msg.sender];
uint256 freeLeft    = alreadyFree >= FREE_PER_WALLET ? 0 : FREE_PER_WALLET - alreadyFree;
uint256 freeNow     = qty <= freeLeft ? qty : freeLeft;
uint256 paidQty     = qty - freeNow;
uint256 cost        = paidQty * mintPrice;
require(msg.value >= cost, "Insufficient ETH");
freeMinted[msg.sender] += freeNow;
```

For wallets with `freeMinted == 0` and `FREE_PER_WALLET == 2`, call `mint(2)` with `value=0`.

## Preflight checklist

1. Query:
   - `mintOpen()` must be true
   - `paused()` must be false if present
   - `totalSupply() + qty <= maxSupply()`
   - `freeMinted(wallet) < FREE_PER_WALLET`
   - `balanceOf(wallet)` for existing holdings
2. Simulate `mint(qty)` with `value=0` before sending.
3. Estimate gas per wallet; do not rely on “free mint” meaning cheap gas.

## Gas lessons

This pattern can be expensive because it mints random IDs and uses enumerable bookkeeping.

Observed on ThreeCH0:

- `mint(2)` estimate: ~348,238 gas
- actual `mint(2)`: ~344,338 gas
- at ~0.20 gwei effective gas price, cost was ~0.000071–0.000075 ETH per wallet
- a safe funding threshold was ~0.00009 ETH per wallet; tiny wallets with `0.00002–0.00005 ETH` were insufficient

When selecting wallets, filter by `balance >= gas_limit * maxFeePerGas`, not merely by nonzero balance.

## Execution pattern

For each wallet:

1. `free = freeMinted(wallet)`
2. `qty = FREE_PER_WALLET - free`
3. If `qty <= 0`, skip.
4. `estimate_gas(mint(qty), value=0)`
5. Build type-2 tx with explicit gas limit (`int(est*1.15)+10000` or higher).
6. Send and wait for receipt.
7. Verify `receipt.status == 1` and `balanceOf(wallet)` increased by `qty`.
8. Use `tokensOfOwner(wallet)` to list token IDs.

## Consolidation pattern

After minting, transfer all token IDs to the primary wallet:

1. For each source wallet, call `tokensOfOwner(source)`.
2. For each token, estimate `transferFrom(source, primary, tokenId)` from the source wallet.
3. If `transferFrom` estimate fails, try `safeTransferFrom`.
4. Send one tx per token, wait for each receipt, and verify final ownership.

Observed transfer costs on ThreeCH0:

- first token from a wallet: ~92k–95k gas
- second token from same wallet: ~85k gas
- at ~0.20 gwei, each transfer was roughly `0.000018–0.000021 ETH`

## Verification pitfall

Immediate `ownerOf(tokenId)` reads right after a transfer receipt can appear stale/inconsistent on some RPC/indexing paths, especially when doing sequential transfers. Do not report success based on a single stale read if receipt is confirmed. After all transfers, re-query `tokensOfOwner(primary)`, `balanceOf(primary)`, and `ownerOf(tokenId)` for every transferred token at the latest block. Only then report final success.

## Reporting gas cost

For final cost reports, compute each tx fee from on-chain receipt:

```python
fee = receipt.gasUsed * receipt.effectiveGasPrice
```

Separate mint fee and transfer fee, then optionally convert ETH to IDR with a live ETH/IDR quote. In this session, 4 mint txs + 8 transfer txs cost about `0.000446638688380089 ETH` total at the time of calculation.
