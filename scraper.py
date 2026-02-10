import os
import requests
import re
import json
import time

def process_links():
    final_list = []
    
    # 1. මූලික දත්ත කියවීම (link.json සහ GitHub Secret)
    try:
        # link.json ගොනුව කියවීම
        with open('link.json', 'r') as f:
            channels = json.load(f)
        
        # GitHub Secret එකෙන් Hash එක ලබා ගැනීම
        hash_code = os.environ.get('SECRET_HASH')
        
        if not hash_code:
            print("Error: SECRET_HASH හමුවුණේ නැත. කරුණාකර GitHub Secrets පරීක්ෂා කරන්න.")
            return
            
    except Exception as e:
        print(f"ගොනු කියවීමේ දෝෂයකි: {e}")
        return

    headers = {'User-Agent': 'Mozilla/5.0'}

    # 2. එක් එක් චැනලය සඳහා දත්ත රැස් කිරීම
    for channel in channels:
        try:
            site_url = channel.get('SiteUrl')
            if not site_url:
                continue
                
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
                    # ලැබුණු දත්ත වෙන් කරගැනීම
                    parts = decrypted_str.split('!')
                    if len(parts) >= 3:
                        kid = parts[0]
                        key = parts[1]
                        extracted_url = parts[2]

                        # --- ලින්ක් එකේ වර්ගය අනුව Structure එක තීරණය කිරීම ---
                        
                        # .m3u8 පවතී නම් (Non-DRM)
                        if ".m3u8" in extracted_url:
                            entry = {
                                "id": channel.get('id'),
                                "name": channel.get('name'),
                                "logo": channel.get('logo'),
                                "streamUrl": extracted_url,
                                "quality": channel.get('quality')
                            }
                        
                        # MPD පවතී නම් (DRM සහිත)
                        else:
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
            
            # පද්ධතියට විවේකයක් ලබා දීම
            time.sleep(1)

        except Exception as e:
            print(f"Error on {channel.get('id')}: {e}")

    # 3. අවසාන ප්‍රතිඵලය "channels" යටතේ ගබඩා කිරීම
    output_data = {
        "channels": final_list
    }

    # final.json ගොනුවට ලිවීම
    with open('final.json', 'w') as f:
        json.dump(output_data, f, indent=4)
    
    print(f"සාර්ථකයි! චැනල් {len(final_list)} ක් final.json වෙත එක් කරන ලදී.")

if __name__ == "__main__":
    process_links()
