import os
import requests
import re
import json
import time
import subprocess
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

def check_playability(url):
    """FFmpeg (ffprobe) මගින් stream එක කියවිය හැකිදැයි බලයි"""
    try:
        # ffprobe command එක: තත්පර 5ක් ඇතුළත stream එක analyze කරයි
        command = [
            'ffprobe', 
            '-v', 'error', 
            '-show_entries', 'format=duration', 
            '-of', 'default=noprint_wrappers=1:nokey=1', 
            '-timeout', '5000000', # 5 seconds
            url
        ]
        # stream එක load කරගන්න බැරි නම් මෙය error එකක් දෙයි
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except Exception:
        return False

def process_links():
    final_list = []
    session = requests.Session()
    # ... (Retry logic කලින් වගේමයි) ...
    retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry_strategy))
    
    # link.json කියවීම සහ SECRET_HASH ලබා ගැනීම
    try:
        with open('link.json', 'r', encoding='utf-8') as f:
            channels = json.load(f)
        hash_code = os.environ.get('SECRET_HASH')
    except Exception as e:
        print(f"Error: {e}")
        return

    headers = {'User-Agent': 'Mozilla/5.0...'} # කලින් තිබූ headers

    for channel in channels:
        try:
            site_url = channel.get('SiteUrl')
            if not site_url: continue
            
            print(f"Checking: {channel.get('name')}")
            res = session.get(site_url, timeout=20)
            
            # Regex එකෙන් data සොයා ගැනීම
            match = re.search(r'(?:const|var|let)\s+(?:hi|encryptedData|scrapedData)\s*=\s*["\'](.*?)["\']', res.text)
            
            if match:
                scraped_code = match.group(1)
                vercel_url = f"https://e-rho-ivory.vercel.app/get?url={scraped_code}&key={hash_code}"
                api_res = session.get(vercel_url, timeout=20)
                decrypted_str = api_res.json().get('decrypted', '')

                if decrypted_str:
                    parts = decrypted_str.split('!')
                    extracted_url = parts[2]
                    
                    # 🔥 මෙන්න මෙතනදී Playability එක Check කරනවා
                    print(f"🎬 Testing stream for {channel.get('name')}...")
                    if check_playability(extracted_url):
                        # Playable නම් පමණක් ලිස්ට් එකට දමයි
                        entry = {
                            "id": channel.get('id'),
                            "name": channel.get('name'),
                            "streamUrl" if ".m3u8" in extracted_url else "mpdUrl": extracted_url,
                            # ... අනිත් data ...
                        }
                        # MPD නම් DRM Keys එක් කිරීම
                        if ".mpd" in extracted_url:
                            kid_list = parts[0].split(',')
                            key_list = parts[1].split(',')
                            entry["drm"] = {"clearKeys": dict(zip(kid_list, key_list))}
                        
                        final_list.append(entry)
                        print(f"✅ Success: {channel.get('name')} is working.")
                    else:
                        print(f"❌ Failed: {channel.get('name')} link is dead or unplayable.")

            time.sleep(1)
        except Exception as e:
            print(f"Error processing {channel.get('name')}: {e}")

    # final.json ලිවීම
    with open('final.json', 'w', encoding='utf-8') as f:
        json.dump({"channels": final_list}, f, indent=4)

if __name__ == "__main__":
    process_links()
