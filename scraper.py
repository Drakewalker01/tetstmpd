import os
import requests
import re
import json
import time
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

def process_links():
    final_list = []
    
    # Session එකක් සාදා Retry logic එකතු කිරීම
    session = requests.Session()
    retry_strategy = Retry(
        total=3, # තුන් පාරක් try කරයි
        backoff_factor=1, # උත්සාහයන් අතර කාලය
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    try:
        with open('link.json', 'r', encoding='utf-8') as f:
            channels = json.load(f)
        
        hash_code = os.environ.get('SECRET_HASH')
        if not hash_code:
            print("Error: SECRET_HASH හමුවුණේ නැත.")
            return
            
    except Exception as e:
        print(f"ගොනු කියවීමේ දෝෂයකි: {e}")
        return

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://google.com'
    }

    for channel in channels:
        try:
            site_url = channel.get('SiteUrl')
            if not site_url: continue
                
            print(f"Processing: {channel.get('name')}")
            
            # Timeout එක තත්පර 20ක් දක්වා වැඩි කර ඇත
            res = session.get(site_url, headers=headers, timeout=20)
            res.raise_for_status()

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
                        kid_list = [k.strip() for k in parts[0].split(',')]
                        key_list = [k.strip() for k in parts[1].split(',')]
                        extracted_url = parts[2]
                        clearkeys_map = dict(zip(kid_list, key_list))

                        if ".m3u8" in extracted_url:
                            entry = {
                                "id": channel.get('id'),
                                "name": channel.get('name'),
                                "logo": channel.get('logo'),
                                "streamUrl": extracted_url,
                                "quality": channel.get('quality')
                            }
                        else:
                            entry = {
                                "id": channel.get('id'),
                                "name": channel.get('name'),
                                "logo": channel.get('logo'),
                                "mpdUrl": extracted_url,
                                "quality": channel.get('quality'),
                                "drm": { "clearKeys": clearkeys_map }
                            }
                        final_list.append(entry)
                        print(f"✅ Success: {channel.get('name')}")
            
            time.sleep(2) # සයිට් එකට බරක් නොවීමට

        except Exception as e:
            print(f"❌ Error on {channel.get('id')}: {e}")

    output_data = {"channels": final_list}
    with open('final.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)
    
    print(f"\nසාර්ථකයි! චැනල් {len(final_list)} ක් final.json වෙත එක් කරන ලදී.")

if __name__ == "__main__":
    process_links()
