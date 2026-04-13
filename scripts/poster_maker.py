import requests
import re
import os
from datetime import datetime, timezone, timedelta
from io import BytesIO
from PIL import Image

print("="*75)
print(" 🏏 CRICKETLIVE: 1080x810 AUTO-CROP GIANT LOGO STUDIO (NEW CRICHD) 🏏")
print("="*75)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "posters")

os.makedirs(OUTPUT_DIR, exist_ok=True)

s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://crichd.at/'
})

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def auto_crop_and_resize(img, max_w, max_h):
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
        
    ratio = min(max_w / img.width, max_h / img.height)
    new_w = int(img.width * ratio)
    new_h = int(img.height * ratio)
    return img.resize((new_w, new_h), Image.Resampling.LANCZOS)

def create_max_logo_poster(match_name, logo1_url, logo2_url, local_path):
    try:
        print(f"    [*] Generating 1080x810 PNG for: {match_name}...")
        
        # ওরা থাম্বনেইল দেয়, আমরা হাই-রেজুলেশন লোগো বের করার চেষ্টা করবো
        high_res1 = re.sub(r'___preview_thumbnail_\d+_\d+', '', logo1_url)
        high_res2 = re.sub(r'___preview_thumbnail_\d+_\d+', '', logo2_url)
        
        res1 = s.get(high_res1, timeout=10)
        if res1.status_code != 200:
            res1 = s.get(logo1_url, timeout=10) # ফেইল করলে অরিজিনাল থাম্বনেইল
            
        res2 = s.get(high_res2, timeout=10)
        if res2.status_code != 200:
            res2 = s.get(logo2_url, timeout=10) # ফেইল করলে অরিজিনাল থাম্বনেইল
        
        if res1.status_code != 200 or res2.status_code != 200:
            print("    [!] Logo download failed. URL might be blocked.")
            return
            
        img1 = Image.open(BytesIO(res1.content)).convert('RGBA')
        img2 = Image.open(BytesIO(res2.content)).convert('RGBA')
        
        # === ১০৮০x৮১০ ফিক্সড ক্যানভাস ===
        canvas_width = 1080
        canvas_height = 810
        canvas = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))
        
        img1 = auto_crop_and_resize(img1, 480, 600)
        img2 = auto_crop_and_resize(img2, 480, 600)
        
        x1 = 270 - (img1.width // 2)
        y1 = 405 - (img1.height // 2)
        
        x2 = 810 - (img2.width // 2)
        y2 = 405 - (img2.height // 2)
        
        canvas.paste(img1, (x1, y1), img1)
        canvas.paste(img2, (x2, y2), img2)
        
        # === ১০০ কেবি এর নিচে রাখার লজিক ===
        quantized_canvas = canvas.convert('P', palette=Image.Palette.ADAPTIVE, colors=256)
        quantized_canvas.save(local_path, "PNG", optimize=True)
        
        file_size_kb = os.path.getsize(local_path) / 1024
        print(f"    [+] Success! Saved to 'posters/{match_name}.png' ({file_size_kb:.1f} KB)")

    except Exception as e:
        print(f"    [!] Error processing '{match_name}': {e}")

def main():
    try:
        print(f"\n[+] Scanning NEW CricHD (crichd.at) Homepage for matches...")
        home_html = s.get("https://crichd.at/", timeout=10).text
        
        events = re.findall(r'<a href="(/events/[^"]+)"[^>]*>([\s\S]*?)</a>', home_html)
        
        active_poster_filenames = []
        now_utc = datetime.now(timezone.utc)
        
        for link, content in events:
            if "-vs-" not in link:
                continue # লিগ বা টুর্নামেন্টের ফালতু পেজগুলো স্কিপ করবে
                
            # নতুন ওয়েবসাইটের টাইম লজিক চেক
            is_valid = False
            if "Live Now!" in content:
                is_valid = True
            else:
                time_match = re.search(r'data-start="([^"]+)".*?data-end="([^"]+)"', content)
                if time_match:
                    try:
                        start = datetime.fromisoformat(time_match.group(1).replace('Z', '+00:00'))
                        end = datetime.fromisoformat(time_match.group(2).replace('Z', '+00:00'))
                        # ম্যাচ শুরুর ৩০ মিনিট আগে থেকে শেষ পর্যন্ত পোস্টার জেনারেট হবে
                        if start - timedelta(minutes=30) <= now_utc <= end:
                            is_valid = True
                    except:
                        pass
                        
            if is_valid:
                match_slug = link.split('/')[-1]
                match_title = match_slug.replace('-', ' ').title().replace(" Vs ", " vs ")
                
                safe_name = sanitize_filename(match_title)
                final_filename = f"{safe_name}.png"
                local_path = os.path.join(OUTPUT_DIR, final_filename)
                active_poster_filenames.append(final_filename)
                
                print(f"\n🎯 Processing Match: {match_title}")
                
                # HTML ব্লক থেকে সরাসরি .webp লোগোর লিংকগুলো বের করে নেওয়া
                images = re.findall(r'<img\s+src="([^"]+\.webp)"', content, re.IGNORECASE)
                
                # সাধারণত ব্লকের শেষের দিকে দুইটা টিমের লোগো থাকে, তাই শেষের দুইটা পিক করা হলো
                if len(images) >= 2:
                    logo1_url = images[-2]
                    logo2_url = images[-1]
                    
                    if logo1_url.startswith('/'): logo1_url = f"https://crichd.at{logo1_url}"
                    if logo2_url.startswith('/'): logo2_url = f"https://crichd.at{logo2_url}"
                    
                    create_max_logo_poster(match_title, logo1_url, logo2_url, local_path)
                else:
                    print(f"    [-] Could not find .webp team logos for {match_slug}")

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
