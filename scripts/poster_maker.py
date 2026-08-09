import requests
import re
import os
import time
from io import BytesIO
from PIL import Image

print("="*75)
print(" 🏏 CRICKETLIVE: 1080x810 AUTO-CROP GIANT LOGO STUDIO 🏏")
print(" 🌐 Source: Cricbuzz API (Upcoming, Live & Recent) 🌐")
print(" 🎨 Background: Solid Light Gray (#F0F0F0) 🎨")
print("="*75)

# Navigate out of the 'scripts' folder to the root directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "posters")

os.makedirs(OUTPUT_DIR, exist_ok=True)

s = requests.Session()
s.headers.update({
    'accept': '*/*',
    'accept-language': 'en-US',
    'content-type': 'application/json',
    'priority': 'u=1, i',
    'referer': 'https://www.cricbuzz.com/',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.7727.56 Safari/537.36'
})

def sanitize_filename(name):
    """Removes invalid characters for Windows/Linux filenames"""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def generate_cricbuzz_logo_url(image_id, team_name):
    """Generates logo URL based on Cricbuzz format"""
    slug = re.sub(r'\s+', '-', team_name).lower()
    return f"https://static.cricbuzz.com/a/img/v1/0x0/i1/c{image_id}/{slug}.jpg"

def auto_crop_and_resize(img, max_w, max_h):
    """Crops empty spaces around logo and resizes to specific dimension"""
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
        
    ratio = min(max_w / img.width, max_h / img.height)
    new_w = int(img.width * ratio)
    new_h = int(img.height * ratio)
    return img.resize((new_w, new_h), Image.Resampling.LANCZOS)

def create_max_logo_poster(match_name, logo1_url, logo2_url, local_path):
    """Creates a 1080x810 poster with both team logos on a solid light gray background"""
    try:
        print(f"    [*] Generating PNG for: {match_name}...")
        
        # Logo download
        res1 = requests.get(logo1_url, timeout=10)
        res2 = requests.get(logo2_url, timeout=10)
        
        if res1.status_code != 200 or res2.status_code != 200:
            print("    [!] Logo download failed. Skipping...")
            return
            
        img1 = Image.open(BytesIO(res1.content)).convert('RGBA')
        img2 = Image.open(BytesIO(res2.content)).convert('RGBA')
        
        # CHANGE HERE: Set canvas to solid light gray (#F0F0F0) instead of transparent
        # Color tuple is (Red, Green, Blue, Alpha). 255 is full opacity.
        canvas = Image.new('RGBA', (1080, 810), (240, 240, 240, 255))
        
        img1 = auto_crop_and_resize(img1, 480, 600)
        img2 = auto_crop_and_resize(img2, 480, 600)
        
        # Position calculation
        x1 = 270 - (img1.width // 2)
        y1 = 405 - (img1.height // 2)
        x2 = 810 - (img2.width // 2)
        y2 = 405 - (img2.height // 2)
        
        canvas.paste(img1, (x1, y1), img1)
        canvas.paste(img2, (x2, y2), img2)
        
        # Optimization & Save
        quantized_canvas = canvas.convert('P', palette=Image.Palette.ADAPTIVE, colors=256)
        quantized_canvas.save(local_path, "PNG", optimize=True)
        
        print(f"    [+] Success! Saved to 'posters/{match_name}.png' ({os.path.getsize(local_path)/1024:.1f} KB)")

    except Exception as e:
        print(f"    [!] Error processing '{match_name}': {e}")

def main():
    try:
        print(f"\n[+] Fetching matches from Cricbuzz API...")
        
        api_url = "https://www.cricbuzz.com/api/home"
        response = s.get(api_url, timeout=15)
        
        if response.status_code != 200:
            print(f"[!] API Request Failed with status: {response.status_code}")
            return
            
        data = response.json()
        matches = data.get("matches", [])
        
        active_poster_filenames = []
        
        # Current time in milliseconds
        now_ms = int(time.time() * 1000)
        
        # Time limits in milliseconds (3 hours before start to 1 hour after end)
        THREE_HOURS_MS = 3 * 60 * 60 * 1000
        ONE_HOUR_MS = 1 * 60 * 60 * 1000
        
        for item in matches:
            match_info = item.get("match", {}).get("matchInfo", {})
            
            start_time = match_info.get("startDate", 0)
            # Default fallback for end_time if missing (start_time + 4 hours)
            end_time = match_info.get("endDate", start_time + (4 * 60 * 60 * 1000)) 
            
            is_valid_match = False
            
            # Check if current time is within [start - 3h] to [end + 1h]
            if start_time and end_time:
                if (start_time - THREE_HOURS_MS) <= now_ms <= (end_time + ONE_HOUR_MS):
                    is_valid_match = True
            
            if is_valid_match:
                team1 = match_info.get("team1", {})
                team2 = match_info.get("team2", {})
                
                t1_name = team1.get("teamName", "")
                t2_name = team2.get("teamName", "")
                t1_id = team1.get("imageId")
                t2_id = team2.get("imageId")
                
                if not (t1_name and t2_name and t1_id and t2_id):
                    continue
                
                match_title = f"{t1_name} vs {t2_name}"
                safe_name = sanitize_filename(match_title)
                final_filename = f"{safe_name}.png"
                local_path = os.path.join(OUTPUT_DIR, final_filename)
                
                active_poster_filenames.append(final_filename)
                
                match_state = match_info.get("state", "Unknown")
                print(f"\n🎯 Processing Match [{match_state}]: {match_title}")
                
                # Check if poster already exists to prevent unnecessary API calls/re-rendering
                if not os.path.exists(local_path):
                    logo1 = generate_cricbuzz_logo_url(t1_id, t1_name)
                    logo2 = generate_cricbuzz_logo_url(t2_id, t2_name)
                    create_max_logo_poster(match_title, logo1, logo2, local_path)
                else:
                    print(f"    [-] Poster already exists. Skipping generation.")

        # Auto-cleanup logic for expired posters
        print("\n[*] Cleaning up old match posters...")
        if os.path.exists(OUTPUT_DIR):
            for file in os.listdir(OUTPUT_DIR):
                if file.endswith('.png') and file not in active_poster_filenames:
                    try:
                        os.remove(os.path.join(OUTPUT_DIR, file))
                        print(f"   [-] Deleted old poster: posters/{file}")
                    except Exception as e:
                        print(f"   [!] Error deleting {file}: {e}")
                        
        if not active_poster_filenames:
            print("\n[-] No matches within the specified time window found.")

    except Exception as e:
        print(f"\n[!] Critical Error: {e}")

if __name__ == "__main__":
    main()
