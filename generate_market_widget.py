import yfinance as yf
import os
import sys

# Force UTF-8 encoding
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

def fetch_market_data():
    tickers = {
        "KOSPI": "^KS11",
        "KOSDAQ": "^KQ11",
        "NASDAQ": "^IXIC"
    }
    
    data = []
    
    for name, ticker_symbol in tickers.items():
        try:
            ticker = yf.Ticker(ticker_symbol)
            # fast_info is often faster and reliable for current price
            # but history(period='1d') is standard
            hist = ticker.history(period="5d")
            
            if len(hist) < 2:
                # Fallback or error
                current_price = 0
                prev_close = 0
            else:
                # Latest close
                current_price = hist['Close'].iloc[-1]
                prev_close = hist['Close'].iloc[-2]
                
            # Calculate change
            change = current_price - prev_close
            change_pct = (change / prev_close) * 100
            
            data.append({
                "name": name,
                "price": current_price,
                "change": change,
                "change_pct": change_pct
            })
            
        except Exception as e:
            print(f"Error fetching {name}: {e}")
            data.append({
                "name": name,
                "price": 0,
                "change": 0,
                "change_pct": 0
            })
            
    return data

def generate_html(market_data):
    # Korean Color Standard: Red = UP, Blue = DOWN
    css = """
    <style>
        ::-webkit-scrollbar { display: none; }
        html { -ms-overflow-style: none; scrollbar-width: none; }
        
        body {
            font-family: "Courier New", Courier, monospace;
            margin: 0;
            padding: 10px;
            background-color: #ffffff;
            color: #37352f;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        
        .market-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.9em;
            padding: 4px 0;
            border-bottom: 1px solid #f0f0f0;
        }
        .market-item:last-child {
            border-bottom: none;
        }
        
        .name {
            font-weight: bold;
            color: #37352f;
        }
        
        .price-info {
            text-align: right;
            display: flex;
            flex-direction: column;
            align-items: flex-end;
        }
        
        .price {
            font-size: 1em;
            font-weight: bold;
        }
        
        .change {
            font-size: 0.8em;
        }
        
        .up { color: #E03E3E; }   /* Red */
        .down { color: #0B6E99; } /* Blue */
        .flat { color: #999999; }
    </style>
    """
    
    items_html = ""
    for item in market_data:
        price_fmt = f"{item['price']:,.2f}"
        
        change_val = item['change']
        pct_val = item['change_pct']
        
        if change_val > 0:
            color_class = "up"
            sign = "+"
            icon = "▲"
        elif change_val < 0:
            color_class = "down"
            sign = "" # Negative number already has minus
            icon = "▼"
        else:
            color_class = "flat"
            sign = ""
            icon = "-"
            
        change_fmt = f"{icon} {sign}{change_val:,.2f} ({sign}{pct_val:.2f}%)"
        
        items_html += f"""
        <div class="market-item">
            <span class="name">{item['name']}</span>
            <div class="price-info">
                <span class="price">{price_fmt}</span>
                <span class="change {color_class}">{change_fmt}</span>
            </div>
        </div>
        """
        
    html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Market Indices</title>
        {css}
    </head>
    <body>
        {items_html}
    </body>
    </html>
    """
    return html

def main():
    print("Fetching market data...")
    try:
        data = fetch_market_data()
    except Exception as e:
        print(f"Global Error fetching data: {e}")
        data = [] # Fallback to empty

    print("Generating HTML...")
    try:
        html = generate_html(data)
        with open("market_widget.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("market_widget.html created.")
    except Exception as e:
        print(f"Error writing HTML: {e}")
        # Write minimal error file to prevent 404
        with open("market_widget.html", "w", encoding="utf-8") as f:
            f.write("<html><body>Market Data Unavailable</body></html>")

if __name__ == "__main__":
    main()
