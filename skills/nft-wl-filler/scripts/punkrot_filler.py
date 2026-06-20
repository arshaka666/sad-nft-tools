from playwright.sync_api import sync_playwright
import json, time, sys, yaml, argparse

def punkrot_fill(wallet: str, twitter_handle: str, quote_url: str = "",
                 auth_token: str = "", ct0: str = "",
                 headless: bool = True) -> dict:
    """
    Fill PunkRot whitelist for one entry.
    
    Args:
        wallet: Ethereum wallet address (0x...)
        twitter_handle: X/Twitter username (without @)
        quote_url: Quote tweet URL (https://x.com/.../status/...)
        auth_token: X auth_token cookie (optional for step 2 tasks)
        ct0: X ct0 cookie (optional for step 2 tasks)
        headless: Run browser headless
        
    Returns:
        dict with 'success', 'error' keys
    """
    result = {"success": False, "error": "", "step": 0}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, args=['--no-sandbox'])
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        
        print(f"[WL] Opening PunkRot...", flush=True)
        page.goto("https://www.punkrot.art/", timeout=30000, wait_until="domcontentloaded")
        time.sleep(3)
        
        # Click GET WHITELIST
        wl_btn = page.query_selector('.terminal-trigger-btn')
        if not wl_btn:
            result["error"] = "GET WHITELIST button not found"
            browser.close()
            return result
        
        wl_btn.click()
        time.sleep(2)
        print(f"[WL] Button clicked, waiting for terminal form...", flush=True)
        
        # Wait for form inputs to appear (~13s animation delay)
        for attempt in range(25):
            time.sleep(1)
            inputs = page.query_selector_all('input')
            if len(inputs) >= 2:
                print(f"[WL] Form appeared after {attempt+1}s", flush=True)
                break
        
        inputs = page.query_selector_all('input')
        if len(inputs) < 2:
            result["error"] = "Form inputs never appeared"
            browser.close()
            return result
        
        # Step 1: Fill Twitter + Wallet
        inputs[0].fill(twitter_handle)
        time.sleep(0.3)
        inputs[1].fill(wallet)
        time.sleep(0.3)
        print(f"[WL] Step 1: {twitter_handle} / {wallet[:10]}...", flush=True)
        
        # Submit Step 1
        next_btn = page.query_selector('button.term-btn:has-text("NEXT")')
        if next_btn:
            next_btn.click()
            time.sleep(4)
        else:
            result["error"] = "EXECUTE: NEXT button not found"
            browser.close()
            return result
        
        result["step"] = 2
        
        # Step 2: Tasks + Quote URL
        task_btns = page.query_selector_all('.term-task-btn')
        for btn in task_btns:
            btn.click()
            time.sleep(0.5)
        print(f"[WL] Tasks clicked ({len(task_btns)}), filling quote URL...", flush=True)
        
        # Fill quote URL
        url_input = page.query_selector('input[placeholder*="x.com"]')
        if url_input and quote_url:
            url_input.fill(quote_url)
            time.sleep(0.3)
        
        # Submit Step 2
        upload_btn = page.query_selector('button.term-btn:has-text("UPLOAD")')
        if not upload_btn:
            upload_btn = page.query_selector('button:has-text("UPLOAD")')
        
        if upload_btn:
            if upload_btn.get_attribute('disabled'):
                error_el = page.query_selector('.term-error')
                result["error"] = f"Upload button disabled: {error_el.inner_text()[:100] if error_el else 'unknown'}"
            else:
                upload_btn.click()
                time.sleep(10)
                result["step"] = 3
                
                # Check result
                success_el = page.query_selector('.term-success')
                if success_el:
                    result["success"] = True
                    result["message"] = success_el.inner_text()[:200]
                else:
                    error_el = page.query_selector('.term-error')
                    if error_el:
                        result["error"] = error_el.inner_text()[:200]
                    else:
                        result["error"] = "No success or error message found"
        else:
            result["error"] = "EXECUTE: UPLOAD button not found"
        
        browser.close()
    
    return result


