import sys
import os
import json
from unittest.mock import MagicMock, patch

# Mock the environment variables and dependencies
os.environ["NOTION_TOKEN"] = "fake_token"
sys.modules["urllib.request"] = MagicMock()

def test_calendar_generation():
    print("1. Syntax Check: Importing generate_calendar_widget...")
    try:
        import generate_calendar_widget
    except SyntaxError as e:
        print(f"❌ Syntax Error: {e}")
        return False
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error during import: {e}")
        return False
    
    print("✅ Syntax Check Passed")

    print("2. Runtime Check: Generating HTML with mock data...")
    try:
        # Create mock data complying with the expected structure
        mock_data = {
            "2026-01-01": [
                {"id": "test", "title": "Test Trade", "emoji": "💰", "profit": 1000, "loss": 0, "display": "Test"}
            ]
        }
        
        # Call the generation function
        html = generate_calendar_widget.generate_interactive_html(mock_data)
        
        if len(html) > 0 and "<!DOCTYPE html" in html:
            print(f"✅ HTML Generation Passed ({len(html)} bytes generated)")
        else:
            print("❌ HTML Generation Failed (Empty output)")
            return False
            
    except Exception as e:
        print(f"❌ Runtime Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    if test_calendar_generation():
        print("\n🎉 ALL CHECKS PASSED. Safe to push.")
        sys.exit(0)
    else:
        print("\n⛔ CHECKS FAILED. Do not push.")
        sys.exit(1)
