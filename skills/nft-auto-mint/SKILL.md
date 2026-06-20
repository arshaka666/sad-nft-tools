---
name: nft-auto-mint
description: "Ethereum NFT minting execution workflow and patterns — contract detection, ABI fetching, Thirdweb/Seadrop/custom ERC-721, competitive free mints, EIP-1559 priority bidding, multi-wallet, and transaction integrity"
version: 2.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [nft, mint, ethereum, ethers, thirdweb, seadrop, web3]
    related_skills: []
---

## NFT Transfer Between Own Wallets

## User Cost-Cap Rule

When the user is sensitive to gas cost or gives a max fee (e.g. "jangan lebih dari $0.10"), enforce the cap before every transfer. Do not broadcast a transfer just because `safeTransferFrom` is cheaper than minting. On a gas-heavy ERC-721, `safeTransferFrom` can still estimate around 65k–85k gas; at high base fee this can exceed $0.10.

Pattern:
1. Parse token IDs from mint receipts (Transfer event from zero address), then verify `ownerOf(tokenId)`.
2. Estimate transfer gas.
3. Fetch current `baseFeePerGas`; set tiny priority (`0.005–0.01 gwei`) for cheap consolidation.
4. Compute worst-case USD fee: `gas_limit * (baseFee + priority) * ETH/USD`.
5. If above the user's cap, **skip/wait** and report the token IDs and current estimate. Never send and apologize later.

## Overview

Mint NFTs on **Ethereum Mainnet** from any contract type. This skill covers the full workflow:

1. **Detect** contract type from address alone
2. **Fetch ABI** automatically via Blockscout
3. **Query** mint price, supply, per-wallet limits, block limits
4. **Mint** with the right function + parameters
5. **Handle** competitive scenarios (block limits, priority bidding)

Supports **Node.js (ethers.js v6)** and **Python (web3.py)** — prefer ethers.js for complex contracts (Thirdweb structs, custom params).

## Prerequisites

- **Node.js** (v18+) with ethers.js v6: `npm install ethers@6` in your project dir
- **Environment**: `PRIVATE_KEY` set as env var (hex with `0x` prefix)
- **RPC**: Free public RPCs work (`https://ethereum.publicnode.com`). For reliability, use Alchemy/Infura RPC.

## Workflow

### Step 0 — Simulation Check: Is Mint Live?

Before sending real ETH, **simulate** the mint call via `eth_call` to confirm the mint is open and your parameters are valid. Also verify the contract name/symbol to confirm you're interacting with the right contract.

```bash
# 1. Check contract name & symbol
curl -s -X POST "https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_call","params":[{"to":"0xCONTRACT","data":"0x06fdde03"},"latest"],"id":1}' \
  | python3 -c "import json,sys; r=json.load(sys.stdin); print('name:', bytes.fromhex(r['result'][130:]).decode().strip(chr(0)))"

curl -s -X POST "https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_call","params":[{"to":"0xCONTRACT","data":"0x95d89b41"},"latest"],"id":1}' \
  | python3 -c "import json,sys; r=json.load(sys.stdin); print('symbol:', bytes.fromhex(r['result'][130:]).decode().strip(chr(0)))"

# 2. Simulate mint(uint256) with qty=1 and value=0.0001 ETH
curl -s -X POST "https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "method":"eth_call",
    "params":[{
      "to":"0xCONTRACT",
      "data":"0xa0712d680000000000000000000000000000000000000000000000000000000000000001",
      "value":"0x5af3107a4000"
    },"latest"],
    "id":1
  }' | python3 -c "
import json,sys
r = json.load(sys.stdin)
if 'error' in r:
    err_data = r['error'].get('data','')
    err_sig = err_data[:10] if err_data else 'no data'
    print(f'REVERT: {err_sig}')
else:
    print('OK — mint would succeed')
"
```

**Error signal cheat sheet for simulation:**
| Revert Data | Meaning | Action |
|-------------|---------|--------|
| `0x64a0ae92` | Mint not open / sale not active (no-code `require(false)` or custom error) |
| `0xd05cb609` | **Sold out / max supply reached** (custom Solidity error on some contracts) | Stop; check `totalSupply() == maxSupply()` |
| `0x949ce241` | Insufficient payment (wrong ETH value) |
| `0x4bd3c027` | Sold out / max supply reached |
| `0x5107dbe7` | Per-wallet limit reached |
| `0xafb93f5e` | Free mint ended / not available (custom error `freeMint()` specific) | Free mint phase closed; check if paid mint available |
| `0x68f2a8ff` | Block limit reached |

If simulation reverts with one of these, **do NOT send a real transaction** — it will waste gas. Inform the user about the specific error.

### Step 0b — dApp source analysis (no block explorer needed)

When the dApp is a **Vercel / Next.js / Vite** static JS bundle, the contract address + ABI + mint function details are embedded in compiled JS. This is often **faster than Blockscout** for new/unverified contracts.

See `references/dapp-source-contract-analysis.md` for the full extraction technique:
- Find the JS bundle from the page HTML
- Extract `0x` addresses, filter out known placeholders
- **Search for VITE_ config constants** (fastest way: `grep -oP 'VITE_[A-Z_]+'`) — reveals contract address, chain ID, deploy block, auxiliary contracts, and backend URLs in one pass
- Find the contract address + ABI context in JS
- Extract function signature strings from the ABI: `grep -oP '"function [^"]*"'` — most reliable way to get exact Solidity signatures and selectors
- Extract function names, event definitions, and validation logic
- Verify via `grep` with surrounding context

