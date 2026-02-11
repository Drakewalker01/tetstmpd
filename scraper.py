import os
import requests
import re
import json
import time

def process_links():
    final_list = []
    
    try:
        with open('link.json', 'r', encoding='utf-8') as f:
            channels = json.load(f)
        
        hash_code = os.environ.get('SECRET_HASH')
        if not hash_code:
            print("Error: SECRET_HASH missing.")
            return
            
    except Exception as e:
        print(f"Error reading files: {e}")
        return

    headers = {'User-Agent': 'Mozilla/5.0'}

    for channel in channels:
        try:
            site_url = channel.get('SiteUrl')
            if not site_url: continue
                
            print(f"Processing: {channel.get('name')}")
            res = requests.get(site_url, headers=headers, timeout=15)

            # ඕනෑම variable නමකින් එන දත්ත හඳුනාගැනීම
            match = re.search(r'(?:const|var|let)\s+(?:hi|encryptedData|scrapedData)\s*=\s*["\'](.*?)["\']', res.text)
            
            if match:
                scraped_code = match.group(1)
                vercel_url = f"https://e-rho-ivory.vercel.app/get?url={scraped_code}&key={hash_code}"
                api_res = requests.get(vercel_url, headers=headers, timeout=15)
                decrypted_str = api_res.json().get('decrypted', '')

                if decrypted_str:
                    parts = decrypted_str.split('!')
                    if len(parts) >= 3:
                        raw_kids = parts[0]
                        raw_keys = parts[1]
                        extracted_url = parts[2]

                        # --- බහුවිධ Keys (Multiple Keys) වෙන් කිරීමේ කොටස ---
                        # කොමා වලින් වෙන් කර ඇති KID සහ Key ලැයිස්තු සකස් කිරීම
                        kid_list = [k.strip() for k in raw_kids.split(',')]
                        key_list = [k.strip() for k in raw_keys.split(',')]
                        
                        # KID සහ Key එකිනෙකට ගැලපීම (Dictionary එකක් සෑදීම)
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
                                "drm": {
                                    "clearKeys": clearkeys_map # මෙතන දැන් ලස්සනට map වෙලා තියෙන්නේ
                                }
                            }
                        
                        final_list.append(entry)
            
            time.sleep(1)

        except Exception as e:
            print(f"Error on {channel.get('id')}: {e}")

    output_data = {"channels": final_list}
    with open('final.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)
    
    print(f"සාර්ථකයි! චැනල් {len(final_list)} ක් එක් කරන ලදී.")

if __name__ == "__main__":
    process_links()
