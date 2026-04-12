import requests
import re
import os
from datetime import datetime, timezone
from io import BytesIO
from PIL import Image

print("="*75)
print(" 🏏 CRICKETLIVE: MAX LOGO & MINI SIZE POSTER STUDIO (UNDER 100KB) 🏏")
print("="*75)

# একদম ফ্রেশ ফোল্ডার: 'posters'
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
        print(f"    [*] Generating HIGH-VIS PNG for: {match_name}...")
        res1 = s.get(logo1_url, timeout=10)
        res2 = s.get(logo2_url, timeout=10)
        
        if res1.status_code != 200 or res2.status_code != 200:
            print("    [!] Logo download failed. URL might be incorrect.")
            return
            
        # ইমেজ ওপেন ও RGBA (ট্রান্সপারেন্ট) মোডে কনভার্ট
        img1 = Image.open(BytesIO(res1.content)).convert('RGBA')
        img2 = Image.open(BytesIO(res2.content)).convert('RGBA')
        
        # === লোগো বড় করার নতুন লজিক (maximize size) ===
        # আমরা চাই লোগো পুরো উচ্চতা দখল করুক। রেজোলিউশন ১০০০ এর কাছাকাছি রাখলে সাইজ কন্ট্রোল করা সোজা।
        target_height = 500  # আগে ছিল ২৫০। এখন লোগো দ্বিগুণ বড় হবে!
        padding_around = 20  # আশেপাশে সামান্য ফাঁকা জায়গা
        middle_gap = 50      # দুই লোগোর মাঝখানের গ্যাপ কমিয়ে দেওয়া হলো
        
        # aspect ratio বজায় রেখে রিসাইজ
        img1_width = int(img1.width * (target_height / img1.height))
        img2_width = int(img2.width * (target_height / img2.height))
        
        img1 = img1.resize((img1_width, target_height), Image.Resampling.LANCZOS)
        img2 = img2.resize((img2_width, target_height), Image.Resampling.LANCZOS)
        
        # ক্যানভাসের সাইজ ক্যালকুলেশন (minimal borders)
        canvas_width = padding_around + img1_width + middle_gap + img2_width + padding_around
        canvas_height = padding_around + target_height + padding_around
        
        # একদম ট্রান্সপারেন্ট ক্যানভাস
        canvas = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))
        
        # লোগো বসানো (পাশাপাশি, minimal space)
        canvas.paste(img1, (padding_around, padding_around), img1)
        canvas.paste(img2, (padding_around + img1_width + middle_gap, padding_around), img2)
        
        # === ১০০ কেবি এর নিচে রাখার ম্যাজিক (PNG Quantization) ===
        # ফাইল সাইজ ড্রামাটিকভাবে কমানোর জন্য RGBA থেকে Indexed color (P mode) এ কনভার্ট
        quantized_canvas = canvas.convert('P', palette=Image.Palette.ADAPTIVE, colors=256)
        
        # সেভ করার সময় অপ্টিমাইজেশন ব্যবহার করা হলো
        quantized_canvas.save(local_path, "PNG", optimize=True)
        file_size_kb = os.path.getsize(local_path) / 1024
        print(f"    [+] Success! Saved to 'posters/{match_name}.png' ({file_size_kb:.1f} KB)")
        
        # ডাবল চেক: যদি তাও ১০০ কেবি এর ওপরে থাকে (খুব রেয়ার), তাহলে রেজোলিউশন কমিয়ে ট্রাই করো।
        if file_size_kb > 100:
             print(f"    [!] Warning: File size ({file_size_kb:.1f} KB) slightly over 100KB, optimizing further...")
             quantized_canvas.save(local_path, "PNG", optimize=True, compress_level=9)
             print(f"    [+] Final size after extra compression: {os.path.getsize(local_path)/1024:.1f} KB")


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
                match_slug = link.split('/')[-1]
                match_title = match_slug.replace('-', ' ').title().replace(" Vs ", " vs ")
                
                safe_name = sanitize_filename(match_title)
                final_filename = f"{safe_name}.png"
                local_path = os.path.join(OUTPUT_DIR, final_filename)
                active_poster_filenames.append(final_filename)
                
                print(f"\n🎯 Processing Match: {match_title}")
                
                # স্লাগ থেকে সরাসরি লোগোর লিংক বানানো
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