**Free-mint-quota pattern:** Some contracts expose both `mintPrice()` (base price) AND `mintCostFor(address)` (actual cost per wallet). If `mintCostFor(address)` returns 0 for a wallet but `mintPrice()` returns > 0, the contract grants a **free first mint per wallet** — subsequent mints cost `mintPrice()`. Always check both functions to distinguish "free for everyone" vs "free first mint per wallet."

### Step 1 — Detect Contract Type

Use Blockscout API to get contract info, ABI, and implementation:

```bash
# Quick check (returns name, verified, proxy type, implementations)
curl -s --max-time 10 "https://eth.blockscout.com/api/v2/smart-contracts/0xCONTRACT" | python3 -c "
import json,sys; d=json.load(sys.stdin)
print('Name:', d.get('name'))
print('Verified:', d.get('is_verified'))
print('Proxy:', d.get('proxy_type'))
for i in d.get('implementations',[]):
    print('Impl:', i.get('address_hash'), '-', i.get('name'))
"
```

**Contract type cheat sheet:**

| Detected Impl Name | Mint Function | Notes |
|---|---|---|
| `DropERC721` (Thirdweb) | `claim(receiver, quantity, currency, pricePerToken, allowlistProof, data)` | Struct param `_allowlistProof`. Currency = `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE` for native ETH |
| `ERC721SeaDropCloneable` (Seadrop) | `mintSeaDrop(minter, quantity)` | ⚠️ `onlyAllowedSeaDrop` modifier — user CAN'T call `mintSeaDrop()` directly on the proxy. Only SeaDrop impl can call it. Use OpenSea UI or call SeaDrop impl directly. |
| Custom ERC-721 | `mint()`, `mint(quantity)`, `mint(to)`, `mint(to, quantity)` | Try incrementally; check price |

### Step 2 — Check Mint Conditions

```bash
# For DROPERC721 (Thirdweb):
# getActiveClaimConditionId()
curl -s -X POST https://ethereum.publicnode.com -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_call","params":[{"to":"0xCONTRACT","data":"0xc68907de"},"latest"],"id":1}'

# getClaimConditionById(ID)
curl -s -X POST https://ethereum.publicnode.com -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_call","params":[{"to":"0xCONTRACT","data":"0x6f8934f40000000000000000000000000000000000000000000000000000000000000001"},"latest"],"id":1}'

# Decode: tuple(startTimestamp, maxClaimableSupply, supplyClaimed, quantityLimitPerWallet, merkleRoot, pricePerToken, currency, metadata)

# For CUSTOM contracts:
# price() / cost() / mintPrice() — check selector
curl -s -X POST https://ethereum.publicnode.com -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_call","params":[{"to":"0xCONTRACT","data":"0xa035b1fe"},"latest"],"id":1}'

# For ERC721SeaDrop: getMintStats(address) returns (mintPrice, totalMinted, maxMintableByWallet)
# mintPrice=0 means FREE. totalMinted = global total. maxMintableByWallet = global cap (often = maxSupply, not per-wallet!)
curl -s -X POST https://ethereum.publicnode.com -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_call","params":[{"to":"0xCONTRACT","data":"0xda023918000000000000000000000000WALLET_ADDRESS"},"latest"],"id":1}'
# Decode: 3 x uint256 = (mintPrice wei, totalMinted, maxMintableByWallet)

# totalSupply() / totalMinted()
curl -s -X POST https://ethereum.publicnode.com -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_call","params":[{"to":"0xCONTRACT","data":"0x18160ddd"},"latest"],"id":1}'

# hasMinted(address) — per-wallet limit check
# selector: keccak256('hasMinted(address)')[:4] = 0x38e21cce
curl -s -X POST https://ethereum.publicnode.com -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_call","params":[{"to":"0xCONTRACT","data":"0x38e21cce000000000000000000000000WALLET_ADDRESS"},"latest"],"id":1}'

# balanceOf(address) — check current holdings
curl -s -X POST https://ethereum.publicnode.com -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_call","params":[{"to":"0xCONTRACT","data":"0x70a08231000000000000000000000000WALLET_ADDRESS"},"latest"],"id":1}'
```

### Step 3 — Mint

Use the templates in `templates/` for ready-to-run Node.js scripts:

| Template | When to Use |
|----------|-------------|
| `templates/mint-claim-thirdweb.js` | Thirdweb DropERC721 with `claim()` |
| `templates/mint-seadrop.js` | Seadrop `mintSeaDrop()` |
| `templates/mint-simple.js` | Custom ERC-721 with `mint()` (no-arg) |
| `templates/mint-with-retry.js` | Any contract with block-limit competition |

**Quick mint approach (no template needed):**

For simple `mint()` contracts:
```bash
cd ~/nft-minting && PK=0x... node -e '
const {ethers} = require("ethers");
const p = new ethers.JsonRpcProvider("https://ethereum.publicnode.com");
const w = new ethers.Wallet(process.env.PK, p);
const c = new ethers.Contract("0xCONTRACT", ["function mint() payable"], w);
c.mint({value: 0, gasLimit: 200000}).then(tx => {
  console.log("Tx:", tx.hash);
  return tx.wait();
}).then(r => console.log("Done! Gas:", r.gasUsed.toString()));
'
```

**Quick mint via web3.py v7 (Hermes venv):**

For `mint(uint256)` contracts with payable value, use the Hermes venv's web3.py directly:

```bash
/usr/local/lib/hermes-agent/venv/bin/python << 'PYEOF'
from web3 import Web3
from eth_account import Account

PK = "0x..."
RPC = "https://eth-mainnet.g.alchemy.com/v2/..."
CONTRACT = "0x894e3f1cA45F9404A8563b09aEC7f24fE24C9461"

w3 = Web3(Web3.HTTPProvider(RPC))

# web3.py v7 requires checksum addresses
contract_addr = Web3.to_checksum_address(CONTRACT)

acct = Account.from_key(PK)
sender = acct.address

value = w3.to_wei(0.0001, 'ether')
nonce = w3.eth.get_transaction_count(sender)
gas_price = w3.to_wei(1, 'gwei')  # 1 gwei = ~$0.15 for typical mint

abi = [{'inputs':[{'internalType':'uint256','name':'quantity','type':'uint256'}],
        'name':'mint','outputs':[],'stateMutability':'payable','type':'function'}]
contract = w3.eth.contract(address=contract_addr, abi=abi)

# Estimate gas (will revert if mint not open!)
try:
    est = contract.functions.mint(1).estimate_gas({'from': sender, 'value': value})
    gas_limit = max(est * 2, 80000)
except Exception as e:
    print(f"Mint not open? {e}")
    gas_limit = 150000  # fallback

tx = contract.functions.mint(1).build_transaction({
    'from': sender, 'value': value, 'nonce': nonce,
    'gas': gas_limit, 'gasPrice': gas_price,
})

signed = acct.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
print(f"Tx: {tx_hash.hex()}")

receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
print(f"Status: {'SUCCESS' if receipt['status'] == 1 else 'FAILED'}")
print(f"Gas: {receipt['gasUsed']}")
PYEOF
```

**Key web3.py v7 gotchas:**
- `Web3.to_checksum_address()` — **required** for all addresses; lowercase addresses throw `InvalidAddress`
- `w3.to_wei()` — use this instead of `Web3.to_wei()` directly
- `acct.sign_transaction(tx)` — returns signed tx; pass `signed.raw_transaction` to `send_raw_transaction`
- `eth_call` simulation before sending real ETH — always worth it to catch revert reasons

## Key Contract Types & Patterns

### A) Thirdweb DropERC721

Uses `claim()` with struct params. The `_allowlistProof` tuple is:
```solidity
tuple(
  bytes32[] proof,         // merkle proof (empty array if no whitelist)
  uint256 quantityLimitPerWallet,  // usually the per-wallet max
  uint256 pricePerToken,           // override price (0 uses condition price)
  address currency                 // override currency (zero addr uses condition currency)
)
```

Typical call:
```javascript
await contract.claim(
  walletAddress,                        // _receiver
  1,                                    // _quantity
  "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE", // _currency (ETH)
  0,                                    // _pricePerToken (free)
  { proof: [], quantityLimitPerWallet: 7, pricePerToken: 0, currency: "0x0000000000000000000000000000000000000000" },
  "0x"                                  // _data
)
```

### B) Seadrop (ERC721SeaDropCloneable)

Uses `mintSeaDrop(address minter, uint256 quantity)`:
```javascript
await contract.mintSeaDrop(walletAddress, 1)
```

### C) Custom ERC-721 (OpenZeppelin based)

Common patterns: `mint()`, `mint(uint256 qty)`, `mint(address to)`, `mint(address to, uint256 qty)`.
Check `price()`, `cost()`, or `mintPrice()` for cost. Check `hasMinted(address)` or `minted(address)` for per-wallet limits.

### D) Class-Slot mintBatch(uint16[N]) — Multi-class distribution mints

Some collections (e.g. EpochRift, game-related NFTs) use a **class-slot** mint pattern where a single tx distributes tokens across N class slots:

```solidity
function mintBatch(uint16[4] quantities) payable
```

- Takes a **static array** of `uint16` values, one per class slot
- Total items minted = `sum(quantities)`
- Price = `mintPrice()` × total quantity (payable)
- Each slot may have an individual cap (e.g. max 2 per class per tx — `[2,2,0,0]` works but `[3,0,0,0]` reverts)

**Detection signals in JS bundle:** Look for function signatures like `"function mintBatch(uint16[4] quantities) payable"` or class-slot language ("sprites per epoch", 4 class slots).

**ABI encoding (eth_abi):** Static arrays encode each element as a full 32-byte word:

```python
from eth_abi import encode
params = encode(['uint16[4]'], [[1, 1, 1, 1]])  # 1 of each class
data = keccak(b'mintBatch(uint16[4])')[:4] + params
```

**Simulation pattern:** Test incrementally — start with `[1,0,0,0]`, then increase quantity per slot to find per-slot limits. If `[N,0,0,0]` fails for N≥3 but `[2,1,0,0]` works, there's a per-slot limit of 2.

**Real-world example (EpochRift):**
```
mintPrice: 0.0005 ETH/NFT
maxMintPerTx: 8
totalSupply: 85/5000
[2,2,0,0] → 4 NFTs, gas 419,576, cost ~0.00203 ETH ✅
[1,1,1,1] → 4 NFTs, gas 482,104, cost ~0.00203 ETH ✅
[3,0,0,0] → ❌ (per-slot limit of 2)
```

### D) ERC721C One-Free-Mint-Per-Block Race

Some ERC721C/custom free mints expose `freeMint()` with a global block slot (`lastFreeMintBlock` / `blockSlotClaimed`) where exactly one wallet can win per Ethereum block. For these, `estimateGas` may revert with `Block slot already claimed` in the current block even though a next-block tx can succeed. Use explicit gas, wait for a fresh block, broadcast immediately, then verify receipts and token IDs. See `references/erc721c-one-free-mint-per-block.md` for the full pattern.

