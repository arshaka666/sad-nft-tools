#!/usr/bin/env python3
"""
Fill a terminal-gate type WL (Ghost Root pattern).
Sequential prompts: type answer → Enter → next prompt.

Usage:
  python3 scripts/terminal_gate_filler.py --url https://www.example-project.xyz/ --answers '["user_name","user_handle","https://x.com/project/status/12345"]'
"""
import argparse, json, time
from playwright.sync_api import sync_playwright

def main():
    parser = argparse.ArgumentParser(description="Terminal gate WL filler")
    parser.add_argument("--url", required=True, help="URL of the terminal gate")
    parser.add_argument("--answers", required=True, help='JSON array of sequential answers e.g. ["name","handle","link"]')
    args = parser.parse_args()
    
    answers = json.loads(args.answers)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        
        page.goto(args.url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        
        for i, answer in enumerate(answers):
            # Wait for the text input to appear
            page.wait_for_selector('input[type="text"], [role="textbox"]', timeout=15000)
            page.wait_for_timeout(1000)
            
            # Type answer
            input_el = page.locator('input[type="text"], [role="textbox"]')
            input_el.fill(answer)
            page.wait_for_timeout(500)
            page.keyboard.press("Enter")
            
            print(f"✅ Step {i+1}: submitted '{answer[:20]}...'")
            page.wait_for_timeout(3000)
        
        # Read final body text
        body = page.inner_text("body")
        print(f"\n--- FINAL OUTPUT ---\n{body[:1000]}")
        browser.close()

if __name__ == "__main__":
    main()
