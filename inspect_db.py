import os
import sys
import json
import urllib.request

# Force UTF-8 encoding
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

def main():
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        print("Error: NOTION_TOKEN not set.")
        sys.exit(1)
        
    db_id = "2f90d907-031e-805c-be36-ebd342683bfa" # Trading Journal ID
    
    url = f"https://api.notion.com/v1/databases/{db_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                props = data.get("properties", {})
                print(f"Properties of Trading Journal ({db_id}):")
                for key, val in props.items():
                    print(f"- {key}: {val.get('type')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
