import os
import requests
import re
import json
import time
import base64
from urllib.parse import unquote
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- 1. Automatic Key Finder Logic ---
def extract_secret_hash(html_content):
    try:
        # Array එක සොයා ගැනීම (_0x488508 වැනි එක)
        array_pattern = r"const _0x[a-f0-9]+=\[((?:'\\x[0-9a-fA-F]{2}',?|'.*?',?)+)\];"
        array_match = re.search(array_pattern, html_content)
        if not array_match: return None
        
        # Array එකේ තියෙන strings ටික list එකකට ගැනීම
        raw_array = array_match.group(1).replace("'", "").split(',')
        
        # Hex strings (\x31...) decode කිරීම
        string_array = []
        for s in raw_array:
            try:
                decoded_s = bytes(s.strip(), "utf-8").decode("unicode_escape")
                string_array.append(decoded_s)
            except: string_array.append(s)

        # Obfuscation එකේ තියෙන Key එකේ Pattern එක අනුව සෙවීම
        # සාමාන්‍යයෙන් මේවා "[pvFH...]" වගේ bracket ඇතුළේ එන strings
        for item in string_array:
            if item.startswith('[') and item.endswith(']') and len(item) > 10:
                return item
        return None
    except Exception as e:
        print(f"⚠️ Key extraction error: {e}")
        return None

# --- 2. XOR Decryption Logic ---
def xor_decrypt(data_base64, key):
    try:
        encrypted_data = base64.b64decode(data_base64)
        decrypted = ""
        for i in range(len(encrypted_data)):
            decrypted += chr(encrypted_data[i] ^ ord(key[i % len(key)]))
        return decrypted
    except: return ""

# --- 3. Main Process ---
def process_links():
    final_list = []
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1)))

    if not os.path.exists('link.json'):
        print("❌ link.json file not found!")
        return

    with open('link.json', 'r', encoding='utf-8') as f:
        channels = json.load(f)

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    for channel in channels:
        site_url = channel.get('SiteUrl')
        if not site_url: continue
        
        print(f"🔍 Processing: {channel.get('name')}")
        try:
            res = session.get(site_url, headers=headers, timeout=20)
            
            # 🔑 මෙතනදී තමයි ඉබේම Secret Hash එක හොයාගන්නේ
            secret_key = extract_secret_hash(res.text)
            
            # Encrypted data එක සොයා ගැනීම
            data_match = re.search(r'encryptedData\s*=\s*["\'](.*?)["\']', res.text)
            
            if secret_key and data_match:
                print(f"✅ Found Key: {secret_key[:10]}...")
                decrypted_str = xor_decrypt(data_match.group(1), secret_key)
                
                if decrypted_str and '!' in decrypted_str:
                    parts = decrypted_str.split('!')
                    if len(parts) >= 3:
                        kids = parts[0].split(',')
                        keys = parts[1].split(',')
                        url = parts[2]
                        
                        entry = {
                            "id": channel.get('id'),
                            "name": channel.get('name'),
                            "logo": channel.get('logo'),
                            "quality": channel.get('quality'),
                            "mpdUrl": url,
                            "drm": { "clearKeys": dict(zip(kids, keys)) }
                        }
                        final_list.append(entry)
                        print(f"🚀 Keys extracted successfully!")
            else:
                print(f"❌ Could not find Key or Data for {channel.get('name')}")

        except Exception as e:
            print(f"⚠️ Error: {e}")

    with open('final.json', 'w', encoding='utf-8') as f:
        json.dump({"channels": final_list}, f, indent=4, ensure_ascii=False)
    
    print(f"\n✨ සම්පූර්ණයි! චැනල් {len(final_list)} ක් සූදානම්.")

if __name__ == "__main__":
    process_links()
