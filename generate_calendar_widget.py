import os
import json
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

def get_number_value(prop):
    if not prop: return None
    p_type = prop.get("type")
    
    val = None
    if p_type == "number":
        val = prop.get("number")
    elif p_type == "formula":
        f_val = prop.get("formula", {})
        f_type = f_val.get("type")
        if f_type == "number":
            val = f_val.get("number")
        elif f_type == "string":
            # Try to parse string e.g. "1,000", "-500"
            s_val = f_val.get("string")
            if s_val:
                try:
                    # Remove commas and currency symbols if present (simple cleanup)
                    clean_s = s_val.replace(",", "").replace("₩", "").replace("$", "").strip()
                    val = float(clean_s)
                except:
                    val = None
                    
    return val

def parse_data(results):
    calendar_data = {}
    
    for page in results:
        props = page.get("properties", {})
        page_id = page.get("id").replace("-", "")
        
        # Find Date
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
        
        # Find Title
        title_candidates = ["종목명", "이름", "Name", "제목", "Item"]
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
        
        # P&L
        profit = 0
        loss = 0
        
        # Try to find Profit
        p_keys = ["판매수익", "Sale Profit", "수익", "Profit", "손익", "실현손익"]
        for k in p_keys:
            if k in props:
                p_val = get_number_value(props[k])
                if p_val is not None:
                    profit = p_val
                    break
                    
        # Try to find Loss
        l_keys = ["판매손실", "Sale Loss", "손실", "Loss", "손실액", "손실금액"]
        for k in l_keys:
            if k in props:
                l_val = get_number_value(props[k])
                if l_val is not None:
                    loss = l_val
                    break
        
        # Logic: If Profit is negative, treat as Loss
        if profit < 0:
            loss = abs(profit) if loss == 0 else loss + abs(profit)
            profit = 0
            
        # Icon
        icon = page.get("icon", {})
        emoji = icon.get("emoji") if icon and icon.get("type") == "emoji" else "💰"
        
        # Display String
        display_str = f"{emoji} {title}"
        details = []
        if profit > 0: details.append(f"+{profit:,}")
        if loss > 0: details.append(f"-{loss:,}")
        if details:
            display_str += f" ({' '.join(details)})"
        
        # Store in dict
        if date_str not in calendar_data:
            calendar_data[date_str] = []
            
        calendar_data[date_str].append({
            "id": page_id,
            "title": title,
            "emoji": emoji,
            "display": display_str,
            "profit": profit,
            "loss": loss
        })
        
    return calendar_data

