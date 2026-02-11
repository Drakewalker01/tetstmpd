import os
import requests
import re
import json
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def check_stream(url, referer_url):
    """ලිංක් එක වැඩ කරනවාද සහ එය සැබෑ stream එකක්දැයි බලයි"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': referer_url
    }
    try:
        # stream=True මගින් මුළු file එකම download නොවී headers පමණක් මුලින් බලයි
        response = requests.get(url, headers=headers, timeout=15, stream=True)
        if response.status_code == 200:
            # මුල් පේළි කිහිපය කියවා බලයි
            content_iter = response.iter_content(chunk_size=512)
            first_chunk = next(content_iter).decode('utf-8', errors='ignore')
            
            # Manifest එකක්දැයි තහවුරු කරගැනීම
            if "#EXTM3U" in first_chunk or "<MPD" in first_chunk:
                return True
        return False
    except:
        return False

def process_links():
    scraped_list = []
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
        print(f"❌ Error reading link.json: {e}")
        return

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

    # --- 1 වන පියවර: Scraping (nocheck.json) ---
    print("🚀 Scraping started...")
    for channel in channels:
        try:
            site_url = channel.get('SiteUrl')
            if not site_url: continue
            
            res = session.get(site_url, headers=headers, timeout=20)
            match = re.search(r'(?:const|var|let)\s+(?:hi|encryptedData|scrapedData)\s*=\s*["\'](.*?)["\']', res.text)
            
            if match:
                scraped_code = match.group(1)
                vercel_url = f"https://e-rho-ivory.vercel.app/get?url={scraped_code}&key={hash_code}"
                api_res = session.get(vercel_url, headers=headers, timeout=20)
                decrypted_str = api_res.json().get('decrypted', '')

                if decrypted_str:
                    parts = decrypted_str.split('!')
                    if len(parts) >= 3:
                        extracted_url = parts[2]
                        entry = {
                            "id": channel.get('id'),
                            "name": channel.get('name'),
                            "logo": channel.get('logo'),
                            "quality": channel.get('quality'),
                            "site_referer": site_url # මේක checker එකට ඕන වෙනවා
                        }
                        
                        if ".m3u8" in extracted_url:
                            entry["streamUrl"] = extracted_url
                        else:
                            entry["mpdUrl"] = extracted_url
                            entry["drm"] = { "clearKeys": dict(zip(parts[0].split(','), parts[1].split(','))) }
                        
                        scraped_list.append(entry)
                        print(f"📡 Scraped: {channel.get('name')}")
            
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ Scraping error on {channel.get('name')}: {e}")

    # nocheck.json සුරැකීම
    with open('nocheck.json', 'w', encoding='utf-8') as f:
        json.dump({"channels": scraped_list}, f, indent=4, ensure_ascii=False)
    print(f"\n📂 nocheck.json saved with {len(scraped_list)} channels.")

    # --- 2 වන පියවර: Validation (final.json) ---
    print("\n🔍 Validating streams...")
    for entry in scraped_list:
        url = entry.get('streamUrl') or entry.get('mpdUrl')
        referer = entry.get('site_referer')
        
        print(f"🧪 Testing: {entry['name']}...")
        if check_stream(url, referer):
            # පිරිසිදු entry එකක් සෑදීම (internal data ඉවත් කර)
            clean_entry = entry.copy()
            if 'site_referer' in clean_entry: del clean_entry['site_referer']
            
            final_list.append(clean_entry)
            print(f"✅ Working: {entry['name']}")
        else:
            print(f"❌ Dead: {entry['name']}")

    # final.json සුරැකීම
    with open('final.json', 'w', encoding='utf-8') as f:
        json.dump({"channels": final_list}, f, indent=4, ensure_ascii=False)
    
    print(f"\n✨ Done! Final list has {len(final_list)} active channels.")

if __name__ == "__main__":
    process_links()
