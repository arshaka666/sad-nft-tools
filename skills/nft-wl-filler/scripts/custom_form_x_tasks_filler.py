#!/usr/bin/env python3
"""
Generic template: Fill a custom web form that requires X/Twitter tasks
(follow, like+RT, comment) with checkboxes.

Usage:
  1. Edit the CONFIG section below with your site's details
  2. Ensure /root/twitter_tokens.yaml exists with auth_token + ct0
  3. python3 custom_form_x_tasks_filler.py
  4. python3 custom_form_x_tasks_verify.py (separate verification step)
"""

# ========== CONFIG — EDIT THESE ==========
SITE_URL = "https://www.ette.world/"
FOLLOW_ACCOUNT = "ettecorp"
TWEET_ID = "2063600616941772850"  # tweet to like+RT+comment
TWITTER_HANDLE = "your_handle"  # REPLACE — handle WITHOUT @
WALLET = "0x1234...5678"  # REPLACE WITH YOUR WALLET
COMMENT_TEXT = "gm @ettecorp 🔥"

# Form selectors — adjust per site
TWITTER_INPUT_SELECTOR = 'input[placeholder*="Twitter" i], input[aria-label*="Twitter" i]'
WALLET_INPUT_SELECTOR = 'input[placeholder*="Wallet" i], input[aria-label*="Wallet" i]'
SUBMIT_BUTTON_SELECTOR = 'button:has-text("APPLY"), button:has-text("Submit"), input[type="submit"]'
# ========== END CONFIG ==========

import yaml, sys, time
from playwright.sync_api import sync_playwright

with open('/root/twitter_tokens.yaml') as f:
    tokens = yaml.safe_load(f)

auth_token = tokens['auth_token']
ct0 = tokens['ct0']

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    context = browser.new_context(
        viewport={"width": 1280, "height": 900},
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )
    page = context.new_page()

    # ========== LOGIN TO X ==========
    print("=== LOGIN ===")
    page.goto("https://x.com", wait_until="domcontentloaded")
    time.sleep(3)
    for domain in [".x.com", ".twitter.com"]:
        context.add_cookies([
            {"name": "auth_token", "value": auth_token, "domain": domain, "path": "/"},
            {"name": "ct0", "value": ct0, "domain": domain, "path": "/"},
        ])
    page.goto("https://x.com/home", wait_until="domcontentloaded")
    time.sleep(4)
    if "login" in page.url:
        print("❌ Login failed!"); browser.close(); sys.exit(1)
    print("✅ Logged in")

    # ========== FOLLOW ==========
    print(f"\n=== FOLLOW @{FOLLOW_ACCOUNT} ===")
    page.goto(f"https://x.com/{FOLLOW_ACCOUNT}", wait_until="domcontentloaded")
    time.sleep(4)
    follow_btn = page.query_selector('[data-testid*="follow"]')
    if follow_btn:
        if "Following" not in follow_btn.inner_text() and "Mengikuti" not in follow_btn.inner_text():
            follow_btn.click(); time.sleep(2); print("✅ Followed")
        else:
            print("✅ Already following")
    else:
        print("⚠️ Follow button not found")

    # ========== LIKE + RT ==========
    print("\n=== LIKE + RT ===")
    page.goto(f"https://x.com/{FOLLOW_ACCOUNT}/status/{TWEET_ID}", wait_until="domcontentloaded")
    time.sleep(5)
    
    like_btn = page.query_selector('[data-testid="like"]')
    if like_btn:
        like_btn.click(); time.sleep(2); print("✅ Liked")
    else:
        print("✅ Already liked" if page.query_selector('[data-testid="unlike"]') else "⚠️ Like btn missing")
    
    retweet_btn = page.query_selector('[data-testid="retweet"]')
    if retweet_btn:
        retweet_btn.click(); time.sleep(2)
        rt_confirm = page.query_selector('[data-testid="retweetConfirm"]')
        if rt_confirm:
            rt_confirm.click(); time.sleep(2); print("✅ Retweeted")
        else:
            print("⚠️ RT confirm missing")
    
    # ========== COMMENT ==========
    print("\n=== COMMENT ===")
    page.goto(f"https://x.com/{FOLLOW_ACCOUNT}/status/{TWEET_ID}", wait_until="domcontentloaded")
    time.sleep(5)
    reply_btn = page.query_selector('[data-testid="reply"]')
    if reply_btn:
        reply_btn.click(); time.sleep(2)
        textarea = page.query_selector('[data-testid="tweetTextarea_0"]')
        if textarea:
            textarea.fill(COMMENT_TEXT); time.sleep(1)
            reply_submit = page.query_selector('[data-testid="tweetButton"]')
            if reply_submit:
                reply_submit.click(); time.sleep(3)
                print(f"✅ Commented: '{COMMENT_TEXT}'")
            else:
                print("⚠️ Reply submit btn missing")
        else:
            print("⚠️ Textarea missing")
    
    # ========== FILL FORM ==========
    print("\n=== FILL FORM ===")
    page.goto(SITE_URL, wait_until="domcontentloaded")
    time.sleep(4)
    
    # Fill Twitter handle
    inp = page.query_selector(TWITTER_INPUT_SELECTOR)
    if inp:
        inp.fill(TWITTER_HANDLE); print(f"✅ Filled Twitter: @{TWITTER_HANDLE}")
    else:
        alt = page.query_selector_all('input[type="text"]')
        if alt: alt[0].fill(TWITTER_HANDLE); print("✅ Filled Twitter (alt)")
    
    # Fill wallet
    inp = page.query_selector(WALLET_INPUT_SELECTOR)
    if inp:
        inp.fill(WALLET); print(f"✅ Filled Wallet: {WALLET[:10]}...{WALLET[-4:]}")
    else:
        alt = page.query_selector_all('input[type="text"]')
        if len(alt) > 1: alt[1].fill(WALLET); print("✅ Filled Wallet (alt)")
    
    time.sleep(2)
    
    # Check all checkboxes
    checks = page.query_selector_all('input[type="checkbox"]')
    for cb in checks:
        if not cb.is_checked():
            try:
                cb.click(); time.sleep(0.5)
                print("✅ Checked a checkbox")
            except:
                pass
    
    time.sleep(1)
    
    # Submit
    btn = page.query_selector(SUBMIT_BUTTON_SELECTOR)
    if btn:
        btn.click(); time.sleep(3); print("✅ Form submitted!")
    else:
        print("⚠️ Submit button not found")
        for b in page.query_selector_all('button'):
            t = b.inner_text().strip()
            if t: print(f"  Button: '{t}'")
    
    page.screenshot(path="/root/wl_result.png")
    print(f"Final URL: {page.url}")
    browser.close()
    print("\n✅ ALL DONE!")
