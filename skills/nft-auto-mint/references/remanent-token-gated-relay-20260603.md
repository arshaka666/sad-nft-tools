# Remanent Token-Gated Relay — June 2026 Notes

Context: Remanent contract `0xb2b8083f52fdbae4ccd04095c3e09d9d9ce840bf` previously allowed free first mints for wallets holding a gate pass token from collection `0x4A93f81BF6e6cC3659Ff429156218413c6f746d7` (pass token ID `2670`). The pass was successfully relayed across W1-W20 in an earlier run.

## Current durable lesson

Before relaying a pass, always re-query `getGateCollections()` live. Do not assume a previously valid gate collection remains valid. In this session, token ID `2670` was transferred from primary to W21 and `ownerOf(2670)` verified as W21, but `mint(1)` still reverted with `NotAllowlisted()` (`0x06fb10a9`) because `0x4A93...` was no longer in the live gate collection list.

## Safe handling pattern

1. Query:
   - `mintPhase()`
   - `getGateCollections()`
   - pass `ownerOf(tokenId)` and `balanceOf(wallet)`
   - target wallet `mintedPerWallet(address)` and Remanent `balanceOf(address)`
2. Confirm the pass contract address is in `getGateCollections()` before any relay.
3. If a relay transfer already occurred but mint simulation returns `NotAllowlisted()`, stop; do not broadcast mint.
4. Return the pass to the primary wallet immediately and verify across multiple RPCs if immediate post-receipt reads look stale.
5. Report honestly: no mint happened unless receipt status confirms the mint tx.

## Session-specific verified txs

- Primary -> W21 pass transfer: `0x6a2a7d04983410523d6d3b627803dc17e6bc26ca2f9f0af899b1e294c33c886e`, receipt status 1.
- W21 -> Primary return transfer: `0xedb87135a4a20a5cd44591f59b2c16cfdc97216b69cc1193f255ccd62a3c71a7`, receipt status 1.
- Final verification: owner of token `2670` returned to primary `0xprimary...wallet`, primary gate balance 1, W21 gate balance 0.
