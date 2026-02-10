import requests
import re
import json
import time

def process_links():
    final_results = []
    try:
        with open('link.json', 'r') as f:
            channels = json.load(f)
        with open('hash.json', 'r') as f:
            hash_code = json.load(f).get('hash')
    except Exception as e:
        print(f"File reading error: {e}")
        return

    headers = {'User-Agent': 'Mozilla/5.0'}

    for channel in channels:
        try:
            site_url = channel.get('SiteUrl')
            print(f"Processing: {channel.get('name')}")

            res = requests.get(site_url, headers=headers, timeout=10)
            hi_match = re.search(r'const hi\s*=\s*"(.*?)";', res.text)
            
            if hi_match:
                scraped_code = hi_match.group(1)
                vercel_url = f"https://e-rho-ivory.vercel.app/get?url={scraped_code}&key={hash_code}"
                
                api_res = requests.get(vercel_url, headers=headers, timeout=15)
                decrypted_str = api_res.json().get('decrypted', '')

                if decrypted_str:
                    parts = decrypted_str.split('!')
                    if len(parts) >= 3:
                        final_results.append({
                            "id": channel.get('id'),
                            "name": channel.get('name'),
                            "logo": channel.get('logo'),
                            "mpdUrl": parts[2],
                            "quality": channel.get('quality'),
                            "drm": {
                                "clearKeys": { parts[0]: parts[1] }
                            }
                        })
            time.sleep(1)
        except Exception as e:
            print(f"Error on {channel.get('id')}: {e}")

    with open('final.json', 'w') as f:
        json.dump(final_results, f, indent=4)
    print("final.json updated!")

if __name__ == "__main__":
    process_links()
