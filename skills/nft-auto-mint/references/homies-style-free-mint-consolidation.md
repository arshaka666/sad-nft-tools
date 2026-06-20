# HOMIES-style custom ERC721A free mint + consolidation

Use this reference for custom ERC721/ERC721A contracts that expose a lowercase `freemint()` plus standard ERC721 transfer functions.

## Contract signals

Example: `HOMIES` at `0xff188576064669fb0e0b189eeaa754574f7f7d58`.

Useful ABI fragments:

```python
ABI = [
  {'inputs': [], 'name': 'freemint', 'outputs': [], 'stateMutability': 'nonpayable', 'type': 'function'},
  {'inputs': [{'type':'address','name':''}], 'name': 'minted', 'outputs': [{'type':'uint256'}], 'stateMutability':'view', 'type':'function'},
  {'inputs': [{'type':'address','name':'account'}], 'name': 'balanceOf', 'outputs': [{'type':'uint256'}], 'stateMutability':'view', 'type':'function'},
  {'inputs': [{'type':'uint256','name':'tokenId'}], 'name': 'ownerOf', 'outputs': [{'type':'address'}], 'stateMutability':'view', 'type':'function'},
  {'inputs': [], 'name': 'totalSupply', 'outputs': [{'type':'uint256'}], 'stateMutability':'view', 'type':'function'},
  {'inputs':[{'type':'address','name':'from'},{'type':'address','name':'to'},{'type':'uint256','name':'tokenId'}], 'name':'transferFrom', 'outputs':[], 'stateMutability':'nonpayable', 'type':'function'},
]
```

## Mint procedure

1. Confirm `totalSupply()`, `MAX_FREE()`, and `minted(wallet)==0`.
2. Simulate with `contract.functions.freemint().estimate_gas({'from': wallet, 'value': 0})`.
3. Check ETH balance covers `gas_limit * maxFeePerGas`.
4. Send EIP-1559 tx with explicit gas and zero value.
5. Wait for receipt. Only call it success if `receipt.status == 1`.
6. Parse token IDs from `Transfer(address(0), wallet, tokenId)` logs in the receipt.
7. Verify `balanceOf(wallet)` and `ownerOf(tokenId)`.

## Token discovery

For ERC721A-style contracts, ownership may only be stored at batch starts. `ownerOf(tokenId)` can walk backwards, so it still works. Prefer receipt log parsing for exact minted IDs. Keep a `KNOWN` mapping from wallet address to token IDs when consolidating later.

```python
sig = Web3.keccak(text='Transfer(address,address,uint256)').hex()
for log in receipt['logs']:
    if log['address'].lower() == CONTRACT.lower() and log['topics'][0].hex() == sig:
        to = '0x' + log['topics'][2].hex()[-40:]
        tid = int(log['topics'][3].hex(), 16)
```

## Consolidation to primary wallet

1. For each controlled wallet, call `balanceOf(wallet)`.
2. If balance > 0, use known receipt token IDs first. If known IDs are incomplete, scan `ownerOf(0..totalSupply-1)` until the wallet's balance count is found.
3. Simulate `transferFrom(wallet, primary, tokenId)` from the owning wallet.
4. Check ETH balance covers transfer gas.
5. Send `transferFrom`; wait for receipt.
6. Verify `ownerOf(tokenId) == primary` and primary `balanceOf` increased.

Important: report only receipt-confirmed transfers. A sent tx is not enough.

## Gas notes

On low-fee mainnet, `transferFrom` for this style used about `42,280` gas and `freemint()` used about `100,199` gas, but always estimate and add margin. A safe pattern is `gas = int(estimate * 1.3) + 5000`, with low but base-fee-valid EIP-1559 priority (for example ~0.12 gwei when the base fee is ~0.14 gwei).
