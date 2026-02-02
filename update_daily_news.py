import os
import sys
import json
import random
import re
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

# Force UTF-8 encoding
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

def fetch_economic_news():
    # Google News RSS (Economy - Korea)
    # Search query '경제' (Economy)
    rss_url = "https://news.google.com/rss/search?q=%EA%B2%BD%EC%A0%9C&hl=ko&gl=KR&ceid=KR:ko"
    
    try:
        req = urllib.request.Request(rss_url)
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                xml_data = response.read()
                root = ET.fromstring(xml_data)
                
                items = []
                # Parse items
                for item in root.findall('.//item'):
                    title = item.find('title').text
                    link = item.find('link').text
                    # Clean title (remove source suffix if possible, e.g. " - NewsSource")
                    if " - " in title:
                        title = title.rsplit(" - ", 1)[0]
                    items.append({"title": title, "link": link})
                
                return items
    except Exception as e:
        print(f"Error fetching RSS: {e}")
        return []

def escape_latex(text):
    if not text:
        return ""
    # aggressive whitelist: allow Hangul, English, Numbers, Space, and safe punctuation
    # \uAC00-\uD7A3 : Hangul Syllables
    # \u3131-\u318E : Hangul Compatibility Jamo
    # a-zA-Z0-9 : Alphanumeric
    # \s : Whitespace
    # \.,\-\?! : Safe punctuation
    
    # First, simple replacements for common blockers
    text = text.replace('"', "'").replace("\n", " ").replace("\\", " ")
    
    # Replace any character NOT in the whitelist with a SPACE
    safe_pattern = re.compile(r'[^ \uAC00-\uD7A3\u3131-\u318Ea-zA-Z0-9\.,\-\?!\%\(\)]')
    
    # Use space instead of empty string
    clean_text = safe_pattern.sub(' ', text)
    
    # Collapse multiple spaces into one
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    # Escape the few allowed specials that need it in LaTeX
    clean_text = clean_text.replace('%', r'\%')
    
    return clean_text

def update_block(token, block_id, news_item):
    url = f"https://api.notion.com/v1/blocks/{block_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    title = news_item['title']
    link = news_item['link']
    
    # Escape title for LaTeX
    safe_title = escape_latex(title)
    
    # Construct Rich Text Param
    # Structure matching callout_children.json:
    # \color{gray} \textsf{\scriptsize 오늘의 뉴스 📊 \color{black} TITLE} \color{black}
    
    expression = f"\\color{{gray}} \\textsf{{\\scriptsize 오늘의 뉴스 📊 \\color{{black}} {safe_title}}} \\color{{black}}"
    
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
                print("News block updated successfully.")
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
            # Optional: Check content if multiple callouts exist
            # For now, assume the first callout is the dashboard header
            callout_id = block.get("id")
            print(f"Found Callout: {callout_id}")
            break
    
    if not callout_id:
        print("Callout block not found.")
        return None

    # 2. Find the News Block in the Callout
    print(f"Searching for News Block in Callout {callout_id}...")
    callout_children = get_children(token, callout_id)
    
    for block in callout_children:
        if block.get("type") == "paragraph":
            # Check if it looks like the News block (contains "오늘의 뉴스" or just assume position)
            # The structure has "Today's News" text usually.
            # We look for "equation" with "오늘의 뉴스" inside
            rich_text = block.get("paragraph", {}).get("rich_text", [])
            for t in rich_text:
                if t.get("type") == "equation":
                    expr = t.get("equation", {}).get("expression", "")
                    if "오늘의 뉴스" in expr or "News" in expr:
                        print(f"Found News Block: {block.get('id')}")
                        return block.get("id")
    
    print("News block not found in Callout.")
    return None

def main():
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        print("Error: NOTION_TOKEN environment variable not set.")
        sys.exit(1)
        
    # Main Page ID (from URL provided by user)
    page_id = "2f90d907-031e-80e8-928d-c7617241966f"
    
    print("Finding target block...")
    target_block_id = find_target_block(token, page_id)
    
    if not target_block_id:
        # Fallback to hardcoded just in case
        print("Using fallback ID...")
        target_block_id = "2f90d907-031e-801b-8345-debfbf1d2dd3"
    
    print("Fetching news...")
    news_items = fetch_economic_news()
    
    if not news_items:
        print("No news found.")
        return
        
    # Pick a random one or the top one?
    # Let's pick a random one from top 5 to keep it fresh but relevant
    top_n = news_items[:5]
    if not top_n: top_n = news_items
    
    selected_news = random.choice(top_n)
    print(f"Selected: {selected_news['title']}")
    
    print(f"Updating block {target_block_id}...")
    update_block(token, target_block_id, selected_news)

if __name__ == "__main__":
    main()
