---
name: nft-wl-filler
description: Isi Google Form WL — reverse engineer form fields, detect sign-in requirement, handle multi-page forms, and complete Twitter tasks
version: 1.7
---

```python
from playwright.sync_api import sync_playwright
import csv, time, random
from pathlib import Path

def run(form_url, data_file="wallets.csv", cookies_file="~/google-cookies.txt", max_entries=5):
    if not Path(data_file).exists():
        print("❌ wallets.csv tidak ditemukan!")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=['--no-sandbox'])
        context = browser.new_context()
        
        # Load Cookies
        print("Loading Google cookies...")
        cookies = []
        with open(cookies_file.replace("~", "/root")) as f:
            for line in f:
                if line.startswith('#') or not line.strip():
                    continue
                parts = line.strip().split('\t')
                if len(parts) >= 7:
                    cookies.append({
                        "name": parts[5],
                        "value": parts[6],
                        "domain": parts[0],
                        "path": parts[2]
                    })
        context.add_cookies(cookies)
        
        page = context.new_page()

        with open(data_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= max_entries: break
                try:
                    print(f"[{i+1}] Mengisi form...")
                    page.goto(form_url, timeout=60000, wait_until="networkidle")
                    time.sleep(3)

                    page.fill('input[aria-label*="Wallet" i]', row.get('wallet', ''))
                    page.fill('input[aria-label*="Twitter" i]', row.get('twitter', ''))
                    
                    page.click('button[type="submit"], span:has-text("Submit")')
                    time.sleep(random.uniform(5, 10))
                    print(f"✅ Sukses {i+1}")
                except Exception as e:
                    print(f"❌ Error baris {i+1}: {e}")
        
        browser.close()
    print("✅ Automation selesai!")

## Google Form Reverse-Engineering

### Extract form fields from HTML

Google Forms embed field structure in `FB_PUBLIC_LOAD_DATA_` JS variable (visible in curl output):

```bash
curl -sL "https://docs.google.com/forms/d/e/{FORM_KEY}/viewform" | grep -oP 'FB_PUBLIC_LOAD_DATA_\s*=\s*\K.*(?=;\s*</script>)'
```

**Structure:** `[null, [formMeta, [field1, field2, ...], ...], ...]`

Each **field** is: `[entry_id, "Title", ...validation, null, null, null, null, null, null, [null, "Description"]]`

- `entry_id` (first element) = the entry.XXXXX number for POST
- Field types: `0` = short text, `4` = checkbox/radio
- Validation: `[2, 100, ["expected_answer"], "Error msg"]` for CODE fields
- Checkbox options have `[["DONE", null, null, null, 0]]` pattern

### Detect sign-in requirement

From curl output, check for:

```bash
grep -o 'data-sign-in-to-continue="[^"]*"' form.html
```

- `data-sign-in-to-continue="true"` → form REQUIRES Google sign-in
- Direct POST to `/formResponse` returns **401** when this is set
- **Cannot** be automated from data center IPs — Google blocks with "This browser or app may not be secure"
- Solution: tell user to open form in their real browser

### Multi-page forms

Look for `data-first-entry` / `data-last-entry` attributes:
- `data-first-entry="0" data-last-entry="1"` = 2 pages
- CODE field + "Next" button on page 1 → validation unlocks page 2
- Extract validation answers from the field's validation tuple

### Direct POST approach (no-sign-in forms only)

```bash
curl -s -X POST \
  -d "entry.580142988=pondSYD" \
  -d "entry.2106406602=https://x.com/user/status/123" \
  -d "entry.1615559766=0x..." \
  -d "fvv=1" \
  -d "pageHistory=0" \
  -d "fbzx=FORM_FBZX" \
  -d "submissionTimestamp=-1" \
  "https://docs.google.com/forms/d/e/{FORM_KEY}/formResponse"
```

- Get `fbzx` from HTML: `<input type="hidden" name="fbzx" value="...">`
- Returns HTTP 401 if sign-in is required

## POND Syndicate Pattern

**Form URL:** Google Form with signing required, CODE field, Twitter tasks

**Fields:**
1. CODE (pondSYD) — short text, unlocks page 2
2. Follow + Like+RT — radio buttons with "DONE"
3. Quote tweet URL — text input
4. EVM Wallet — text input

**Twitter tasks (Playwright + cookie auth):**
- Follow: navigate to `x.com/PONDHandle` → click `[data-testid*="follow"]`
- Like: `[data-testid="like"]` on the tweet page
- RT: `[data-testid="retweet"]` → `[data-testid="retweetConfirm"]`
- Quote tweet (reliable method):
  1. Navigate to tweet URL
  2. Click `[data-testid="retweet"]` → select "Kutip" (or "Quote") from dropdown `[role="menuitem"]`
  3. Fill `[data-testid="tweetTextarea_0"]` with quote text
  4. Click `[data-testid="tweetButton"]` (not tweetButtonInline)
- **Alt quote method:** `https://x.com/intent/post?quote_tweet_id={ID}&text={URLENCODED_TEXT}`

