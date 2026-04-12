import requests
import re
import os
from datetime import datetime, timezone
from io import BytesIO
from PIL import Image

print("="*75)
print(" 🏏 CRICKETLIVE: 1080x810 MAX LOGO POSTER STUDIO 🏏")
print("="*75)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "posters")

os.makedirs(OUTPUT_DIR, exist_ok=True)

s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def create_max_logo_poster(match_name, logo1_url, logo2_url, local_path):
    if os.path.exists(local_path):
        print(f"    [=] Poster already exists: {match_name}.png")
        return

    try:
        print(f"    [*] Generating 1080x810 PNG for: {match_name}...")
        res1 = s.get(logo1_url, timeout=10)
        res2 = s.get(logo2_url, timeout=10)
        
        if res1.status_code != 200 or res2.status_code != 200:
            print("    [!] Logo download failed. URL might be incorrect.")
            return
            
        img1 = Image.open(BytesIO(res1.content)).convert('RGBA')
        img2 = Image.open(BytesIO(res2.content)).convert('RGBA')
        
        # === ১০৮০x৮১০ ফিক্সড ক্যানভাস লজিক ===
        canvas_width = 1080
        canvas_height = 810
        canvas = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))
        
        # লোগো ম্যাক্সিমাম কতটা বড় হতে পারবে (অর্ধেক ক্যানভাসের চেয়ে একটু কম)
        max_logo_w = 480
        max_logo_h = 750
        
        # Aspect ratio ঠিক রেখে লোগো বড় করা
        img1.thumbnail((max_logo_w, max_logo_h), Image.Resampling.LANCZOS)
        img2.thumbnail((max_logo_w, max_logo_h), Image.Resampling.LANCZOS)
        
        # লোগোগুলোকে একদম সেন্টারে বসানোর ক্যালকুলেশন
        # বাম দিকের লোগোর সেন্টার (270, 405)
        x1 = 270 - (img1.width // 2)
        y1 = 405 - (img1.height // 2)
        
        # ডান দিকের লোগোর সেন্টার (810, 405)
        x2 = 810 - (img2.width // 2)
        y2 = 405 - (img2.height // 2)
        
        # ক্যানভাসে লোগো বসানো
        canvas.paste(img1, (x1, y1), img1)
        canvas.paste(img2, (x2, y2), img2)
        
        # === ১০০ কেবি এর নিচে রাখার লজিক ===
        quantized_canvas = canvas.convert('P', palette=Image.Palette.ADAPTIVE, colors=256)
        
        quantized_canvas.save(local_path, "PNG", optimize=True)
        file_size_kb = os.path.getsize(local_path) / 1024
        
        # ডাবল চেক সাইজ অপ্টিমাইজেশন
        if file_size_kb > 100:
             quantized_canvas.save(local_path, "PNG", optimize=True, compress_level=9)
             file_size_kb = os.path.getsize(local_path) / 1024
             
        print(f"    [+] Success! Saved to 'posters/{match_name}.png' ({file_size_kb:.1f} KB)")

    except Exception as e:
        print(f"    [!] Error processing '{match_name}': {e}")

def main():
    try:
        print(f"\n[+] Scanning CricHD Homepage for Live/Upcoming matches...")
        home_html = s.get("https://crichd.asia/", timeout=10).text
        event_blocks = re.findall(r'<a[^>]+href="(/events/[^"]+)"[^>]*>([\s\S]*?)</a>', home_html)
        
        active_poster_filenames = []
        now_utc = datetime.now(timezone.utc)
        
        for link, content in event_blocks:
            if "-vs-" not in link or "Ended" in content:
                continue
                
            time_match = re.search(r'data-countdown="([^"]+)"', content)
            if not time_match:
                continue
                
            match_time = datetime.strptime(time_match.group(1), "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
            
            if (match_time - now_utc).total_seconds() <= 1800:
                match_slug = link.split('/')[-1]
                match_title = match_slug.replace('-', ' ').title().replace(" Vs ", " vs ")
                
                safe_name = sanitize_filename(match_title)
                final_filename = f"{safe_name}.png"
                local_path = os.path.join(OUTPUT_DIR, final_filename)
                active_poster_filenames.append(final_filename)
                
                print(f"\n🎯 Processing Match: {match_title}")
                
                try:
                    team1_slug, team2_slug = match_slug.split('-vs-')
                    logo1_url = f"https://images.crichd.asia/team/{team1_slug}/logo.webp"
                    logo2_url = f"https://images.crichd.asia/team/{team2_slug}/logo.webp"
                    
                    create_max_logo_poster(match_title, logo1_url, logo2_url, local_path)
                except ValueError:
                    print(f"    [-] Could not split teams properly for {match_slug}")

        print("\n[*] Cleaning up old match posters...")
        if os.path.exists(OUTPUT_DIR):
            for file in os.listdir(OUTPUT_DIR):
                if file.endswith('.png') and file not in active_poster_filenames:
                    try:
                        os.remove(os.path.join(OUTPUT_DIR, file))
                        print(f"   [-] Deleted old poster: posters/{file}")
                    except:
                        pass

    except Exception as e:
        print(f"\n[!] Critical Error: {e}")

if __name__ == "__main__":
    main()
