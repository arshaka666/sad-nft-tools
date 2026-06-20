#!/usr/bin/env python3
"""
Google Form OAuth Device Flow Submitter.

For forms that REQUIRE Google sign-in (data-sign-in-to-continue="true").
User just visits google.com/device on their phone and enters a code.

Usage:
    python3 google_form_device_flow.py FORM_KEY [wallets.csv]

Args:
    FORM_KEY: The form ID from the URL (e.g., 1FAIpQLS...)
    wallets.csv: Optional path to CSV with twitter,wallet columns
"""
import csv, json, os, sys, time, requests
from pathlib import Path

SCOPE = "https://www.googleapis.com/auth/forms"

# Public OAuth client for testing — swap with your own for production
CLIENT_ID = "550517050959.apps.googleusercontent.com"
CLIENT_SECRET = ""
TOKEN_DIR = Path.home() / ".google_forms_tokens"

def get_form_structure(form_key):
    """Extract form fields from FB_PUBLIC_LOAD_DATA_"""
    import re
    url = f"https://docs.google.com/forms/d/e/{form_key}/viewform"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    html = r.text
    
    # Check sign-in requirement
    sign_in = 'data-sign-in-to-continue' in html
    print(f"Sign-in required: {'YES' if sign_in else 'NO'}")
    
    match = re.search(r'FB_PUBLIC_LOAD_DATA_\s*=\s*(\[.*?\]);', html, re.DOTALL)
    if not match:
        print("❌ Could not find form structure in HTML")
        return None
    
    import json
    data = json.loads(match.group(1))
    form_items = data[1][1]
    
    fields = []
    radio_options = {}
    for item in form_items:
        entry_id = str(item[0])
        question = item[1] if isinstance(item[1], str) else item[1][1]
        qtype = item[3]  # 0=text, 2=radio, 4=checkbox
        opts = []
        if len(item) > 4 and isinstance(item[4], list):
            opts = [o[1] for o in item[4] if isinstance(o, list) and len(o) > 1]
        fields.append({"entry": entry_id, "question": question, "type": qtype, "options": opts})
        if qtype == 2:
            radio_options[entry_id] = opts
    
    print(f"\nForm has {len(fields)} fields (sign-in={'required' if sign_in else 'optional'}):")
    for f in fields:
        opt_str = f" | options: {', '.join(f['options'])}" if f['options'] else ""
        print(f"  entry.{f['entry']} | {f['question']}{opt_str}")
    
    return {"sign_in": sign_in, "fields": fields, "radio_options": radio_options}


def get_oauth_token(form_key):
    """Run OAuth2 Device Flow — user approves on phone."""
    token_file = TOKEN_DIR / f"{form_key}.json"
    
    # Check existing token
    if token_file.exists():
        with open(token_file) as f:
            token_data = json.load(f)
        
        if token_data.get("expires_at", 0) > time.time():
            print("✅ Existing token still valid")
            return token_data["access_token"]
        
        # Try refresh
        if "refresh_token" in token_data:
            print("Refreshing token...")
            r = requests.post("https://oauth2.googleapis.com/token", data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "refresh_token": token_data["refresh_token"],
                "grant_type": "refresh_token",
            })
            if r.status_code == 200:
                new_data = r.json()
                new_data["expires_at"] = time.time() + new_data.get("expires_in", 3600)
                if "refresh_token" not in new_data:
                    new_data["refresh_token"] = token_data["refresh_token"]
                token_data.update(new_data)
                with open(token_file, 'w') as f:
                    json.dump(token_data, f)
                return new_data["access_token"]
            else:
                print("Token expired, re-authorizing...")
    
    # Device flow
    TOKEN_DIR.mkdir(parents=True, exist_ok=True)
    
    r = requests.post("https://oauth2.googleapis.com/device/code", data={
        "client_id": CLIENT_ID,
        "scope": SCOPE,
    })
    device_data = r.json()
    
    print(f"\n📱 Open {device_data['verification_url']} on your phone")
    print(f"🔑 Enter code: {device_data['user_code']}")
    print("Waiting up to 120 seconds...")
    
    for _ in range(24):
        time.sleep(device_data.get("interval", 5))
        
        r = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "device_code": device_data["device_code"],
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        })
        token_data = r.json()
        
        if "access_token" in token_data:
            token_data["expires_at"] = time.time() + token_data.get("expires_in", 3600)
            with open(token_file, 'w') as f:
                json.dump(token_data, f)
            print("✅ Authorized!")
            return token_data["access_token"]
        
        err = token_data.get("error")
        if err == "authorization_pending":
            continue
        elif err == "slow_down":
            time.sleep(5)
        elif err in ("access_denied", "expired_token"):
            print(f"❌ {err}")
            return None
    
    print("❌ Timed out")
    return None


