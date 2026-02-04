import os
import json
import urllib.request
import urllib.error
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

def fetch_assets(token, db_id):
    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    payload = { "page_size": 100 }
    data_json = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data_json, headers=headers)
    
    results = []
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                results = data.get("results", [])
    except Exception as e:
        print(f"Error fetching assets: {e}")
        
    assets = []
    for page in results:
        props = page.get("properties", {})
        
        # Item Name (Title) - Try '항목' (Korean) or 'Item' (English)
        title_list = props.get("항목", {}).get("title", [])
        if not title_list:
            title_list = props.get("Item", {}).get("title", [])
            
        if not title_list:
            # Debugging: Print keys if title not found
            # print(f"Skipping page {page['id']}: '항목' or 'Item' property not found. Keys: {list(props.keys())}")
            continue
            
        name = "".join([t.get("plain_text", "") for t in title_list])
        
        # Amount (Number) - Try '금액' or 'Amount'
        amount_obj = props.get("금액", {})
        if not amount_obj: amount_obj = props.get("Amount", {})
        amount = amount_obj.get("number", 0)
        
        # Type (Select) - Try '유형' or 'Type'
        type_obj = props.get("유형", {})
        if not type_obj: type_obj = props.get("Type", {})
        
        asset_type = type_obj.get("select", {})
        type_name = asset_type.get("name", "Other") if asset_type else "Other"
        
        assets.append({
            "name": name,
            "amount": amount,
            "type": type_name
        })
        
    return assets

def generate_html(assets):
    # Simple Notion Color Mapping
    # Notion Colors (Light Mode)
    # Gray, Brown, Orange, Yellow, Green, Blue, Purple, Pink, Red
    NOTION_COLORS = [
        "#9B9A97", # Gray
        "#E3E2E0", # Light Gray (Default)
        "#EEE0DA", # Brown
        "#FADEC9", # Orange
        "#FDECC8", # Yellow
        "#DBEDDB", # Green
        "#D3E5EF", # Blue
        "#E8DEEE", # Purple
        "#F5E0E9", # Pink
        "#FFE2DD", # Red
    ]
    
    html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Asset Allocation</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.0.0"></script>
        <style>
            ::-webkit-scrollbar {{ display: none; }}
            html {{ -ms-overflow-style: none; scrollbar-width: none; }}

            :root {{
                --bg-color: #ffffff;
                --text-color: #37352f;
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
                justify-content: center;
            }}
            .chart-container {{
                position: relative;
                width: 90vw;
                max-width: 400px;
                height: auto;
                aspect-ratio: 1 / 1;
                margin-top: 10px;
            }}
            h2 {{
                margin-top: 0; 
                margin-bottom: 0px;
                font-size: 0.9em; 
                font-weight: bold; 
                width: 100%; 
                max-width: 600px; 
                text-align: left;
                padding-bottom: 2px;
                line-height: 1.2;
            }}
            .total-assets {{
                margin-top: 4px;
                font-size: 0.85em;
                font-weight: bold;
                color: #37352f;
                font-family: "Courier New", Courier, monospace;
                line-height: 1.2;
            }}
        </style>
    </head>
    <body>
        <h2>My Assets</h2>
        <div class="total-assets" id="totalDisplay"></div>
        <div class="chart-container">
            <canvas id="assetChart"></canvas>
        </div>

        <script>
            // Register DataLabels Plugin
            Chart.register(ChartDataLabels);

            const rawData = {json.dumps(assets)};
            
            const labels = rawData.map(d => d.name);
            const data = rawData.map(d => d.amount);
            
            // Calculate Total
            const total = data.reduce((a, b) => a + b, 0);
            document.getElementById('totalDisplay').innerText = 'TOTAL: ₩' + total.toLocaleString();

            // Notion Colors
            const notionPalette = {json.dumps(NOTION_COLORS)};
            
            // Assign colors cyclically
            const bgColors = rawData.map((_, i) => notionPalette[i % notionPalette.length]);

            const ctx = document.getElementById('assetChart').getContext('2d');
            const myChart = new Chart(ctx, {{
                type: 'pie',
                data: {{
                    labels: labels,
                    datasets: [{{
                        data: data,
                        backgroundColor: bgColors,
                        borderWidth: 1,
                        borderColor: '#ffffff',
                        hoverOffset: 4
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            display: false,
                        }},
                        tooltip: {{
                            backgroundColor: '#37352f',
                            titleFont: {{ family: "'Courier New', Courier, monospace" }},
                            bodyFont: {{ family: "'Courier New', Courier, monospace" }},
                            callbacks: {{
                                label: function(context) {{
                                    let label = context.label || '';
                                    if (label) {{
                                        label += ': ';
                                    }}
                                    let value = context.raw;
                                    let percentage = Math.round((value / total) * 100) + '%';
                                    label += '₩' + value.toLocaleString() + ' (' + percentage + ')';
                                    return label;
                                }}
                            }}
                        }},
                        datalabels: {{
                            color: '#37352f',
                            labels: {{
                                name: {{
                                    align: 'top',
                                    offset: -4, // Pull closer to center (default is +4 away)
                                    font: {{
                                        family: "'Courier New', Courier, monospace",
                                        size: 9,
                                        weight: 'normal'
                                    }},
                                    formatter: function(value, context) {{
                                        let percentage = Math.round((value / total) * 100);
                                        if (percentage < 3) return null;
                                        return context.chart.data.labels[context.dataIndex];
                                    }}
                                }},
                                value: {{
                                    align: 'bottom',
                                    offset: -4, // Pull closer to center
                                    font: {{
                                        family: "'Courier New', Courier, monospace",
                                        size: 20,
                                        weight: 'bold'
                                    }},
                                    formatter: function(value, context) {{
                                        let percentage = Math.round((value / total) * 100);
                                        if (percentage < 3) return null;
                                        return percentage + '%';
                                    }}
                                }}
                            }}
                        }}
                    }},
                    layout: {{
                        padding: 0
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """
    return html

def find_asset_db(token, page_id):
    print(f"Scanning Page {page_id} for Asset DB...")
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
                data = json.loads(response.read().decode("utf-8"))
                for block in data.get("results", []):
                    if block.get("type") == "child_database":
                        title = block.get("child_database", {}).get("title", "")
                        # Check for "자산" or "Asset"
                        if "자산" in title or "Asset" in title:
                            print(f"Found Database: {title} ({block.get('id')})")
                            return block.get("id")
    except Exception as e:
        print(f"Error scanning for DB: {e}")
    return None

def main():
    token = os.environ.get("NOTION_TOKEN")
    page_id = os.environ.get("NOTION_PAGE_ID")
    
    if not token:
        print("Error: NOTION_TOKEN environment variable not set.")
        sys.exit(1)
    
    db_id = "2f90d907-031e-8105-8ed9-d2dbd48595ce" # My Assets Fallback
    
    if page_id:
        found_id = find_asset_db(token, page_id)
        if found_id:
            db_id = found_id
        else:
            print("Could not find Asset database in page. Using fallback ID.")
    else:
        print("Warning: NOTION_PAGE_ID not set. Using fallback DB ID.")
    
    print("Fetching assets...")
    assets = fetch_assets(token, db_id)
    print(f"Found {len(assets)} assets.")
    
    print("Generating chart HTML...")
    html = generate_html(assets)
    
    with open("asset_chart.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("asset_chart.html created.")

if __name__ == "__main__":
    main()
