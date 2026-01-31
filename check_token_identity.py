import urllib.request
import urllib.error
import json
import os

def check_token_identity():
    # usage: NOTION_TOKEN=... python check_token_identity.py
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        # Fallback for direct run
        token = "ntn_I3641115422aw21TI9L4EKCf7Cwt6bPS5Exy3b7cxpU9Oh"
    
    url = "https://api.notion.com/v1/users/me"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    print(f"Testing Token: {token[:4]}...{token[-4:]}")
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                print("Token is VALID.")
                print("Bot Owner:", data.get("bot", {}).get("owner", {}))
                print("Name:", data.get("name"))
                return True
    except urllib.error.HTTPError as e:
        print(f"Token Check Failed: {e.code} - {e.reason}")
        print(e.read().decode('utf-8'))
    except Exception as e:
        print(f"Error: {e}")
        
    return False

if __name__ == "__main__":
    check_token_identity()
