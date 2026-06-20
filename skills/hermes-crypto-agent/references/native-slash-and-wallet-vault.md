# Native Web3 slash commands + wallet vault operations

## When this reference applies
Use this when a user invokes native gateway shortcuts such as `/wallet`, `/balance`, `/portofolio`, `/track-wallet`, `/mint-history`, or asks to batch-create wallets for NFT/Ethereum work.

## Slash-command routing lessons
- Keep Web3 slash commands class-level and mapped to the active skill, not to stale backup directories.
- Telegram command names cannot contain hyphens. Register/surface hyphenated commands as underscores in Telegram menu while accepting both forms in typed text where possible:
  - `/track-wallet` ⇄ `/track_wallet`
  - `/mint-history` ⇄ `/mint_history`
- Support common user spelling/shape for mint history: `/mint history ...` and `/mint histroy ...` should route to the mint-history intent.
- After editing Hermes gateway command registry or handler code, verify both registry and menu output, then restart/reload the gateway so Telegram `set_my_commands` refreshes.

## Backup skill collision pitfall
If a backup folder like `hermes-crypto-agent.backup_YYYY...` retains frontmatter `name: hermes-crypto-agent`, native `/hermes-crypto-agent` or Web3 shortcuts can load the backup instead of the active skill. Fix slash-command scanning or rename/exclude backup directories so the active path resolves to:

```text
/root/.hermes/skills/web3/hermes-crypto-agent
```

Verification pattern:

```python
from agent.skill_commands import reload_skills, resolve_skill_command_key, get_skill_commands
reload_skills()
key = resolve_skill_command_key('hermes-crypto-agent')
info = get_skill_commands().get(key, {}) if key else {}
assert '.backup_' not in str(info.get('skill_dir'))
```

## Batch wallet creation safety pattern
For user-owned Ethereum/NFT wallet batches:
1. Use EVM by default if the user’s current Web3 context is NFT + Ethereum.
2. Generate/import through the encrypted `WalletManager` vault, not plaintext files.
3. Ensure `HERMES_MASTER_PW` exists in `~/.hermes/.env`; create a strong random value if absent and chmod `.env` to `0600`.
4. Store secrets only in `~/.hermes/vault.enc`; chmod the vault to `0600`.
5. Export public addresses only, e.g. `label,chain,address`. Never export private keys, mnemonics, seeds, or token credentials.
6. Validate after generation:
   - expected wallet count
   - all addresses match `^0x[a-fA-F0-9]{40}$`
   - all addresses unique
   - vault/export file permissions are `0600`
   - public exports contain no private-key-like 64-hex strings and no `private`, `mnemonic`, or `seed` columns
7. If gateway must read the new env value, schedule/restart gateway after the current run rather than interrupting active work mid-turn.

## Minimal public-output format
Report only:
- count created
- vault path and permission
- public address export paths
- verification results
- first few public addresses if useful

Do **not** print private keys or mnemonics in the chat. If the user later asks to reveal seed/private key, require explicit confirmation and show only the requested wallet secret once.
