# Contract Sold-Out Detection & Recovery

## Problem

Contracts revert with opaque custom errors like `0xd05cb609` when sold out. The user wastes gas on failed transactions if you don't check supply first.

## Solution: Check Total Supply BEFORE Any Mint

**Always run this check before sending real ETH:**

```python
from web3 import Web3
import requests

w3 = Web3(Web3.HTTPProvider(RPC))

# totalSupply()
data = "0x18160ddd"
r = requests.post(RPC, json={
    "jsonrpc":"2.0","method":"eth_call",
    "params":[{"to":contract_addr, "data":data}, "latest"],
    "id":1
})
total = int(r.json()['result'], 16)

# maxSupply() — try common selectors
for sel in ["0x32cb6b0c", "0x935a8b84", "0x6b20c454"]:
    r = requests.post(RPC, json={
        "jsonrpc":"2.0","method":"eth_call",
        "params":[{"to":contract_addr, "data":sel}, "latest"],
        "id":1
    })
    max_s = int(r.json()['result'], 16)
    if max_s > 0:
        break

if total >= max_s:
    print(f"❌ SOLD OUT: {total}/{max_s}")
    # Inform user immediately — don't attempt mint
else:
    print(f"✅ Supply: {total}/{max_s} remaining")
```

## Error Signal Reference

When gas estimation with `eth_call` (simulation) reverts, decode the error:

| Revert Data | Meaning | Action |
|-------------|---------|--------|
| `0xd05cb609` | **Sold out** (custom Solidity error) | Check totalSupply == maxSupply first |
| `0x64a0ae92` | Mint not open / sale not active | Inform user |
| `0x949ce241` | Insufficient payment | Wrong ETH value sent |
| `0x68f2a8ff` | Block limit reached | Wait & retry with higher priority |
| `0x5107dbe7` | Per-wallet limit reached | Use different wallet |
| `0x4bd3c027` | Sold out (standard error) | Stop |

## Gas Estimation Failure Recovery

If `estimateGas` reverts, try these in order:

1. **Call simulate first** (eth_call) — same as `estimateGas` via web3 but you get the revert data
2. **If simulation also reverts** → decode error from above table, inform user
3. **If simulation succeeds but estimateGas fails** → use fixed gas limit:
   ```python
   gas_limit = 150000  # safe fallback for most mints
   # Or for known contracts: gas_limit = max(previous_successful_gas * 1.3, 80000)
   ```

## Full Safe Mint Pattern

```python
# Step 1: Check totalSupply vs maxSupply → sold out?
# Step 2: Check balanceOf(wallet) → already minted?
# Step 3: Simulate mint via eth_call → catch reverts
# Step 4: Estimate gas (or use fixed fallback)
# Step 5: Check balance >= value + gas
# Step 6: Build, sign, send
# Step 7: WAIT for receipt (claim success only when receipt.status == 1)
```

## Recovery After Failed Mint

If a transaction fails but ETH was spent on gas:

1. No NFT was received (never minted)
2. Gas was wasted (~$0.02-0.15)
3. Wallet nonce was consumed — fetch fresh nonce for next tx
4. Check wallet balance to confirm ETH wasn't lost (only gas was spent)
