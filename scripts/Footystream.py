import requests
import re
import os
from datetime import datetime, timezone, timedelta
from io import BytesIO
from PIL import Image

print("="*75)
print(" ⚽ FOOTYSTREAM: 1080x810 AUTO-CROP GIANT LOGO STUDIO ⚽")
print("="*75)

# ফোল্ডার সেটআপ
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "posters")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# সেশন এবং হেডার সেটআপ
s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://footystream.pk/'
})

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def auto_crop_and_resize(img, max_w, max_h):
    # চারপাশের ফালতু ট্রান্সপারেন্ট অংশ কেটে ফেলা (Auto-crop)
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
        
    # রেশিও ঠিক রেখে রিসাইজ করা (Lanczos filter for best quality)
    ratio = min(max_w / img.width, max_h / img.height)
    new_w = int(img.width * ratio)
    new_h = int(img.height * ratio)
    return img.resize((new_w, new_h), Image.Resampling.LANCZOS)

def create_max_logo_poster(match_name, logo1_url, logo2_url, local_path):
    try:
        # লোগো লিংকগুলো যদি relative হয়, তবে ডোমেইন জোড়া লাগানো
        if not logo1_url.startswith('http'): logo1_url = "https://footystream.pk" + logo1_url
        if not logo2_url.startswith('http'): logo2_url = "https://footystream.pk" + logo2_url
            
        res1 = s.get(logo1_url, timeout=10)
        res2 = s.get(logo2_url, timeout=10)
        
        if res1.status_code != 200 or res2.status_code != 200:
            print("    [!] Logo download failed.")
            return
            
        img1 = Image.open(BytesIO(res1.content)).convert('RGBA')
        img2 = Image.open(BytesIO(res2.content)).convert('RGBA')
        
        # 1080x810 সাইজের খালি ট্রান্সপারেন্ট ক্যানভাস
        canvas = Image.new('RGBA', (1080, 810), (0, 0, 0, 0))
        
        # লোগোগুলোকে সর্বোচ্চ 480x600 সাইজে বড় করা
        img1 = auto_crop_and_resize(img1, 480, 600)
        img2 = auto_crop_and_resize(img2, 480, 600)
        
        # দুই পাশে সেন্টার পজিশন ক্যালকুলেট করা (প্রথম লোগো বামে, দ্বিতীয় লোগো ডানে)
        x1 = 270 - (img1.width // 2)
        y1 = 405 - (img1.height // 2)
        x2 = 810 - (img2.width // 2)
        y2 = 405 - (img2.height // 2)
        
        # ক্যানভাসে লোগো বসানো
        canvas.paste(img1, (x1, y1), img1)
        canvas.paste(img2, (x2, y2), img2)
        
        # সাইজ কমানোর জন্য 256 কালারে Quantize করা (100 KB এর নিচে রাখার ম্যাজিক)
        quantized_canvas = canvas.convert('P', palette=Image.Palette.ADAPTIVE, colors=256)
        quantized_canvas.save(local_path, "PNG", optimize=True)
        
        file_size_kb = os.path.getsize(local_path) / 1024
        print(f"    [+] Success! Saved: 'posters/{os.path.basename(local_path)}' ({file_size_kb:.1f} KB)")

    except Exception as e:
        print(f"    [!] Error processing '{match_name}': {e}")

def main():
    try:
        print(f"\n[+] Scanning Footystream (footystream.pk)...")
        home_url = "https://footystream.pk/"
        home_html = s.get(home_url, timeout=15).text
        
        # <a> ট্যাগগুলো আলাদা করা যেগুলো /events/ দিয়ে শুরু
        events = re.findall(r'<a[^>]*href=["\'](?:https://footystream\.pk)?/events/([^"\']+)["\'][^>]*>([\s\S]*?)</a>', home_html, re.IGNORECASE)
        
        active_poster_filenames = []
        now_utc = datetime.now(timezone.utc)
        
        for slug, content in events:
            # যদি লিংকটায় "vs" না থাকে, তবে সেটা কোনো টিম ভার্সেস টিম ম্যাচ না (যেমন: F1 বা Snooker)
            if "-vs-" not in slug:
                continue
                
            is_valid = False
            
            # টাইম বের করা
            start_match = re.search(r'data-start=["\']([^"\']+)["\']', content)
            end_match = re.search(r'data-end=["\']([^"\']+)["\']', content)
            
            if start_match and end_match:
                try:
                    # '2026-04-13T18:45:00.000Z' এই ফরম্যাটকে ডিকোড করা
                    start_time_str = start_match.group(1)
                    start = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
                    end = datetime.strptime(end_match.group(1), "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
                    
                    # ম্যাচ শুরুর ৩০ মিনিট আগে থেকে শেষ পর্যন্ত ছবি বানাবে
                    if start - timedelta(minutes=30) <= now_utc <= end:
                        is_valid = True
                except Exception as e:
                    pass
                        
            if is_valid:
                # দলের নাম বের করা (flex gap-2 items-center ক্লাসের ভেতর থাকে)
                team_matches = re.findall(r'<div[^>]*class=["\'][^"\']*flex gap-2 items-center[^"\']*["\'][^>]*>([\s\S]*?)</div>', content)
                
                teams = []
                images = []
                
                for tm in team_matches:
                    # দলের নাম এক্সট্রাক্ট করা (HTML ট্যাগ মুছে ফেলা)
                    team_name = re.sub(r'<[^>]+>', '', tm).strip()
                    if team_name: teams.append(team_name)
                    
                    # লোগোর লিংক এক্সট্রাক্ট করা
                    img_match = re.search(r'<img[^>]*src=["\']([^"\']+)["\']', tm, re.IGNORECASE)
                    if img_match: images.append(img_match.group(1))

                if len(teams) >= 2 and len(images) >= 2:
                    match_title = f"{teams[0]} vs {teams[1]}"
                    safe_name = sanitize_filename(match_title)
                    final_filename = f"{safe_name}.png"
                    local_path = os.path.join(OUTPUT_DIR, final_filename)
                    
                    active_poster_filenames.append(final_filename)
                    
                    print(f"\n🎯 Processing Match: {match_title}")
                    
                    # যদি ছবি আগে থেকেই বানানো থাকে, তবে আবার বানাবো না (CPU বাঁচানো)
                    if os.path.exists(local_path):
                        print(f"    [*] Poster already exists. Skipping.")
                    else:
                        create_max_logo_poster(match_title, images[0], images[1], local_path)
                else:
                    print(f"\n    [-] Could not find team names or logos for '{slug}'")

        print("\n[*] Cleaning up old match posters...")
        if os.path.exists(OUTPUT_DIR):
            for file in os.listdir(OUTPUT_DIR):
                if file.endswith('.png') and file not in active_poster_filenames:
                    try:
                        os.remove(os.path.join(OUTPUT_DIR, file))
                        print(f"   [-] Deleted old poster: posters/{file}")
                    except Exception as e:
                        print(f"   [!] Failed to delete {file}: {e}")

    except Exception as e:
        print(f"\n[!] Critical Error: {e}")

if __name__ == "__main__":
    main()
