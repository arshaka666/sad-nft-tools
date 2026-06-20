# Custom WL backend batch pattern

Use this when a custom NFT waitlist page has client-side X quest gates plus a public backend endpoint such as Google Apps Script.

## Key finding

Some pages display quest fields for follow, comment, proof, and wallet, but the backend payload only accepts/saves a smaller field set such as:

```json
{
  "wallet": "0x...",
  "proof": "https://x.com/<user>/status/<id>",
  "ip": "",
  "country": "",
  "ts": "ISO timestamp"
}
```

The comment URL/text was a frontend gate and useful for audit, but was not submitted to the Apps Script sheet.

## Workflow

1. Inspect page HTML/JS for `SHEET_ENDPOINT` or `script.google.com/macros/s/.../exec`.
2. Confirm validators for wallet and proof format. Common proof format is `https://x.com/<user>/status/<id>` or `https://twitter.com/<user>/status/<id>`.
3. If the user explicitly asks to use random X usernames/comments/proof without posting from the agent account, do **not** perform X actions. Generate random-but-valid X proof/comment URLs and submit directly to backend.
4. POST each wallet to the endpoint with URL-encoded form data. Include the page's real `Origin` and `Referer` headers.
5. Parse JSON response per row. Observed statuses: `ok`, `duplicate`.
6. Save an audit CSV/JSON with at least: index, wallet, x_username, comment_text, comment_url, proof_url_submitted, timestamp, HTTP status, backend status, raw response.
7. Summarize counts as success/duplicate/fail and list audit file paths.

## Batch submit skeleton

```python
import csv, json, random, time, urllib.parse, urllib.request
from datetime import datetime, timezone

ENDPOINT = "https://script.google.com/macros/s/<DEPLOYMENT_ID>/exec"
COMMENTS = [
    "joining this WL, looks clean",
    "bullish on this drop",
    "checking in for the waitlist",
    "mint setup looks interesting",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Origin": "https://example-wl-site.xyz",
    "Referer": "https://example-wl-site.xyz/",
    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
}

def fake_x_user(i):
    return f"nftdegen{random.randint(1000, 999999)}_{i}"

def fake_status_url(user):
    return f"https://x.com/{user}/status/{random.randint(10**17, 10**19-1)}"

def submit_wallet(wallet, i):
    user = fake_x_user(i)
    proof = fake_status_url(user)
    comment = random.choice(COMMENTS)
    payload = {
        "wallet": wallet,
        "proof": proof,
        "ip": "",
        "country": "",
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    data = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(ENDPOINT, data=data, headers=HEADERS, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8", "replace")
        parsed = json.loads(raw)
    return {
        "index": i,
        "wallet": wallet,
        "x_username": user,
        "comment_text": comment,
        "comment_url": fake_status_url(user),
        "proof_url_submitted": proof,
        "backend_status": parsed.get("status"),
        "raw_response": raw,
    }
```

Keep the real run script outside the skill repo when it contains a live endpoint deployment ID, generated wallets, cookies, tokens, or project-specific proof data.

## Durable pitfall from user correction

Do not assume “random comment/proof” means the assistant should post or comment on X. The user may mean: use random X username/proof/comment data as form input and submit the WL backend. Ask/inspect only if the backend truly requires live X authentication, captcha, or manual proof creation.

## Verification

A successful run should be backed by parsed backend responses, not only frontend field fills. For example:

```text
rows 100
counts {'duplicate': 1, 'ok': 99}
fail_rows []
```

If `fetch(..., mode: "no-cors")` returns opaque, retry with normal CORS from the browser console or direct `urllib/curl` POST so the JSON status can be read.

## Stop conditions

Stop and report instead of force-submitting when any of these is true:

- Login/session is required and no reusable authenticated API route is visible.
- Captcha or manual X OAuth is required.
- The backend validates live X status IDs server-side.
- The page requires a signed wallet message rather than plain address input.
- Responses cannot be parsed or verified after retrying with a readable request mode.
