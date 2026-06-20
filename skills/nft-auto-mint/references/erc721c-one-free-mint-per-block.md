# ERC721C One-Free-Mint-Per-Block Race Pattern (MYTHROT-style)

Use this for contracts that expose `freeMint()` plus state like `lastFreeMintBlock`, `hasMintedFree(address)`, `canFreeMint(address)`, and comments/mechanics indicating exactly one free winner per Ethereum block.

## Contract signals

Typical ABI/source signals:

- `function freeMint() external nonpayable`
- `mintOpen() -> bool`
- `lastFreeMintBlock() -> uint256`
- `blockSlotClaimed() -> bool`
- `hasMintedFree(address) -> bool`
- `canFreeMint(address) -> bool`
- `balanceOf(address) -> uint256`
- `totalMinted()`, `TOTAL_SUPPLY()`, `remaining()`
- Revert string: `Block slot already claimed`

Mechanics seen on MYTHROT:

- Only one free mint succeeds per block globally.
- Each wallet can win free mint only once.
- Free mint is gas-only, but failed race transactions still consume gas and nonce.
- Winning `freeMint()` gas used was about `118,366`.

## Execution strategy

1. Fetch verified source/ABI from Sourcify or Blockscout if Etherscan blocks/API key unavailable.
   - Sourcify metadata example: `https://repo.sourcify.dev/contracts/full_match/1/<address>/metadata.json`
   - Blockscout legacy ABI endpoint often works: `https://eth.blockscout.com/api?module=contract&action=getabi&address=<address>`
2. Preflight each wallet:
   - ETH balance
   - nonce
   - `hasMintedFree(wallet)`
   - `balanceOf(wallet)`
   - `mintOpen()`, `remaining()`, `lastFreeMintBlock()`
3. Do **not** rely on `estimate_gas` when current block slot is already claimed; it will revert with `Block slot already claimed` even though next-block tx can succeed.
4. Build raw type-2 tx with explicit gas and fee:
   - `gas = 125000` (MYTHROT used ~118366)
   - use priority around recent winners; in the session, 0.8–1.0 gwei priority/maxFee won reliably while lower bids often lost.
   - keep wallet funding in mind: `gasLimit * maxFeePerGas` must fit balance, even if actual base fee is lower.
   - For hot races, size the wallet for the *cap*, not the expected spend. A 125k gas tx at 1.0 gwei maxFee requires `0.000125 ETH` available just to broadcast; add headroom if you may retry.
   - Prefer one decisive bid per wallet over repeated low bids. If the first attempt reverts from a lost slot, re-check `hasMintedFree`, balance, and recent winner fees before deciding whether to top up and retry.
5. Wait for a fresh block, then send immediately after detecting it. The tx targets the next block’s open slot.
6. Broadcast to multiple stable RPCs if available, but avoid slow/dead RPCs in the hot path because one hanging send can miss the block.
7. Always wait for receipt and check `receipt.status == 1`. A revert means the slot was lost; it consumed gas/nonce.
8. Verify post-mint with `hasMintedFree(wallet)` and `balanceOf(wallet)`. Parse token IDs from the `FreeMint(address,uint256,uint256)` event if Transfer parsing misses due topic formatting.

## Token ID discovery

For this pattern, the contract may emit both:

- standard `Transfer(address indexed from, address indexed to, uint256 indexed tokenId)`
- custom `FreeMint(address indexed minter, uint256 tokenId, uint256 blockNumber)`

If Transfer parsing returns empty, query/decode `FreeMint` logs:

```python
from eth_utils import keccak
free_topic = '0x' + keccak(text='FreeMint(address,uint256,uint256)').hex()
wallet_topic = '0x' + '0' * 24 + wallet.lower()[2:]
logs = w3.eth.get_logs({
    'fromBlock': latest - 200,
    'toBlock': latest,
    'address': contract,
    'topics': [free_topic, wallet_topic],
})
# data[0:32] = tokenId, data[32:64] = blockNumber
```

## Pitfalls

- A wallet can fail multiple block races and still show `hasMintedFree == false`; do not report minted unless receipt success or post-mint balance confirms.
- Failed race txs can leave wallets underfunded for another aggressive attempt. Calculate remaining balance before retrying.
- **Balance reads after funding can be stale on some public RPCs even after `receipt.status == 1`.** If a top-up receipt is confirmed but the recipient balance appears unchanged, do not assume the transfer failed; verify the transaction `value`/receipt and re-read from a fresh RPC or after a few blocks. In the MYTHROT session, publicnode returned stale recipient balances immediately after successful funding; later reads showed the expected `0.00018 ETH` balances.
- **Funding cap must include the next bid strategy, not just the nominal gas spend.** EIP-1559 senders must be able to cover `gasLimit * maxFeePerGas` at broadcast time. If a wallet is funded with only ~$0.20, one failed race at ~0.7 gwei effective gas can leave it unable to broadcast another 0.75–1.0 gwei cap tx even though the actual previous gas spent was smaller than the cap.
- For one-slot-per-block races, avoid multi-attempt loops that keep spending from the same underfunded wallet. Prefer **one high-bid attempt per wallet**, then stop, verify, and top up before retrying. Repeated low/mid bids (e.g. 0.58–0.85 gwei priority during a busy MYTHROT run) can lose several blocks and drain wallets without minting.
- If using buffered Python in background jobs, run scripts with `python -u` or `print(..., flush=True)` so progress is visible.
- Some RPC endpoints may answer `eth_blockNumber` but 403 or stall on `eth_call`/broadcast. Treat RPC choice as hot-path critical; keep a short list of responsive endpoints and remove slow ones during race mints.
