import os
import json
import urllib.request
import urllib.error
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

def create_database(token, page_id):
    url = "https://api.notion.com/v1/databases"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    payload = {
        "parent": { "type": "page_id", "page_id": page_id },
        "title": [
            {
                "type": "text",
                "text": { "content": "My Assets" }
            }
        ],
        "properties": {
            "Item": { "title": {} },
            "Amount": { "number": { "format": "won" } },
            "Type": { 
                "select": {
                    "options": [
                        { "name": "Stock", "color": "orange" },
                        { "name": "Cash", "color": "gray" },
                        { "name": "Crypto", "color": "blue" },
                        { "name": "Real Estate", "color": "yellow" }
                    ]
                } 
            }
        },
        "is_inline": True
    }
    
    data_json = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data_json, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                resp_body = response.read().decode("utf-8")
                db_data = json.loads(resp_body)
                db_id = db_data.get("id")
                print(f"Database created successfully: {db_id}")
                return db_id
    except urllib.error.HTTPError as e:
        print(f"Failed to create DB: {e.code} {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"Error: {e}")
        
    return None

def add_entry(token, db_id, item, amount, asset_type):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    payload = {
        "parent": { "database_id": db_id },
        "properties": {
            "Item": {
                "title": [ { "text": { "content": item } } ]
            },
            "Amount": {
                "number": amount
            },
            "Type": {
                "select": { "name": asset_type }
            }
        }
    }
    
    data_json = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data_json, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                print(f"Added entry: {item}")
                return True
    except urllib.error.HTTPError as e:
         print(f"Failed to add entry {item}: {e.read().decode('utf-8')}")
    except Exception as e:
         print(f"Error adding {item}: {e}")
         
    return False

def main():
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        print("Error: NOTION_TOKEN environment variable not set.")
        sys.exit(1)
    page_id = "2f90d907-031e-80e8-928d-c7617241966f" # Main page ID
    
    print("Creating 'My Assets' Database...")
    db_id = create_database(token, page_id)
    
    if db_id:
        print(f"Populating dummy data into {db_id}...")
        # Dummy Data
        data = [
            ("삼성전자", 5000000, "Stock"),
            ("테슬라(Tesla)", 8000000, "Stock"),
            ("비트코인(BTC)", 3000000, "Crypto"),
            ("원화 현금", 2000000, "Cash"),
            ("달러 예수금", 1500000, "Cash"),
            ("주택청약", 10000000, "Real Estate")
        ]
        
        for item, amount, asset_type in data:
            add_entry(token, db_id, item, amount, asset_type)
            
        print("Done.")

if __name__ == "__main__":
    main()