## Handling Competitive Free Mints

**Many free mints** have a global per-block limit (e.g. `MAX_PER_BLOCK = 10`). When popular, all 10 slots fill in the first seconds of each block.

### Strategy: Priority Fee Bidding

1. **Use EIP-1559 (type 2) transactions** with explicit `maxPriorityFeePerGas`
2. **Check what others are paying** — look at recent successful transactions to the contract in the latest block
3. **Bid 1.5–3 gwei priority** for moderately competitive mints, up to 6+ gwei for hot mints
4. **Monitor block-by-block** — send tx immediately when a new block arrives

### Strategy: Bypass estimateGas

`estimateGas` simulates against the current block state. If the block is full (all 10 slots taken), estimation reverts with `BlockLimitReached`. **Always bypass estimation** for competitive mints — supply an explicit `gasLimit`:

```javascript
// BAD — estimateGas reverts if block is full:
await contract.mint({ value: 0 });

// GOOD — supply explicit gasLimit to skip estimation:
await contract.mint({ value: 0, gasLimit: 200000 });

// BEST — raw transaction, no framework estimation:
const signed = await wallet.signTransaction({
  to: contractAddr,
  data: "0x1249c58b", // mint() selector
  value: "0x0",
  gasLimit: "0x30D40", // 200000
  maxPriorityFeePerGas: "0x59682F00", // 1.5 gwei
  maxFeePerGas: "0x" + (baseFee + priority).toString(16),
  chainId: 1, type: 2, nonce,
});
```

### Strategy: Retry Loop

Loop across blocks until the mint succeeds:
```javascript
for (let i = 0; i < 30; i++) {
  await waitForNewBlock();  // ~12s per block
  try { await sendRawTx(); return; } catch (e) { /* retry */ }
}
```

## Scripts & Templates

| File | Description |
|------|-------------|
| `scripts/nft_auto_mint.py` | Python/web3.py mint script (simple contracts only) |
| `references/homies-style-free-mint-consolidation.md` | Reference pattern for HOMIES-style custom ERC721A `freemint()` and multi-wallet consolidation. |
| `templates/mint-simple.js` | Node.js ethers.js v6 skeleton for basic `mint()` |
| `templates/mint-claim-thirdweb.js` | Node.js ethers.js v6 for Thirdweb DropERC721 `claim()` |
| `templates/mint-seadrop.js` | Node.js ethers.js v6 for Seadrop `mintSeaDrop()` |
| `templates/mint-with-retry.js` | Node.js with block-limit retry + priority fee bidding |
| `references/contract-detection.md` | Contract type detection patterns and API queries |
| `references/wallet-generation.md` | Wallet generation with Python eth-account |
| `references/funding-fresh-wallet-for-free-mints.md` | Pattern for generating a fresh secondary wallet, funding it from the primary wallet, executing a free mint, and verifying receipt/ownership without exposing keys. |
| `references/funding-generated-wallet-ranges.md` | Fund a selected range of generated wallets by fiat-denominated gas budget, with ETH/USD conversion, EIP-1559 transfers, receipt/balance verification, and zero-balance `eth_call` simulation pitfall. |
| `references/mirror-multiwallet-mint-consolidation.md` | Mirror-style multi-wallet free mint + consolidation: `mintCost(address,qty)==0`, receipt log token discovery, stale post-receipt read verification, and `safeTransferFrom` back to primary. |
| `references/commit-reveal-free-mints.md` | Commit-reveal free mints: `commit(bytes32)` then delayed `revealAndMint(salt, cellId)`, salt/state handling, cell/lane selection, reveal-window and tiny-wallet gas pitfalls. |
| `references/disclosure-visitors-commit-reveal.md` | Disclosure Visitors-specific lessons: expired commits permanently lock wallets, fund before committing, deeper cell scanning, final ownership verification, and gas/PnL accounting. |
| `references/disclosure-visitors-commit-reveal.md` | Disclosure Visitors-specific commit-reveal pitfall: expired commits are permanent (`AlreadyCommitted()` on recommit), no clear/reset function; includes selectors and reporting buckets. |
| `references/erc721c-one-free-mint-per-block.md` | ERC721C/MYTHROT-style `freeMint()` race where exactly one wallet wins per block; includes preflight, next-block broadcast, gas/fee sizing, retry funding pitfalls, and `FreeMint` event token discovery. |
| `references/token-gated-pass-rotation.md` | Rotate a single gate/pass NFT across generated wallets for token-gated first-free mints; includes USD funding, sequential receipt verification, volatile base-fee retry, and interrupted-run reporting. |
| `references/remanent-token-gated-relay-20260603.md` | Remanent-specific pass relay lesson: always re-query `getGateCollections()` before using an old gate pass; if `NotAllowlisted()` occurs after pass transfer, return the pass and verify owner across RPCs. |
| `references/block-wardens-cost-capped-mint.md` | Block Wardens/WARDEN lessons: `mint()` free mint with high gas, strict `$0.10` fee cap math, EIP-1559 cheap policy, receipt topic normalization without `0x`, and transfer-consolidation skip thresholds. |
| `references/free-quota-mint-consolidation.md` | Free-per-wallet quota contracts where `mint(uint256)` internally applies free allowance (`FREE_PER_WALLET`, `freeMinted`), plus multi-wallet balance filtering, minting, NFT consolidation, final ownership verification, and gas/IDR accounting. |
| `references/token-gated-pass-relay-free-mints.md` | Token-gated one-free-mint relay: move a qualifying ERC-721 pass wallet-to-wallet, mint free once per wallet, top up only short wallets, resume safely after interruptions, and verify token IDs via Transfer logs. |
| `references/remanent-consolidation-resume-20260603.md` | Remanent-style multi-wallet ERC721 consolidation after relay mints: build tokenId maps from receipts, skip already-primary owners, top up short source wallets, resume safely after interruptions, and require final `ownerOf` verification (`notMain == []`). |
| `references/homies-style-free-mint-consolidation.md` | Custom ERC721A-style lowercase `freemint()` flow: `minted(address)` eligibility, receipt token discovery, and `transferFrom` consolidation to the primary wallet. |
| `references/one-fish-gold-rod-batch.md` | One Fish Gold Rod batch mint: backend catch-proof voucher flow, signed intent format, queue-busy retry behavior, Vercel security checkpoint pitfall, and safe `mintFishBatch` execution sequence. |
| `references/commit-dice-signature-mint.md` | Commit → Dice + Signature mint pattern: 2-step with paid commit + server-signed `mintWithDice`, MAX_ATTEMPTS hard cap, trusted signer problem, cost breakdown, and pitfalls. |
| `references/erc20-artifact-projects.md` | How to handle NFT-looking projects that are actually ERC20 artifact/object launches with later ERC721 wrapping; includes DAEMONS-style Uniswap v4 hook discovery and clone filtering. |
| `references/wallet-addresses.md` | Active wallet addresses (3 wallets stored in memory) |
| `references/opensea-allowlist-fcfs-bot.md` | OpenSea FCFS allowlist bot: reverse engineer GraphQL `swap()` query, batch mint via field aliasing, SIWE auth flow, Rust bot architecture |
| `references/x-authenticated-mint-radar.md` | Authenticated X/Twitter NFT radar: cookie-safe search, `curl_cffi` + `X-Client-Transaction-Id`, topic routing, no-agent cron split for free mint vs WL alerts |
| `references/seadrop-only-allowed.md` | ERC721SeaDrop `onlyAllowedSeaDrop` modifier: why `mintSeaDrop()` can't be called directly, how to mint via OpenSea UI or Seadrop impl |
| `references/x-nft-radar-telegram-format.md` | X/Twitter and live-mint radar Telegram formatting: user prefers source link first, short description below, max top 3, silent when no signal, and topic routing for LFY. |
| `references/x-nft-radar-telegram-format.md` | X/Twitter NFT radar cron pattern: script-only `no_agent=True`, topic routing, dedupe, and the user's preferred clean Telegram format (link first, short description below). |
| `references/authenticated-x-mint-radar.md` | Authenticated X/Twitter keyword radar for free mint/allowlist/stealth mint monitoring with Telegram topic cron delivery. |
| `references/waypoint-hot-mint-radar.md` | Waypoint MintScan HOT/live mint radar: extraction pattern, OpenSea/TX enrichment, WIB header, compact embedded-link Telegram format, and anti-spam rules. |
| `references/nft-skill-distribution-package.md` | Shareable **NFT SKILL** ZIP package pattern: curated Web3/NFT related skills, tutorial files, installer layout, cron templates, radar scripts, and secret-safety verification. |

