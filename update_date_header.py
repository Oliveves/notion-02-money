import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

# Force UTF-8 encoding
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

def get_kst_time():
    # UTC to KST (+9)
    utc_now = datetime.now(timezone.utc)
    kst_now = utc_now + timedelta(hours=9)
    return kst_now

def update_block(token, block_id):
    url = f"https://api.notion.com/v1/blocks/{block_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    now = get_kst_time()
    
    # Format: 26 (YY), 1 (M), 31 (D), Sat (Day)
    yy = now.strftime("%y")
    m = str(now.month)
    d = str(now.day)
    day = now.strftime("%a") # Mon, Tue... (User example said 'Sat' which is short, but 'Monday' in json. 'Sat' typically %a)
    # User's example: \large Sat. JSON example: \large Monday. 
    # User said "Sat" in prompt. I will use %a (Short) based on prompt "Sat".
    
    # Construct LaTeX
    # \texttt{\small 26} \texttt{\tiny \ 년} \quad \texttt{\huge 1} \texttt{\tiny \ 월} \quad \texttt{\huge 31} \texttt{\tiny \ 일} \quad\texttt{\large Sat}
    expression = f"\\texttt{{\\small {yy}}} \\texttt{{\\tiny \\ 년}} \\quad \\texttt{{\\huge {m}}} \\texttt{{\\tiny \\ 월}} \\quad \\texttt{{\\huge {d}}} \\texttt{{\\tiny \\ 일}} \\quad\\texttt{{\\large {day}}}"
    
    payload = {
        "paragraph": {
            "rich_text": [
                {
                    "type": "equation",
                    "equation": { 
                        "expression": expression
                    }
                }
            ]
        }
    }
    
    data_json = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data_json, headers=headers, method="PATCH")
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                print(f"Date header updated to: {yy}.{m}.{d} ({day})")
            else:
                print(f"Failed to update block: {response.status}")
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"Error updating block: {e}")

def get_children(token, block_id):
    url = f"https://api.notion.com/v1/blocks/{block_id}/children"
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
                return data.get("results", [])
    except Exception as e:
        print(f"Error fetching children: {e}")
    return []

def find_target_block(token, page_id):
    # 1. Find the Callout Block in the Page
    print(f"Searching for Callout in Page {page_id}...")
    page_children = get_children(token, page_id)
    
    callout_id = None
    for block in page_children:
        if block.get("type") == "callout":
            callout_id = block.get("id")
            print(f"Found Callout: {callout_id}")
            break
    
    if not callout_id:
        print("Callout block not found.")
        return None

    # 2. Find the Date Block in the Callout
    print(f"Searching for Date Block in Callout {callout_id}...")
    callout_children = get_children(token, callout_id)
    
    for block in callout_children:
        if block.get("type") == "paragraph":
            # Check equation for date-like content (year/month/day/year)
            rich_text = block.get("paragraph", {}).get("rich_text", [])
            for t in rich_text:
                if t.get("type") == "equation":
                    expr = t.get("equation", {}).get("expression", "")
                    # "2026", "Monday", "Sat", "년"
                    if "text" in expr or "20" in expr: 
                        # Weak check, but improved: check if it's NOT the news block
                        if "오늘의 뉴스" not in expr and "News" not in expr:
                            print(f"Found Date Block: {block.get('id')}")
                            return block.get("id")
    
    print("Date block not found in Callout.")
    return None

def main():
    token = os.environ.get("NOTION_TOKEN")
    page_id = os.environ.get("NOTION_PAGE_ID")
    
    if not token:
        print("Error: NOTION_TOKEN environment variable not set.")
        sys.exit(1)

    if not page_id:
        print("Error: NOTION_PAGE_ID environment variable not set.")
        sys.exit(1)
        
    # Main Page ID
    # page_id = "2f90d907-031e-80e8-928d-c7617241966f"
    
    print("Finding target block...")
    target_block_id = find_target_block(token, page_id)
    
    if not target_block_id:
        print("Using fallback ID...")
        # Block ID from callout_children.json (the first paragraph with the date)
        target_block_id = "2f90d907-031e-80b0-96de-e75401ced683"
    
    print("Updating date header...")
    update_block(token, target_block_id)

if __name__ == "__main__":
    main()
