# Token ID Discovery Reference

## Problem

After minting, you often need the **token ID** to verify receipt, display in summaries, or prepare for transfers. Some contracts implement ERC721Enumerable (has `tokenOfOwnerByIndex`), but many don't. This reference covers both paths.

## Method 1: ERC721Enumerable (tokenOfOwnerByIndex)

If the contract supports it, call `tokenOfOwnerByIndex(owner, index)`:

```bash
# balanceOf first
curl -s -X POST "$RPC" -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_call","params":[{
    "to":"0xCONTRACT",
    "data":"0x70a08231000000000000000000000000OWNER_ADDRESS"
  },"latest"],"id":1}'

# Then iterate indexes 0..balance-1
curl -s -X POST "$RPC" -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_call","params":[{
    "to":"0xCONTRACT",
    "data":"0x2f745c59000000000000000000000000OWNER_ADDRESS" + PADDED_INDEX
  },"latest"],"id":1}'
```

**Python (web3.py):**
```python
contract = w3.eth.contract(address=addr, abi=abi_erc721_enumerable)
for i in range(balance):
    token_id = contract.functions.tokenOfOwnerByIndex(owner, i).call()
```

## Method 2: Transaction Receipt Logs (Works for ALL ERC-721)

**Always works** regardless of ERC721Enumerable support. Parse the `Transfer` event from the mint transaction receipt.

### ERC-721 Transfer Event Structure
```
event Transfer(address indexed from, address indexed to, uint256 indexed tokenId)
```
- Topic[0] = `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef`
- Topic[1] = `from` (0x0..0 for mints)
- Topic[2] = `to` (your wallet, padded to 32 bytes)
- Topic[3] = `tokenId` (the ID you need)

### Python Implementation

```python
from web3 import Web3

w3 = Web3(Web3.HTTPProvider(RPC))

def get_token_ids_from_tx(tx_hash: str, target_wallet: str = None):
    receipt = w3.eth.get_transaction_receipt(tx_hash)
    if not receipt or receipt['status'] != 1:
        return []
    
    token_ids = []
    for log in receipt['logs']:
        topics = [t.hex() for t in log['topics']]
        if len(topics) >= 4 and topics[0] == "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef":
            # Topic[3] is always the token ID (uint256 indexed)
            token_id = int(topics[3], 16)
            receiver = "0x" + topics[2][-40:]
            
            if target_wallet is None or receiver.lower() == target_wallet.lower():
                token_ids.append({
                    'token_id': token_id,
                    'receiver': receiver
                })
    
    return token_ids

# Usage
tx_hash = "0x315d83db..."
tokens = get_token_ids_from_tx(tx_hash, "0xabcd...1234")
for t in tokens:
    print(f"Token ID: {t['token_id']} → {t['receiver'][:10]}...")
```

### Key Details

- Topic[2] (`to`) is **32 bytes, left-padded with zeros**. A wallet `0xabcd...1234` becomes `0x000000000000000000000000abcd...1234` in the log. Parse it by taking the last 40 chars.
- Topic[3] (`tokenId`) is also 32 bytes, left-padded with zeros. `int(topics[3], 16)` gives the decimal ID.
- Some contracts emit additional events alongside Transfer (e.g. `0x53ad88936...` for claim events). Focus on Topic[0] = Transfer signature.
- Mint events have Topic[1] = `0x0000000000000000000000000000000000000000000000000000000000000000` (zero address = mint from contract).

## Method 3: Alchemy getAssetTransfers (API)

When you need historical token IDs without iterating all txs:

```python
import requests

payload = {
    "jsonrpc": "2.0",
    "method": "alchemy_getAssetTransfers",
    "params": [{
        "fromBlock": "0x0", "toBlock": "latest",
        "fromAddress": "0x0000000000000000000000000000000000000000",  # mint
        "toAddress": wallet_address,
        "contractAddresses": [contract_address],
        "category": ["erc721"],
        "withMetadata": True
    }],
    "id": 1
}
r = requests.post(RPC, json=payload)
```

## Notes

- Token IDs can be very large (10000+) — always use `int()` not limited parsing
- Never assume token IDs are sequential
- After a transfer, the receipt of the **transfer tx** contains the token ID in its logs too (Transfer event from old owner to new owner)
