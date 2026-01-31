import os
import json
import random
import sys
import urllib.request
import urllib.error

# Force UTF-8 encoding for stdout/stderr
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

def get_page_content_lines(token, page_id):
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                resp_body = response.read().decode("utf-8")
                blocks = json.loads(resp_body).get("results", [])
                
                lines = []
                for block in blocks:
                    if block.get("type") == "paragraph":
                        rich_text = block.get("paragraph", {}).get("rich_text", [])
                        plain_text = "".join([t.get("plain_text", "") for t in rich_text])
                        # Keep even empty lines if they are part of formatting? 
                        # Usually we might want to skip only completely empty blocks if valid text exists.
                        # But for "line preservation" let's keep non-empty strings, or maybe meaningful breaks.
                        if plain_text.strip():
                            lines.append(plain_text)
                return lines
    except Exception as e:
        print(f"Error fetching page content: {e}")
    return []

def get_random_key_message(token, db_id):
    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    payload = { "page_size": 100 }
    data_json = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data_json, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                print(f"Failed to query database: {response.status}")
                return None
            
            resp_body = response.read().decode("utf-8")
            data = json.loads(resp_body)
            results = data.get("results", [])
            
            if not results:
                print("No entries found in Key Message database.")
                return None
                
            # Pick random
            choice = random.choice(results)
            page_id = choice.get("id")
            
            # 1. Try to get Body Content first (per logic "content first, fallback to title" or "title missing -> content")
            # User said: "If title is missing, use content". 
            # But let's check both or prioritize content if it looks like a message body.
            # actually usually Notion users put long text in body.
            
            lines = get_page_content_lines(token, page_id)
            if lines:
                return "\n".join(lines)
            
            # 2. Fallback to Title
            props = choice.get("properties", {})
            title_list = []
            for key, val in props.items():
                if val.get("type") == "title":
                    title_list = val.get("title", [])
                    break
            
            if title_list:
                text = "".join([t.get("plain_text", "") for t in title_list])
                return text
            
            return "No Text Found"
            
    except Exception as e:
        print(f"Error getting key message: {e}")
        return None

def find_or_create_child_paragraph(token, parent_id):
    url = f"https://api.notion.com/v1/blocks/{parent_id}/children"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                resp_body = response.read().decode("utf-8")
                results = json.loads(resp_body).get("results", [])
                
                # Look for an existing paragraph block
                for block in results:
                    if block.get("type") == "paragraph":
                        return block.get("id")
                
                # If no paragraph found (or only other types), create one
                print("No suitable child block found. Creating new paragraph...")
                create_payload = {
                    "children": [
                        {
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [{ "text": { "content": "Placeholder" } }]
                            }
                        }
                    ]
                }
                create_json = json.dumps(create_payload).encode("utf-8")
                create_req = urllib.request.Request(url, data=create_json, headers=headers, method="PATCH")
                
                with urllib.request.urlopen(create_req) as create_resp:
                     if create_resp.status == 200:
                        create_body = create_resp.read().decode("utf-8")
                        new_results = json.loads(create_body).get("results", [])
                        if new_results:
                            return new_results[0].get("id")
                            
    except Exception as e:
        print(f"Error finding/creating child block: {e}")
        
    return None

def update_equation_block(token, block_id, text):
    url = f"https://api.notion.com/v1/blocks/{block_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    # Split text by newline to create multi-line equation
    lines = text.split('\n')
    
    # Format: \texttt{\scriptsize \color{black}{TEXT}}
    # User requested format:
    # \texttt{\scriptsize \color{black}{매일 아침마다 마중을 나와주는 }} \\[-0.1em] \texttt{\scriptsize \color{black}{우유 사랑해}}
    
    formatted_lines = [f"\\texttt{{\\scriptsize \\color{{black}}{{{line}}}}}" for line in lines if line.strip()]
    
    if not formatted_lines:
        formatted_lines = [f"\\texttt{{\\scriptsize \\color{{black}}{{{text}}}}}"]

    # Join with \\[-0.1em]
    latex_content = " \\\\[-0.1em] ".join(formatted_lines)
    
    payload = {
        "paragraph": { 
            "rich_text": [
                {
                    "type": "equation",
                    "equation": { "expression": latex_content }
                }
            ]
        }
    }
    
    data_json = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data_json, headers=headers, method="PATCH")
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                print("Block updated successfully.")
            else:
                print(f"Failed to update block: {response.status}")
    except Exception as e:
        print(f"Error updating block: {e}")

def main():
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        # Fallback for local testing
        token = "ntn_I3641115422aw21TI9L4EKCf7Cwt6bPS5Exy3b7cxpU9Oh"
    
    # 'Key Message(입력)' Database ID
    db_id = "2f90d907-031e-80b6-a49b-d2b34e29359d"
    
    # 'Key Message' Callout ID
    target_callout_id = "2f90d907-031e-80ff-b50d-ee245fc589b1"
    
    print("Fetching random key message...")
    text = get_random_key_message(token, db_id)
    
    if not text:
        print("Could not fetch message.")
        return
        
    print(f"Selected: {text}")
    
    print(f"Finding child block of {target_callout_id}...")
    child_id = find_or_create_child_paragraph(token, target_callout_id)
    
    if child_id:
        print(f"Updating child block {child_id}...")
        update_equation_block(token, child_id, text)
    else:
        print("Could not find or create child block to update.")

if __name__ == "__main__":
    main()
