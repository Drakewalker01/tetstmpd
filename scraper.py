import os
import requests
import re
import json
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def check_stream(url, referer_url):
    """ලිංක් එක සැබවින්ම වැඩ කරන Manifest එකක්දැයි පරීක්ෂා කරයි"""
    session = requests.Session()
    # Retry logic එකක් එක් කිරීම
    retries = Retry(total=2, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Referer': referer_url,
        'Origin': re.search(r'https?://[^/]+', referer_url).group(0) if referer_url else None,
        'Accept': '*/*',
        'Connection': 'keep-alive'
    }

    try:
        # stream=True දමා headers පමණක් නොව content එකේ මුල් කොටස පරීක්ෂා කරයි
        # allow_redirects=True මගින් Cloudfront වැනි Redirects හසුකර ගනී
        response = session.get(url, headers=headers, timeout=15, stream=True, allow_redirects=True)
        
        if response.status_code == 200:
            # මුල් chunk එක කියවා එහි අන්තර්ගතය බලයි
            it = response.iter_content(chunk_size=1024)
            first_chunk = next(it).decode('utf-8', errors='ignore').strip()
            
            # M3U8 හෝ MPD දත්ත තිබේදැයි ඉතා නිවැරදිව පරීක්ෂා කිරීම
            is_m3u8 = "#EXTM3U" in first_chunk
            is_mpd = "<MPD" in first_chunk or 'xmlns="urn:mpeg:dash:schema:mpd:2011"' in first_chunk
            
            if is_m3u8 or is_mpd:
                return True
        return False
    except Exception as e:
        print(f"      ⚠️ Check Error: {str(e)[:50]}")
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
        print(f"❌ Error reading link.json: {e}")
        return

    main_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }

    # --- පියවර 1: Scraping ---
    print("🚀 Starting Scraper...")
    for channel in channels:
        try:
            site_url = channel.get('SiteUrl')
            if not site_url: continue
            
            res = session.get(site_url, headers=main_headers, timeout=20)
            # Regex patterns (දැනට ඇති ඒවාම භාවිතා වේ)
            match = re.search(r'(?:const|var|let)\s+(?:hi|encryptedData|scrapedData)\s*=\s*["\'](.*?)["\']', res.text)
            
            if match:
                scraped_code = match.group(1)
                vercel_url = f"https://e-rho-ivory.vercel.app/get?url={scraped_code}&key={hash_code}"
                api_res = session.get(vercel_url, headers=main_headers, timeout=20)
                decrypted_str = api_res.json().get('decrypted', '')

                if decrypted_str:
                    parts = decrypted_str.split('!')
                    if len(parts) >= 3:
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
                            entry["drm"] = { 
                                "clearKeys": dict(zip(parts[0].split(','), parts[1].split(','))) 
                            }
                        
                        scraped_list.append(entry)
                        print(f"📡 Found: {channel.get('name')}")
            
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ Scrape Error on {channel.get('name')}: {e}")

    # nocheck.json සුරැකීම
    with open('nocheck.json', 'w', encoding='utf-8') as f:
        json.dump({"channels": scraped_list}, f, indent=4, ensure_ascii=False)

    # --- පියවර 2: Validation ---
    print("\n🔍 Validating Streams...")
    for entry in scraped_list:
        url = entry.get('streamUrl') or entry.get('mpdUrl')
        referer = entry.get('site_referer')
        
        print(f"🧪 Testing: {entry['name']}...")
        if check_stream(url, referer):
            # පිරිසිදු entry එකක් සාදා final list එකට එකතු කිරීම
            clean_entry = {k: v for k, v in entry.items() if k != 'site_referer'}
            final_list.append(clean_entry)
            print(f"   ✅ Working")
        else:
            print(f"   ❌ Failed / Dead")

    # final.json සුරැකීම
    with open('final.json', 'w', encoding='utf-8') as f:
        json.dump({"channels": final_list}, f, indent=4, ensure_ascii=False)
    
    print(f"\n✨ Done! {len(final_list)} Verified channels saved to final.json.")

if __name__ == "__main__":
    process_links()
