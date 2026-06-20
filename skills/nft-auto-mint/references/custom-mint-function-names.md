# Custom Mint Function Names (2025-2026 collections)

Many newer NFT contracts use non-standard mint function names instead of the generic `mint()`.

## Observed in this session
- Contract: `0xdb971E79304C8E0dc439f444fDdc2C5648D081E5` (DinoNFT / DinoEggs)
- Working function: `mintDino(uint256 quantity)` — payable, 1 param

## Detection update
The `_find_mint_fn` helper in `scripts/nft_auto_mint.py` was extended to include:
`mintdino`, `mintegg`, `mintnft`

## Recommended workflow
1. Fetch ABI from Blockscout
2. Filter for `stateMutability == "payable"` + name contains "mint"
3. Use the first matching function name dynamically

This pattern avoids hardcoding and catches creative naming like `mintDino`, `claimDinoEgg`, `publicMintSeason2`, etc.