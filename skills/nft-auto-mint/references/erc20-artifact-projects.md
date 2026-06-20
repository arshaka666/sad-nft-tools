# DAEMONS-style ERC20 artifact projects

Use this reference when an NFT-looking project is actually an ERC20 “object/artifact” launch with later ERC721 wrapping.

## Signals

- Website copy says “ERC20 object model”, “whole token corresponds to artifact”, “wrap into ERC721”, or “Uniswap v4 hook”.
- Routes like `/my-daemons` or `/explore` may exist but show `COMING SOON`.
- No wallet-connect or mint button is active in the frontend.
- Frontend JS may not contain contract addresses; addresses may need to be discovered from DEX/search/on-chain explorers.
- The correct action may be **swap/buy ERC20**, not mint ERC721.

## Discovery workflow

1. Inspect official site text and links first.
   - Look for X/Discord/docs links and exact wording about ERC20 vs ERC721.
   - If docs are disabled or coming soon, do not assume a hidden mint.

2. Inspect bundled JS for hardcoded addresses and web3 libraries.
   - Search for `0x[a-fA-F0-9]{40}`, `mint`, `wrap`, `contract`, `wagmi`, `viem`, `ethers`, `connect`.
   - If no wallet library/address is present, the landing page may be informational only.

3. Search DEX aggregators for likely ERC20s.
   - Dexscreener search can reveal multiple clones; list candidates with chain, pair, token address, liquidity, volume, and supply.
   - Prefer candidates whose verified source references the official website/X and whose supply matches site copy.

4. Verify candidate contracts on Blockscout/Etherscan.
   - Read `name()`, `symbol()`, `decimals()`, `totalSupply()`, `balanceOf(user)`.
   - Fetch verified source and confirm official URLs/comments.
   - Check creation txs and owner/admin actions such as `setHook`, `renounceOwnership`, pool creation.

5. For Uniswap v4 hook projects, recover hook/pool details from transactions.
   - Decode `setHook(address)` on the token contract.
   - Decode liquidity-manager `createPoolAndAddLiquidity((currency0,currency1,fee,tickSpacing,hooks),...)` to get token/hook/pool config.

6. Report clearly:
   - “Not a direct NFT mint” if true.
   - Token contract, hook, pool/Dexscreener link, user wallet token balance.
   - Whether any executable mint/wrap action exists now.
   - If only buying ERC20 is possible, say so and avoid sending any mint transaction.

## DAEMONS example validated in-session

Official site: `https://daemons.life/`

Likely official token discovered:
- Token: `0x96B760d7c19fbf542ea0E35702e88fED49F10416`
- Name/symbol: `DAEMONS` / `DAEMON`
- Supply: `6666`
- Verified source name: `DaemonToken`
- Source comments include `Website: https://daemons.life` and `Twitter: https://x.com/DAEMONSv4`

Hook/pool:
- Hook set via `setHook`: `0x2066BB6Fd52cA49ca7e6b9B861e8a140162740c0`
- V4 ETH/DAEMON pool shown by Dexscreener/decoded pool tx:
  `0x2c40f5ef0931c1b761aabe06077fb88e5c4e9f3e9e889e34003116d7c531737d`

Important pitfall:
- Dexscreener returned multiple DAEMONS/DAEMON tokens, including higher-liquidity or higher-volume clones. Do not pick solely by volume/price. Verify supply and official source references.
