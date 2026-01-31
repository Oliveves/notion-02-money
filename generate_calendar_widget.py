import os
import json
import datetime
import calendar
import sys
import urllib.request
import urllib.error

# Force UTF-8 encoding for stdout/stderr
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

def fetch_db_data(token, db_id):
    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    payload = { "page_size": 100 }
    
    results = []
    has_more = True
    start_cursor = None
    
    while has_more:
        if start_cursor: payload["start_cursor"] = start_cursor
        
        data_json = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_json, headers=headers)
        
        try:
            with urllib.request.urlopen(req) as response:
                if response.status != 200:
                    print(f"Error fetching DB: Status {response.status}")
                    break
                
                resp_body = response.read().decode("utf-8")
                data = json.loads(resp_body)
                
                results.extend(data.get("results", []))
                has_more = data.get("has_more")
                start_cursor = data.get("next_cursor")
                
        except urllib.error.HTTPError as e:
            print(f"HTTP Error fetching DB: {e.code} - {e.reason}")
            # Try to read error body
            try:
                err_body = e.read().decode("utf-8")
                print(f"Error body: {err_body}")
            except:
                pass
            break
        except Exception as e:
            print(f"Error: {e}")
            break
        
    return results

def parse_data(results):
    calendar_data = {}
    
    for page in results:
        props = page.get("properties", {})
        page_id = page.get("id").replace("-", "")
        
        # Find Date Property
        # Trading Journal likely uses "Date" or "날짜"
        date_candidates = ["날짜", "Date", "Time", "일시"]
        date_prop = None
        for key in date_candidates:
            if key in props:
                date_prop = props[key].get("date")
                if date_prop: break
        
        if not date_prop: continue
        date_str = date_prop.get("start")
        if not date_str: continue
        date_str = date_str[:10] # YYYY-MM-DD
        
        # Find Title Property
        title_candidates = ["이름", "Name", "제목", "Item"]
        title_list = []
        for key in title_candidates:
            if key in props and props[key].get("type") == "title":
                title_list = props[key].get("title", [])
                break
        
        if not title_list:
            for key, val in props.items():
                if val.get("type") == "title":
                    title_list = val.get("title", [])
                    break
                    
        title = "".join([t.get("plain_text", "") for t in title_list])
        if not title: title = "Untitled"
        
        # Icon
        icon = page.get("icon", {})
        emoji = icon.get("emoji") if icon and icon.get("type") == "emoji" else "💰"
        
        if date_str not in calendar_data:
            calendar_data[date_str] = []
            
        calendar_data[date_str].append({
            "id": page_id,
            "title": title,
            "emoji": emoji,
            "display": f"{emoji} {title}"
        })
        
    return calendar_data