def x_quote_tweet(tweet_id: str, text: str = "gm",
                  auth_token: str = "", ct0: str = "",
                  headless: bool = True) -> str:
    """
    Quote a tweet using X compose/post endpoint.
    Returns the quote tweet URL.
    """
    from urllib.parse import quote
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, args=['--no-sandbox'])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            viewport={"width": 1280, "height": 900},
            locale="en-US"
        )
        page = context.new_page()
        
        # Set cookies
        page.goto("https://x.com", timeout=15000, wait_until="domcontentloaded")
        time.sleep(1)
        context.add_cookies([
            {"name": "auth_token", "value": auth_token, "domain": ".x.com", "path": "/"},
            {"name": "ct0", "value": ct0, "domain": ".x.com", "path": "/"},
        ])
        
        # Use compose/post with quote_tweet_id param (more reliable than menu)
        encoded_text = quote(text)
        compose_url = f"https://x.com/compose/post?quote_tweet_id={tweet_id}&text={encoded_text}"
        page.goto(compose_url, timeout=30000, wait_until="domcontentloaded")
        time.sleep(6)
        
        # Click the post button
        post_btn = page.wait_for_selector('[data-testid="tweetButton"]', timeout=10000)
        if post_btn and not post_btn.get_attribute('disabled'):
            post_btn.click()
            time.sleep(5)
        
        # Get quote tweet URL from profile
        page.goto("https://x.com/home", timeout=30000, wait_until="domcontentloaded")
        time.sleep(4)
        
        # Find the most recent tweet (usually first)
        tweets = page.query_selector_all('[data-testid="tweet"]')
        if tweets:
            link_el = tweets[0].query_selector('a[href*="/status/"]')
            if link_el:
                href = link_el.get_attribute('href')
                if href:
                    browser.close()
                    return f"https://x.com{href}"
        
        browser.close()
        return ""


def x_follow(target: str, auth_token: str = "", ct0: str = "",
             headless: bool = True) -> bool:
    """Follow an X account using cookie auth."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, args=['--no-sandbox'])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            viewport={"width": 1280, "height": 900}
        )
        page = context.new_page()
        
        page.goto("https://x.com", timeout=15000, wait_until="domcontentloaded")
        time.sleep(1)
        context.add_cookies([
            {"name": "auth_token", "value": auth_token, "domain": ".x.com", "path": "/"},
            {"name": "ct0", "value": ct0, "domain": ".x.com", "path": "/"},
        ])
        
        page.goto(f"https://x.com/{target.replace('@', '')}", timeout=30000, wait_until="domcontentloaded")
        time.sleep(5)
        
        follow_btn = page.query_selector('[data-testid*="follow" i]')
        if follow_btn:
            follow_btn.click()
            time.sleep(2)
            browser.close()
            return True
        
        browser.close()
        return False  # Already following or not found


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PunkRot WL Filler")
    parser.add_argument("--wallet", required=True, help="Wallet address")
    parser.add_argument("--twitter", required=True, help="Twitter handle")
    parser.add_argument("--quote-url", help="Quote tweet URL")
    parser.add_argument("--cookies", help="Twitter cookies YAML file")
    parser.add_argument("--visible", action="store_true", help="Show browser")
    args = parser.parse_args()
    
    auth_token = ct0 = ""
    if args.cookies:
        with open(args.cookies) as f:
            tokens = yaml.safe_load(f)
            auth_token = tokens.get('auth_token', '')
            ct0 = tokens.get('ct0', '')
    
    # If no quote URL but we have cookies, try to quote a tweet
    if not args.quote_url and auth_token and ct0:
        punkrot_tweet = "2062133210167779535"  # PunkRot's announcement tweet
        print(f"[X] Quoting tweet {punkrot_tweet}...", flush=True)
        args.quote_url = x_quote_tweet(
            punkrot_tweet, "gm. secured the bag",
            auth_token, ct0, headless=not args.visible
        )
        if args.quote_url:
            print(f"[X] Quote URL: {args.quote_url}", flush=True)
    
    result = punkrot_fill(
        args.wallet, args.twitter, args.quote_url or "",
        auth_token, ct0, headless=not args.visible
    )
    
    if result["success"]:
        print(f"\n✅ WL FILLED for @{args.twitter}")
        if result.get("message"):
            print(f"   {result['message']}")
    else:
        print(f"\n❌ FAILED for @{args.twitter}: {result['error']}")
