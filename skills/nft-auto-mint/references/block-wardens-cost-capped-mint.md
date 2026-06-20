# Block Wardens / WARDEN Session Lessons — Cost-Capped Free Mint + Consolidation

Contract: `0x0631716336bcA07219cF8EeEB09d729f8c7CC93B` (Block Wardens / WARDEN)

## Contract pattern

- Public free mint uses `mint()` (nonpayable), not `mint(uint256)`.
- Useful views observed:
  - `mintOpen() -> bool`
  - `price()/mintPrice()/MINT_PRICE() -> 0`
  - `canMint(address) -> bool`
  - `numberMinted(address) -> uint256`
  - `remainingSupply()/totalSupply()`
- Per-wallet limit is 1.
- Mint gas is high for a free mint: roughly `219k–229k` gas used; estimates around `226k–235k`.

## Cost-cap pitfall

The user expects very cheap mints (about `$0.10` max) and reacted negatively when mints cost `$0.23–$0.26`. For this contract, at ~220k gas and ~$1,800/ETH, the effective gas price must be about `<= 0.25 gwei` to stay under `$0.10`:

```text
max_effective_gwei ~= (0.10 / eth_usd) * 1e9 / gas_used
# gas_used=220000, eth_usd=1800 => ~0.2525 gwei
```

If `baseFeePerGas + priorityFee` is higher than this, skip/wait. Do not try to force a lower `maxFeePerGas` below base fee.

## EIP-1559 cheap policy

For cheap mints/transfers:

- Use `maxPriorityFeePerGas` around `0.005–0.02 gwei`.
- Use `maxFeePerGas = baseFeePerGas + priority` (or a tiny base cushion only if still under cap).
- Compute worst-case fee with `gas_limit * maxFeePerGas` and compare against the user's USD cap before broadcasting.

## Receipt/token parsing gotcha

When reading `web3.py` receipt log topics, `.hex()` may return strings **without** the `0x` prefix. Normalize topics with `.replace('0x','')` before comparing.

Transfer event parser:

```python
TRANSFER_TOPIC = 'ddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
ZERO_TOPIC = '0' * 64
for lg in receipt.logs:
    topics = [t.hex().lower().replace('0x','') for t in lg.topics]
    if len(topics) >= 4 and topics[0] == TRANSFER_TOPIC and topics[1] == ZERO_TOPIC:
        to = Web3.to_checksum_address('0x' + topics[2][-40:])
        token_id = int(topics[3], 16)
```

## Consolidation lesson

Even `safeTransferFrom` can exceed `$0.10` when base fee is high. For WARDEN, transfer estimates were about `66k gas` and gas limit about `81k`; at ~0.70–0.75 gwei base fee, estimated transfer cost was `$0.102–$0.109`, so transfers were correctly skipped under a `$0.10` cap.
