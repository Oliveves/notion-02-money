import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime
from collections import defaultdict

# Force UTF-8 encoding
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Configuration
TRADING_DB_ID = "2f90d907-031e-805c-be36-ebd342683bfa"
PARENT_PAGE_ID = "2f90d907-031e-80e8-928d-c7617241966f" # Main Page where new DB will be created

def notion_request(token, endpoint, method="GET", payload=None):
    url = f"https://api.notion.com/v1/{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    data = json.dumps(payload).encode("utf-8") if payload else None
    
    try:
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code} on {endpoint}: {e.read().decode('utf-8')}")
        return None
    except Exception as e:
        print(f"Error on {endpoint}: {e}")
        return None

def find_or_create_monthly_db(token):
    # 1. Search for existing DB
    # We look for a child database of the parent page with title "Monthly Returns"
    search_payload = {
        "query": "Monthly Returns",
        "filter": {
            "value": "database",
            "property": "object"
        }
    }
    # Note: Search is global, filtering by parent is harder in search API.
    # Be careful not to pick up a wrong one.
    # Better: List children of PARENT_PAGE_ID
    
    children = notion_request(token, f"blocks/{PARENT_PAGE_ID}/children?page_size=100")
    if children:
        for block in children.get("results", []):
            if block.get("type") == "child_database":
                # Check title provided in block info? child_database block usually has title
                title = block.get("child_database", {}).get("title", "")
                if title == "Monthly Returns":
                    print(f"Found existing Monthly Returns DB: {block['id']}")
                    return block['id']

    # 2. Create if not found
    print("Creating 'Monthly Returns' Database...")
    create_payload = {
        "parent": { "type": "page_id", "page_id": PARENT_PAGE_ID },
        "title": [ { "type": "text", "text": { "content": "Monthly Returns" } } ],
        "properties": {
            "Month": { "title": {} },
            "Total Profit": { "number": { "format": "won" } },
            "Total Loss": { "number": { "format": "won" } },
            "Net Return": { "number": { "format": "won" } },
            "Trade Count": { "number": { "format": "number" } }
        },
        "is_inline": True
    }
    
    db = notion_request(token, "databases", method="POST", payload=create_payload)
    if db:
        return db.get("id")
    return None

def fetch_trading_data(token):
    # Query all records from Trading Journal
    # We need: Date, 판매수익 (Sale Profit), 판매손실 (Sale Loss)
    
    all_rows = []
    has_more = True
    next_cursor = None
    
    print("Fetching Trading Journal data...")
    
    while has_more:
        payload = { "page_size": 100 }
        if next_cursor: payload["start_cursor"] = next_cursor
        
        data = notion_request(token, f"databases/{TRADING_DB_ID}/query", method="POST", payload=payload)
        if not data: break
        
        for page in data.get("results", []):
            props = page.get("properties", {})
            
            # Find Date
            date_str = None
            date_prop = props.get("날짜") or props.get("Date")
            if date_prop and date_prop.get("date"):
                date_str = date_prop.get("date").get("start")
            
            if not date_str: continue
            
            # Find Profit/Loss
            # User specified "판매수익", "판매손실"
            profit = 0
            loss = 0
            
            # Profit
            p_prop = props.get("판매수익") or props.get("Sale Profit")
            if p_prop and p_prop.get("number"):
                profit = p_prop.get("number")
                
            # Loss
            l_prop = props.get("판매손실") or props.get("Sale Loss")
            if l_prop and l_prop.get("number"):
                loss = l_prop.get("number")
                
            all_rows.append({
                "date": date_str,
                "profit": profit,
                "loss": loss
            })
            
        has_more = data.get("has_more")
        next_cursor = data.get("next_cursor")
        
    return all_rows

def update_monthly_log(token, db_id, monthly_data):
    # 1. Fetch existing entries to find row IDs for each month
    existing_map = {} # "YYYY-MM" -> page_id
    
    query = notion_request(token, f"databases/{db_id}/query", method="POST", payload={"page_size":100})
    if query:
        for page in query.get("results", []):
            # Get Title (Month)
            title_list = page.get("properties", {}).get("Month", {}).get("title", [])
            if title_list:
                m_str = "".join([t.get("plain_text", "") for t in title_list])
                existing_map[m_str] = page["id"]

    # 2. Upsert
    for month_str, stats in monthly_data.items():
        net = stats["profit"] - stats["loss"] # Assuming loss is positive number in DB? Or negative?
        # Usually users enter Loss as positive number in "Loss" column. 
        # Net = Profit - Loss.
        
        props = {
            "Month": { "title": [ { "text": { "content": month_str } } ] },
            "Total Profit": { "number": stats["profit"] },
            "Total Loss": { "number": stats["loss"] },
            "Net Return": { "number": net },
            "Trade Count": { "number": stats["count"] }
        }
        
        if month_str in existing_map:
            # Update
            print(f"Updating {month_str}...")
            notion_request(token, f"pages/{existing_map[month_str]}", method="PATCH", payload={"properties": props})
        else:
            # Create
            print(f"Creating {month_str}...")
            notion_request(token, "pages", method="POST", payload={
                "parent": { "database_id": db_id },
                "properties": props
            })

def main():
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        print("Error: NOTION_TOKEN not set.")
        sys.exit(1)
        
    # 1. Setup DB
    monthly_db_id = find_or_create_monthly_db(token)
    if not monthly_db_id:
        print("Failed to find or create Monthly Returns DB.")
        return

    # 2. Aggregate Data
    rows = fetch_trading_data(token)
    print(f"Fetched {len(rows)} trading records.")
    
    # Group by Month
    monthly_agg = defaultdict(lambda: {"profit": 0, "loss": 0, "count": 0})
    
    for row in rows:
        # date_str is YYYY-MM-DD
        dt = row["date"][:7] # YYYY-MM
        monthly_agg[dt]["profit"] += (row["profit"] or 0)
        monthly_agg[dt]["loss"] += (row["loss"] or 0)
        monthly_agg[dt]["count"] += 1
        
    # 3. Update DB
    update_monthly_log(token, monthly_db_id, monthly_agg)
    print("Monthly log update complete.")

if __name__ == "__main__":
    main()
