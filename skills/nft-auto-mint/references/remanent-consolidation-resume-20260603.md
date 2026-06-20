# Remanent-style ERC721 multi-wallet consolidation lessons (2026-06-03)

Context: after token-gated relay mints, the task was to consolidate Remanent ERC721 tokens from W1-W30 into the primary wallet.

## Durable workflow lessons

1. **Build an idempotent resume map first**
   - Persist or reconstruct `{wallet_index -> tokenId}` from successful mint receipts / saved state.
   - Before sending any transfer, call `ownerOf(tokenId)`.
   - Skip if `ownerOf(tokenId) == primary`.
   - Only send if `ownerOf(tokenId) == source_wallet`.
   - Treat any other owner as a mismatch and report it, not as success.

2. **Prefer receipt-derived token IDs over broad log scans**
   - Broad `get_logs` scans across large block ranges can hang or be slow on public RPCs.
   - Fast path: parse stored mint transaction hashes, fetch receipts, decode `Transfer(0x0, wallet, tokenId)` logs, then verify with `ownerOf`.
   - Use limited block scans only as fallback when `balanceOf(wallet) > decoded_ids_count`.

3. **Resume after interruption without double-sending**
   - Use a fixed token map and `ownerOf` gates so a rerun is safe.
   - If a process is interrupted after some transfers confirm, rerun the resume script; already-consolidated tokens will be skipped.

4. **Top up only when transfer gas is insufficient**
   - Compute `need = gas_limit * maxFeePerGas` for each source wallet.
   - If source ETH balance is short and primary key is available, top up `need - balance + small_buffer`, wait for receipt status `1`, then re-check balance before sending the NFT transfer.
   - Record topup txs separately from NFT transfer txs.

5. **Verify final ownership, not just transfer receipts**
   - For every intended token, final output should include `ownerOf(tokenId)`.
   - Success condition for the batch: `notMain == []` for the full token set.
   - Do not claim completion from tx sent alone; receipt `status=1` plus final owner check is required.

6. **RPC/output practicalities**
   - If a background process appears stuck with no output, test RPC latency separately and rerun with `PYTHONUNBUFFERED=1` in foreground or with stricter per-request timeouts.
   - Prefer a responsive Alchemy/Infura RPC for sequential receipt waits; keep `ethereum.publicnode.com` as fallback.

## Minimal resume script structure

- Constants: primary wallet, contract, fixed `{wallet_index: tokenId}` map.
- Load source wallet private keys from local JSON files without printing keys.
- For each token:
  1. `owner = ownerOf(tokenId)`
  2. if owner is primary: skip
  3. if owner is not expected source wallet: record mismatch
  4. estimate/default transfer gas
  5. top up source if needed
  6. send `safeTransferFrom(source, primary, tokenId)` with EIP-1559 fee
  7. wait for receipt and check `ownerOf(tokenId)`
- Final verification: list all owners and assert no token remains outside primary.
