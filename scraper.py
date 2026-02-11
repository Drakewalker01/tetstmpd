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
        with open('link.json', 'r', encoding='utf-8') as f:
            channels = json.load(f)
        
        # GitHub Secret එකෙන් Hash එක ලබා ගැනීම
        hash_code = os.environ.get('SECRET_HASH')
        
        if not hash_code:
            print("Error: SECRET_HASH හමුවුණේ නැත. කරුණාකර GitHub Secrets පරීක්ෂා කරන්න.")
            return
            
    except FileNotFoundError:
        print("Error: link.json ගොනුව හමුවුණේ නැත.")
        return
    except Exception as e:
        print(f"ගොනු කියවීමේ දෝෂයකි: {e}")
        return

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
    }

    # 2. එක් එක් චැනලය සඳහා දත්ත රැස් කිරීම
    for channel in channels:
        try:
            site_url = channel.get('SiteUrl')
            if not site_url:
                continue
                
            print(f"පරීක්ෂා කරමින් පවතී: {channel.get('name')}...")

            # වෙබ් පිටුව ලබා ගැනීම
            res = requests.get(site_url, headers=headers, timeout=15)
            res.raise_for_status() # HTTP errors පරීක්ෂාව

            # --- යාවත්කාලීන කරන ලද Regex එක ---
            # මෙය const, var, let යන ඕනෑම එකක් සහ hi, encryptedData වැනි ඕනෑම නමක් සොයයි
            # " " හෝ ' ' යන දෙවර්ගයේම quotes හඳුනා ගනී
            pattern = r'(?:const|var|let)\s+(?:hi|encryptedData|scrapedData)\s*=\s*["\'](.*?)["\']'
            match = re.search(pattern, res.text)
            
            if match:
                scraped_code = match.group(1)
                
                # Vercel API එකට දත්ත යැවීම
                vercel_url = f"https://e-rho-ivory.vercel.app/get?url={scraped_code}&key={hash_code}"
                api_res = requests.get(vercel_url, headers=headers, timeout=15)
                api_data = api_res.json()
                
                decrypted_str = api_data.get('decrypted', '')

                if decrypted_str:
                    # ලැබුණු දත්ත වෙන් කරගැනීම (Format: kid!key!url)
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
                        print(f"සාර්ථකයි: {channel.get('name')}")
            else:
                print(f"Warning: {channel.get('name')} සඳහා දත්ත කේතය සොයාගත නොහැකි විය.")
            
            # පද්ධතියට විවේකයක් ලබා දීම (Anti-blocking සඳහා)
            time.sleep(1.5)

        except Exception as e:
            print(f"දෝෂයකි ({channel.get('id')}): {e}")

    # 3. අවසාන ප්‍රතිඵලය "channels" යටතේ ගබඩා කිරීම
    output_data = {
        "channels": final_list
    }

    # final.json ගොනුවට ලිවීම
    try:
        with open('final.json', 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=4, ensure_ascii=False)
        
        print("-" * 30)
        print(f"සියල්ල අවසන්! චැනල් {len(final_list)} ක් final.json වෙත එක් කරන ලදී.")
    except Exception as e:
        print(f"ගොනුව ලිවීමේදී දෝෂයක් ඇති විය: {e}")

if __name__ == "__main__":
    process_links()
