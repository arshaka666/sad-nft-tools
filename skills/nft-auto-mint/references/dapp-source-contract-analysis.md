# dApp Source Contract Analysis

When a mint website deploys via **Vercel / Next.js / Vite** (static JS bundles, no server), the contract address, ABI, and mint function details are embedded in the **compiled JS bundle**. This reference shows how to extract them without Etherscan/Blockscout.

## Technique: Extract from Compiled JS Bundle

### Step 1 — Find the JS bundle

Visit the dApp URL. In browser console or via curl:

```bash
curl -s "https://mintsite.vercel.app/" | grep -oP 'src="/assets/[^"]*\\.js"' | head -3
# → src="/assets/index-CNsjsjWZ.js"
```

The filename includes a hash (cache-busting). Grab the full URL and download.

### Step 2 — Extract contract address

The compiled bundle still contains literal `0x` addresses. Find the actual contract:

```bash
curl -s "https://mintsite.vercel.app/assets/index-CNsjsjWZ.js" | grep -oP '"0x[a-fA-F0-9]{40}"' | sort -u
# → "0xeeeeeeee14d718c2b47d9923deab1335e144eeee"  (ETH placeholder)
# → "0xca11bde05977b3631167028862be2a173976ca11"  (Multicall3)
# → "0x1c8B4b521b7528B250298de1C765acEC2EC4412D"   ← contract
# → "0x0000000000000000000000000000000000000000"   (zero addr)
```

**Known non-contract addresses to filter out:**
- `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE` — ETH placeholder
- `0x0000000000000000000000000000000000000000` — zero address
- `0xca11bde05977b3631167028862be2a173976ca11` — Multicall3
- `0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e` — Seaport 1.6 conduit
- `0xeeeeeeee14d718c2b47d9923deab1335e144eeee` — another ETH placeholder variant
- `0x5792579257925792579257925792579257925792` — placeholder test address
- `0xffffffffffffffffffffffffffffffffffffffff` — placeholder max address
- `0xfffffffffffffffffffffffffffffffebaaedce6` — Seaport contract

Then verify the candidate by finding its usage context:

```bash
curl -s "https://mintsite.vercel.app/assets/index-CNsjsjWZ.js" | grep -oP '.{0,200}0x1c8B4b521b7528B250298de1C765acEC2EC4412D.{0,200}'
```

This gives context showing what the address is assigned to — usually paired with an ABI object or config object.

### Step 3 — Look for VITE_ config constants (FASTER than raw grep)

Vite builds expose **environment config variables** as string literals in the compiled JS. Search for `VITE_` prefixed keys:

```bash
curl -s "https://mintsite.vercel.app/assets/index-XXXX.js" | grep -oP 'VITE_[A-Z_]+' | sort -u
# → VITE_APP_NAME
# → VITE_MINT_CHAIN_ID
# → VITE_MINT_CONTRACT_ADDRESS    ← THE NFT CONTRACT
# → VITE_MINT_DEPLOY_BLOCK
# → VITE_MINT_EXPLORER_URL
# → VITE_POTION_CONTRACT_ADDRESS  ← Secondary token contract
# → VITE_GUILD_VAULT_ADDRESS
# → VITE_CONVEX_URL
# → VITE_IPFS_GATEWAY_URL
```

Then extract the config block — these `VITE_` keys are often grouped together with their values:

```bash
curl -s "https://mintsite.vercel.app/assets/index-XXXX.js" | grep -oP '.{0,50}VITE_MINT_CONTRACT_ADDRESS".{0,150}' | head -3
```

**Advantages over raw address grep:**
- Skips false positives (placeholders, known addresses)
- Shows you WHAT each address is for (`MINT` vs `POTION` vs `GUILD_VAULT`)
- Reveals chain ID, deploy block, explorer URL in one pass
- Also reveals backend URLs (Convex, IPFS gateway) that may be part of the mint flow

### Step 4 — Extract ABI and function names

The JS bundle contains the full ABI array as inline JSON. Search for function names:

```bash
curl -s "https://mintsite.vercel.app/assets/index-CNsjsjWZ.js" | grep -oP '.{0,300}mint.{0,300}'
```

