import os
import sys
import json
import random
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

def update_block(token, block_id, news_item):
    url = f"https://api.notion.com/v1/blocks/{block_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    title = news_item['title']
    link = news_item['link']
    
    # Construct Rich Text Param
    # 1. "오늘의 뉴스 📊 " (Gray)
    # 2. Title (Default, Link)
    
    payload = {
        "paragraph": {
            "rich_text": [
                {
                    "type": "equation",
                    "equation": { 
                        "expression": f"\\scriptsize \\color{{gray}} \\text{{오늘의 뉴스 📊 }} \\color{{black}} \\text{{{title}}}" 
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

def main():
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        print("Error: NOTION_TOKEN environment variable not set.")
        sys.exit(1)
        
    # Block ID of the detailed news line (found in callout_children.json)
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
