import os
import requests
import re
import json
import time
import subprocess
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def check_playability(url):
    """FFmpeg (ffprobe) භාවිතා කර stream එක කියවිය හැකිදැයි තත්පර 10ක් ඇතුළත පරීක්ෂා කරයි"""
    try:
        # ffprobe command: මෙහිදී stream එකේ headers සහ metadata පරීක්ෂා කරයි
        command = [
            'ffprobe', 
            '-v', 'error', 
            '-show_entries', 'format=format_name', 
            '-of', 'default=noprint_wrappers=1:nokey=1', 
            '-timeout', '10000000', # Microseconds (තත්පර 10)
            url
        ]
        # stream එක load කරගත නොහැකි නම් returncode 0 නොවේ
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
        return result.returncode == 0
    except Exception as e:
        print(f"      ⚠️ Playability check error: {e}")
        return False

def process_links():
    final_list = []
    
    # Session සහ Retry Logic
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    # ගොනු කියවීම
    try:
        with open('link.json', 'r', encoding='utf-8') as f:
            channels = json.load(f)
        
        hash_code = os.environ.get('SECRET_HASH')
        if not hash_code:
            print("❌ Error: SECRET_HASH හමුවුණේ නැත.")
            return
    except Exception as e:
        print(f"❌ Error reading files: {e}")
        return

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    for channel in channels:
        try:
            site_url = channel.get('SiteUrl')
            if not site_url: continue
                
            print(f"🔄 Processing: {channel.get('name')}")
            
            res = session.get(site_url, headers=headers, timeout=20)
            res.raise_for_status()

            # Data Scrape කිරීම
            pattern = r'(?:const|var|let)\s+(?:hi|encryptedData|scrapedData)\s*=\s*["\'](.*?)["\']'
            match = re.search(pattern, res.text)
            
            if match:
                scraped_code = match.group(1)
                vercel_url = f"https://e-rho-ivory.vercel.app/get?url={scraped_code}&key={hash_code}"
                
                api_res = session.get(vercel_url, headers=headers, timeout=20)
                decrypted_str = api_res.json().get('decrypted', '')

                if decrypted_str:
                    parts = decrypted_str.split('!')
                    if len(parts) >= 3:
                        extracted_url = parts[2]
                        
                        # 🔥 Playability Checker
                        print(f"   🔍 Checking stream status...")
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
                                kid_list = [k.strip() for k in parts[0].split(',')]
                                key_list = [k.strip() for k in parts[1].split(',')]
                                entry["drm"] = { "clearKeys": dict(zip(kid_list, key_list)) }
                            
                            final_list.append(entry)
                            print(f"   ✅ Success: {channel.get('name')} is working.")
                        else:
                            print(f"   ❌ Skipped: {channel.get('name')} (Stream unplayable)")
            
            time.sleep(1) 

        except Exception as e:
            print(f"   ❌ Error on {channel.get('name')}: {e}")

    # final.json සුරැකීම
    output_data = {"channels": final_list}
    with open('final.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)
    
    print(f"\n✨ සාර්ථකයි! චැනල් {len(final_list)} ක් final.json වෙත එක් කරන ලදී.")

if __name__ == "__main__":
    process_links()