### OAuth Device Flow (for sign-in-required forms)

When a form has `data-sign-in-to-continue="true"`, direct POST to `/formResponse` returns 401. **Don't give up** — use Google OAuth Device Flow instead:

1. **Check if sign-in is actually required**: `grep -c 'data-sign-in-to-continue' form.html` → 0 = no sign-in (simple POST works), 1+ = sign-in required
2. **Extract form structure** from `FB_PUBLIC_LOAD_DATA_` in page HTML (same as above)
3. **Run OAuth Device Flow** — user opens `google.com/device` on their phone, enters a code, approves. No browser automation needed:
   ```python
   import requests
   # Step 1: Get device code
   r = requests.post("https://oauth2.googleapis.com/device/code", data={
       "client_id": "<YOUR_CLIENT_ID>",
       "scope": "https://www.googleapis.com/auth/forms",
   })
   device_data = r.json()
   # Show user: verification_url + user_code
   # Step 2: Poll for token (user approves on phone)
   r = requests.post("https://oauth2.googleapis.com/token", data={
       "client_id": "<YOUR_CLIENT_ID>",
       "client_secret": "<YOUR_CLIENT_SECRET>",
       "device_code": device_code,
       "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
   })
   ```
4. **Submit via Forms API** with the access token:
   ```python
   headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
   body = {"responses": [{"questionId": "ENTRY_ID", "textAnswers": {"answers": [{"value": "answer"}]}}]}
   r = requests.post(f"https://forms.googleapis.com/v1/forms/{FORM_ID}/responses", headers=headers, json=body)
   ```

**Public client ID for testing:** `550517050959.apps.googleusercontent.com` (Google OAuth Playground client — works for device flow, but may be rate-limited)

**Alternative:** Direct POST to `/formResponse` with `Authorization: Bearer *** header also works when the API endpoint isn't available.

**Usage pattern:** Ask user to open `google.com/device` on their phone and enter the code. The clipboard is fine — just paste the short code.

### Available Scripts
- `custom_form_x_tasks_filler.py` — reusable template for custom web forms with embedded X task links + checkboxes (ette.world pattern). Edit the CONFIG section, then run directly.
- `custom_form_x_tasks_verify.py` — companion verification script. Run after the filler to confirm follow/like/RT were completed.

### No-sign-in forms (most common)

Many Google Forms do NOT require sign-in, even when the "Sign in to Google" link appears. Always check first:

```bash
curl -sL "https://docs.google.com/forms/d/e/{FORM_KEY}/viewform" | grep -c 'data-sign-in-to-continue'
```

When no sign-in required, submit directly:
```bash
curl -s -X POST "https://docs.google.com/forms/d/e/{FORM_KEY}/formResponse" \
  -d "entry.XXXXXXX=value" \
  -d "entry.XXXXXXX=value" \
  -d "fvv=1" -d "pageHistory=0" -d "submissionTimestamp=-1"
```
Note: `fbzx` is **optional** for forms without sign-in — the POST works without it.

### Extract form structure (full Python)

```python
import re, json, urllib.request

url = "https://docs.google.com/forms/d/e/{FORM_KEY}/viewform"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read().decode('utf-8', errors='replace')

match = re.search(r'FB_PUBLIC_LOAD_DATA_\s*=\s*(\[.*?\]);', html, re.DOTALL)
if match:
    data = json.loads(match.group(1))
    form_items = data[1][1]
    for item in form_items:
        entry_id = item[0]
        question_text = item[1] if isinstance(item[1], str) else (item[1][1])
        qtype = item[3]  # 0=text, 2=radio, 4=checkbox
        print(f"entry.{entry_id} | type={qtype} | {question_text}")
        if len(item) > 4 and isinstance(item[4], list):
            for opt in item[4]:
                print(f"   -> {opt[1]}")
```

### Pitfalls
- Google sign-in REQUIRED forms return 401 on direct POST — try OAuth Device Flow instead
- Browser-based Google login from data center IPs → "This browser or app may not be secure" regardless of stealth technique — skip browser-based login entirely in favor of OAuth Device Flow
- No-sign-in forms still accept POST without `fbzx` — don't waste time looking for it
- OAuth tokens expire in ~1 hour; refresh with `grant_type=refresh_token` if a refresh_token is returned
- The Forms API (`forms.responses.create`) requires the form to be owned/shared with the authenticated Google account — if API fails, fall back to direct POST with Bearer token
- Twitter cookie auth: set cookies on BOTH `.x.com` and `.twitter.com` domains
- After posting quote tweet, navigate to profile and scroll to find the new tweet link
- Indonesian locale: X menu shows "Kutip" (not "Quote"), "Posting" (not "Tweet")