## Multi-Wallet Management

For minting with **multiple wallets** (e.g. 1-per-wallet mints, parallel minting):

### Wallet List (stored in memory)

Check `memory` for the current wallet list (address + private key saved during session setup).

### Generating New Wallets

Use Python's `eth-account` in the Hermes venv:

```bash
# Ensure eth-account is installed first
/usr/local/lib/hermes-agent/venv/bin/python -m ensurepip --upgrade
/usr/local/lib/hermes-agent/venv/bin/python -m pip install eth-account

# Generate wallets
/usr/local/lib/hermes-agent/venv/bin/python -c "
from eth_account import Account
acct = Account.create()
print(f'Address: {acct.address}')
print(f'Private Key: {acct.key.hex()}')
"
```

Save to memory: `memory(action='add', target='memory', content=...)`.

### Switching Active Wallet

Set `PRIVATE_KEY` env var to the desired wallet's private key before minting. The active/default wallet is `0xprimary...wallet` (set via `.env`).

> See `references/wallet-generation.md` for the full procedure.

## 🔥 OpenSea FCFS Allowlist Mint

For mints using **OpenSea allowlists** (`mintSigned`), the flow is fundamentally different from public mints. OpenSea's backend generates the salt + signature server-side — you can't pre-build calldata.

**Approach** (from @Zun2025's reverse engineering): Hit OpenSea's internal GraphQL endpoint `swap(action: MINT)` to fetch signed calldata, then batch all wallets into ONE GraphQL request using field aliasing.

Full breakdown: `references/opensea-allowlist-fcfs-bot.md`

### Quick Reference
- **Auth**: SIWE sign → parsed fields → `x-app-id: os2-web` header → cookies
- **Batch trick**: `query B { w0: swap(...) { txData } w1: swap(...) { txData } }` — 1 HTTP round-trip for all wallets
- **Warm-up**: pre-fetch nonces at T-5s, keepalive connections
- **Region**: deploy near IAD (Ashburn, VA) — ~8ms ping to OpenSea/Base
- **Signing**: libsecp256k1 C FFI (~1.8x faster than pure Rust)

## Common Pitfalls

1. **estimateGas reverts on competitive mints** — always bypass with explicit `gasLimit` when you see `BlockLimitReached`

2. **BlockLimitReached means all 10 global slots are taken** — wait for next block (~12s). Not a bug.

3. **Public mapping selector confusion** — `hasMinted(address)` selector = `0x38e21cce`. Don't guess — compute with `ethers.id("hasMinted(address)").substring(0, 10)`.

4. **Thirdweb `claim()` needs struct** — Ethers.js v6: pass as object `{proof: [], ...}`. Python web3.py can't easily encode Thirdweb structs.

5. **Free mint on mainnet still costs gas** — at 1.5 gwei priority + 0.13 base, 140k gas ≈ 0.00023 ETH (~$0.70). Budget accordingly.

6. **1-per-wallet mints** — many free mints limit to 1 per address. Check `hasMinted()` first. No way to bypass.

7. **Public RPC flakiness** — publicnode.com, llamarpc.com can be unreliable (522 errors). Rotate or use paid RPC.

8. **Nonce management** — failed txs still consume nonce. Always fetch fresh `getTransactionCount` before sending.

9. **Funding-then-transfer nonce pitfall** — When you fund a child wallet from main (ETH send), the child wallet's nonce does NOT change (it's receiving, not sending). But the main wallet's nonce does advance. Always fetch the child wallet nonce AFTER the funding tx confirms, not before. Use `'latest'` (not `'pending'`) for clean reads:

   ```python
   # ✅ CORRECT: fund first, then get fresh nonce for transfer
   tx_fund = {'from': MAIN, 'to': child, ...}
   w3.eth.wait_for_transaction_receipt(h_fund)
   nonce = w3.eth.get_transaction_count(child, 'latest')  # fresh!
   ```

