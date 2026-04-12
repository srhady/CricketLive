import requests
import re
import os
from datetime import datetime, timezone
from io import BytesIO
from PIL import Image

print("="*70)
print(" 🎨 CRICKETLIVE: BULLETPROOF POSTER STUDIO 🎨")
print("="*70)

# আপনার ফোল্ডারের নাম bing_posters করা হলো
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "bing_posters")

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
            print("    [!] Logo download failed. URL might be incorrect.")
            return
            
        img1 = Image.open(BytesIO(res1.content)).convert('RGBA')
        img2 = Image.open(BytesIO(res2.content)).convert('RGBA')
        
        logo_size = (250, 250)
        img1 = img1.resize(logo_size, Image.Resampling.LANCZOS)
        img2 = img2.resize(logo_size, Image.Resampling.LANCZOS)
        
        canvas = Image.new('RGBA', (800, 400), (0, 0, 0, 0))
        canvas.paste(img1, (100, 75), img1)
        canvas.paste(img2, (450, 75), img2)
        
        canvas.save(local_path, "PNG")
        print(f"    [+] Success! Saved to 'bing_posters/{match_name}.png'")

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
                # URL থেকে স্লাগ বের করা (lucknow-super-giants-vs-gujarat-titans)
                match_slug = link.split('/')[-1]
                
                # সুন্দর নাম তৈরি
                match_title = match_slug.replace('-', ' ').title().replace(" Vs ", " vs ")
                
                safe_name = sanitize_filename(match_title)
                final_filename = f"{safe_name}.png"
                local_path = os.path.join(OUTPUT_DIR, final_filename)
                active_poster_filenames.append(final_filename)
                
                print(f"\n🎯 Processing Match: {match_title}")
                
                # দ্য জিনিয়াস ট্রিক: স্লাগ থেকে সরাসরি লোগোর লিংক বানানো!
                try:
                    team1_slug, team2_slug = match_slug.split('-vs-')
                    logo1_url = f"https://images.crichd.asia/team/{team1_slug}/logo.webp"
                    logo2_url = f"https://images.crichd.asia/team/{team2_slug}/logo.webp"
                    
                    create_match_poster(match_title, logo1_url, logo2_url, local_path)
                except ValueError:
                    print(f"    [-] Could not split teams properly for {match_slug}")

        print("\n[*] Cleaning up old match posters...")
        if os.path.exists(OUTPUT_DIR):
            for file in os.listdir(OUTPUT_DIR):
                if file.endswith('.png') and file not in active_poster_filenames:
                    try:
                        os.remove(os.path.join(OUTPUT_DIR, file))
                        print(f"   [-] Deleted old poster: bing_posters/{file}")
                    except:
                        pass

    except Exception as e:
        print(f"\n[!] Critical Error: {e}")

if __name__ == "__main__":
    main()
