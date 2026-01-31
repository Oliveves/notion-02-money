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
    # Prepare data for Chart.js
    labels = [a["name"] for a in assets]
    data = [a["amount"] for a in assets]
    types = [a["type"] for a in assets]
    
    # Simple Color Mapping based on Type
    # We can assign colors dynamically in JS or here.
    # Let's do it in JS for a modern look (gradients or specific palettes).
    
    html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Asset Allocation</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                margin: 0;
                padding: 20px;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                background-color: #ffffff; /* Transparent or White */
                color: #37352f;
            }}
            .chart-container {{
                position: relative;
                width: 90vw;
                max-width: 400px;
                height: auto;
                aspect-ratio: 1 / 1;
            }}
            h2 {{
                margin-top: 0;
                margin-bottom: 20px;
                font-size: 1.2em;
                font-weight: 600;
            }}
            .total-assets {{
                margin-top: 15px;
                font-size: 1em;
                font-weight: bold;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <h2>Asset Allocation</h2>
        <div class="chart-container">
            <canvas id="assetChart"></canvas>
        </div>
        <div class="total-assets" id="totalDisplay"></div>

        <script>
            const rawData = {json.dumps(assets)};
            
            // Group by Type or just show all Items? User asked for "Pie Chart of Investment Funds".
            // Showing all items usually looks busy if many. 
            // Better to offer a Toggle? For now, let's show Items directly as it's likely few major accounts (Tesla, Bitcoin, Cash).
            
            const labels = rawData.map(d => d.name);
            const data = rawData.map(d => d.amount);
            const types = rawData.map(d => d.type);
            
            // Calculate Total
            const total = data.reduce((a, b) => a + b, 0);
            document.getElementById('totalDisplay').innerText = 'Total: ₩' + total.toLocaleString();

            // Colors based on Type
            const typeColors = {{
                "Stock": "#FF9500", // Orange
                "Cash": "#8E8E93",  // Gray
                "Crypto": "#007AFF", // Blue
                "Real Estate": "#FFCC00", // Yellow
                "Other": "#AF52DE"   // Purple
            }};
            
            const bgColors = rawData.map(d => typeColors[d.type] || "#CCCCCC");

            const ctx = document.getElementById('assetChart').getContext('2d');
            const myChart = new Chart(ctx, {{
                type: 'doughnut', // Doughnut looks more modern than simple Pie
                data: {{
                    labels: labels,
                    datasets: [{{
                        data: data,
                        backgroundColor: bgColors,
                        borderWidth: 0,
                        hoverOffset: 10
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            position: 'bottom',
                            labels: {{
                                padding: 20,
                                usePointStyle: true,
                                font: {{
                                    size: 11
                                }}
                            }}
                        }},
                        tooltip: {{
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
                        }}
                    }},
                    cutout: '60%', // Doughnut thickness
                    layout: {{
                        padding: 10
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
