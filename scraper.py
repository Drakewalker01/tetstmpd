import os
import requests
import re
import json
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3

# SSL Warnings ඉවත් කිරීමට
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def check_stream(url, referer_url):
    """ලිංක් එක සැබවින්ම වැඩ කරනවාදැයි පරීක්ෂා කරයි"""
    session = requests.Session()
    
    # ඉතාමත් නිවැරදි Browser Headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Referer': referer_url,
        'Origin': re.search(r'https?://[^/]+', referer_url).group(0) if referer_url else 'https://google.com',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }

    try:
        # verify=False යෙදීමෙන් SSL ගැටලු මගහරවා ගනී
        response = session.get(url, headers=headers, timeout=15, stream=True, verify=False, allow_redirects=True)
        
        if response.status_code == 200:
            # මුල් කොටස කියවා බැලීම
            content_iter = response.iter_content(chunk_size=1024)
            chunk = next(content_iter).decode('utf-8', errors='ignore')
            
            # Manifest එකක තිබිය යුතු ප්‍රධාන ලක්ෂණ
            if "#EXTM3U" in chunk or "<MPD" in chunk or "xmlns" in chunk:
                return True
            else:
                print(f"      ⚠️ Data Error: Header 200 වුණත් Manifest එකක් නොවේ (Content: {chunk[:20]}...)")
        else:
            print(f"      ❌ HTTP Error: Status Code {response.status_code}")
            
        return False
    except Exception as e:
        print(f"      ⚠️ Network Error: {str(e)[:50]}")
        return False

def process_links():
    scraped_list = []
    final_list = []
    
    session = requests.Session()
    hash_code = os.environ.get('SECRET_HASH')
    
    try:
        with open('link.json', 'r', encoding='utf-8') as f:
            channels = json.load(f)
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # --- Step 1: Scraping ---
    print("🚀 Scraper ආරම්භ කළා...")
    for channel in channels:
        try:
            site_url = channel.get('SiteUrl')
            res = session.get(site_url, timeout=20, verify=False)
            
            match = re.search(r'(?:const|var|let)\s+(?:hi|encryptedData|scrapedData)\s*=\s*["\'](.*?)["\']', res.text)
            
            if match:
                scraped_code = match.group(1)
                vercel_url = f"https://e-rho-ivory.vercel.app/get?url={scraped_code}&key={hash_code}"
                api_res = session.get(vercel_url, timeout=20, verify=False)
                decrypted_str = api_res.json().get('decrypted', '')

                if decrypted_str:
                    parts = decrypted_str.split('!')
                    extracted_url = parts[2].strip()
                    
                    entry = {
                        "id": channel.get('id'),
                        "name": channel.get('name'),
                        "logo": channel.get('logo'),
                        "quality": channel.get('quality'),
                        "site_referer": site_url
                    }
                    
                    if ".m3u8" in extracted_url:
                        entry["streamUrl"] = extracted_url
                    else:
                        entry["mpdUrl"] = extracted_url
                        entry["drm"] = { "clearKeys": dict(zip(parts[0].split(','), parts[1].split(','))) }
                    
                    scraped_list.append(entry)
                    print(f"📡 Scraped: {channel.get('name')}")
            
            time.sleep(1)
        except:
            continue

    # nocheck.json සුරැකීම
    with open('nocheck.json', 'w', encoding='utf-8') as f:
        json.dump({"channels": scraped_list}, f, indent=4, ensure_ascii=False)

    # --- Step 2: Validation ---
    print("\n🔍 ලිංක් පරීක්ෂා කිරීම (Validation)...")
    for entry in scraped_list:
        url = entry.get('streamUrl') or entry.get('mpdUrl')
        referer = entry.get('site_referer')
        
        print(f"🧪 Testing: {entry['name']}...")
        if check_stream(url, referer):
            clean_entry = {k: v for k, v in entry.items() if k != 'site_referer'}
            final_list.append(clean_entry)
            print(f"   ✅ Working")
        else:
            print(f"   ❌ Failed")

    # final.json සුරැකීම
    with open('final.json', 'w', encoding='utf-8') as f:
        json.dump({"channels": final_list}, f, indent=4, ensure_ascii=False)
    
    print(f"\n✨ අවසන්! වැඩ කරන චැනල් {len(final_list)} ක් ලැබුණා.")

if __name__ == "__main__":
    process_links()