def generate_interactive_html(calendar_data):
    # Pass data as JSON
    data_json = json.dumps(calendar_data)
    
    html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Interactive Trading Calendar</title>
        <style>
            ::-webkit-scrollbar {{ display: none; }}
            html {{ -ms-overflow-style: none; scrollbar-width: none; }}
            
            :root {{
                --bg-color: #ffffff;
                --text-color: #37352f;
                --grid-border: #e0e0e0;
                --hover-bg: #f7f7f5;
                --today-bg: #f5f5f5;
                --today-text: #616161;
                /* User specified colors */
                --profit-color: #E56458; 
                --loss-color: #3E8BD8;
            }}
            body {{
                font-family: "Courier New", Courier, monospace;
                margin: 0;
                padding: 12px 20px 20px 20px;
                background-color: var(--bg-color);
                color: var(--text-color);
                display: flex;
                flex-direction: column;
                align-items: center;
                user-select: none; /* prevent selection when clicking buttons */
            }}
            
            .header-container {{
                display: flex;
                justify-content: flex-start; /* Align left */
                align-items: center;
                gap: 15px; /* Space between title and buttons */
                width: 100%;
                max-width: 600px;
                margin-bottom: 10px;
            }}
            
            h1 {{
                margin: 0;
                font-size: 0.9em; 
                font-weight: bold; 
                text-align: left; /* Keep month left aligned if preferred, or center */
            }}
            
            .nav-btn {{
                background: none;
                border: 1px solid transparent;
                cursor: pointer;
                font-family: "Courier New", Courier, monospace;
                font-size: 0.5em; /* Adjusted to 0.5em as requested */
                color: #999;
                padding: 0 1px; /* Tighter spacing */
                border-radius: 4px;
                transition: color 0.2s, background 0.2s;
            }}
            .nav-btn:hover {{
                color: #333;
                background: #f0f0f0;
            }}
            
            .calendar-grid {{
                display: grid;
                grid-template-columns: repeat(7, 1fr);
                gap: 8px;
                width: 100%;
                max-width: 600px;
                margin-bottom: 20px;
            }}
            
            .day-header {{
                text-align: center;
                font-size: 0.8em;
                color: #999;
                padding-bottom: 8px;
            }}
            
            .day-cell {{
                aspect-ratio: 1 / 1;
                border-radius: 8px;
                background: #fff;
                box-shadow: 0 0 0 1px var(--grid-border);
                position: relative;
                cursor: pointer;
                transition: background 0.2s;
                /* Center content (Day Number) */
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 0; 
                font-size: 0.85em;
                font-weight: bold;
                /* Remove overflow: hidden so tooltip can show */
                overflow: visible;
            }}
            
            .day-cell:hover {{
                background: var(--hover-bg);
                z-index: 10;
            }}
            
            .day-cell.empty {{
                background: transparent;
                box-shadow: none;
                cursor: default;
            }}
            
            .day-cell.today {{
                background: var(--today-bg);
                color: var(--today-text);
                box-shadow: 0 0 0 1px var(--today-text);
            }}
            
            /* Entry indicator: Grey underline on the number */
            .has-entry .day-number {{
                border-bottom: 2px solid #ccc;
                padding-bottom: 0px;
            }}

            .tooltip {{
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
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                white-space: normal;
                line-height: 1.4;
            }}
            
            .tooltip::after {{
                content: "";
                position: absolute;
                top: 100%;
                left: 50%;
                margin-left: -5px;
                border-width: 5px;
                border-style: solid;
                border-color: #333 transparent transparent transparent;
            }}
            
            .day-cell:hover .tooltip {{
                visibility: visible;
                opacity: 1;
            }}
            
            .entry-item {{ margin-bottom: 2px; }}
            .entry-item:last-child {{ margin-bottom: 0; }}

            .day-number {{ 
                pointer-events: none; 
                font-size: 1.0em;
            }}
            
            .pl-text {{
                font-weight: bold;
            }}
            /* In tooltip (dark background), lighter colors might be better, 
               but user asked for Red/Blue standard. 
               Red on Dark Grey (#333) might be low contrast. 
               Let's brighten them slightly or use standard. */
            .loss {{ color: #4fc3f7; }} /* Light Blue for dark bg */
            .profit {{ color: #ff8a80; }} /* Light Red/Pink for dark bg */

            .nav-container {{
                display: flex;
                align-items: center;
                gap: 2px;
            }}

            .summary-footer {{
                width: 100%;
                max-width: 600px;
                border-top: 1px solid var(--grid-border);
                padding-top: 12px;
                display: flex;
                justify-content: space-between;
                font-size: 0.85em;
                color: #555;
            }}
            .summary-item {{
                display: flex;
                flex-direction: column;
                gap: 4px;
            }}
            .summary-label {{
                font-size: 0.9em;
                color: #999;
            }}
            .summary-value {{
                font-weight: bold;
                font-size: 1.1em;
            }}
            
            /* Footer Colors (White BG) - Use Standard */
            .summary-value.loss {{ color: var(--loss-color); }}
            .summary-value.profit {{ color: var(--profit-color); }}
            
        </style>
    </head>
    <body>
        <div class="header-container">
            <h1 id="monthLabel">Loading...</h1>
            <div class="nav-container">
                <button class="nav-btn" id="prevBtn">◀</button>
                <button class="nav-btn" id="nextBtn">▶</button>
            </div>
        </div>
        
        <div class="calendar-grid" id="calendarGrid">
            <!-- Headers and Days inserted by JS -->
        </div>

        <div class="summary-footer">
            <div class="summary-item">
                <div class="summary-label">Monthly Return</div>
                <div class="summary-value" id="monthReturn">-</div>
            </div>
            <div class="summary-item" style="text-align: right;">
                <div class="summary-label">Yearly Return</div>
                <div class="summary-value" id="yearReturn">-</div>
            </div>
        </div>

        <script>
            const eventData = {data_json};
            let currentDate = new Date(); // Defaults to today on client side

            const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

            function formatNumber(num) {{
                if (num === 0) return "0";
                const sign = num > 0 ? "+" : "-";
                return `${{sign}}${{Math.abs(num).toLocaleString()}}`;
            }}
            
            function updateSummary(year, month) {{
                // Calculate Monthly (YYYY-MM)
                let mProfit = 0;
                let mLoss = 0;
                
                // Calculate Yearly (YYYY)
                let yProfit = 0;
                let yLoss = 0;
                
                // Iterate all event keys
                for (const dateKey in eventData) {{
                    // dateKey is "YYYY-MM-DD"
                    const parts = dateKey.split("-");
                    const dYear = parseInt(parts[0]);
                    const dMonth = parseInt(parts[1]) - 1; // 0-indexed
                    
                    const entries = eventData[dateKey];
                    
                    // Yearly Accumulation
                    if (dYear === year) {{
                        entries.forEach(e => {{
                            yProfit += (e.profit || 0);
                            yLoss += (e.loss || 0);
                        }});
                        
                        // Monthly Accumulation
                        if (dMonth === month) {{
                            entries.forEach(e => {{
                                mProfit += (e.profit || 0);
                                mLoss += (e.loss || 0);
                            }});
                        }}
                    }}
                }}
                
                const mNet = mProfit - mLoss;
                const mEl = document.getElementById('monthReturn');
                mEl.innerText = formatNumber(mNet);
                mEl.className = 'summary-value ' + (mNet > 0 ? 'profit' : (mNet < 0 ? 'loss' : ''));
                
                const yNet = yProfit - yLoss;
                const yEl = document.getElementById('yearReturn');
                yEl.innerText = formatNumber(yNet);
                yEl.className = 'summary-value ' + (yNet > 0 ? 'profit' : (yNet < 0 ? 'loss' : ''));
            }}

            function renderCalendar() {{
                const year = currentDate.getFullYear();
                const month = currentDate.getMonth(); // 0-11
                
                // Update Header
                const monthName = monthNames[month];
                document.getElementById('monthLabel').innerText = `${{year}} ${{monthName}}`;
                
                // Calculate Grid
                const firstDay = new Date(year, month, 1);
                const lastDay = new Date(year, month + 1, 0); // Last day of current month
                
                const numDays = lastDay.getDate();
                const startDayOfWeek = firstDay.getDay(); // 0 (Sun) - 6 (Sat)
                
                const grid = document.getElementById('calendarGrid');
                grid.innerHTML = ''; // Clear previous
                
                // Day Headers
                const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
                days.forEach(d => {{
                    const el = document.createElement('div');
                    el.className = 'day-header';
                    el.innerText = d;
                    grid.appendChild(el);
                }});
                
                // Empty cells before start
                for (let i = 0; i < startDayOfWeek; i++) {{
                    const el = document.createElement('div');
                    el.className = 'day-cell empty';
                    grid.appendChild(el);
                }}
                
                // Days
                const today = new Date();
                const isCurrentMonth = (today.getFullYear() === year && today.getMonth() === month);
                const todayDate = today.getDate();
                
                for (let d = 1; d <= numDays; d++) {{
                    const cell = document.createElement('div');
                    cell.className = 'day-cell';
                    
                    // Check matches
                    // construct YYYY-MM-DD string with padding
                    const mStr = String(month + 1).padStart(2, '0');
                    const dStr = String(d).padStart(2, '0');
                    const dateKey = `${{year}}-${{mStr}}-${{dStr}}`;
                    
                    const entries = eventData[dateKey] || [];
                    
                    if (isCurrentMonth && d === todayDate) {{
                        cell.classList.add('today');
                    }}
                    
                    // Add day number
                    // Centered for clean look
                    const numSpan = document.createElement('span');
                    numSpan.className = 'day-number';
                    numSpan.innerText = d;
                    cell.appendChild(numSpan);
                    
                    if (entries.length > 0) {{
                        cell.classList.add('has-entry');
                        
                        // Create Tooltip
                        let tooltipContent = '';
                        
                        entries.forEach(e => {{
                            // Logic: ItemName (+Amount)
                            let amountStr = '';
                            let colorClass = '';
                            
                            if (e.loss > 0) {{
                                amountStr = `(-${{e.loss.toLocaleString()}})`;
                                colorClass = 'loss';
                            }} else if (e.profit > 0) {{
                                amountStr = `(+${{e.profit.toLocaleString()}})`;
                                colorClass = 'profit';
                            }}
                            
                            // e.title + amountStr
                            // If neither, just title
                            
                            const displayLine = amountStr ? `${{e.title}} ${{amountStr}}` : e.title;
                            tooltipContent += `<div class="entry-item ${{colorClass}}">${{displayLine}}</div>`;
                        }});
                        
                        const tooltip = document.createElement('div');
                        tooltip.className = 'tooltip';
                        tooltip.innerHTML = tooltipContent;
                        cell.appendChild(tooltip);
                    }}
                    
                    grid.appendChild(cell);
                }}
                
                // Update Summary
                updateSummary(year, month);
            }}

            // Event Listeners
            document.getElementById('prevBtn').addEventListener('click', () => {{
                currentDate.setMonth(currentDate.getMonth() - 1);
                renderCalendar();
            }});
            
            document.getElementById('nextBtn').addEventListener('click', () => {{
                currentDate.setMonth(currentDate.getMonth() + 1);
                renderCalendar();
            }});
            
            // Initial Render
            renderCalendar();
        </script>
    </body>
    </html>
    """
    return html

def main():
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        print("Error: NOTION_TOKEN environment variable not set.")
        sys.exit(1)
        
    db_id = "2f90d907-031e-805c-be36-ebd342683bfa"
    
    print(f"Fetching Trading Journal data...")
    raw_data = fetch_db_data(token, db_id)
    print(f"Fetched {len(raw_data)} entries.")
    
    print("Parsing data...")
    calendar_data = parse_data(raw_data)
    
    print("Generating Interactive HTML...")
    html_content = generate_interactive_html(calendar_data)
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print("index.html created successfully.")

if __name__ == "__main__":
    main()
