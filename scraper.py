import os
import requests
import re
import json
import time
import subprocess
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def check_playability(url):
    """FFmpeg (ffprobe) මගින් සැබෑ Video/Audio streams තියෙනවාදැයි පරීක්ෂා කරයි"""
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    
    try:
        # ffprobe එකට headers ලබා දීම වැදගත් (නැත්නම් block වෙන්න පුළුවන්)
        command = [
            'ffprobe', 
            '-v', 'error', 
            '-headers', f'User-Agent: {user_agent}\r\n',
            '-show_entries', 'stream=codec_type', 
            '-of', 'csv=p=0', 
            '-timeout', '15000000', # තත්පර 15ක් දක්වා වැඩි කර ඇත
            url
        ]
        
        # මෙහිදී output එක ලෙස 'video' හෝ 'audio' වැනි වචන ලැබිය යුතුයි
        result = subprocess.run(command, capture_output=True, text=True, timeout=20)
        output = result.stdout.lower()
        
        # අවම වශයෙන් video හෝ audio stream එකක් තිබේදැයි බලයි
        if result.returncode == 0 and ('video' in output or 'audio' in output):
            return True
        return False
    except Exception as e:
        return False

def process_links():
    final_list = []
    session = requests.Session()
    retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry_strategy))

    try:
        with open('link.json', 'r', encoding='utf-8') as f:
            channels = json.load(f)
        hash_code = os.environ.get('SECRET_HASH')
        if not hash_code:
            print("❌ SECRET_HASH missing")
            return
    except Exception as e:
        print(f"❌ File error: {e}")
        return

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

    for channel in channels:
        try:
            site_url = channel.get('SiteUrl')
            if not site_url: continue
            
            print(f"🔄 Processing: {channel.get('name')}")
            res = session.get(site_url, headers=headers, timeout=25)
            
            match = re.search(r'(?:const|var|let)\s+(?:hi|encryptedData|scrapedData)\s*=\s*["\'](.*?)["\']', res.text)
            
            if match:
                scraped_code = match.group(1)
                vercel_url = f"https://e-rho-ivory.vercel.app/get?url={scraped_code}&key={hash_code}"
                api_res = session.get(vercel_url, headers=headers, timeout=25)
                decrypted_str = api_res.json().get('decrypted', '')

                if decrypted_str:
                    parts = decrypted_str.split('!')
                    if len(parts) >= 3:
                        extracted_url = parts[2]
                        
                        # වැඩිදියුණු කළ Checker එක
                        print(f"   🔍 Probing stream: {channel.get('name')}...")
                        if check_playability(extracted_url):
                            entry = {
                                "id": channel.get('id'),
                                "name": channel.get('name'),
                                "logo": channel.get('logo'),
                                "quality": channel.get('quality')
                            }
                            if ".m3u8" in extracted_url:
                                entry["streamUrl"] = extracted_url
                            else:
                                entry["mpdUrl"] = extracted_url
                                entry["drm"] = { 
                                    "clearKeys": dict(zip(parts[0].split(','), parts[1].split(','))) 
                                }
                            
                            final_list.append(entry)
                            print(f"   ✅ Verified: {channel.get('name')}")
                        else:
                            print(f"   ⚠️ Discarded: {channel.get('name')} (No active stream found)")
            
            time.sleep(2) # Server එකට සහනයක් වීමට

        except Exception as e:
            print(f"   ❌ Error: {channel.get('name')} -> {e}")

    with open('final.json', 'w', encoding='utf-8') as f:
        json.dump({"channels": final_list}, f, indent=4, ensure_ascii=False)
    
    print(f"\nDone! {len(final_list)} channels added.")

if __name__ == "__main__":
    process_links()
