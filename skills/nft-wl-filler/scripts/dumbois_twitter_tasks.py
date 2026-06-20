#!/usr/bin/env python3
"""
Do Dumbois Twitter tasks for a given handle:
1. Follow @thedumbois
2. Like + RT their latest tweet (ID: 2062189467725598999)
3. Comment "I am Dumb" tagging 2 friends

Usage:
  python3 scripts/dumbois_twitter_tasks.py --tokens twitter_tokens.yaml --handle handle
"""
import yaml, argparse, sys, time
from playwright.sync_api import sync_playwright

# Dumbois tweet to interact with
TWEET_ID = "2062189467725598999"
TWEET_URL = f"https://x.com/thedumbois/status/{TWEET_ID}"

def login(context, tokens):
    """Set up X cookies on the context."""
    page = context.new_page()
    page.goto("https://x.com", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2000)
    context.add_cookies([
        {"name": "auth_token", "value": tokens['auth_token'], "domain": ".x.com", "path": "/"},
        {"name": "ct0", "value": tokens['ct0'], "domain": ".x.com", "path": "/"},
        {"name": "auth_token", "value": tokens['auth_token'], "domain": ".twitter.com", "path": "/"},
        {"name": "ct0", "value": tokens['ct0'], "domain": ".twitter.com", "path": "/"},
    ])
    return page

def do_follow(page, handle):
    """Follow @handle."""
    print(f"--- FOLLOW @{handle} ---")
    page.goto(f"https://x.com/{handle}", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2000)
    btn = page.locator('[data-testid*="follow" i]')
    if btn.count() > 0:
        btn.first.click()
        page.wait_for_timeout(2000)
        print(f"✅ Followed @{handle}")
    else:
        print(f"Already following @{handle} or not found")

def do_like_rt(page):
    """Like + RT the Dumbois tweet."""
    print("--- LIKE + RT ---")
    page.goto(TWEET_URL, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2000)
    
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

def do_comment(page, text):
    """Comment on the Dumbois tweet."""
    print("--- COMMENT ---")
    page.goto(TWEET_URL, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)
    
    reply = page.locator('[data-testid="reply"]')
    if reply.count() > 0:
        reply.first.click()
        page.wait_for_timeout(1500)
        
        textarea = page.locator('[data-testid="tweetTextarea_0"]')
        if textarea.count() > 0:
            textarea.first.fill(text)
            page.wait_for_timeout(1000)
            
            tweet_btn = page.locator('[data-testid="tweetButton"]')
            if tweet_btn.count() > 0:
                tweet_btn.first.click(force=True)
                page.wait_for_timeout(3000)
                print("✅ Commented")
            else:
                print("No tweet button found")
        else:
            print("No textarea found")
    else:
        print("No reply button found")

def main():
    parser = argparse.ArgumentParser(description="Dumbois Twitter tasks")
    parser.add_argument("--tokens", default="twitter_tokens.yaml", help="YAML file with auth_token and ct0")
    parser.add_argument("--comment", default="GM! @friend1 @friend2 #projectname", help="Comment text")
    args = parser.parse_args()
    
    with open(args.tokens) as f:
        tokens = yaml.safe_load(f)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = login(context, tokens)
        
        # Follow
        do_follow(page, "thedumbois")
        
        # Like + RT
        do_like_rt(page)
        
        # Comment
        do_comment(page, args.comment)
        
        browser.close()
        print("\n✅ All Dumbois Twitter tasks done!")

if __name__ == "__main__":
    main()
