# Token-Gated Pass Rotation + USD Funding Pattern

Use this when a mint is allowlist/token-gated but only one wallet holds the required pass NFT, and the user wants to mint across multiple generated wallets.

## Pattern

1. Verify the gate pass ownership first:
   - `ownerOf(passTokenId)` must equal the current wallet before minting.
   - `balanceOf(currentWallet)` on the gate collection should be > 0.
2. Simulate the target mint from the current wallet with zero value and no unnecessary fee fields:
   - For Remanent-style contracts, `mint(uint256)` may be free only for the first mint (`mintedPerWallet == 0`) and only while the wallet holds a gate NFT.
   - Decode custom errors before sending: `NotAllowlisted()` means the pass is not currently held by that wallet.
3. Send the mint transaction and wait for `receipt.status == 1` before doing anything else.
4. Parse the minted NFT token IDs from `Transfer(0x0, wallet, tokenId)` logs in the receipt.
5. Transfer the gate pass to the next wallet with `safeTransferFrom(current, next, passTokenId)`.
6. Wait for the gate-transfer receipt and verify `ownerOf(passTokenId) == nextWallet` before starting the next wallet.
7. Repeat sequentially. Do not parallelize wallets that share one moving pass NFT.

## Funding Before Rotation

Each wallet needs enough ETH for **both** actions if it will mint and then pass the gate NFT onward:

- Current wallet except final wallet: mint gas + pass-transfer gas.
- Final wallet: mint gas only unless the pass should be returned.
- If the user asks to fund by USD amount, fetch a live ETH/USD quote, compute `amount_wei = int((usd / eth_usd) * 1e18)`, and report quote source.

## Fee/Nonce Lessons

- Very low `maxFeePerGas` can cause transactions to disappear from the RPC/mempool when base fee rises before inclusion. If a sent tx times out, check both `get_transaction_receipt(tx)` and `get_transaction(tx)` plus `get_transaction_count(address, 'latest'/'pending')` before retrying.
- If the tx is not found and latest/pending nonce are equal, treat the nonce as clear and resend with a higher fee cap.
- For small-wallet funding batches, sending multiple transfers from the primary with sequential pending nonces works, but every receipt must still be checked individually.
- Use a fee cap floor during funding (e.g. `max(baseFee*2 + priority, 1.2 gwei)`) when base fee is volatile; otherwise a low-fee tx can stall or vanish.

## Reporting

- Never call a mint or transfer successful until `receipt.status == 1` is confirmed.
- If a previous process was interrupted, explicitly say which transactions were confirmed and which were only broadcast/pending/not found.
- Report tx URLs, receipt status, gas used, and final balances/ownership. Never print private keys.

## Remanent Example Details

Remanent (`0xb2b8083f52fdbae4ccd04095c3e09d9d9ce840bf`) has a `mint(uint256)` function where the first mint can be free, but in phase 1 the caller must hold one of the gate collections. The relevant observed custom error was:

- `0x06fb10a9` = `NotAllowlisted()`

The pass collection `0x4A93f81BF6e6cC3659Ff429156218413c6f746d7` became one of the gate collections; transferring token `2670` to W1 made W1 eligible for simulation, but wallet gas still had to be sufficient for mint and subsequent pass transfer.