10. **Sequential batch timeout** — Long multi-wallet consolidation scripts (~10 wallets × 2 txs each = 20+ txs) can exceed the 180s terminal timeout. Each `wait_for_transaction_receipt` blocks ~12s+. Split into separate script runs: (a) fund all underfunded wallets, (b) transfer all NFTs. Or cap each run to 5-6 wallets max.

11. **Contract is a proxy** — always check implementations via Blockscout. The implementation contract has the real ABI and function selectors.

12. **Always simulate before sending** — Some contracts look like they have working `mint()` in the ABI but revert with "mint not open" (`0x64a0ae92`) once called. Save $0.15+ in wasted gas by doing an `eth_call` simulation first (see Step 0). The user only sees a successful mint as a "mint" — a simulation revert tells you the sale isn't live yet, not that your code is wrong.

13. **ERC721SeaDrop `onlyAllowedSeaDrop`** — `mintSeaDrop()` on the NFT proxy has the `onlyAllowedSeaDrop` modifier (revert `0x15e26ff3`). User wallets CAN'T call it directly. Must mint via OpenSea UI or call the Seadrop implementation contract. When you see SeaDrop in ABI, always check who is allowed to call the mint function.

## Signature-based / Backend-Authorized Mints (Anti-Bot Pattern)

Many modern free mints (especially 2025–2026) use a **short-lived signature** pattern instead of simple `mint()`:

- Frontend calls a backend endpoint (e.g. `/api/mint-auth`) with wallet + Turnstile token
- Backend returns `{ authId, deadline, signature }`
- Frontend builds a custom transaction (often using a specific selector like `0xe41813c0`) that includes the permit
- Contract verifies the signature on-chain

**Key signals this pattern is in use:**
- `mint(uint256)` or `claim()` does not exist or always reverts
- Frontend JS contains functions like `rv()`, `hv()`, `Zn()`, `permit` encoding
- Cloudflare Turnstile (or similar) is present and required before the Mint button enables

**Recommended workflow:**
1. Use browser tools to extract the minified JS bundle
2. Search for the mint function selector and encoding helpers (`0xe41813c0`, `rv(`, `hv(`)
3. Recreate the encoding logic in Python (web3.py) or ethers.js
4. Script must request a fresh Turnstile token from user (automation almost always fails)
5. POST to the auth endpoint, then construct the exact calldata the contract expects

**User preference (Indonesian users):**  
Prefer "gas langsung" style — give the script quickly with minimal explanation. Only explain when the user explicitly asks "kenapa" or the tx fails. Always use the primary wallet from `.env` unless told otherwise.

### Specific Token ID Selection Mints (e.g. CryptoQuack-style contracts)
When the site lets users pick specific tokenIds (not blind mint):

1. **Always verify availability on-chain first** — the frontend "Available" filter can be stale.
   ```python
   tokenMinted_abi = [{"inputs":[{"internalType":"uint256","name":"tokenId","type":"uint256"}],"name":"tokenMinted","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"}]
   contract = w3.eth.contract(address=contract_addr, abi=tokenMinted_abi)
   available = [id for id in candidate_ids if not contract.functions.tokenMinted(id).call()]
   ```

2. If no IDs available, run a quick random search loop (max 200 attempts) to surface fresh available IDs.

3. Only after filtering available IDs → run the eth_call simulation on `mint(to, tokenIds)`.

4. Common revert on these contracts: `0xddefae28` = AlreadyMinted (one or more IDs taken). Never assume frontend data is fresh.

This pattern was validated on CryptoQuack (0x4210b92d...) where totalSupply was already 7695 and many high IDs were taken.

**Turnstile limitation:**  
Automated browser sessions (Playwright, browser tools) almost always fail Turnstile invisible checks. Plan for the user to solve it once manually and paste the token. Never claim full automation is possible.

