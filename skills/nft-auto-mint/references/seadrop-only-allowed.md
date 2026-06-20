# ERC721SeaDrop — `onlyAllowedSeaDrop` Modifier

## The Problem

When you find an ERC721SeaDrop (Seadrop) contract and call `mintSeaDrop(address,uint256)`, it reverts with:

```
0x15e26ff3 → OnlyAllowedSeaDrop()
```

This is NOT a bug or closed mint — it's a **modifier restriction**. Only the registered SeaDrop implementation contract can call `mintSeaDrop()` on the NFT proxy.

## Detection

1. Identify Seadrop via Blockscout: `ERC721SeaDropCloneable` or `ERC721SeaDrop`
2. The ABI shows `mintSeaDrop(address minter, uint256 quantity)` as nonpayable
3. Simulate with `eth_call` → returns `0x15e26ff3` (OnlyAllowedSeaDrop error selector)

## Solutions

### A) Use OpenSea UI (easiest)
If the collection is listed on OpenSea drops, users just click "Mint" on the OpenSea page. OpenSea's frontend calls their Seadrop backend, which calls the SeaDrop implementation, which calls `mintSeaDrop()` on the proxy.

### B) Find & call SeaDrop implementation
The SeaDrop implementation is an intermediary contract. To find it:
- Check the proxy's implementation via ERC1967 storage slot: `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`
- If the ABI on Blockscout shows `updatePublicDrop(address seaDropImpl, ...)` functions, the `seaDropImpl` parameter IS the implementation address
- The SeaDrop impl has its own `mint()` or `purchase()` function that forwards to the NFT proxy

### C) Via OpenSea GraphQL (for bots)
See `references/opensea-allowlist-fcfs-bot.md` — use `swap(action: MINT)` GraphQL query to fetch signed calldata, then send as raw tx.

## getMintStats helper

Even though you can't call `mintSeaDrop()` directly, you CAN call `getMintStats(address)` (view function, no modifier):

```
selector: 0xda023918  (keccak256("getMintStats(address)")[:4])
params:   address minter
returns:  (uint256 mintPrice, uint256 totalMinted, uint256 maxMintableByWallet)
```

- `mintPrice` = 0 means FREE mint
- `totalMinted` = global total supply minted (NOT per-wallet)
- `maxMintableByWallet` = from PublicDrop config (often = maxSupply, NOT per-wallet limit)