def submit_form(form_key, access_token, entries, fields, radio_options):
    """Submit form responses using OAuth token."""
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    
    for entry in entries:
        twitter = entry.get("twitter", "").replace("@", "")
        wallet = entry.get("wallet", "")
        
        print(f"\n--- {twitter or 'anonymous'} | {wallet[:10]}... ---")
        
        # Build response from fields
        responses = []
        for f in fields:
            value = ""
            q = f["question"].lower()
            
            if "x" in q and ("account" in q or "link" in q or "twitter" in q):
                value = f"https://x.com/{twitter}"
            elif "wallet" in q or "eth" in q or "address" in q:
                value = wallet
            elif "hear" in q or "found" in q:
                value = "Twitter / X"
            elif "draw" in q or "attract" in q or "interest" in q:
                value = "Interesting artwork and unique concept"
            elif "enough" in q and "eth" in q:
                value = "Yes"
            else:
                value = input(f"  Answer for '{f['question']}': ")
            
            responses.append({
                "questionId": f["entry"],
                "textAnswers": {"answers": [{"value": value}]}
            })
        
        # Try Forms API first
        body = {"responses": responses}
        r = requests.post(
            f"https://forms.googleapis.com/v1/forms/{form_key}/responses",
            headers=headers, json=body
        )
        
        if r.status_code == 200:
            print(f"  ✅ Forms API: {r.status_code}")
            continue
        
        # Fallback: direct POST with Bearer token
        print(f"  Forms API: {r.status_code} — trying direct POST...")
        
        form_url = f"https://docs.google.com/forms/d/e/{form_key}/formResponse"
        data = {"fvv": "1", "pageHistory": "0", "submissionTimestamp": "-1"}
        for f in fields:
            data[f"entry.{f['entry']}"] = next(
                (resp["textAnswers"]["answers"][0]["value"] for resp in responses if resp["questionId"] == f["entry"]),
                ""
            )
        
        r2 = requests.post(form_url, headers=headers, data=data)
        if r2.status_code == 200:
            print(f"  ✅ Direct POST: {r2.status_code}")
        else:
            print(f"  ❌ Failed: {r2.status_code} - {r2.text[:80]}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nExample: python3 google_form_device_flow.py 1FAIpQLSdwvzH8b...")
        sys.exit(1)
    
    form_key = sys.argv[1]
    wallet_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"Form: {form_key}")
    
    # Step 1: Get form structure
    result = get_form_structure(form_key)
    if not result:
        sys.exit(1)
    
    fields = result["fields"]
    radio_options = result["radio_options"]
    
    # Step 2: Read wallet data
    entries = []
    if wallet_file and os.path.exists(wallet_file):
        with open(wallet_file) as f:
            entries = list(csv.DictReader(f))
        print(f"\nEntries: {len(entries)}")
        for e in entries:
            print(f"  • {e.get('twitter', '?')} | {e.get('wallet', '?')[:10]}...")
    
    # Step 3: Get token (if sign-in required)
    if result["sign_in"]:
        if not entries:
            print("\nNo entries to submit, just showing form structure.")
            return
        
        token = get_oauth_token(form_key)
        if not token:
            print("❌ No auth token — cannot submit sign-in-required form")
            sys.exit(1)
        
        submit_form(form_key, token, entries, fields, radio_options)
    else:
        print(f"\n⚠️  Form does NOT require sign-in")
        print(f"   Use direct curl POST instead — no OAuth needed!")
        print(f"   Example:")
        for f in fields:
            print(f"     -d \"entry.{f['entry']}=value\"")
        print(f"     -d \"fvv=1\" -d \"pageHistory=0\" -d \"submissionTimestamp=-1\"")
        print(f"     https://docs.google.com/forms/d/e/{form_key}/formResponse")


if __name__ == "__main__":
    main()
