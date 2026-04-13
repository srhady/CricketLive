import requests
import re
import os
from datetime import datetime, timezone, timedelta
from io import BytesIO
from PIL import Image

print("="*75)
print(" ⚽ FOOTYSTREAM: 1080x810 GIANT LOGO STUDIO (ROOT FOLDER MODE) ⚽")
print("="*75)

# ফোল্ডার সেটআপ: scripts ফোল্ডার থেকে এক ধাপ পেছনে গিয়ে footy_posters ফোল্ডার ধরা
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "footy_posters")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# সেশন সেটআপ
s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Referer': 'https://footystream.pk/'
})

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def auto_crop_and_resize(img, max_w, max_h):
    # অটো ক্রপ (ফালতু ট্রান্সপারেন্ট অংশ বাদ দেওয়া)
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
        
    # হাই কোয়ালিটি রিসাইজ
    ratio = min(max_w / img.width, max_h / img.height)
    new_w = int(img.width * ratio)
    new_h = int(img.height * ratio)
    return img.resize((new_w, new_h), Image.Resampling.LANCZOS)

def create_max_logo_poster(match_name, logo1_url, logo2_url, local_path):
    try:
        if not logo1_url.startswith('http'): logo1_url = "https://footystream.pk" + logo1_url
        if not logo2_url.startswith('http'): logo2_url = "https://footystream.pk" + logo2_url
            
        res1 = s.get(logo1_url, timeout=15)
        res2 = s.get(logo2_url, timeout=15)
        
        if res1.status_code != 200 or res2.status_code != 200:
            return False
            
        img1 = Image.open(BytesIO(res1.content)).convert('RGBA')
        img2 = Image.open(BytesIO(res2.content)).convert('RGBA')
        
        # ১০৮০x৮১০ ক্যানভাস
        canvas = Image.new('RGBA', (1080, 810), (0, 0, 0, 0))
        
        img1 = auto_crop_and_resize(img1, 480, 600)
        img2 = auto_crop_and_resize(img2, 480, 600)
        
        # পজিশনিং
        canvas.paste(img1, (270 - (img1.width // 2), 405 - (img1.height // 2)), img1)
        canvas.paste(img2, (810 - (img2.width // 2), 405 - (img2.height // 2)), img2)
        
        # ২৫৬ কালার অপ্টিমাইজেশন (আন্ডার ১০০ কেবি)
        quantized = canvas.convert('P', palette=Image.Palette.ADAPTIVE, colors=256)
        quantized.save(local_path, "PNG", optimize=True)
        
        print(f"    [+] Saved: {os.path.basename(local_path)} ({os.path.getsize(local_path)/1024:.1f} KB)")
        return True

    except Exception as e:
        print(f"    [!] Poster Error: {e}")
        return False

def main():
    try:
        print(f"\n[+] Scanning Footystream.pk...")
        home_html = s.get("https://footystream.pk/", timeout=20).text
        
        # ইভেন্ট লিংক এবং কন্টেন্ট খুঁজে বের করা
        events = re.findall(r'<a[^>]*href=["\'](?:https://footystream\.pk)?/events/([^"\']+)["\'][^>]*>([\s\S]*?)</a>', home_html, re.IGNORECASE)
        
        active_poster_filenames = []
        now_utc = datetime.now(timezone.utc)
        
        for slug, content in events:
            if "-vs-" not in slug: continue
                
            is_valid = False
            start_match = re.search(r'data-start=["\']([^"\']+)["\']', content)
            end_match = re.search(r'data-end=["\']([^"\']+)["\']', content)
            
            if start_match and end_match:
                try:
                    start = datetime.strptime(start_match.group(1), "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
                    end = datetime.strptime(end_match.group(1), "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
                    
                    # ৩০ মিনিট আপকামিং অথবা রানিং ম্যাচ
                    if start - timedelta(minutes=30) <= now_utc <= end:
                        is_valid = True
                except: continue
                        
            if is_valid:
                # লোগো এবং নাম এক্সট্রাক্ট
                team_matches = re.findall(r'<div[^>]*class=["\'][^"\']*flex gap-2 items-center[^"\']*["\'][^>]*>([\s\S]*?)</div>', content)
                teams = []
                images = []
                
                for tm in team_matches:
                    team_name = re.sub(r'<[^>]+>', '', tm).strip()
                    if team_name: teams.append(team_name)
                    img_match = re.search(r'<img[^>]*src=["\']([^"\']+)["\']', tm, re.IGNORECASE)
                    if img_match: images.append(img_match.group(1))

                if len(teams) >= 2 and len(images) >= 2:
                    match_title = f"{teams[0]} vs {teams[1]}"
                    safe_name = sanitize_filename(match_title)
                    final_filename = f"{safe_name}.png"
                    local_path = os.path.join(OUTPUT_DIR, final_filename)
                    active_poster_filenames.append(final_filename)
                    
                    if not os.path.exists(local_path):
                        print(f"\n🎯 Generating for: {match_title}")
                        create_max_logo_poster(match_title, images[0], images[1], local_path)
                    else:
                        print(f"    [*] Skip: {match_title} (Exists)")

        # অটো-ক্লিনআপ
        print("\n[*] Cleaning up old posters in footy_posters/...")
        if os.path.exists(OUTPUT_DIR):
            for file in os.listdir(OUTPUT_DIR):
                if file.endswith('.png') and file not in active_poster_filenames:
                    try:
                        os.remove(os.path.join(OUTPUT_DIR, file))
                        print(f"   [-] Deleted: {file}")
                    except: pass

    except Exception as e:
        print(f"\n[!] Critical Error: {e}")

if __name__ == "__main__":
    main()
