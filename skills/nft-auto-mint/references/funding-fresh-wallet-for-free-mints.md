# Funding a Fresh Wallet for Free Mints

Session-derived pattern for Ethereum free mints when the requested wallet lacks a private key or the user asks to create a fresh wallet and fund it from the primary wallet.

## Use case

- User wants mint from a secondary/fresh wallet.
- Primary wallet key is available in runtime as `PRIVATE_KEY`.
- Secondary wallet key is missing or user asks to create a new one.
- Mint is free (`value=0`) but requires gas on Ethereum mainnet.

## Safe workflow

1. Load primary key from environment only; never print private keys.
2. Generate a fresh wallet via `eth_account.Account.create()`.
3. Save the new wallet address and private key to `/root/.hermes/.env` or the active Hermes env path with `0600` permissions.
   - Use task-specific names if appropriate, e.g. `ONI_WALLET2_ADDRESS`, `ONI_WALLET2_PRIVATE_KEY`.
4. Query contract state before funding:
   - paused flag (`isPaused()` if present)
   - free remaining/supply
   - `freeMinted(address)` or equivalent for the new wallet
   - estimate gas for the free mint call
5. Calculate funding amount from gas price and gas estimate:
   - Fund enough for `gas_limit * gas_price` plus buffer.
   - For Ethereum low-fee conditions, a practical minimum like `0.00008 ETH` covered a ~105k-gas free mint at ~0.37 gwei, leaving dust for future gas.
6. Send ETH topup from primary wallet to fresh wallet.
7. Wait for topup receipt and require `receipt.status == 1` before attempting mint.
8. Execute mint from fresh wallet.
9. Wait for mint receipt and require `receipt.status == 1` before saying success.
10. Verify NFT ownership with `balanceOf(new_wallet)` and, if available, `tokensOfOwner(new_wallet)`.

## Pitfalls

- Do not claim success after `send_raw_transaction`; only after receipt status confirms.
- Do not print or chat private keys. Store them in env and report only the variable names and address.
- If the user says "free mint", prefer the explicit free function (`freemint()`, `freeMint()`, etc.) over paid `mint(uint256)` unless simulation shows otherwise.
- When a known wallet address exists but its private key is not available, do not fake execution. Either ask the user to add the key or create a fresh wallet if the user authorizes it.