### Variant: Commit → Dice + Signature (Paid Commit then Server-Signed Mint)

Some mints use a 2-step **commit-then-dice** pattern where step 1 costs a fixed fee (e.g. 0.0001 ETH) and step 2 needs a server-side EIP-191 signature:

1. `commitToMint(bytes32 commitment)` — paid, stores commitment hash (often `keccak256(user)`)
2. `mintWithDice(uint256 diceResult, uint256 nonce, bytes signature)` — free, but **requires signature from `trustedSigner`**

**Critical differences from standard commit-reveal:**
- You choose `diceResult` (1–6) — the number of tokens you receive
- The `commitment` is NOT a secret salt — it's just `keccak256(user)`
- Signature comes from the project's backend private key — **cannot be generated offline**
- **MAX_ATTEMPTS (hard cap)** — typically 2 commits max per wallet, then permanently locked
- Commit fee is **non-refundable** — spent even if you never complete step 2

**What to tell the user:** They must use the official dApp frontend to get the signature. No way around it unless the project exposes a public signing API.

See `references/commit-dice-signature-mint.md` for full breakdown, detection checklist, and pitfalls.

## Commit-Reveal Wallet Lock Pitfall

For commit-reveal contracts, always inspect the source/ABI for whether expired commits can be cleared or overwritten. Some contracts (e.g. Disclosure Visitors) permanently reject a second `commit()` whenever `commits[msg.sender].commitment != 0`, even after `REVEAL_WINDOW` expires. In those contracts, missing the reveal window permanently locks that wallet out of minting. Fund wallets for both commit and reveal **before** committing, and never do slow sequential topups inside the reveal window. See `references/disclosure-visitors-commit-reveal.md` for a concrete pattern.

## Error Signal Reference

| Revert / Error | Meaning | Action |
|----------------|---------|--------|
| `SoldOut()` | Max supply reached | Stop, find another contract |
| `AlreadyMinted()` | Wallet already minted (1 per wallet) | Use different wallet |
| `BlockLimitReached()` | Global per-block limit hit | Wait for next block, retry with priority |
| `WrongValue()` | msg.value ≠ price | Check price again, send exact amount |
| `execution reverted (no data)` | Generic require(false) | Usually block/tx ordering issue, retry |
| `0xda3908f7` | BlockLimitReached (custom error) | Retry next block with higher priority |
| `0x64a0ae92` | Mint not open / sale not active | Mint hasn't started yet; inform user |
| `0x949ce241` | Insufficient payment (wrong ETH value) | Double-check mint price |
| `0x4bd3c027` | Sold out / max supply reached | Stop |
| `0x5107dbe7` | Per-wallet limit reached (already minted max allowed per wallet) | Use different wallet |
| `0x68f2a8ff` | Block limit reached (global per-block cap full) | Retry next block |
| `0x64a0ae92` with null data | Mint not open (common for timed sales) | Check sale start time / phase |
| `0xd05cb609` | **Sold out / max supply reached** (custom Solidity error, often hidden — not standard revert) | Stop; check totalSupply() == maxSupply() to confirm |
| `0xafb93f5e` | **Free mint ended / not available** (custom error emitted by `freeMint()` functions — different from `maxSupply`) | Free mint phase is closed; check if paid mint (`mint(uint256)` with value) is available instead |
| `0xcec10c11` as mint selector | Alternate `mint(uint256)` selector — some contracts don't use standard `0xa0712d68` | When simulation with `0xa0712d68` reverts, try reading dispatch table from bytecode and testing each payable selector |
| `Insufficient funds` | Wallet ETH balance < value + gas | Not enough ETH in wallet; check balance first |
| 522 / timeout | RPC node down | Switch RPC endpoint |

## ⚠️ CRITICAL RULE: Transaction Integrity — NEVER Claim Success Without Receipt

**For specific-ID mints:** Always surface the filtered `available` list to the user before sending the tx so they can confirm the IDs are the ones they wanted.

```
THIS IS THE SINGLE MOST IMPORTANT RULE IN THIS SKILL.
Violating it destroys user trust.
```

**Rule:** A transaction is NOT successful until `receipt.status == 1` is confirmed via `wait_for_transaction_receipt()`. 

### What NOT to do (the user caught this):

```python
# BAD — user will say "bohong kamu belum execute tx apapun"
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
print(f"✅ Tx sent! Link: https://etherscan.io/tx/{tx_hash.hex()}")
# ^ No receipt check! Tx might revert silently or pending forever
```

### What to ALWAYS do:

```python
# GOOD — wait for receipt, check status
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
print(f"Tx sent: {tx_hash.hex()}")

# BLOCK until confirmed
receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
status = receipt['status']  # 1 = success, 0 = failure

if status == 1:
    print(f"✅ SUCCESS — Gas used: {receipt['gasUsed']}")
else:
    print(f"❌ FAILED — tx reverted on-chain")
```

**Never output "SUCCESS ✅", "Done ✅", or similar confidence text until `receipt.status == 1`.** Sending a tx to the mempool is NOT success.

### Prerequisite: Check Balance FIRST

Always check wallet balance before minting to avoid "insufficient funds" at send time:

```python
bal = w3.eth.get_balance(sender)
total_needed = value + (gas_limit * gas_price)
if bal < total_needed:
    print(f"❌ Insufficient funds. Have {w3.from_wei(bal, 'ether')} ETH, need {w3.from_wei(total_needed, 'ether')} ETH")
    # Offer to reduce gas price or tell user to top up
```

