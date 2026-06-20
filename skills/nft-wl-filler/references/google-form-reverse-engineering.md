# Google Form Reverse-Engineering

> How to extract field structure, entry IDs, validation rules, and sign-in requirements from any Google Form's raw HTML.

## Quick Check: Does the form require sign-in?

```bash
FORM_KEY="1FAIpQLSdwvzH8bFzCQ2MXsUhF7UtPf358x2_gjAUi2bsHwBXklt_YGQ"
curl -sL "https://docs.google.com/forms/d/e/${FORM_KEY}/viewform" | grep -o 'data-sign-in-to-continue="[^"]*"'
```

- `true` → Google sign-in required. **Cannot automate from server.** Direct POST returns 401.
- `false` or absent → can potentially submit via direct POST or automated browser.

## Extract All Fields & Entry IDs

```bash
FORM_KEY="1FAIpQLSdwvzH8bFzCQ2MXsUhF7UtPf358x2_gjAUi2bsHwBXklt_YGQ"
curl -sL "https://docs.google.com/forms/d/e/${FORM_KEY}/viewform" | \
  grep -oP 'FB_PUBLIC_LOAD_DATA_\s*=\s*\K.*(?=;\s*</script>)' > form_data.json
```

### Parsing the `FB_PUBLIC_LOAD_DATA_` structure

```
[null, [formMeta, [field1, field2, ...], ...], null, null, ...]
```

Each field: `[entry_id, "Field Title", ...validation..., null, null, null, null, null, null, [null, "Description"]]`

| Element | Meaning |
|---------|---------|
| `entry_id` (first) | The `entry.XXXXX` number for POST |
| `"Title"` (second) | Field label shown to user |
| field type | `0`=short text, `4`=checkbox/radio, `8`=section header |
| validation tuple | `[2, maxLen, ["expected"], "Error msg"]` — CODE field pattern |

### Field type reference

From the 3rd element + validation context:
- **0 (short text):** `[entry_id, "Label", null, 0, [[validation_or_null]]]` — simple text input
- **4 (checkbox/radio):** `[entry_id, "Label", null, 4, [[option_id, [["DONE", ...]], 1, ...]]]` — clickable option
- **8 (section/description):** `[entry_id, "Section Title", "...description...", 8, ...]` — header text only

## Extract Form Action URL and fbzx

```bash
curl -sL "https://docs.google.com/forms/d/e/${FORM_KEY}/viewform" | grep -o 'action="[^"]*formResponse'
# → https://docs.google.com/forms/d/e/{FORM_KEY}/formResponse

curl -sL "https://docs.google.com/forms/d/e/${FORM_KEY}/viewform" | grep -oP 'name="fbzx" value="\K[^"]*'
# → e.g. -1112255991407298147
```

## Multi-Page Forms

Look for:
```html
data-first-entry="0" data-last-entry="1"
```

- `first-entry` = current page index (0-based)
- `last-entry` = last page index
- If they differ, the form has multiple pages
- Page 1 typically has a CODE field with validation
- Clicking "Next" (`div[role="button"][jsname="OCpkoe"]`) advances to page 2
- Hidden field `pageHistory=0` tracks which page was submitted

## Direct POST Method (for forms WITHOUT sign-in requirement)

```bash
curl -s -X POST \
  -d "entry.580142988=pondSYD" \
  -d "entry.783727651=DONE" \
  -d "entry.2106406602=https://x.com/user/status/123" \
  -d "entry.1615559766=0x..." \
  -d "fvv=1" \
  -d "partialResponse=[null,null,\"-1112255991407298147\"]" \
  -d "pageHistory=0" \
  -d "fbzx=-1112255991407298147" \
  -d "submissionTimestamp=-1" \
  "https://docs.google.com/forms/d/e/${FORM_KEY}/formResponse"
```

Required hidden fields:
- `fvv=1` — form version value
- `pageHistory=0` — page index being submitted
- `fbzx=...` — form ID (extract from HTML)
- `submissionTimestamp=-1` — auto timestamp
- `partialResponse=[null,null,"{fbzx}"]`

## Sign-In Required: Known Blockage

When `data-sign-in-to-continue="true"`:
- Direct curl POST → **HTTP 401**
- Playwright headless → Google shows "This browser or app may not be secure"
- Playwright + xvfb headed → same block
- System Chrome (channel="chrome") → same block
- Undetected-chromedriver → same block
- **Cause:** Google detects data center IPs + automation signals. No known workaround for servers.
- **Action:** Tell user to open form in their real browser (phone/desktop). Complete Twitter tasks on your end.

## Real Example: POND Syndicate Round 1 WL

**Form Key:** `1FAIpQLSdwvzH8bFzCQ2MXsUhF7UtPf358x2_gjAUi2bsHwBXklt_YGQ`

**Extracted fields:**
| Entry ID | Type | Label | Validation |
|----------|------|-------|------------|
| 580142988 | short text | CODE | Answer: "pondSYD", Error: "Wrong Code!!" |
| 212700206 | section | Task WL submission | Description text |
| 783727651 | radio | Follow here | Options: DONE |
| 1795631508 | radio | Reetwet & Like here | Options: DONE |
| 2106406602 | short text | Quote tweet here & drop link | Free text |
| 1615559766 | short text | EVM address | Free text |

**fbzx:** `-1112255991407298147`  
**Sign-in required:** Yes (`data-sign-in-to-continue="true"`)  
**Pages:** 2 (`data-first-entry="0" data-last-entry="1"`)
