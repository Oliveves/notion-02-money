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
                return True
    except Exception as e:
        print(f"Error appending children: {e}")
    return False

def find_news_blocks(token, page_id):
    # 1. Find Callout
    print(f"Searching for Callout in Page {page_id}...")
    page_children = get_children(token, page_id)
    callout_id = None
    
    print(f"Debug: Page has {len(page_children)} children.")
    
    # Recursive search function
    def find_target_blocks_recursive(blocks, depth=0):
        if depth > 5: return None, None # Increased depth limit
        
        found_callout = None
        found_header = None
        
        for block in blocks:
            b_type = block.get("type")
            b_id = block.get("id")
            
            # Check if this block IS the header ("오늘의 뉴스")
            # Usually in paragraph or equation
            content_text = ""
            if b_type == "paragraph":
                rich_text = block.get("paragraph", {}).get("rich_text", [])
                for t in rich_text:
                    content_text += t.get("plain_text", "") + t.get("equation", {}).get("expression", "")
            
            if "오늘의 뉴스" in content_text or "News" in content_text:
                 print(f"Found Header Block by Text: {b_id}")
                 found_header = b_id
                 # If we found header, the parent might be the container we want, 
                 # OR we just return this header ID to update IT, and the next block for content.
                 # But we need to return callout_id (container) to append if needed?
                 # Actually main() uses header_id to update content.
            
            if b_type == "callout":
                found_callout = b_id
                
            # If we found both, great, but header is most important for updating existing.
            if found_header:
                return found_callout, found_header # Return what we have

            # Check containers (column_list -> column, callout content, toggle)
            if float(depth) < 5 and block.get("has_children"):
                children = get_children(token, b_id)
                c_callout, c_header = find_target_blocks_recursive(children, depth + 1)
                
                # If child found something, bubble it up.
                # Prioritize child's discovery
                if c_header: 
                    return (c_callout if c_callout else found_callout), c_header
                if c_callout and not found_callout:
                    found_callout = c_callout
        
        return found_callout, found_header

    callout_id, header_id = find_target_blocks_recursive(page_children)
    
    # Fallback: If no callout found with header but we need one, just take the FIRST callout found on the page.
    if not callout_id:
        print("Specific News Callout not found. Searching for ANY callout...")
        for block in page_children:
            if block.get("type") == "callout":
                callout_id = block.get("id")
                print(f"Fallback Callout found: {callout_id}")
                break
    
    # If header found, we can deduce content_id comes after it?
    # The original logic expected callout -> header -> content.
    # If we found header but it's deep, we need its sibling.
    # This is getting complex. 
    # Simplified strategy: If header_id matches, we need to find its parent to find its next sibling?
    # Notion API doesn't give parent easily or siblings without re-fetching parent children.
    # BUT, if we returned the LIST of blocks in recursive search, we could find the index.
    
    # Retrying simple approach: Just update the header if found. 
    # If content needs update, we need content_id.
    # Let's assume if we found header_id, we can try to append content to its parent? No.
    
    # If header is found, let's just use it.
    # For content, if we can't find it easily, maybe we just append to the SAME container as header?
    
    content_id = None # We'll skip finding content_block specific ID for now if we use text search
    # If we found callout but no header, we return (callout, None, None) which leads to append.
    # If we found header, we return (None, header, None) -> Update header. 
    # But where does content go?
    
    return callout_id, header_id, None

    # 2. Find Header Block ("오늘의 뉴스") inside Callout
    print(f"Searching for News Header in Callout {callout_id}...")
    callout_children = get_children(token, callout_id)
    
    header_block_id = None
    content_block_id = None
    
    for i, block in enumerate(callout_children):
        if block.get("type") == "paragraph":
            rich_text = block.get("paragraph", {}).get("rich_text", [])
            for t in rich_text:
                # Check for Equation with specific content or just "News"
                if t.get("type") == "equation":
                    expr = t.get("equation", {}).get("expression", "")
                    if "오늘의 뉴스" in expr or "News" in expr:
                        header_block_id = block.get("id")
                        # Check if next block exists
                        if i + 1 < len(callout_children):
                            content_block_id = callout_children[i+1].get("id")
                        break
        if header_block_id: break
        
    return callout_id, header_block_id, content_block_id

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
    callout_id, header_id, content_id = find_news_blocks(token, page_id)
    
    if not callout_id:
        # Fallback if callout logic creates issues, but we need callout ID.
        # Assuming manual ID for safety if search fails? 
        # For now, if dynamic search fails, we can't proceed easily.
        return

    # 1. Update/Create Header
    header_expression = r"\substack{ \color{gray} \textsf{\scriptsize 오늘의 뉴스 📊} }"
    header_payload = {
        "paragraph": {
            "rich_text": [{
                "type": "equation",
                "equation": { "expression": header_expression }
            }]
        }
    }
    
    if header_id:
        update_block_content(token, header_id, header_payload)
    else:
        # Append Header
        print("Header block not found. creating...")
        append_children(token, callout_id, [{
            "object": "block",
            "type": "paragraph",
            "paragraph": header_payload["paragraph"]
        }])
        # Re-fetch to get the new structure? Or just append content too.
        # If we append header, we should append content right after.
        
    # 2. Update/Create Content
    # Use Rich Text with Link
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
        # We assume the block after header is the content block.
        # We overwrite it.
        update_block_content(token, content_id, content_payload)
    else:
        # If header existed but content didn't, or both didn't exist
        print("Content block not found. creating...")
        append_children(token, callout_id, [{
            "object": "block",
            "type": "paragraph",
            "paragraph": content_payload["paragraph"]
        }])

if __name__ == "__main__":
    main()
