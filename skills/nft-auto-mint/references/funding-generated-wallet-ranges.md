# Funding Generated Wallet Ranges by USD Amount

Use this when the user asks to fund a subset of generated Ethereum wallets (for example "wallet 2-5") from the primary wallet with a small fiat-denominated gas budget.

## Pattern

1. Load the generated wallet address list from the saved wallet file, but never print private keys.
   - Generated wallet batch files may have range-specific names such as `wallets_21_50_<timestamp>.json`; do not assume only the older W1-W20 file exists. Prefer the newest file whose stored `wallet_range` or wallet `index` values cover the requested range.
2. Parse the user's wallet range exactly (e.g. Wallet 2, 3, 4, 5), excluding the primary wallet unless explicitly requested.
3. Fetch a live ETH/USD quote from two lightweight APIs if possible, then use one quote to compute:
   - `amount_wei = int((usd_amount / eth_usd) * 1e18)`
4. Load the primary private key from `PRIVATE_KEY` in runtime env only; verify the derived address matches the known primary wallet before signing.
5. Send one EIP-1559 ETH transfer per recipient:
   - `type: 2`, `chainId: 1`, `gas: 21000`
   - For cheap mainnet funding in low-fee conditions, prefer `maxPriorityFeePerGas = 0.01 gwei` first. This has confirmed reliably when base fee is low (~0.2–0.3 gwei) and keeps per-transfer gas tiny.
   - Use `maxFeePerGas = max(int(baseFee*1.15) + priority, 0.12 gwei)` for cheap mode. For faster/more conservative mode use `baseFee*1.4 + priority`.
   - If the user asks for a USD amount (e.g. `$0.20 each`), compute `amount_wei` from a live ETH/USD quote and print the exact ETH amount per wallet before sending.
6. Wait for each transfer receipt and require `receipt.status == 1` before reporting success.
7. Re-read balances from `latest` after receipts; some RPC reads immediately after a receipt can appear stale for a recipient even though the receipt is confirmed.
8. Report only addresses, amounts, tx hashes, receipt status, and verified balances — never private keys.

## Pitfall: background funding scripts with delayed output

If a funding script is run in the background and `process.wait` times out with no output, do not assume failure or success. Poll/log the process. Some successful runs may emit all output only near the end because of network calls or buffering. Only report success after reading the final log and verifying each `RECEIPT status=1` plus post-transfer balances.

## EIP-1559 cheap funding parameters validated

For low-fee Ethereum mainnet conditions around `baseFee ~= 0.18-0.30 gwei`, the following funding profile confirmed reliably for sequential wallet top-ups while keeping per-transfer gas tiny:

- `type: 2`, `chainId: 1`, `gas: 21000`
- `maxPriorityFeePerGas = 0.01 gwei`
- `maxFeePerGas = max(int(baseFee * 1.15) + priority, 0.12 gwei)`
- Send sequential nonces from primary and wait for each receipt `status == 1` before final reporting.
- For `$0.20 each` funding, compute ETH from a live quote and expect around `0.0001066-0.0001069 ETH` when ETH is ~$1,870.
- Always preflight total requirement: `amount_wei * n + 21000 * maxFeePerGas * n`, and abort if the primary balance is below this max need.

## Pitfall: eth_call from zero-balance generated wallets

When simulating a free mint from an empty wallet, some RPCs reject `eth_call` if the transaction includes EIP-1559 fee fields because the simulated sender cannot cover `gas * price`, even for a call. For zero-value free-mint simulation from empty wallets, either:

- omit fee fields and rely on call defaults, or
- use legacy `gasPrice: 0` for the simulation call.

Do not treat this specific `insufficient funds for gas * price + value` during `eth_call` as a mint-contract failure if the wallet has not yet been funded. Fund first or re-run simulation with `gasPrice: 0`.
