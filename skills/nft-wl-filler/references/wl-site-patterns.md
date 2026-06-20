# WL Site Pattern Reference

Session-specific details for whitelist sites encountered in practice.

## Dave Krugman — Windows by Dave Krugman

**URL:** `https://windows.davekrugman.com/`
**Pattern:** Standard Web Form (Type 1)
**Mint Day:** June 16, 2026

**Form fields:**
- `Your name` (required)
- `Your email` (required)
- `Wallet address`
- Checkboxes: WINDOWS, BUILDINGS, CITY (all optional but good to select all)

**Submit button:** `button:has-text("Submit interest")`

**Success response:** "Thanks — we'll be in touch." (page text updates, no redirect)

**Notes:** Checkboxes are React-controlled. Clicking them via browser tool may not toggle state — use JS `document.querySelectorAll('input[type="checkbox"]')` click dispatching instead.

---

## Ghost Root

**URL:** `https://www.ghost-root.xyz/`
**Pattern:** Terminal Gate (Type 2)
**Token:** GSTR // ETH

**Terminal prompts (in order):**
1. `NAME:` → user's real name (e.g. "johndoe")
2. `X HANDLE:` → Twitter handle (e.g. "user_handle" or "@user_handle")
3. `RT LINK:` → URL of retweet of @gosutoruts pinned post

**Pre-work required:**
- Go to `x.com/gosutoruts`
- Like + RT their pinned post
- Get the tweet URL (e.g. `https://x.com/gosutoruts/status/2061165062773956830`)
- Paste the RT link in the terminal

**Verification response:**
```
> SCANNING HANDLE @user_handle...
> CROSS-REFERENCING SIGNAL DATABASE...
> CHECKING TWEET INTEGRITY...
> VALIDATING PROOF OF LOYALTY...
> CRACKING ENCRYPTION LAYER 1....... DONE
> CRACKING ENCRYPTION LAYER 2....... DONE
> BYPASSING FIREWALL................. DONE
```

**Success text:** "SESSION RESTORED: {NAME} @{HANDLE}"
**Project info after success:** 2000 machine terminals, permanently on Ethereum, no public interface, signal drop TBA, monitor @gosutoruts

**Notes:** The input field is reused for each prompt. Type → Enter → wait for next prompt. No buttons to click — only text inputs and Enter key.

---

## Dumbois

**URL:** `https://www.dumbois.lol/apply`
**Pattern:** React App with Twitter Tasks (Type 3)

**Form fields:**
- X USERNAME (allegedly) — text input, no @ needed
- EVM WALLET — must start with 0x

**Three tasks (all client-side React state):**
1. `FOLLOW @thedumbois`
2. `LIKE + RT this tweet` (tweet ID: 2062189467725598999)
3. `COMMENT "I am Dumb" + TAG 2 FRIENDS`

**Button classes:**
- `task-check` — toggle done button (toggles React state: `followed`, `liked`, `commented`)
- `task-go` — opens Twitter intent in new tab + auto-sets state to true
- `apply-submit locked` — submit button, disabled until 100%

**Critical: Override window.open before clicking any task-go buttons:**
```javascript
window.open = function() { return null; };
```

**Progress calculation:**
- Form fields filled + toggle done = 40%
- Each task toggled = 20%
- Total = 100% → button changes to "SUBMIT MY DUMBNESS"

**Submit button text progression:**
- 0%: "not dumb yet. do something."
- 20%: "barely dumb. keep going."
- 40%: "getting dumber..."
- 60%: "pretty dumb honestly"
- 80%: "almost peak dumb"
- 100%: "PEAK DUMB — SUBMIT NOW" → button text becomes "SUBMIT MY DUMBNESS"

**Success response:**
```
APPLICATION RECEIVED
welcome to the napkin, @{handle}.
your wallet {wallet_short} is now officially Dumb.
```

**Twitter task details (from JS source):**
- Tweet ID for like+RT and comment: `2062189467725598999`
- COMMENT href: `https://x.com/intent/post?in_reply_to=2062189467725598999&text=I am Dumb @ @`

**Pitfalls:**
1. browser_click on task-check may not trigger React onClick. Use `.click()` via JS dispatch or `document.querySelectorAll('.task-check').forEach(b => b.click())`.
2. task-go buttons navigate the current page away via `window.open`. Override it or they'll redirect you to X/Twitter.
3. After successful submission, the page shows referral link. No further action needed.

---

## Ette Corporation

**URL:** `https://www.ette.world/`
**Pattern:** Custom Web Form with X Task Links + Checkboxes (Type 4)
**Mint Day:** Unknown (WL open)

**Form fields:**
- `Twitter` — text input (handle without @, e.g. "user_handle")
- `EVM Wallet Address` — text input (e.g. "0x1234...abcd")

**Three X task links (each with a checkbox):**
1. `Follow ETTE CORP.` → `https://x.com/ettecorp`
2. `Like & RT Post` → `https://x.com/ettecorp/status/{TWEET_ID}`
3. `Comment` → `https://x.com/ettecorp/status/{TWEET_ID}` (same tweet as Like&RT)

**X task tweet ID:** `2063600616941772850`

**Submit button:** `button:has-text("APPLY")`

**Verification selectors (Playwright):**
- Follow: `[data-testid*="follow"]` — check text !== "Follow"/"Ikuti" (should be "Mengikuti"/"Following")
- Like: `[data-testid="unlike"]` — presence means liked
- Retweet: `[data-testid="unretweet"]` — presence means retweeted
- Comment: After replying, verify via profile or screenshot

**Unified script approach (recommended workflow):**
1. Single Playwright script does: login X → follow → like+RT → comment → fill form → check all checkboxes → click APPLY
2. Separate verification script confirms: login X → check follow/like/RT statuses → screenshot
3. Comment content: keep it simple and organic (e.g. "gm @ettecorp 🔥")
4. X selectors are locale-dependent: Indonesian locale uses "Mengikuti", "Ikuti", "Kutip", "Posting"

**Success signal:** Form resets to initial state after submission (no success page/message — the blank form IS the success indicator).

**Pitfalls:**
- Checkboxes may be React-controlled. Verify they actually toggled after clicking. If browser_click fails, use JS dispatch: `document.querySelectorAll('input[type="checkbox"]').forEach(cb => { if(!cb.checked) cb.click(); })`
- After APPLY click, the page may just reload to initial state — this is normal and means success.
- The script must navigate to x.com first, set cookies on BOTH `.x.com` and `.twitter.com` domains, then navigate to target page.
