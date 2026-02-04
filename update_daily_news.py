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

    # 2. Find Header Block ("오늘의 뉴스") inside Callout
    print(f"Searching for News Header in Callout {callout_id}...")
    callout_children = get_children(token, callout_id)
    
    header_block_id = None
    content_block_id = None
    header_is_container = False # Flag: if True, header is a Callout containing the news
    
    for i, block in enumerate(callout_children):
        # Case A: Header is a Paragraph (Old style)
        if block.get("type") == "paragraph":
            rich_text = block.get("paragraph", {}).get("rich_text", [])
            for t in rich_text:
                expr = t.get("equation", {}).get("expression", "") if t.get("type") == "equation" else t.get("plain_text", "")
                if "오늘의 뉴스" in expr or "News" in expr:
                    header_block_id = block.get("id")
                    if i + 1 < len(callout_children):
                        content_block_id = callout_children[i+1].get("id")
                    break
        
        # Case B: Header is a Callout (New style requests)
        elif block.get("type") == "callout":
            rich_text = block.get("callout", {}).get("rich_text", [])
            for t in rich_text:
                txt = t.get("plain_text", "")
                if "오늘의 뉴스" in txt or "News" in txt:
                    header_block_id = block.get("id")
                    header_is_container = True
                    print("Found Header as Callout (Container).")
                    
                    # Look for content INSIDE this header callout
                    inner_children = get_children(token, header_block_id)
                    if inner_children:
                        # Find the first paragraph block to update
                        for child in inner_children:
                            if child.get("type") == "paragraph":
                                content_block_id = child.get("id")
                                break 
                    break
                    
        if header_block_id: break
        
    return callout_id, header_block_id, content_block_id, header_is_container

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
    callout_id, header_id, content_id, header_is_container = find_news_blocks(token, page_id)
    
    if not callout_id:
        print("Could not find main callout.")
        return

    # 1. Update/Create Header
    header_expression = r"\substack{ \color{gray} \textsf{\scriptsize 오늘의 뉴스 📊} }"
    
    parent_for_content = callout_id # Default fallback
    
    if header_id:
        # Update Header Text (to fix stale dates/titles)
        # We need to know the type to send correct payload
        
        target_type = "callout" if header_is_container else "paragraph"
        final_payload = {
            target_type: {
                "rich_text": [{
                    "type": "equation",
                    "equation": { "expression": header_expression }
                }]
            }
        }
        
        print(f"Updating Header ({target_type})...")
        update_block_content(token, header_id, final_payload)
            
        parent_for_content = header_id if header_is_container else callout_id
    else:
        # Create NEW Header
        # User requested Nested Callout structure
        print("Header block not found. Creating new Inner Callout Header...")
        
        new_header_payload = {
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{
                    "type": "equation",
                    "equation": { "expression": header_expression }
                }],
                "icon": { "emoji": "📰" },
                "color": "gray_background"
            }
        }
        
        # Append nested callout
        resp = append_children(token, callout_id, [new_header_payload])
        
        if resp and "results" in resp and len(resp["results"]) > 0:
            new_block = resp["results"][0]
            new_header_id = new_block.get("id")
            print(f"Created new header callout: {new_header_id}")
            parent_for_content = new_header_id 
        else:
            print("Failed to create header? Fallback to callout parent.")
            parent_for_content = callout_id

    # 2. Update/Create Content
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
        update_block_content(token, content_id, content_payload)
    else:
        print(f"Content block not found. Appending to {parent_for_content}...")
        append_children(token, parent_for_content, [{
            "object": "block",
            "type": "paragraph",
            "paragraph": content_payload["paragraph"]
        }])

if __name__ == "__main__":
    main()
