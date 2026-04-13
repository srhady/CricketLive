import requests
import re
from datetime import datetime, timezone, timedelta

print("="*60)
print(" 🛠️ CRICHD.AT DEEP DEBUGGER 🛠️")
print("="*60)

try:
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://crichd.at/'
    })

    print("\n[1] Fetching homepage...")
    res = s.get("https://crichd.at/", timeout=15)
    print(f" -> Status Code: {res.status_code}")
    
    print("\n[2] Checking HTML snippet (First 300 chars to verify it's the real site):")
    print("-" * 40)
    print(res.text[:300].replace('\n', ' '))
    print("-" * 40)

    print("\n[3] Finding Event Blocks...")
    events = re.findall(r'<a href="(/events/[^"]+)"[^>]*>([\s\S]*?)</a>', res.text)
    print(f" -> Total Event Links Found: {len(events)}")

    print("\n[4] Time & Logic Analysis...")
    now_utc = datetime.now(timezone.utc)
    print(f" -> Current Script UTC Time: {now_utc}")

    for link, content in events:
        if "-vs-" not in link:
            continue
        
        print(f"\n   [Target] {link}")
        if "Live Now!" in content:
            print("      - Status: 'Live Now!' text found in HTML.")
        else:
            time_match = re.search(r'data-start="([^"]+)".*?data-end="([^"]+)"', content)
            if time_match:
                start_str = time_match.group(1).replace('Z', '+00:00')
                end_str = time_match.group(2).replace('Z', '+00:00')
                
                try:
                    start = datetime.fromisoformat(start_str)
                    end = datetime.fromisoformat(end_str)
                    
                    time_to_start = start - now_utc
                    minutes_to_start = time_to_start.total_seconds() / 60
                    
                    print(f"      - Match Start Time (UTC): {start}")
                    print(f"      - Minutes until start:    {minutes_to_start:.1f} mins")
                    
                    if start - timedelta(minutes=30) <= now_utc <= end:
                        print("      - VERDICT: ✅ QUALIFIES (Generating Image)")
                    else:
                        print("      - VERDICT: ❌ REJECTED (Outside 30m window)")
                except Exception as e:
                    print(f"      - Time Parse Error: {e}")
            else:
                print("      - No time data or Live text found.")

except Exception as e:
    print(f"❌ Error: {e}")
