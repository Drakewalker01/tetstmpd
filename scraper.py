import requests
import re
import json
import time

def process_links():
    final_list = []
    try:
        # link.json සහ hash.json කියවීම
        with open('link.json', 'r') as f:
            channels = json.load(f)
        with open('hash.json', 'r') as f:
            hash_code = json.load(f).get('hash')
    except Exception as e:
        print(f"ගොනු කියවීමේ දෝෂයකි: {e}")
        return

    headers = {'User-Agent': 'Mozilla/5.0'}

    for channel in channels:
        try:
            site_url = channel.get('SiteUrl')
            print(f"Processing: {channel.get('name')}")

            # වෙබ් පිටුවෙන් "hi" කේතය සෙවීම
            res = requests.get(site_url, headers=headers, timeout=10)
            hi_match = re.search(r'const hi\s*=\s*"(.*?)";', res.text)
            
            if hi_match:
                scraped_code = hi_match.group(1)
                # Vercel API එකට දත්ත යැවීම
                vercel_url = f"https://e-rho-ivory.vercel.app/get?url={scraped_code}&key={hash_code}"
                
                api_res = requests.get(vercel_url, headers=headers, timeout=15)
                decrypted_str = api_res.json().get('decrypted', '')

                if decrypted_str:
                    # String එක කෑලි වලට වෙන් කිරීම
                    parts = decrypted_str.split('!')
                    if len(parts) >= 3:
                        kid = parts[0]
                        key = parts[1]
                        extracted_url = parts[2]

                        # --- Structure එක තීරණය කිරීම ---
                        if ".m3u8" in extracted_url:
                            # Non-DRM (M3U8) Structure
                            entry = {
                                "id": channel.get('id'),
                                "name": channel.get('name'),
                                "logo": channel.get('logo'),
                                "streamUrl": extracted_url,
                                "quality": channel.get('quality')
                            }
                        else:
                            # DRM (MPD) Structure
                            entry = {
                                "id": channel.get('id'),
                                "name": channel.get('name'),
                                "logo": channel.get('logo'),
                                "mpdUrl": extracted_url,
                                "quality": channel.get('quality'),
                                "drm": {
                                    "clearKeys": { kid: key }
                                }
                            }
                        final_list.append(entry)
            
            time.sleep(1) # Server එකට විවේකයක්

        except Exception as e:
            print(f"Error on {channel.get('id')}: {e}")

    # අවසාන ප්‍රතිඵලය "channels" කියන key එක යටතේ ගබඩා කිරීම
    output_data = {
        "channels": final_list
    }

    with open('final.json', 'w') as f:
        json.dump(output_data, f, indent=4)
    
    print("final.json සාර්ථකව update කරන ලදී!")

if __name__ == "__main__":
    process_links()
