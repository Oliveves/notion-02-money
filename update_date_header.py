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

def main():
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        print("Error: NOTION_TOKEN environment variable not set.")
        sys.exit(1)
        
    # Block ID from callout_children.json (the first paragraph with the date)
    target_block_id = "2f90d907-031e-80b0-96de-e75401ced683"
    
    print("Updating date header...")
    update_block(token, target_block_id)

if __name__ == "__main__":
    main()
