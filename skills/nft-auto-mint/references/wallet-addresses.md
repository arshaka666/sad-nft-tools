# Active Wallets for NFT Minting

## Wallet Map

| # | Address | Status | Private Key Location |
|---|---------|--------|---------------------|
| 1 | `0xprimary...wallet` | Primary / Default — always check `.env` for PRIVATE_KEY | `~/.hermes/.env` under `PRIVATE_KEY=` |
| 2 | `0xabcd...1234` | Secondary — for parallel minting / 1-per-wallet limits | Saved in Hermes memory |
| 3 | `0xtertiary...5678` | Tertiary — backup | Saved in Hermes memory |

## Usage

- For wallet #1: `PRIVATE_KEY` env var is set in `.env` — used by default
- For wallets #2/#3: Pass `pk=` override to the mint script or export `PRIVATE_KEY` before running

## Switching Active Wallet

```bash
# Before running mint script
export PRIVATE_KEY="0x..."
```

Or inline in Python:
```python
from eth_account import Account
acct = Account.from_key("0x...")
```

## Security

- Private keys are stored in Hermes memory backend (SQLite on VPS)
- Wallet #1 key is also in `~/.hermes/.env`
- No wallets have been broadcast/shared to third parties