def generate_html(calendar_data):
    today = datetime.date.today()
    year = today.year
    month = today.month
    
    cal = calendar.Calendar(firstweekday=6) # Sunday start
    month_days = cal.monthdayscalendar(year, month)
    
    month_name = datetime.date(year, month, 1).strftime("%B %Y")
    
    # CSS - Gray Theme
    css = """
    <style>
        ::-webkit-scrollbar { display: none; }
        html { -ms-overflow-style: none; scrollbar-width: none; }

        :root {
            --bg-color: #ffffff;
            --text-color: #37352f;
            --grid-border: #e0e0e0;
            --hover-bg: #f7f7f5;
        }
        body {
            font-family: "Courier New", Courier, monospace;
            margin: 0;
            padding: 12px 20px 20px 20px;
            background-color: var(--bg-color);
            color: var(--text-color);
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        h1 { 
            margin-top: 0; 
            margin-bottom: 10px; 
            font-size: 0.9em; 
            font-weight: bold; 
            width: 100%; 
            max-width: 600px; 
            text-align: left; 
        }
        
        .calendar-grid {
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 8px;
            width: 100%;
            max-width: 600px;
        }
        
        .day-header {
            text-align: center;
            font-size: 0.8em;
            color: #999;
            padding-bottom: 8px;
        }
        
        .day-cell {
            aspect-ratio: 1 / 1;
            border-radius: 8px;
            background: #fff;
            box-shadow: 0 0 0 1px var(--grid-border);
            position: relative;
            cursor: pointer;
            transition: background 0.2s;
            display: flex;
            justify-content: center;
            align-items: center;
            font-size: 0.85em;
            font-weight: bold;
        }
        
        .day-cell:hover {
            background: var(--hover-bg);
            z-index: 10;
        }
        
        .day-cell.empty {
            background: transparent;
            box-shadow: none;
            cursor: default;
        }
        
        /* GRAY THEME EDIT */
        .today {
            background: #f5f5f5; /* Light Gray */
            color: #616161;      /* Dark Gray */
            box-shadow: 0 0 0 1px #616161;
        }
        
        .tooltip {
            visibility: hidden;
            background-color: #333;
            color: #fff;
            text-align: left;
            border-radius: 6px;
            padding: 8px 12px;
            position: absolute;
            z-index: 1000;
            bottom: 125%; 
            left: 50%;
            transform: translateX(-50%);
            width: max-content;
            max-width: 300px;
            opacity: 0;
            transition: opacity 0.3s;
            font-size: 0.8em;
            font-weight: normal;
            pointer-events: auto;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            white-space: normal;
        }
        
        .tooltip::after {
            content: "";
            position: absolute;
            top: 100%;
            left: 50%;
            margin-left: -5px;
            border-width: 5px;
            border-style: solid;
            border-color: #333 transparent transparent transparent;
        }
        
        .day-cell:hover .tooltip {
            visibility: visible;
            opacity: 1;
        }
        
        .entry-item {
            margin-bottom: 4px;
        }
        .entry-item:last-child {
            margin-bottom: 0;
        }

        /* GRAY THEME EDIT */
        .has-entry .day-number {
            border-bottom: 3px solid #bdbdbd; /* Medium Gray */
            padding-bottom: 2px;
            display: inline-block;
            line-height: 1.2;
        }
        
        .day-number {
             pointer-events: none;
        }
    </style>
    """
    
    html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Trading Calendar</title>
        {css}
    </head>
    <body>
        <h1>{month_name}</h1>
        <div class="calendar-grid">
            <div class="day-header">Sun</div>
            <div class="day-header">Mon</div>
            <div class="day-header">Tue</div>
            <div class="day-header">Wed</div>
            <div class="day-header">Thu</div>
            <div class="day-header">Fri</div>
            <div class="day-header">Sat</div>
    """
    
    for week in month_days:
        for day in week:
            if day == 0:
                html += '<div class="day-cell empty"></div>'
            else:
                date_str = f"{year}-{month:02d}-{day:02d}"
                entries = calendar_data.get(date_str, [])
                
                classes = "day-cell"
                if date_str == str(today): classes += " today"
                if entries: classes += " has-entry"
                
                tooltip_html = ""
                if entries:
                    content_items = []
                    for e in entries:
                        item_html = f'<div class="entry-item">{e["display"]}</div>'
                        content_items.append(item_html)
                    
                    content_html = "".join(content_items)
                    tooltip_html = f'<div class="tooltip">{content_html}</div>'
                elif day > 0:
                     tooltip_html = f'<div class="tooltip">No Info</div>'

                html += f"""
                <div class="{classes}">
                    <span class="day-number">{day}</span>
                    {tooltip_html}
                </div>
                """
                
    html += """
        </div>
    </body>
    </html>
    """
    return html

def main():
    token = os.environ.get("NOTION_TOKEN")
    # Trading Journal Database ID
    db_id = "2f90d907-031e-805c-be36-ebd342683bfa"
    
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        print("Error: NOTION_TOKEN environment variable not set.")
        sys.exit(1)
        
    print(f"Fetching Notion data for DB: {db_id}")
    raw_data = fetch_db_data(token, db_id)
    print(f"Fetched {len(raw_data)} entries.")
    
    print("Parsing data...")
    calendar_data = parse_data(raw_data)
    
    print("Generating HTML...")
    html_content = generate_html(calendar_data)
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print("index.html created successfully.")

if __name__ == "__main__":
    main()
