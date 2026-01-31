import urllib.request
import urllib.error
import json

TOKEN = "ntn_I3641115422aw21TI9L4EKCf7Cwt6bPS5Exy3b7cxpU9Oh"
DB_ID = "2f90d907-031e-805c-be36-ebd342683bfa"

def test_token():
    url = f"https://api.notion.com/v1/databases/{DB_ID}"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            print(f"Success! Status: {response.status}")
            data = json.loads(response.read().decode("utf-8"))
            print(f"Title: {data.get('title', [{}])[0].get('text', {}).get('content', 'Unknown')}")
            for prop in data.get("properties", {}):
                print(f"Prop: {prop}")
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.reason}")
        print(e.read().decode('utf-8'))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_token()
