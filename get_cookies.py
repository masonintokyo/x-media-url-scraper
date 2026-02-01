import os
import json
import base64
import sqlite3
import shutil
import tempfile
import argparse
import glob
from datetime import datetime, timedelta

# Try imports for Chrome/Edge decryption
try:
    import win32crypt
    from Cryptodome.Cipher import AES
    HEADLESS_MODE = False
except ImportError:
    HEADLESS_MODE = True

def get_chrome_datetime(chromedate):
    """Return a `datetime` object from a chrome format datetime
    Since `chromedate` is formatted as the number of microseconds since January, 1601"""
    if chromedate != 86400000000 and chromedate:
        try:
            return datetime(1601, 1, 1) + timedelta(microseconds=chromedate)
        except Exception as e:
            return datetime.now()
    else:
        return ""

def get_encryption_key(local_state_path):
    if not os.path.exists(local_state_path):
        return None
    
    with open(local_state_path, "r", encoding="utf-8") as f:
        state = f.read()
        local_state = json.loads(state)

    # Decode the encryption key from Base64
    encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
    # Remove DPAPI 'DPAPI' prefix (first 5 bytes)
    encrypted_key = encrypted_key[5:]
    # Decrypt the key with the Windows DPAPI
    return win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]

def decrypt_data(data, key):
    try:
        # Get the initialization vector
        iv = data[3:15]
        data = data[15:]
        # Generate cipher
        cipher = AES.new(key, AES.MODE_GCM, iv)
        # Decrypt password
        return cipher.decrypt(data)[:-16].decode()
    except:
        try:
            return str(win32crypt.CryptUnprotectData(data, None, None, None, 0)[1])
        except:
            return ""

def extract_chromium_cookies(browser_name, user_data_path, output_file="cookies.txt"):
    """Extracts cookies from Chromium-based browsers (Chrome/Edge)."""
    
    # Paths usually:
    # Chrome: User Data/Default/Network/Cookies
    # Edge: User Data/Default/Network/Cookies
    # Note: Modern versions keep cookies in "Network/Cookies", older in just "Cookies"
    
    # Find Local State file
    local_state_path = os.path.join(user_data_path, "Local State")
    if not os.path.exists(local_state_path):
        print(f"[ERROR] Could not find {browser_name} Local State file.")
        return False
    
    key = get_encryption_key(local_state_path)
    if not key:
        print(f"[ERROR] Failed to retrieve encryption key for {browser_name}.")
        return False

    # Find Cookies DB
    # Search in Default and Profile X
    possible_paths = [
        os.path.join(user_data_path, "Default", "Network", "Cookies"),
        os.path.join(user_data_path, "Default", "Cookies"),
    ]
    # Scan for other profiles
    profiles = glob.glob(os.path.join(user_data_path, "Profile *"))
    for p in profiles:
        possible_paths.append(os.path.join(p, "Network", "Cookies"))
        possible_paths.append(os.path.join(p, "Cookies"))

    cookie_db = None
    for p in possible_paths:
        if os.path.exists(p):
            cookie_db = p
            break
            
    if not cookie_db:
        print(f"[ERROR] Could not find {browser_name} cookies database.")
        print(f"Searched in: {user_data_path}")
        return False

    print(f"[INFO] Reading cookies from: {cookie_db}")

    # Copy extraction logic
    filename = os.path.join(tempfile.gettempdir(), f"{browser_name}_Cookies.db")
    try:
        shutil.copyfile(cookie_db, filename)
    except PermissionError:
        print(f"[ERROR] Could not read cookie DB. Please CLOSE {browser_name} and try again.")
        return False

    db = sqlite3.connect(filename)
    cursor = db.cursor()
    
    query = "SELECT host_key, name, value, path, is_secure, expires_utc, encrypted_value FROM cookies WHERE host_key LIKE '%x.com' OR host_key LIKE '%twitter.com'"
    
    try:
        cursor.execute(query)
    except sqlite3.OperationalError:
        # Schema might differ
        print("[ERROR] Database schema mismatch. This script supports standard Chrome/Edge schemas.")
        return False

    cookies_found = 0
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# Netscape HTTP Cookie File\n")
        f.write("# This is a generated file!  Do not edit.\n\n")
        
        for host_key, name, value, path, is_secure, expires_utc, encrypted_value in cursor.fetchall():
            if not value:
                decrypted_value = decrypt_data(encrypted_value, key)
            else:
                decrypted_value = value
            
            # Convert timestamp
            # expires_utc is microseconds since 1601
            # Netscape format needs seconds since 1970 (Unix)
            # 11644473600 seconds difference
            expire_unix = 0
            if expires_utc > 0:
                 expire_seconds = expires_utc / 1000000
                 expire_unix = int(expire_seconds - 11644473600)
                 if expire_unix < 0: expire_unix = 0

            flag = "TRUE" if host_key.startswith('.') else "FALSE"
            secure = "TRUE" if is_secure else "FALSE"
            
            f.write(f"{host_key}\t{flag}\t{path}\t{secure}\t{expire_unix}\t{name}\t{decrypted_value}\n")
            cookies_found += 1

    db.close()
    try:
        os.remove(filename)
    except:
        pass

    if cookies_found > 0:
        print(f"[SUCCESS] Extracted {cookies_found} cookies from {browser_name}.")
        return True
    else:
        print(f"[WARN] No X.com cookies found in {browser_name}.")
        return False

