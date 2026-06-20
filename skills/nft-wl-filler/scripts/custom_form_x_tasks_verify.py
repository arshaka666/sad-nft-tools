#!/usr/bin/env python3
"""
Generic verification: Confirm X tasks are done after running the filler script.

Usage:
  Ensure /root/twitter_tokens.yaml exists, then edit CONFIG and run.
"""

# ========== CONFIG ==========
FOLLOW_ACCOUNT = "ettecorp"
TWEET_ID = "2063600616941772850"
# ========== END CONFIG ==========

import yaml, time
from playwright.sync_api import sync_playwright

with open('/root/twitter_tokens.yaml') as f:
    tokens = yaml.safe_load(f)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    context = browser.new_context(
        viewport={"width": 1280, "height": 900},
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    )
    page = context.new_page()
    
    page.goto("https://x.com", wait_until="domcontentloaded")
    time.sleep(3)
    for domain in [".x.com", ".twitter.com"]:
        context.add_cookies([
            {"name": "auth_token", "value": tokens['auth_token'], "domain": domain, "path": "/"},
            {"name": "ct0", "value": tokens['ct0'], "domain": domain, "path": "/"},
        ])
    
    page.goto(f"https://x.com/{FOLLOW_ACCOUNT}", wait_until="domcontentloaded")
    time.sleep(4)
    
    follow_btn = page.query_selector('[data-testid*="follow"]')
    if follow_btn:
        print(f"Follow: {'✅' if 'Follow' not in follow_btn.inner_text() else '❌'} ({follow_btn.inner_text()})")
    
    page.goto(f"https://x.com/{FOLLOW_ACCOUNT}/status/{TWEET_ID}", wait_until="domcontentloaded")
    time.sleep(4)
    
    like = page.query_selector('[data-testid="unlike"]')
    print(f"Liked: {'✅' if like else '❌'}")
    
    rt = page.query_selector('[data-testid="unretweet"]')
    print(f"Retweeted: {'✅' if rt else '❌'}")
    
    page.screenshot(path="/root/wl_verify.png")
    print("\nScreenshot saved to /root/wl_verify.png")
    browser.close()
