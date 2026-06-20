# Wallet Generation Reference

## Python eth-account (Hermes Venv)

Generate Ethereum wallets using `eth_account` in the Hermes Agent venv.

### Installation (one-time)

```bash
/usr/local/lib/hermes-agent/venv/bin/python -m ensurepip --upgrade
/usr/local/lib/hermes-agent/venv/bin/python -m pip install eth-account
```

### Generate One Wallet

```bash
/usr/local/lib/hermes-agent/venv/bin/python -c "
from eth_account import Account
acct = Account.create()
print(f'Address: {acct.address}')
print(f'Private Key: {acct.key.hex()}')
"
```

### Generate Multiple Wallets

```bash
/usr/local/lib/hermes-agent/venv/bin/python -c "
from eth_account import Account

for i in range(5):
    acct = Account.create()
    print(f'Wallet {i+1}:')
    print(f'  Address: {acct.address}')
    print(f'  Private Key: {acct.key.hex()}')
"
```

### Save to Memory

After generation, persist wallet info via the memory tool:

```python
memory(action='add', target='memory', content='Wallet N: ADDRESS\\nPrivate Key: 0x...')
```

### Current Wallet Map (from memory)

This user maintains 3 wallets for parallel minting:

| # | Address | Role |
|---|---------|------|
| 1 | `0xprimary...wallet` | Primary (`.env` PRIVATE_KEY) |
| 2 | `0xabcd...1234` | Secondary |
| 3 | `0xtertiary...5678` | Tertiary |

> See `references/wallet-addresses.md` for full details.

### Usage in Minting

Set the desired wallet as active before minting:

```bash
export PRIVATE_KEY="0xTHE_PRIVATE_KEY"
```

Or pass inline in Node.js scripts:

```javascript
const wallet = new ethers.Wallet("0xPRIVATE_KEY", provider);
```

## Security Notes

- Private keys are **not recoverable**. Save them immediately to memory.
- Never share private keys or commit them to git.
- The Hermes venv is local to the VPS — keys are as safe as the host.
- For production, use a hardware wallet or multisig for large holdings.