def find_all_firefox_cookie_dbs(appdata):
    base_path = os.path.join(appdata, 'Mozilla', 'Firefox', 'Profiles')
    if not os.path.exists(base_path):
        return []
    return glob.glob(os.path.join(base_path, "*", "cookies.sqlite"))

def extract_firefox_cookies(output_file="cookies.txt"):
    appdata = os.getenv('APPDATA')
    if not appdata:
        print("[ERROR] Cannot find APPDATA.")
        return False

    dbs = find_all_firefox_cookie_dbs(appdata)
    if not dbs:
        print("[ERROR] No Firefox profiles found.")
        return False

    print(f"[INFO] Found {len(dbs)} Firefox profiles.")
    
    total_cookies = 0
    # We will append to file, but we should start fresh first
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Netscape HTTP Cookie File\n")
        f.write("# Generated from Firefox\n\n")

    for db_path in dbs:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_db = tmp.name
        
        try:
            shutil.copy2(db_path, tmp_db)
            conn = sqlite3.connect(tmp_db)
            cursor = conn.cursor()
            
            query = "SELECT host, path, isSecure, expiry, name, value FROM moz_cookies WHERE host LIKE '%x.com' OR host LIKE '%twitter.com'"
            cursor.execute(query)
            rows = cursor.fetchall()
            
            if rows:
                with open(output_file, 'a', encoding='utf-8') as f:
                    for row in rows:
                        host, path, is_secure, expiry, name, value = row
                        domain_flag = "TRUE" if host.startswith('.') else "FALSE"
                        secure_flag = "TRUE" if is_secure else "FALSE"
                        f.write(f"{host}\t{domain_flag}\t{path}\t{secure_flag}\t{expiry}\t{name}\t{value}\n")
                total_cookies += len(rows)
            conn.close()
        except Exception:
            pass
        finally:
            if os.path.exists(tmp_db):
                os.remove(tmp_db)

    if total_cookies > 0:
        print(f"[SUCCESS] Extracted {total_cookies} cookies from Firefox.")
        return True
    else:
        print("[WARN] No X cookies found in any Firefox profile.")
        return False

def main():
    print("====================================")
    print("      Browser Cookie Extractor      ")
    print("====================================")
    print("Please select which browser you are logged into X (Twitter) with:")
    print("1. Google Chrome")
    print("2. Mozilla Firefox")
    print("3. Microsoft Edge")
    print("0. Exit")
    
    choice = input("\nEnter number (1-3): ").strip()
    
    appdata = os.getenv('LOCALAPPDATA')
    roaming = os.getenv('APPDATA')
    
    if choice == '1':
        path = os.path.join(appdata, "Google", "Chrome", "User Data")
        if extract_chromium_cookies("Chrome", path):
            print("\nDone! 'cookies.txt' has been created.")
    
    elif choice == '2':
        if extract_firefox_cookies():
            print("\nDone! 'cookies.txt' has been created.")
            
    elif choice == '3':
        path = os.path.join(appdata, "Microsoft", "Edge", "User Data")
        if extract_chromium_cookies("Edge", path):
            print("\nDone! 'cookies.txt' has been created.")
            
    elif choice == '0':
        print("Exiting.")
    else:
        print("Invalid choice.")
        
    input("\nPress Enter to close window...")

if __name__ == "__main__":
    if HEADLESS_MODE:
        print("[ERROR] Required libraries (pywin32, pycryptodomex) missing.")
        print("Please run: pip install pywin32 pycryptodomex")
        input()
    else:
        main()
