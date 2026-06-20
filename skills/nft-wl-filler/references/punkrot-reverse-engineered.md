# PunkRot WL Form — Reverse-Engineered (June 2026)

Source: Next.js chunk `2qjvrly2lxmzt.js` — the whitelist terminal component.

## State Shape

```js
const [step, setStep] = useState(1)                // 1, 2, or 3
const [formData, setFormData] = useState({
  twitterUsername: "",
  walletAddress: "",
  quoteTweetLink: ""
})
const [tasks, setTasks] = useState({
  followed: false,   // Step 2 — click follow button
  quoted: false      // Step 2 — click quote button
})
const [loading, setLoading] = useState(false)
const [error, setError] = useState("")
const [success, setSuccess] = useState(null)
const [logs, setLogs] = useState([])
```

## Rendering Structure

```
section#whitelist.terminal-section
  ├── (noise overlay component)
  ├── .terminal-trigger-wrapper           // when !open
  │   └── button.terminal-trigger-btn     // "GET WHITELIST"
  └── .terminal-container.glitch-in       // when open
      ├── .terminal-header
      │   ├── .term-dots (3 spans)
      │   └── .term-title "PR_WL_CLIENT_v2.0"
      ├── .terminal-body
      │   ├── .terminal-logs              // scrolling log lines
      │   │   ├── .term-log.glitch-in     // current typing line with cursor
      │   │   └── .term-log.type-in       // historical lines (mapped array)
      │   ├── .term-error.type-in         // error message (conditional)
      │   └── (scroll ref div)
      └── .terminal-input-area.fade-in (when !typing)
          ├── Step 1 (step===1)
          │   └── form.term-form
          │       ├── .term-group: label "Twitter Username:" → input[placeholder=username]
          │       ├── .term-group: label "Wallet Address:" → input[placeholder="0x..."]
          │       └── button.term-btn "[ EXECUTE: NEXT ]"
          ├── Step 2 (step===2)
          │   └── form.term-form
          │       ├── .term-tasks
          │       │   ├── button.term-task-btn (onClick: window.open + set followed=true)
          │       │   │   "[ ] FOLLOW @PunkRot"
          │       │   └── button.term-task-btn (onClick: set quoted=true)
          │       │       "[ ] QUOTE TARGET TWEET"
          │       ├── .term-group: label "Quote Tweet URL:" → input[placeholder="https://x.com/..."]
          │       └── .term-actions
          │           ├── button.term-btn.term-back "[BACK]"
          │           └── button.term-btn (disabled: !followed||!quoted)
          │               "[ EXECUTE: UPLOAD ]"
          └── Step 3 (step===3)
              └── .term-success
                  ├── .term-success-icon "ACCESS GRANTED"
                  └── .term-success-text "YOU HAVE SURVIVED THE ROT."

## Validation Rules

**Step 1 → Step 2:**
- `twitterUsername.trim()` must be truthy
- `walletAddress.trim()` must be ≥ 20 chars
- Error shown: `"ERR: INVALID WALLET ADDRESS"` if validation fails

**Step 2 → Submit:**
- `tasks.followed` AND `tasks.quoted` must both be true
- `quoteTweetLink` must match regex: `/^https?:\/\/(twitter\.com|x\.com)\/.+\/status\/\d+/i`
- Error shown: `"ERR: TASKS INCOMPLETE"` or `"ERR: INVALID X URL"`

## Network Calls

### POST `/api/whitelist`
```json
{
  "twitterUsername": "string",
  "walletAddress": "0x...",
  "quoteTweetLink": "https://x.com/.../status/..."
}
```
Success: `{ data: { id: "..." } }` — shows last 8 chars uppercased as clearance ID
Failure: `{ error: "..." }` — shown in `.term-error`

### POST `/api/log` (fire-and-forget, catches errors silently)
```json
{ "event": "STEP_1_COMPLETE|SUBMITTING|SUBMIT_ERROR|SUBMIT_SUCCESS|NETWORK_ERROR", "data": {...} }
```

## Initial Boot Logs
1. `> PASSING SECURITY PROTOCOLS... [OK]`
2. `> DECRYPTING FILESYSTEM...`
3. `> CONNECTING TO PUNKROT MAINFRAME... [CONNECTED]`
4. `> 222 SPOTS REMAINING.`
5. `> AWAITING USER INPUT...`

## Key Selectors for Playwright
| Element | Selector |
|---|---|
| Trigger button | `.terminal-trigger-btn` or `text=GET WHITELIST` |
| Step 1 form | `.terminal-form` (waits after clicking trigger) |
| Twitter input | `input[placeholder="username"]` |
| Wallet input | `input[placeholder="0x..."]` |
| Execute Next | `.term-btn:has-text("EXECUTE: NEXT")` |
| Follow task | `.term-task-btn:has-text("FOLLOW")` |
| Quote task | `.term-task-btn:has-text("QUOTE")` |
| Quote URL input | `input[placeholder="https://x.com/..."]` |
| Upload button | `.term-btn:has-text("EXECUTE: UPLOAD")` |
| Back button | `.term-btn.term-back` |
| Success | `.term-success` |
| Error | `.term-error` |
