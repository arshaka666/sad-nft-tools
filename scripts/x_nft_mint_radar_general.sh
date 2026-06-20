#!/usr/bin/env bash
# Anti-spam: max 3, current month only, prioritize very recent posts (<=72h), dedupe by tweet/url/content fingerprint.
exec python3 "${HERMES_HOME:-$HOME/.hermes}"/scripts/x_nft_mint_radar_format.py --mode general --limit 3 --max-age-hours 72
