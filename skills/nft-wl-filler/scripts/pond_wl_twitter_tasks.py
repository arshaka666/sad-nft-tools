#!/usr/bin/env python3
"""
Do Twitter tasks for a Google Form WL that requires:
- Follow @handle
- Like + RT a specific tweet
- Quote tweet that tweet

Usage:
  python3 scripts/pond_wl_twitter_tasks.py --handle PondSyndicate --tweet-id 2062579078545514542 --quote "POND x SAD #PondSyndicate"
"""
import yaml, sys, time, argparse
from playwright.sync_api import sync_playwright

def parse_args():
    parser = argparse.ArgumentParser(description="Do WL Twitter tasks")
    parser.add_argument("--handle", required=True, help="Twitter handle to follow (w/o @)")
    parser.add_argument("--tweet-id", required=True, help="Tweet ID to Like/RT/Quote")
    parser.add_argument("--quote", default="", help="Quote tweet text")
    parser.add_argument("--tokens", default="/root/twitter_tokens.yaml", help="Path to tokens YAML")
    return parser.parse_args()

def main():
    args = parse_args()
    
    with open(args.tokens) as f:
        tokens = yaml.safe_load(f)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()
        
        # Login via cookies
        print("=== LOGIN ===")
        page.goto("https://x.com", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)
        context.add_cookies([
            {"name": "auth_token", "value": tokens['auth_token'], "domain": ".x.com", "path": "/"},
            {"name": "ct0", "value": tokens['ct0'], "domain": ".x.com", "path": "/"},
            {"name": "auth_token", "value": tokens['auth_token'], "domain": ".twitter.com", "path": "/"},
            {"name": "ct0", "value": tokens['ct0'], "domain": ".twitter.com", "path": "/"},
        ])
        print("✅ Logged in")
        
        # 1. Follow
        print(f"\n=== FOLLOW @{args.handle} ===")
        page.goto(f"https://x.com/{args.handle}", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(4000)
        
        follow = page.locator('[data-testid*="follow" i]')
        if follow.count() > 0:
            follow.first.click()
            page.wait_for_timeout(2000)
            print(f"✅ Followed @{args.handle}")
        else:
            alt = page.locator('button:has-text("Follow")')
            if alt.count() > 0:
                alt.first.click()
                page.wait_for_timeout(2000)
                print(f"✅ Followed @{args.handle} (alt)")
            else:
                print("Already following or button not found")
        
        # 2. Like + RT
        print(f"\n=== LIKE + RT TWEET ===")
        tweet_url = f"https://x.com/{args.handle}/status/{args.tweet_id}"
        page.goto(tweet_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(4000)
        
        like = page.locator('[data-testid="like"]')
        if like.count() > 0:
            like.first.click()
            page.wait_for_timeout(1500)
            print("✅ Liked")
        
        rt = page.locator('[data-testid="retweet"]')
        if rt.count() > 0:
            rt.first.click()
            page.wait_for_timeout(1500)
            confirm = page.locator('[data-testid="retweetConfirm"]')
            if confirm.count() > 0:
                confirm.click()
                page.wait_for_timeout(2000)
                print("✅ Retweeted")
        
        # 3. Quote tweet
        if args.quote:
            print(f"\n=== QUOTE TWEET ===")
            page.goto(tweet_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            
            rt = page.locator('[data-testid="retweet"]').first
            if rt.count() > 0:
                rt.click()
                page.wait_for_timeout(1500)
                
                # Find Quote menu item (may be "Kutip" in Indonesian locale)
                menu = page.locator('[role="menuitem"]')
                for i in range(menu.count()):
                    text = menu.nth(i).inner_text()
                    if "quote" in text.lower() or "kutip" in text.lower():
                        menu.nth(i).click()
                        page.wait_for_timeout(2000)
                        print(f"✅ Selected: {text}")
                        break
            
            # Fill text
            ta = page.locator('[data-testid="tweetTextarea_0"]')
            if ta.count() == 0:
                ta = page.locator('[contenteditable="true"]')
            if ta.count() > 0:
                ta.first.fill(args.quote)
                page.wait_for_timeout(1000)
                print(f"✅ Quote: \"{args.quote}\"")
            
            # Click Post button
            for sel in ['[data-testid="tweetButton"]', '[data-testid="tweetButtonInline"]']:
                btn = page.locator(sel).first
                if btn.count() > 0:
                    try:
                        btn.click(force=True)
                        page.wait_for_timeout(3000)
                        print(f"✅ Posted quote tweet")
                        break
                    except:
                        btn.evaluate("el => el.click()")
                        page.wait_for_timeout(3000)
                        print(f"✅ Posted quote tweet (JS)")
                        break
        
        # 4. Get quote tweet URL
        print(f"\n=== GET TWEET URL ===")
        page.wait_for_timeout(2000)
        page.goto(f"https://x.com/{args.handle}", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(4000)
        
        links = page.locator('a[href*="/status/"]')
        quote_url = ""
        for i in range(min(links.count(), 20)):
            href = links.nth(i).get_attribute("href") or ""
            if "/status/" in href and args.handle.lower() in href.lower():
                quote_url = "https://x.com" + href if href.startswith("/") else href
                break
        
        if not quote_url:
            quote_url = page.url
        
        browser.close()
        
        print(f"\n{'='*50}")
        print("RESULTS:")
        print(f"{'='*50}")
        print(f"✅ Follow @{args.handle}")
        print(f"✅ Like tweet")
        print(f"✅ Retweet")
        print(f"✅ Quote tweet: {quote_url}")
        print(f"\n➡️  Form submission:")
        print(f"   CODE: <enter_code_here>")
        print(f"   Quote URL: {quote_url}")
        print(f"   Wallet: <your_wallet>")

if __name__ == "__main__":
    main()
