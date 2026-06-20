# Token-Gated Free Mint Relay Pattern

Use this when a contract gives each wallet one free mint only if `mintPhase == 1` and the caller holds a qualifying ERC-721 gate/pass NFT.

## Pattern validated on Remanent-style contracts

1. Verify the mint source, not just frontend state:
   - `mintPhase == 1` means token-gated allowlist.
   - `mintedPerWallet(address) == 0` means the wallet still has its first free mint available.
   - `getGateCollections()` must include the pass collection.
   - `gate.ownerOf(passTokenId)` or `gate.balanceOf(wallet) > 0` must match the active wallet before simulation.

2. Relay one pass NFT across generated wallets:
   - Start from the wallet currently owning the pass.
   - For each wallet: `estimate_gas mint(1)` with `value=0`, send mint, wait for receipt `status == 1`, verify `balanceOf(wallet)` and `mintedPerWallet(wallet)`.
   - Then `safeTransferFrom(currentWallet, nextWallet, passTokenId)`, wait for receipt, verify `ownerOf(passTokenId)`.
   - Repeat until the final wallet; leave the pass on the final wallet unless the user asks to return it.

3. Funding strategy:
   - Do not assume old balances are enough; calculate per-wallet budget from current `baseFeePerGas` plus a cap.
   - For very low base fee conditions, a tight EIP-1559 cap can work better than a blanket `maxFee = 3x base`, because tiny wallets may fail balance checks even though the actual fee would be low.
   - For relay mints, wallets before the last need `mint gas + pass transfer gas`; the last wallet only needs mint gas.
   - If only some wallets are short, top up only those wallets from primary before proceeding.

4. Practical gas numbers seen on Remanent:
   - `mint(1)` estimated around `181,219`, receipt gas used around `178,634`.
   - Gate pass `safeTransferFrom` estimated around `62,975-62,987`, receipt gas used around `57,894-57,906`.
   - Use explicit gas limits around `200,716` for mint and `75,000` for pass transfer when estimates match these values.

5. Verification and token IDs:
   - Always wait for receipt before saying mint/transfer succeeded.
   - Verify `rem.balanceOf(wallet) == 1` and `mintedPerWallet(wallet) == 1` after mint.
   - If receipt log parsing misses token IDs, query `Transfer(address indexed from,address indexed to,uint256 indexed tokenId)` logs from zero address to each wallet over the confirmed block range.
   - Some RPCs lag the head or reject a too-far `toBlock`; retry with that RPC's current `eth_blockNumber` or use another RPC.

## Pitfalls

- If `mint(1)` with `value=0` reverts `NotAllowlisted()`, the wallet does not hold an active gate NFT; transfer the pass first.
- If the previous run was interrupted, check `mintedPerWallet`, `balanceOf`, and the pass owner before resuming. A transaction may have confirmed even though the final chat response was interrupted.
- `InsufficientPayment()` can appear when simulating from a wallet that already used its free mint; use `mintedPerWallet` to decide whether to skip or stop.
- Do not claim a token ID from a receipt until it is parsed from logs or verified by an event query.
