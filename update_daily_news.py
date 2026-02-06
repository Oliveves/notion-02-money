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

import urllib.parse

def fetch_economic_news():
    # Keywords: Samsung, SK Hynix, Kospi, Nasdaq, Fed (Interest Rate), Exchange Rate
    keywords = ["삼성전자", "SK하이닉스", "코스피", "나스닥", "금리", "환율", "뉴욕증시"]
    query = " OR ".join(keywords)
    encoded_query = urllib.parse.quote(query)
    
    # Google News RSS with the specific query
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
    
    try:
        req = urllib.request.Request(rss_url)
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                xml_data = response.read()
                root = ET.fromstring(xml_data)
                
                all_items = []
                for item in root.findall('.//item'):
                    title = item.find('title').text
                    link = item.find('link').text
                    
                    # Clean Title
                    if " - " in title:
                        title = title.rsplit(" - ", 1)[0]
                    
                    all_items.append({"title": title, "link": link})
                
                # --- Filtering Logic ---
                filtered_items = []
                exclusion_keywords = ["[광고]", "게시판", "인사", "부고", "화촉", "모집", "단신"]
                
                for item in all_items:
                    # 1. Exclude irrelevant
                    if any(bad in item['title'] for bad in exclusion_keywords):
                        continue
                        
                    # 2. Assign Priority (1 = High, 2 = Medium)
                    # High Priority: Directly mentions major keywords in TITLE
                    priority = 2
                    if any(k in item['title'] for k in keywords):
                        priority = 1
                    
                    item['priority'] = priority
                    filtered_items.append(item)
                
                # Sort by Priority (1 first)
                filtered_items.sort(key=lambda x: x['priority'])
                
                return filtered_items
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
        return None  # Return None to indicate failure
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

def delete_block(token, block_id):
    url = f"https://api.notion.com/v1/blocks/{block_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    req = urllib.request.Request(url, headers=headers, method="DELETE")
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                print(f"Block {block_id} deleted.")
                return True
    except Exception as e:
        print(f"Error deleting block {block_id}: {e}")
    return False

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
            
    # 3. If Content Containers found, identify them
    # Changed: Return ALL found containers to allow cleanup in main()
    found_containers = []
    
    if content_container_id:
        # We found the first one in the loop above
        found_containers.append(content_container_id)
        
    # Check if there are MORE containers (duplicates)
    if callout_children:
        for block in callout_children:
            if block.get("type") == "callout" and block.get("id") != content_container_id:
                 found_containers.append(block.get("id"))
                     
    return callout_id, header_block_id, found_containers, content_block_id

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
    callout_id, header_id, found_containers, _ = find_news_blocks(token, page_id)
    # Note: find_news_blocks no longer returns content_id, we derive it from containers
    
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

    # 2. Handle Content Containers (Inner Callout)
    target_container_id = None
    
    if found_containers:
        # Strategy: Keep the first one, delete the rest
        target_container_id = found_containers[0]
        print(f"Using existing inner callout: {target_container_id}")
        
        if len(found_containers) > 1:
            print(f"Found {len(found_containers)-1} duplicates. cleaning up...")
            for extra_id in found_containers[1:]:
                delete_block(token, extra_id)
                
        # REMOVE ICON (Update property)
        # Note: Notion API might not support setting icon to null for callouts directly if it forces default. 
        # We try setting it to null (None in python json dump).
        print("Removing icon from inner callout...")
        update_block_content(token, target_container_id, {
            "callout": {
                "icon": None 
            }
        })
                
    else:
        # Create NEW Container (No Icon)
        print("Creating New Inner Callout (No Icon)...")
        # To have no icon, we might omit it or set it to null? 
        # Notion usually defaults to an icon if omitted. 
        # Let's try explicit null. If that fails, we fallback to specific handling.
        resp = append_children(token, callout_id, [{
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [], 
                "icon": None, # Attempt to set no icon
                "color": "gray_background"
            }
        }])
        if resp and "results" in resp and len(resp["results"]) > 0:
            target_container_id = resp["results"][0].get("id")
            print(f"Created inner callout: {target_container_id}")

    # 3. Update Content (Text-Only Strategy)
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
    
    if target_container_id:
        print(f"Checking content in {target_container_id}...")
        children = get_children(token, target_container_id)
        
        if children is None:
            print("API Error fetching children. Aborting.")
            return
            
        if children:
            # Update First Child
            first_child_id = children[0].get("id")
            print(f"Updating text in {first_child_id}...")
            update_block_content(token, first_child_id, content_payload)
            
            # Delete Tail (Cleanup)
            if len(children) > 1:
                print("Cleaning up extra content blocks...")
                for extra in children[1:]:
                    delete_block(token, extra.get("id"))
        else:
            # Empty container, append
            print("Appending new content block...")
            append_children(token, target_container_id, [{
                "object": "block",
                "type": "paragraph",
                "paragraph": content_payload["paragraph"]
            }])

if __name__ == "__main__":
    main()
