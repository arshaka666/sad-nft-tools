#!/usr/bin/env python3
"""
Ghost Root (GSTR) Twitter tasks:
1. Go to @gosutoruts
2. Like + RT the pinned post
3. Return the RT link

Usage:
  python3 scripts/ghostroot_twitter_tasks.py --tokens twitter_tokens.yaml
  # Returns the RT link on stdout
"""
import yaml, argparse, sys
from playwright.sync_api import sync_playwright

def main():
    parser = argparse.ArgumentParser(description="Ghost Root Twitter tasks")
    parser.add_argument("--tokens", default="twitter_tokens.yaml")
    args = parser.parse_args()
    
    with open(args.tokens) as f:
        tokens = yaml.safe_load(f)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()
        
        # Login
        page.goto("https://x.com", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)
        context.add_cookies([
            {"name": "auth_token", "value": tokens['auth_token'], "domain": ".x.com", "path": "/"},
            {"name": "ct0", "value": tokens['ct0'], "domain": ".x.com", "path": "/"},
            {"name": "auth_token", "value": tokens['auth_token'], "domain": ".twitter.com", "path": "/"},
            {"name": "ct0", "value": tokens['ct0'], "domain": ".twitter.com", "path": "/"},
        ])
        
        # Go to @gosutoruts
        page.goto("https://x.com/gosutoruts", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        
        # Like the pinned post
        like = page.locator('[data-testid="like"]')
        if like.count() > 0:
            like.first.click()
            page.wait_for_timeout(1500)
            print("✅ Liked pinned post", file=sys.stderr)
        
        # Retweet
        rt = page.locator('[data-testid="retweet"]')
        if rt.count() > 0:
            rt.first.click()
            page.wait_for_timeout(1500)
            confirm = page.locator('[data-testid="retweetConfirm"]')
            if confirm.count() > 0:
                confirm.click()
                page.wait_for_timeout(2000)
                print("✅ Retweeted pinned post", file=sys.stderr)
        
        # Get tweet link
        tweet_links = page.locator('a[href*="/status/"]')
        tweet_url = ""
        for i in range(min(tweet_links.count(), 10)):
            href = tweet_links.nth(i).get_attribute("href")
            if href and "/status/" in href:
                tweet_url = "https://x.com" + href if href.startswith("/") else href
                break
        
        browser.close()
        
        if tweet_url:
            print(tweet_url)  # stdout = RT link for piping
        else:
            print("ERROR: Could not get tweet URL", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
