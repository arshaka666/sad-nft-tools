# One Fish / Gold Rod Batch Mint Pattern

Session learning from One Fish (`0xbc50d500a6170a7dfd108e1b908a2c94611bc828`) on Ethereum mainnet.

## Contract shape

- Verified/source available via Sourcify/Blockscout.
- Contract name/symbol: `One Fish` / `ONEFISH`.
- Main batch mint function:
  - `mintFishBatch(uint256 startTokenId, uint256 count, uint256 nonce, uint256 deadline, bytes signature)` payable
- Single mint function:
  - `mintFish(uint256 tokenId, uint256 nonce, uint256 deadline, bytes signature)` payable
- Gold Rod pass function:
  - `buyGoldRod()` payable, price `GOLD_ROD_PRICE = 0.00025 ETH`
- Batch limit:
  - `GOLD_MINT_LIMIT = 5`
- Eligibility/read methods:
  - `hasGoldRod(address)`
  - `goldMinted(address)`
  - `goldMintsUsed(address)`
  - `nextAvailableTokenId()`
  - `mintPrice(uint256)`
  - `mintOpen()` / `paused()`

## Frontend proof flow

The contract requires backend-signed catch vouchers. Direct Etherscan/writeContract cannot work unless the user already has a valid voucher.

Frontend bundle revealed:

```js
PG(player, count, intentNonce) =>
  `One Fish catch proof batch\nPlayer: ${player}\nCount: ${count}\nNonce: ${intentNonce}`

POST /api/catch-proof-batch
{
  player,
  count,
  intentNonce,
  intentMessage,
  intentSignature
}

// response
{
  startTokenId,
  count,
  tokenIds?,
  nonce,
  deadline,
  signature
}
```

Then send:

```solidity
mintFishBatch(startTokenId, count, nonce, deadline, signature)
```

with exact `msg.value = sum(mintPrice(tokenId) for tokenId in [startTokenId, startTokenId+count-1])`.

Single mint uses analogous endpoint `/api/catch-proof` and message:

```text
One Fish catch proof
Player: <address>
Token ID: <tokenId>
Nonce: <intentNonce>
```

## Important backend behavior

The proof API can return:

```json
{"code":"mint_queue_busy","error":"Gold Rod queue is waiting for the current batch to confirm.","retryAfterSeconds":2}
```

This is not a contract revert. It means the project backend is serializing Gold Rod batches. Retry politely using `retryAfterSeconds`.

If repeated automated polling triggers Vercel Security Checkpoint / `403`, stop. Do not claim the mint is impossible; tell the user that proof acquisition must be done via a normal browser session that passes the Vercel security check, then transaction can proceed with the returned voucher.

## Safe execution sequence

1. Check wallet balance and contract state:
   - `mintOpen == true`
   - `paused == false`
   - `hasGoldRod(wallet) == true` for batch mint
   - `goldMinted/goldMintsUsed` to see remaining quota
2. Create intent message exactly as frontend does and sign with wallet key.
3. POST to `/api/catch-proof-batch` with browser-like headers (`Origin`/`Referer`), retry on 202/409/429/503.
4. Once voucher is returned, immediately re-check `nextAvailableTokenId()` and compute exact price range with `mintPrice`.
5. Simulate `mintFishBatch(...)` with exact value.
6. Only broadcast if simulation passes and funds cover `value + gas`.
7. Wait for receipt; only report success when `receipt.status == 1`.
8. Parse `Transfer(0x0, wallet, tokenId)` logs for minted IDs.

## Pitfalls

- Direct Etherscan write with arbitrary nonce/deadline/signature will revert `InvalidCatchProof`.
- `startTokenId` is assigned by backend and tied to the signed voucher; do not guess it from a stale screenshot.
- Prices in the UI are deterministic per token via `mintPrice(tokenId)`, but the currently assigned token IDs can move while the queue is busy.
- Avoid aggressive proof polling; it may trigger Vercel Security Checkpoint and block the session.
- If proof acquisition is blocked by Vercel, clearly report **no transaction was sent**. Never imply mint success without tx receipt.
