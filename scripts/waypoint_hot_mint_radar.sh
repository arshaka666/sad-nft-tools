#!/usr/bin/env bash
# Waypoint HOT NFT radar with persistent collection-level dedupe.
exec python3 "${HERMES_HOME:-$HOME/.hermes}"/scripts/waypoint_hot_mint_radar.py --limit 2 --listen-seconds 8 --max-collection-age-hours 72
