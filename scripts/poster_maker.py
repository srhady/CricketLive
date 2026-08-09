import requests
import re
import os
import time
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

print("="*75)
print(" 🏏 CRICKETLIVE: 1080x810 AUTO-CROP GIANT LOGO STUDIO 🏏")
print(" 🌐 Source: Cricbuzz API (Upcoming, Live & Recent) 🌐")
print(" 🎨 Background: Deep Navy Studio (#0F172A) + Large Circular Telegram Watermark 🎨")
print("="*75)

# Navigate out of the 'scripts' folder to the root directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "posters")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Watermark credentials
TELEGRAM_LOGO_URL = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSaSPdPPY4GyA1xREeBCQ7DKXRd-zzddux-SB7CgBQkOg&s=10"
WATERMARK_TEXT = "@SRHady12"

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

def fetch_telegram_icon_circular():
    """Fetches, makes circular, and resizes the Telegram icon for watermark"""
    try:
        res = requests.get(TELEGRAM_LOGO_URL, timeout=10)
        if res.status_code == 200:
            icon = Image.open(BytesIO(res.content)).convert('RGBA')
            
            # 1. Resize to a square larger than target (to avoid pixelation during mask composition)
            size = (100, 100) # Increased size before mask
            icon_square = icon.resize(size, Image.Resampling.LANCZOS)
            
            # 2. Create circular mask
            mask = Image.new('L', size, 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, size[0], size[1]), fill=255)
            
            # 3. Apply mask using composite
            circular_icon = Image.composite(icon_square, Image.new('RGBA', size, (0, 0, 0, 0)), mask)
            
            # 4. Final resize to fit the large font size
            final_size = (36, 36) # Increased size to match 40-size font height
            circular_icon = circular_icon.resize(final_size, Image.Resampling.LANCZOS)
            return circular_icon
    except Exception as e:
        print(f"    [!] Failed to download Telegram icon: {e}")
    return None

def create_max_logo_poster(match_name, logo1_url, logo2_url, local_path, tg_icon):
    """Creates a 1080x810 poster with team logos, custom background, and watermark"""
    try:
        print(f"    [*] Generating PNG for: {match_name}...")
        
        # Download team logos
        res1 = requests.get(logo1_url, timeout=10)
        res2 = requests.get(logo2_url, timeout=10)
        
        if res1.status_code != 200 or res2.status_code != 200:
            print("    [!] Logo download failed. Skipping...")
            return
            
        img1 = Image.open(BytesIO(res1.content)).convert('RGBA')
        img2 = Image.open(BytesIO(res2.content)).convert('RGBA')
        
        # Solid Deep Navy Blue Studio Background (#0F172A)
        canvas = Image.new('RGBA', (1080, 810), (15, 23, 42, 255))
        
        # Auto-crop and resize team logos
        img1 = auto_crop_and_resize(img1, 480, 600)
        img2 = auto_crop_and_resize(img2, 480, 600)
        
        # Position calculation for team logos
        x1 = 270 - (img1.width // 2)
        y1 = 405 - (img1.height // 2)
        x2 = 810 - (img2.width // 2)
        y2 = 405 - (img2.height // 2)
        
        canvas.paste(img1, (x1, y1), img1)
        canvas.paste(img2, (x2, y2), img2)
        
        # Draw Watermark in Bottom-Right Corner
        draw = ImageDraw.Draw(canvas)
        
        # --- LARGE FONT ---
        try:
            # Increase font size to 40 for Arial (previous size was 22)
            font = ImageFont.truetype("arial.ttf", 40)
        except:
            # Fallback to default font (size cannot be changed)
            font = ImageFont.load_default()
            
        bbox = draw.textbbox((0, 0), WATERMARK_TEXT, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        padding_right = 30
        padding_bottom = 25
        icon_spacing = 10 # Slightly increased spacing for large watermark
        
        icon_w = tg_icon.width if tg_icon else 0
        icon_h = tg_icon.height if tg_icon else 0
        
        total_watermark_w = icon_w + icon_spacing + text_w
        
        start_x = 1080 - padding_right - total_watermark_w
        start_y = 810 - padding_bottom - max(icon_h, text_h)
        
        # Paste Telegram icon
        if tg_icon:
            icon_y = start_y + (max(icon_h, text_h) - icon_h) // 2
            # Pastel circular icon
            canvas.paste(tg_icon, (int(start_x), int(icon_y)), tg_icon)
            
        # Draw Watermark Text
        text_x = start_x + icon_w + icon_spacing
        text_y = start_y + (max(icon_h, text_h) - text_h) // 2
        draw.text((text_x, text_y), WATERMARK_TEXT, fill=(226, 232, 240, 240), font=font)
        
        # Convert and optimize output
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
        
        # Download Telegram icon once for all posters, make it circular and resize to 36x36
        tg_icon = fetch_telegram_icon_circular()
        
        active_poster_filenames = []
        
        now_ms = int(time.time() * 1000)
        THREE_HOURS_MS = 3 * 60 * 60 * 1000
        ONE_HOUR_MS = 1 * 60 * 60 * 1000
        
        for item in matches:
            match_info = item.get("match", {}).get("matchInfo", {})
            
            start_time = match_info.get("startDate", 0)
            end_time = match_info.get("endDate", start_time + (4 * 60 * 60 * 1000))
            
            is_valid_match = False
            
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
                
                if not os.path.exists(local_path):
                    logo1 = generate_cricbuzz_logo_url(t1_id, t1_name)
                    logo2 = generate_cricbuzz_logo_url(t2_id, t2_name)
                    create_max_logo_poster(match_title, logo1, logo2, local_path, tg_icon)
                else:
                    print(f"    [-] Poster already exists. Skipping generation.")

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
