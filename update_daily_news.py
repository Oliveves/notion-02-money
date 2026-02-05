# ... (Previous imports kept) ...
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
    rss_url = "https://news.google.com/rss/search?q=%EA%B2%BD%EC%A0%9C&hl=ko&gl=KR&ceid=KR:ko"
    try:
        req = urllib.request.Request(rss_url)
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                xml_data = response.read()
                root = ET.fromstring(xml_data)
                items = []
                for item in root.findall('.//item'):
                    title = item.find('title').text
                    link = item.find('link').text
                    if " - " in title:
                        title = title.rsplit(" - ", 1)[0]
                    items.append({"title": title, "link": link})
                return items
    except Exception as e:
        print(f"Error fetching RSS: {e}")
        return []

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

def update_block_content(token, block_id, payload):
    url = f"https://api.notion.com/v1/blocks/{block_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    data_json = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data_json, headers=headers, method="PATCH")
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                print(f"Block {block_id} updated.")
                return True
    except Exception as e:
        print(f"Error updating block {block_id}: {e}")
    return False

def append_children(token, parent_id, children_list):
    url = f"https://api.notion.com/v1/blocks/{parent_id}/children"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    payload = { "children": children_list }
    data_json = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data_json, headers=headers, method="PATCH")
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                print(f"Appended children to {parent_id}.")
                # Return the response so we can get IDs of created blocks
                return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print(f"Error appending children: {e}")
    return None

def find_news_blocks(token, page_id):
    # 1. Find Callout
    print(f"Searching for Callout in Page {page_id}...")
    page_children = get_children(token, page_id)
    callout_id = None
    
    # Recursive search function to find the OUTER callout
    def find_target_blocks_recursive(blocks, depth=0):
        if depth > 5: return None
        for block in blocks:
            if block.get("type") == "callout":
                return block.get("id")
            if block.get("has_children"):
                children = get_children(token, block.get("id"))
                found = find_target_blocks_recursive(children, depth + 1)
                if found: return found
        return None

    callout_id = find_target_blocks_recursive(page_children)
    
    if not callout_id:
        print("No Callout found in page.")
        return None, None, None, False

    # 2. Iterate Children of Main Callout to find Components
    print(f"Searching for Components in Callout {callout_id}...")
    callout_children = get_children(token, callout_id)
    
    header_block_id = None
    content_container_id = None
    content_block_id = None
    
    for block in callout_children:
        block_type = block.get("type")
        
        # A. Search for Header ("Today's News")
        if not header_block_id and block_type in ["paragraph", "equation", "heading_1", "heading_2", "heading_3"]:
            # Check text content
            text_content = ""
            if block_type == "paragraph":
                rich_text = block.get("paragraph", {}).get("rich_text", [])
                for t in rich_text:
                    if t.get("type") == "equation":
                        text_content += t.get("equation", {}).get("expression", "")
                    else:
                        text_content += t.get("plain_text", "")
            
            if "오늘의 뉴스" in text_content or "News" in text_content:
                header_block_id = block.get("id")
                print(f"Found Header Block: {header_block_id}")

        # B. Search for Content Container (Inner Callout)
        if not content_container_id and block_type == "callout":
            content_container_id = block.get("id")
            print(f"Found Content Container (Inner Callout): {content_container_id}")
            
    # 3. If Content Container found, find the content inside it
    if content_container_id:
        inner_children = get_children(token, content_container_id)
        if inner_children:
            for child in inner_children:
                if child.get("type") == "paragraph":
                    content_block_id = child.get("id")
                    break
                    
    return callout_id, header_block_id, content_container_id, content_block_id

def main():
    token = os.environ.get("NOTION_TOKEN")
    page_id = os.environ.get("NOTION_PAGE_ID")

    if not token:
        print("Error: NOTION_TOKEN not set.")
        sys.exit(1)
        
    if not page_id:
        print("Error: NOTION_PAGE_ID not set.")
        sys.exit(1)
    
    # Fetch News
    news_items = fetch_economic_news()
    if not news_items:
        print("No news found.")
        return
    selected_news = random.choice(news_items[:5] if news_items else [])
    
    # Identify Blocks
    callout_id, header_id, content_container_id, content_id = find_news_blocks(token, page_id)
    
    if not callout_id:
        print("Could not find main callout.")
        return

    # 1. Update/Create Header (Standalone)
    header_expression = r"\substack{ \color{gray} \textsf{\scriptsize 오늘의 뉴스 📊} }"
    
    if header_id:
        # Update existing header
        print(f"Updating Header Block {header_id}...")
        update_block_content(token, header_id, {
            "paragraph": {
                "rich_text": [{
                    "type": "equation",
                    "equation": { "expression": header_expression }
                }]
            }
        })
    else:
        # Create new Header
        print("Creating New Header Block...")
        append_children(token, callout_id, [{
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{
                    "type": "equation",
                    "equation": { "expression": header_expression }
                }]
            }
        }])

    # 2. Update/Create Content Container (Inner Callout)
    target_container_id = content_container_id
    
    if not target_container_id:
        # Create Inner Callout if missing
        print("Creating New Inner Callout (Content Container)...")
        resp = append_children(token, callout_id, [{
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [], # Empty text for container
                "icon": { "emoji": "📰" },
                "color": "gray_background"
            }
        }])
        if resp and "results" in resp and len(resp["results"]) > 0:
            target_container_id = resp["results"][0].get("id")
            print(f"Created inner callout: {target_container_id}")
    
    # 3. Update/Create News Content
    content_payload = {
        "paragraph": {
            "rich_text": [{
                "type": "text",
                "text": { 
                    "content": selected_news['title'],
                    "link": { "url": selected_news['link'] }
                },
                "annotations": { "color": "default", "underline": False } 
            }]
        }
    }
    
    if content_id:
        print(f"Updating Content Block {content_id}...")
        update_block_content(token, content_id, content_payload)
    elif target_container_id:
        print(f"Appending Content to Container {target_container_id}...")
        append_children(token, target_container_id, [{
            "object": "block",
            "type": "paragraph",
            "paragraph": content_payload["paragraph"]
        }])
    else:
        print("Failed to find or create a target container for content.")

if __name__ == "__main__":
    main()
