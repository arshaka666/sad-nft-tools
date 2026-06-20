# OpenSea FCFS Allowlist Mint Bot

Berdasarkan artikel **"How I built FCFS NFT Minter Bot?"** oleh [@Zun2025](https://x.com/Zun2025/status/2037435538828063196) — 115K+ views.

## The Problem

OpenSea allowlist mints pake **`mintSigned`** — butuh **salt + signature** dari server OpenSea. Gak bisa pre-build calldata kaya public mint biasa.

```solidity
function mintSigned(
    address to, uint256 quantity,
    bytes32 salt, bytes memory signature
) public payable
```

Kalo public mint: encode calldata locally → sign offline → fire tx pas go-live. ✅  
Kalo allowlist di OpenSea: **gak bisa** — butuh salt + signature dari server dulu.

## Reverse Engineering

### 1. Key Chunk: `008d99104100f8fb.js`

Ditemukan di webpack chunk Next.js OpenSea. Dua GraphQL query:

| Query | Fungsi |
|-------|--------|
| `MintActionTimelineQuery` | **Core** — fetch calldata via `swap(action: MINT)`. Return `transactionSubmissionData`: `target` (contract), `calldata` (encoded w/ salt+signature), `value` (ETH) |
| `MintQuery` | Fetch collection metadata, drop identifiers, chain info |

### 2. SIWE Auth Flow

OpenSea pake Sign-In With Ethereum buat auth internal.

**CRITICAL DETAILS (gak ada di dokumentasi):**

| Parameter | Value | Pitfall |
|-----------|-------|---------|
| SIWE message statement | `"wants you to sign in with your account:"` | **Bukan** `"Ethereum account"` — 1 kata salah, server reject silently |
| URI | `encodeURI("https://opensea.io/")` | **Wajib trailing slash** |
| Wallet address | lowercase, as-is | No checksum encoding — `0xabc...` not `0xAbC...` |
| Verify endpoint input | **Parsed fields** (bukan raw signed message) | Kirim `{domain, address, statement, uri, version, chainId, nonce, issuedAt, signature, chainArch: "EVM", connectorId: "injected"}` |
| Response | Set-Cookie: `access_token` + `refresh_token` | max-age ~3.5 hari |
| **Missing header** | `x-app-id: os2-web` | Tanpa ini, semua GraphQL request ditolak 400 |

### 3. Infrastructure & Latency

```
gql.opensea.io     → Cloudflare IAD (Ashburn, VA) → ~8ms ping
mainnet-preconf.base.org → Cloudflare IAD            → ~7ms ping
Round-trip swap query                                    → ~80ms total
```

**Rule of thumb:** Dari region IAD (US East Coast), ~80ms round-trip. Dari Eropa/Asia, 200-400ms. Di FCFS mint, itu beda **block N vs block N+1**.

## Bot Architecture (Rust)

### Flow Diagram

```
Auto-Scheduling (poll dropBySlug tiap 30s)
    ↓
Warm-Up Phase (T-5s: pre-fetch nonces, keepalive)
    ↓
Calldata Fetch (T-1.5s: hammer swap(), BATCH wallets)
    ↓
Sign & Send (libsecp256k1 C FFI, cached nonce)
    ↓
Confirmation (base_transactionStatus RPC)
```

### STEP 1 — Auto-Scheduling

- Query `dropBySlug` GraphQL → dapet stage timing, start times, stage indexes, labels
- Sleep 30s, polling terus
- Auto-adjust kalo creator ngubah waktu — gak perlu manual reschedule

### STEP 2 — Warm-Up (T-5 detik)

Pre-compute semua yang bisa sebelum fire time:

1. **Nonce pre-fetching** — fetch nonce tiap wallet dari RPC, cache. Zero delay.
2. **Chain ID** — confirm sekali, cache forever.
3. **HTTP connection warming** — keepalive ping ke OpenSea endpoint + RPC. HTTP/2 koneksi dingin kalo gak dipake.

**Fault-tolerant:** Kalo 1 wallet gagal fetch nonce → skip wallet itu doang. Kalo semua gagal → fallback ke live fetching. **Never abort entirely. Always degrade gracefully.**

### STEP 3 — Calldata Fetch (T-1.5 detik ⭐ KEY INNOVATION)

#### Tight Retry Loop

Hammer `swap()` query mulai 1.5 detik sebelum mint time. Pas OpenSea mulai return valid calldata, langsung siap — gak nunggu.

#### BATCH GRAPHQL — Field Aliasing

**Ini trik utama yang gak ada di bot lain:** Semua wallet di-batch dalam **1 GraphQL query** pake field aliasing:

```graphql
query B {
  w0: swap(address: "0xWallet0", collectionSlug: "...", quantity: 1) {
    transactionSubmissionData {
      target
      calldata
      value
    }
  }
  w1: swap(address: "0xWallet1", collectionSlug: "...", quantity: 1) {
    transactionSubmissionData {
      target
      calldata
      value
    }
  }
  # ... up to 50+ wallets in ONE request
}
```

**Kenapa ini gila cepat:**
- **1 HTTP round-trip** buat semua wallet (bukan N request)
- **1 POST** -> semua calldata balik sekaligus
- Query name `"B"` = minimal bytes
- Mapping trivial dari alias (`w0`, `w1`, ...)

**Per-alias error handling:**
| Error | Action |
|-------|--------|
| `InsufficientFund` | Skip wallet, no retry |
| `DropNotMintingError` | Mint belum live → retry whole batch |
| ≥1 wallet sukses | Batch lanjut; individual failures gak bunuh batch |

### STEP 4 — Sign & Send

Pas mint live, semua udah siap:

1. **Build tx** — pake cached nonce + calldata dari OpenSea + gas params from config
2. **Sign** — pake **libsecp256k1 via C FFI** (bukan pure Rust k256 crate)
   - C library ~1.8x lebih cepat (~70 μs per signature)
3. **Send** — `eth_sendRawTransaction` ke RPC

**No gas estimation in hot path** — pake gas params fixed dari config.

### STEP 5 — Confirmation (Base chain)

Pake `base_transactionStatus` RPC method:

| Status | Artinya |
|--------|---------|
| `Unknown` | Tx belum kelihatan |
| `Known` | Tx diterima |
| `Preconfirmed` | Confirmed |

Pas status jadi `Known` → switch ke receipt polling. Pas receipt landing → recording + done.

## Key Takeaways for NFT Minting

1. **OpenSea allowlist != public mint** — Flow-nya beda total. `mintSigned()` butuh server salt + signature via GraphQL `swap()` endpoint
2. **Batch GraphQL with field aliasing** — 1 query, banyak wallet. Ini trik paling underrated.
3. **Auth flow:** SIWE sign → parsing fields → `x-app-id: os2-web` → cookies → GraphQL
4. **Region matters:** Deploy deket IAD (Ashburn, VA) buat sub-100ms ke OpenSea/Base
5. **Warm-up** everything: nonces, chain ID, HTTP connections
6. **Rust + libsecp256k1 C FFI** for ~1.8x faster signing

## Source

- X Article: https://x.com/Zun2025/status/2037435538828063196
- Author: [@Zun2025](https://x.com/Zun2025)
- Views: 115K+
