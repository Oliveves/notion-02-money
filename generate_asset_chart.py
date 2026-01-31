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
        
        # Item Name
        title_list = props.get("Item", {}).get("title", [])
        if not title_list: continue
        name = "".join([t.get("plain_text", "") for t in title_list])
        
        # Amount
        amount = props.get("Amount", {}).get("number", 0)
        
        # Type
        asset_type = props.get("Type", {}).get("select", {})
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
                margin-bottom: 2px;
                font-size: 0.9em; 
                font-weight: bold; 
                width: 100%; 
                max-width: 600px; 
                text-align: left;
                padding-bottom: 8px;
            }}
            .total-assets {{
                margin-top: 20px;
                font-size: 0.85em;
                font-weight: bold;
                color: #37352f;
                font-family: "Courier New", Courier, monospace;
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
                            font: {{
                                family: "'Courier New', Courier, monospace",
                                weight: 'bold',
                                size: 12
                            }},
                            formatter: function(value, context) {{
                                let percentage = Math.round((value / total) * 100);
                                if (percentage < 3) return null; // Hide labels for very small slices
                                return context.chart.data.labels[context.dataIndex] + '\\n' + percentage + '%';
                            }},
                            align: 'center',
                            anchor: 'center',
                            textAlign: 'center'
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

def main():
    token = os.environ.get("NOTION_TOKEN", "ntn_I3641115422aw21TI9L4EKCf7Cwt6bPS5Exy3b7cxpU9Oh")
    db_id = "2f90d907-031e-8105-8ed9-d2dbd48595ce" # My Assets
    
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
