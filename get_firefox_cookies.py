import os
import shutil
import sqlite3
import tempfile
import configparser
import glob

def find_all_cookie_dbs():
    """Finds all cookies.sqlite files in Firefox profiles."""
    appdata = os.getenv('APPDATA')
    if not appdata:
        return []
    
    base_path = os.path.join(appdata, 'Mozilla', 'Firefox', 'Profiles')
    if not os.path.exists(base_path):
        return []

    # search recursively or just in immediate subdirs
    # usually Profiles/<random_string>.default-release/cookies.sqlite
    return glob.glob(os.path.join(base_path, "*", "cookies.sqlite"))

def extract_from_db(db_path, output_file="cookies.txt"):
    """Tries to extract X cookies from a specific DB."""
    if not os.path.exists(db_path):
        return 0

    # Copy to temp
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_db = tmp.name
    
    rows = []
    try:
        shutil.copy2(db_path, tmp_db)
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()
        
        query = "SELECT host, path, isSecure, expiry, name, value FROM moz_cookies WHERE host LIKE '%x.com' OR host LIKE '%twitter.com'"
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"[DEBUG] Error reading {db_path}: {e}")
        return 0
    finally:
        if os.path.exists(tmp_db):
            os.remove(tmp_db)

    if not rows:
        return 0

    # Write to file if we found cookies
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Netscape HTTP Cookie File\n")
        f.write("# This is a generated file!  Do not edit.\n\n")
        
        for row in rows:
            host, path, is_secure, expiry, name, value = row
            domain_flag = "TRUE" if host.startswith('.') else "FALSE"
            secure_flag = "TRUE" if is_secure else "FALSE"
            f.write(f"{host}\t{domain_flag}\t{path}\t{secure_flag}\t{expiry}\t{name}\t{value}\n")
    
    return len(rows)

def main():
    print("Scanning for Firefox profiles...")
    dbs = find_all_cookie_dbs()
    
    if not dbs:
        print("[ERROR] No Firefox profiles with cookies.sqlite found.")
        return

    print(f"[INFO] Found {len(dbs)} potential profile(s). Checking for X/Twitter cookies...")

    found = False
    for db in dbs:
        print(f" - Checking: {db}")
        count = extract_from_db(db)
        if count > 0:
            print(f"[SUCCESS] Found {count} X cookies! Saved to 'cookies.txt'.")
            found = True
            break
    
    if not found:
        print("[WARN] Scanned all profiles but found no cookies for x.com or twitter.com.")
        print("Please ensure you are logged into X on Firefox.")

if __name__ == "__main__":
    main()

