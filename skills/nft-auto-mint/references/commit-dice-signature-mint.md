# Commit → Dice + Signature Mint Pattern

## Pattern Overview

Some NFT mints use a **2-step process**: a paid `commit` followed by a signature-gated `mintWithDice` or similar reveal. Unlike standard commit-reveal where the user controls the reveal salt, here the reveal step requires a **server-side EIP-191 signature** from a trusted signer — meaning the mint cannot be completed offline.

Discovered on **FinancialCalligraphyDisc (FCD)** at `0x286d46be39dd415655710F4960DF67879e0Bd5dC` (Ethereum mainnet).

## Step 1: `commitToMint(bytes32 commitment)`

```solidity
function commitToMint(bytes32 commitment) external payable {
    require(msg.value >= commitFee, "insufficient fee");
    // stores commitment, increments attemptCount
}
```

- **Cost**: `commitFee` (0.0001 ETH on FCD) — paid upfront, NOT refundable
- **commitment**: A simple `keccak256` of the user address — not a secret salt. The contract checks: `commitment == keccak256(abi.encodePacked(msg.sender))`
- **MAX_ATTEMPTS**: Hard cap (2 on FCD). Once `attemptCount[msg.sender] >= MAX_ATTEMPTS`, wallet is permanently locked from committing again. **Irreversible — no reset function.**
- **Paid even if you never mint**: The commit fee is consumed even if you never call step 2.

**Verification after commit:**
```python
attemptCount_abi = [{
    "inputs": [{"name":"","type":"address"}],
    "name": "attemptCount",
    "outputs": [{"name":"","type":"uint256"}],
    "stateMutability": "view",
    "type": "function"
}]
count = contract.functions.attemptCount(user_address).call()
# Expect: count >= 1 after successful commit
```

## Step 2: `mintWithDice(uint256 diceResult, uint256 nonce, bytes signature)`

```solidity
function mintWithDice(uint256 diceResult, uint256 nonce, bytes calldata signature) external {
    // Verifies signature from trustedSigner
    // mints diceResult tokens to caller
}
```

Parameters:
| Param | Type | Value | Notes |
|-------|------|-------|-------|
| `diceResult` | uint256 | 1–6 | Number of tokens you receive. Choice is up to you — the contract doesn't randomize. |
| `nonce` | uint256 | 1 (first attempt) | Matches `attemptCount[msg.sender]` after commit. |
| `signature` | bytes | EIP-191 signature | **Must be from `trustedSigner`** — you CANNOT generate it yourself. |

## The Signature Problem

The signature must be produced by the contract's `trustedSigner` address:

```solidity
address public trustedSigner;  // FCD: 0xFC11D7D08dF23106Ac728c4A54c2d49F34F2c000
```

The expected message hash follows EIP-191:

```solidity
function diceMessageHash(address user, uint256 diceResult, uint256 nonce) public view returns (bytes32) {
    return ECDSA.toEthSignedMessageHash(
        keccak256(abi.encodePacked(user, diceResult, nonce))
    );
}
```

**You cannot generate this signature offline.** The private key for `trustedSigner` is held by the project backend. The signature is only available through the official dApp frontend when you:

1. Connect your wallet to the dApp
2. Complete any required captcha/verification
3. The backend signs your request and injects the signature into the transaction

## Solutions for the User

### A) Use the official dApp frontend (recommended)
- Navigate to the project website
- Connect the wallet that already committed
- Complete the mint flow — the frontend handles signature generation
- After success, verify token IDs via Transfer events in receipt logs

### B) Wait for the project to release a signature API
- Some projects expose a public API endpoint for signature generation
- Check project docs, Discord, or Twitter for API documentation
- Example hypothetical: `POST /api/mint-signature { wallet, diceResult } → { signature }`
- Not available on FCD as of discovery

## Cost Breakdown (FCD Mainnet Example)

| Item | Cost |
|------|------|
| commitFee | 0.0001 ETH (~$0.18 at ~$1,800 ETH) |
| Gas for commit | ~80k gas, ~0.00003 ETH (at 0.2 gwei) |
| Gas for mintWithDice | ~100-150k gas, ~0.00004 ETH |
| **Total per wallet** | **~0.00017 ETH (~$0.30)** |

## Pitfalls

1. **MAX_ATTEMPTS = 2 is a HARD LOCK** — If you commit twice (e.g. first commit expired, you commit again), the wallet is **permanently locked** from minting via this contract. There is no `clearCommit()` or reset function. **Fund the wallet enough for BOTH commit AND eventual mint fee before the first commit.**

2. **Dice result ≠ random** — Don't assume the contract rolls dice for you. You pick `diceResult` (1–6) yourself. Pick the number of tokens you want.

3. **Commit fee is spent regardless** — Even if signature is never obtained, the 0.0001 ETH commit fee is gone. Only commit when you're sure the project is active.

4. **DRPC/Public RPC revert on `attemptCount`** — Some public RPC endpoints (eth.drpc.org, publicnode.com) may revert when calling `attemptCount(address)` or `mintState(address)` if the wallet hasn't committed on that specific RPC's synced state. Use a different RPC or check via Etherscan/Blockscout.

5. **No cross-wallet signature reuse** — `diceMessageHash` includes `user` address, so W1's signature cannot be used for W2. Each wallet needs its own signature from the frontend.

6. **Recommended sequence: fund → commit → immediately mint** — Don't leave a wallet in "committed but not minted" state. If you get distracted and the project goes offline, you lose both the commit fee and the wallet.

## Detection Checklist

Suspect a commit-dice-signature pattern when:

- [ ] Contract has `commitToMint` or similar commit function with a fee
- [ ] Contract has `mintWithDice` or similar function taking `diceResult` + `signature`
- [ ] Public `trustedSigner` or `signer` address in contract state
- [ ] `MAX_ATTEMPTS` or `maxAttempts` constant with low value (2–5)
- [ ] No `revealAndMint` or `claim` function
- [ ] No public mint function without signature
