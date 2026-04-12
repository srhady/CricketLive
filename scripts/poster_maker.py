import requests
import re
import os
from datetime import datetime, timezone
from io import BytesIO
from PIL import Image

print("="*70)
print(" 🎨 CRICKETLIVE: CLEAN FOLDER POSTER STUDIO 🎨")
print("="*70)

# পাথ ডাইনামিক করা হলো যাতে স্ক্রিপ্ট scripts/ ফোল্ডারে থাকলেও ছবিগুলো রুট ডিরেক্টরিতে যায়
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "posters")

os.makedirs(OUTPUT_DIR, exist_ok=True)

s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def create_match_poster(match_name, logo1_url, logo2_url, local_path):
    if os.path.exists(local_path):
        print(f"    [=] Poster already exists: {match_name}.png")
        return

    try:
        print(f"    [*] Generating PNG for: {match_name}...")
        res1 = s.get(logo1_url, timeout=10)
        res2 = s.get(logo2_url, timeout=10)
        
        if res1.status_code != 200 or res2.status_code != 200:
            print("    [!] Logo download failed.")
            return
            
        img1 = Image.open(BytesIO(res1.content)).convert('RGBA')
        img2 = Image.open(BytesIO(res2.content)).convert('RGBA')
        
        logo_size = (250, 250)
        img1 = img1.resize(logo_size, Image.Resampling.LANCZOS)
        img2 = img2.resize(logo_size, Image.Resampling.LANCZOS)
        
        # 800x400 সাইজের ট্রান্সপারেন্ট ক্যানভাস
        canvas = Image.new('RGBA', (800, 400), (0, 0, 0, 0))
        canvas.paste(img1, (100, 75), img1)
        canvas.paste(img2, (450, 75), img2)
        
        canvas.save(local_path, "PNG")
        print(f"    [+] Success! Saved to 'posters/{match_name}.png'")

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
            
            # ৩০ মিনিটের ফিল্টার
            if (match_time - now_utc).total_seconds() <= 1800:
                match_title = link.split('/')[-1].replace('-', ' ').title().replace(" Vs ", " vs ")
                
                safe_name = sanitize_filename(match_title)
                final_filename = f"{safe_name}.png"
                local_path = os.path.join(OUTPUT_DIR, final_filename)
                active_poster_filenames.append(final_filename)
                
                print(f"\n🎯 Extracting Logos for: {match_title}")
                event_html = s.get(f"https://crichd.asia{link}", timeout=10).text
                
                logos = re.findall(r'<img alt="[^"]+"[^>]+src="(https://images\.crichd\.asia/team/[^"]+/logo\.webp)"', event_html)
                unique_logos = list(dict.fromkeys(logos))
                
                if len(unique_logos) >= 2:
                    create_match_poster(match_title, unique_logos[0], unique_logos[1], local_path)
                else:
                    print(f"    [-] Couldn't find both team logos for {match_title}")

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
