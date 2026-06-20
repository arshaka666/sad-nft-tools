# Mirror multi-wallet free mint + consolidation pattern

Session-derived pattern for simple Ethereum ERC-721 mints where each wallet gets one free token and the user wants the NFTs consolidated back to a primary wallet.

## Contract pattern observed

- Site exposed an inline viem ABI with:
  - `mint(uint256 quantity) payable`
  - `mintCost(address,uint256) view returns (uint256)`
  - `totalSupply()`, `MAX_SUPPLY()`, `mintOpen()`
  - `balanceOf(address)`, `ownerOf(uint256)`
- For fresh wallets, `mintCost(wallet, 1) == 0`, so mint tx `value` is `0`; only gas is needed.
- Token IDs were most reliably discovered by parsing the mint transaction receipt's ERC-721 `Transfer(address(0), wallet, tokenId)` logs.

## Workflow

1. Inspect the site HTML/JS for contract address, chain, ABI, and mint function.
2. Confirm contract name/symbol, `mintOpen`, `totalSupply < MAX_SUPPLY`, and `mintCost(wallet,1) == 0` for each source wallet.
3. Fund secondary wallets with a fiat-denominated gas budget if requested (e.g. `$0.30` each), using live ETH/USD and receipt verification.
4. Simulate `mint(1)` from each wallet before sending.
   - For zero-balance pre-funding simulations, use `eth_call` with `gasPrice: 0` or simulate after funding; some RPCs reject EIP-1559 `eth_call` from a zero-balance account with `insufficient funds for gas * price + value` even when the contract logic would pass.
5. Send `mint(1)` with `value=0`, explicit EIP-1559 fees, and a gas limit based on estimate plus buffer.
6. Wait for `receipt.status == 1` for every tx; do not claim success at send time.
7. Verify ownership with both:
   - `balanceOf(wallet)` / `ownerOf(tokenId)` at `latest`
   - Transfer logs in the tx receipt.
8. If consolidating, call `safeTransferFrom(source, primary, tokenId)` from each source wallet, wait for receipts, then verify `ownerOf(tokenId) == primary` and `balanceOf(source) == 0`.

## Verification pitfall

Immediately after a confirmed receipt, some RPC reads may briefly return stale `balanceOf`/`ownerOf` values in the same script. If the receipt is status `1` but a read looks wrong, do **not** report success or failure yet. Re-query at `latest` after the next block or with a fresh call, and parse the receipt `Transfer` logs to confirm the actual owner.

## User-facing style

For this user's NFT tasks, keep the final concise and operational: wallet, token ID, tx hash, owner/balance verification. Avoid long explanations unless the tx fails or the user asks why.