### Gas Price Floor and User Cost Caps

Even with low gas, never go below the base fee. On Ethereum mainnet (May 2026):
- Base fee: ~0.1 gwei
- Safe gas price: 0.11–0.14 gwei  
- **Use 0.2+ gwei for reliable inclusion** only when it stays inside the user's stated USD cap
- Explicit legacy `gasPrice` works fine — no need for EIP-1559 on low-fee L1

**Hard USD fee caps:** If the user gives a max fee like "jangan lebih dari $0.10", enforce it before broadcasting. Compute:

```python
fee_est_wei = gas_limit * maxFeePerGas  # EIP-1559 worst case
fee_est_usd = Decimal(fee_est_wei) / Decimal(10)**18 * eth_usd
if fee_est_usd > Decimal("0.10"):
    print("SKIP_FEE_GT_CAP")
    # do not send; wait for base fee to drop
```

For gas-heavy ERC-721 mints (~220k gas), a $0.10 cap at ~$1,800/ETH means effective gas price must be roughly `<= 0.25 gwei`. If current `baseFeePerGas + priorityFee` is above that, **skip/wait**; setting a lower `maxFeePerGas` cannot bypass the base fee and may only leave the tx pending/failing. Use very small priority fees (`0.005–0.02 gwei`) for cheap consolidation/transfers, but only when `baseFee + priority` remains under the USD cap.

### Full Safe Mint Pattern (web3.py v7)

```python
from web3 import Web3
from eth_account import Account

w3 = Web3(Web3.HTTPProvider(RPC))
acct = Account.from_key(PK)
sender = acct.address
contract_addr = Web3.to_checksum_address(CONTRACT)  # REQUIRED in web3.py v7!

bal = w3.eth.get_balance(sender)
print(f"Balance: {w3.from_wei(bal, 'ether')} ETH")

value = w3.to_wei(0.0001, 'ether')
nonce = w3.eth.get_transaction_count(sender)
gas_price = w3.to_wei(0.2, 'gwei')

abi = [{'inputs':[{'internalType':'uint256','name':'quantity','type':'uint256'}],
        'name':'mint','outputs':[],'stateMutability':'payable','type':'function'}]
contract = w3.eth.contract(address=contract_addr, abi=abi)

# Step A: Simulate first (catch mint-not-open errors without spending gas)
try:
    est = contract.functions.mint(1).estimate_gas({'from': sender, 'value': value})
    gas_limit = int(est * 1.3) + 5000
except Exception as e:
    print(f"❌ Simulation reverted: {e}")
    gas_limit = 150000  # conservative fallback

# Step B: Check funds
total_needed = value + (gas_limit * gas_price)
if bal < total_needed:
    print(f"❌ Need {w3.from_wei(total_needed, 'ether')} ETH, have {w3.from_wei(bal, 'ether')}")
    # abort or offer lower gas

# Step C: Build, sign, send
tx = contract.functions.mint(1).build_transaction({
    'from': sender, 'value': value,
    'nonce': nonce, 'gas': gas_limit, 'gasPrice': gas_price,
})
signed = acct.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
print(f"Tx sent: {tx_hash.hex()}")

# Step D: WAIT for receipt before claiming success
receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
if receipt['status'] == 1:
    print(f"✅ MINT SUCCESS")
    print(f"   Gas used: {receipt['gasUsed']}")
    print(f"   Block: {receipt['blockNumber']}")
else:
    print(f"❌ MINT FAILED (reverted on-chain)")
```

## NFT/Web3 Radar Telegram Formatting

When sending NFT/Web3 radar updates to this user, prefer compact member-friendly Telegram posts over verbose research cards. Put the source/link first only when the user asks for raw-link style; for group cron posts use embedded Markdown links and short status lines.

Key preferences learned from use:
- Keep HOT live-mint posts titled `🔥 HOT NFT Live Mint`.
- Use WIB (`Asia/Jakarta`) timestamps in message headers.
- Avoid cron wrapper text like `Cronjob Response: ...`; set `cron.wrap_response=false` for clean channel posts.
- Avoid long raw URL blocks. Use embedded links like `[Waypoint](...) • [OpenSea](...) • [Tx](...)`.
- Send at most 3 items; if the signal is weak, send fewer or stay silent.
- Keep descriptions to one short line and end with `DYOR sebelum mint.`

See `references/waypoint-hot-mint-radar.md` for the Waypoint MintScan workflow and exact Telegram format.

## Verification Checklist

- [ ] Contract verified on Etherscan/Blockscout
- [ ] Mint price confirmed via `price()` / `mintPrice()` / `claimCondition()`
- [ ] Wallet hasn't already minted (check `hasMinted` or `balanceOf`)
- [ ] **Total supply below max** — ALWAYS check FIRST to avoid wasting gas on sold-out contracts (see `references/sold-out-detection.md`)
- [ ] Wallet balance sufficient for value + gas
- [ ] Gas estimation simulation passes (`eth_call`), otherwise decode revert error
- [ ] Gas price set (minimum 0.15 gwei on current mainnet; 0.2+ for reliable inclusion)
- [ ] Explicit gasLimit set (bypass estimation for competitive mints)
- [ ] **Receipt confirmed with status==1** (NOT just "tx sent")
- [ ] Tx hash confirmed on Etherscan with status 1
- [ ] Token ID parsed from Transfer event in receipt logs (see `references/token-discovery.md`)
- [ ] BalanceOf / OpenSea confirms NFT received