This typically reveals:

1. **Function names** — `mint`, `mintPrice`, `mintCostFor`, `totalSupply`, `MAX_SUPPLY`, etc.
2. **ABI fragments** — the full `[{type:"function",name:"mint",stateMutability:"payable",inputs:[],outputs:...}]` arrays
3. **Event definitions** — `Minted(address,uint256,uint96)` etc.
4. **Config objects** — chain ID, contract address mapping

### Step 5 — Extract full function signatures from the ABI

The ABI in the JS bundle includes the exact function signatures as Solidity strings:

```bash
curl -s "https://mintsite.vercel.app/assets/index-XXXX.js" | grep -oP '"function [^"]*"' | sort -u
# → "function mintBatch(uint16[4] quantities) payable"    ← Main mint function
# → "function mintPrice() view returns (uint256)"
# → "function mintPaused() view returns (bool)"
# → "function maxMintPerTx() view returns (uint16)"
# → "function totalSupply() view returns (uint256)"
# → "function earlyEpochWhitelistOnly() view returns (bool)"
# → "function epochWhitelist(uint16 epochId, address wallet) view returns (bool)"
# → "function gamePoolReserve() view returns (uint256)"
```

This is the **most reliable** way to get the mint function — these are the exact ABI strings used by wagmi/viem on the frontend.

### Special Pattern: mintBatch(uint16[4]) — Class-slot mints

Some collections (e.g. EpochRift) use a **class-slot** mint pattern where you specify how many tokens of each class to mint in a single tx:

```solidity
function mintBatch(uint16[4] quantities) payable
```

- Takes an array of 4 `uint16` values, each representing quantity for one class
- Total minted = sum of all 4 values
- Each class may have an individual cap (e.g. max 2 per class per tx)
- Price = `mintPrice()` × total quantity

**ABI encoding for simulation:**

For a `uint16[4]` static array in Solidity ABI, each element is encoded as a full 32-byte word (padded):

```python
from eth_abi import encode

# [1, 0, 0, 0] = 1 of class 0, 0 of others
params = encode(['uint16[4]'], [[1, 0, 0, 0]])
data = selector + params
# → 0x0dfeb726 + 4 × 32 bytes = 132 bytes total
```

The `[1, 1, 1, 1]` pattern means 1 of each class (4 total). If `[3, 0, 0, 0]` fails but `[2, 1, 0, 0]` works, it means per-slot limits apply (max 2 per class per tx).

### Step 6 — Derive function selectors from extracted ABI

Once you have function signatures, compute the 4-byte selectors to call them:

```python
from eth_utils import keccak

# keccak("mintBatch(uint16[4])")[:4] → 0x0dfeb726
selector = keccak(b'mintBatch(uint16[4])')[:4].hex()
```

Cross-check against the JS to confirm. Some contracts use non-standard selectors.

### Step 7 — Simulate and mint

Use the extracted function signature + selector to build eth_call simulations:

```python
from web3 import Web3
from eth_abi import encode

w3 = Web3(Web3.HTTPProvider(RPC))
addr = w3.to_checksum_address(CONTRACT)
wallet = w3.to_checksum_address(WALLET)

selector = keccak(b'mintBatch(uint16[4])')[:4]
params = encode(['uint16[4]'], [[1, 0, 0, 0]])  # 1 NFT class 0
data = selector + params

# Simulate
price = w3.eth.call({'to': addr, 'data': keccak(b'mintPrice()')[:4].hex()})
mint_price = w3.codec.decode(['uint256'], price)[0]
total_price = mint_price * 1  # × quantity

result = w3.eth.call({
    'from': wallet, 'to': addr,
    'data': data, 'value': total_price
})
# No revert = mint will succeed
```

### Step 3a (alt) — Find ABI via function signature strings

If `grep -oP '"function [^"]*"'` returns nothing, try searching for patterns near the contract address in the JS:

```bash
# Find the JS file that has the contract address
curl -s "https://mintsite.xyz/assets/index-XXXX.js" | grep -oP '.{0,30}0xNFT_CONTRACT_ADDRESS.{0,200}'
```

This often reveals the ABI variable name or the ABI array assigned nearby.

### Step 3b (alt) — Multiple JS files

Vite splits code across multiple JS chunks. If nothing is found in the main `index-*.js`, check other files:

```bash
curl -s "https://mintsite.xyz/" | grep -oP 'src="/assets/[^"]*\\.js"' | head -10 | while read f; do
  f="https://mintsite.xyz$(echo $f | sed 's/src="//;s/"//')"
  curl -s "$f" | grep -l "mint" 2>/dev/null || true
done
```

## Rationale

Why do this instead of Etherscan/Blockscout?

| Reason | When |
|--------|------|
| **Unverified contract** | Blockscout returns empty ABI |
| **Before deployment** | dApp on testnet with no block explorer record |
| **Newly deployed** | Contract exists but not indexed yet |
| **Speed** | No external API calls needed — just curl the JS |
| **Human-readable names** | Some contracts use obfuscated or proxied function names; the frontend JS uses the actual function names as called by wagmi/viem |

## Example: Full Extraction from a Real dApp

In a real session (Inscription Pepe, 2026-06-05):

```bash
# 1. Find JS bundle from page HTML
curl -s https://inscriptionpepe.vercel.app/ | grep -oP 'src="[^"]*\\.js"'
# → /assets/index-CNsjsjWZ.js

# 2. Find all hex addresses
curl -s https://inscriptionpepe.vercel.app/assets/index-CNsjsjWZ.js | grep -oP '"0x[a-fA-F0-9]{40}"'

# 3. Find contract address context
curl -s ... | grep -oP '.{0,200}0x1c8B4b521b7528B250298de1C765acEC2EC4412D.{0,200}'
# Reveals: z3="0x1c8B4b521b7528B250298de1C765acEC2EC4412D", chainId=1, B3={chainId:j3,InscriptionPepe:z3}
# Also reveals full ABI: bv=[{type:"function",name:"mint",stateMutability:"payable",inputs:[]}, ...]

# 4. Extract full ABI
grep -oP 'const bv=\\[.*?\\];'  # or search for the ABI variable name found in step 3
```

### Example: EpochRift epochrift.xyz (2026-06-07)

**VITE config extraction:**
```bash
curl -s "https://www.epochrift.xyz/assets/index-BKRmADb6.js" | grep -oP 'VITE_[A-Z_]+' | sort -u
# → VITE_APP_NAME, VITE_MINT_CHAIN_ID (1), VITE_MINT_CONTRACT_ADDRESS, VITE_MINT_DEPLOY_BLOCK
# → VITE_POTION_CONTRACT_ADDRESS, VITE_GUILD_VAULT_ADDRESS, VITE_CONVEX_URL
```

**Function signatures:**
```bash
curl -s "..." | grep -oP '"function [^"]*"' | sort -u
# → "function mintBatch(uint16[4] quantities) payable"
# → "function mintPrice() view returns (uint256)"
# → "function mintPaused() view returns (bool)"
# → "function maxMintPerTx() view returns (uint16)"
# → "function earlyEpochWhitelistOnly() view returns (bool)"
# → "function epochWhitelist(uint16 epochId, address wallet) view returns (bool)"
```

**On-chain check:**
```
mintPrice: 0.0005 ETH → FREE-adjacent (~$0.085/NFT at $1700/ETH)
mintPaused: False → Mint is OPEN
earlyEpochWhitelistOnly: False → Public can mint
maxMintPerTx: 8
totalSupply: 85/5000 → Lots of supply remaining
```

## Limitations

- **Minified bundles** are harder to read but all data is still there — use `grep` with context, not human reading
- **Code-split bundles** (React.lazy) may split ABI and contract address into separate files — check all `assets/*.js` files
- **Turnstile / captcha-dependant mints**: The contract address may still be extractable, but the mint function requires a server-side signature that can't be recreated from the bundle alone. See `references/commit-dice-signature-mint.md`
- **Wagmi/viem contracts from third-party libraries**: Some projects import ABIs from external packages. In these cases, the function signatures may not be string literals in the JS but imported at build time — still present but harder to grep. Try searching for `functionName:` or `address:` patterns instead.
