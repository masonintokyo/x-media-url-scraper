# X (Twitter) Video URL Scraper

A simple tool to scrape all video post URLs from a specific X user's specific media tab.  
The output is a text file (`urls.txt`) compatible with [yt-dlp](https://github.com/yt-dlp/yt-dlp) for batch downloading.

## Features
- **Browser Automation**: Uses Selenium to scroll through the infinite timeline.
- **Login Support**: Bypasses login walls using cookies extracted from your local browser (Chrome, Edge, or Firefox).
- **Format**: Outputs strictly clean URLs (e.g., `https://x.com/user/status/12345`).

---

## 🚀 Usage (For Users)

If you have the executable files (`.exe`), follow these steps:

### 1. Get Cookies
X requires you to be logged in to view media timelines efficiently.
1. Ensure you are logged into **X.com** on Chrome, Edge, or Firefox.
2. Run `get_cookies.exe`.
3. Select your browser from the menu.
4. A file named `cookies.txt` will be created in the same folder.

### 2. Run Scraper
1. Run `x_video_scraper.exe`.
2. Enter the **X Username** target (e.g., `elonmusk` for `@elonmusk`).
   - *(Optional) You can also run it via command line: `x_video_scraper.exe username`*
3. The tool will launch a browser, scroll through the Media tab, and collect links.
4. When finished (or stopped with `Ctrl+C`), a file named `urls.txt` is saved.

### 3. Download Videos
Use `yt-dlp` to download the videos found:
```bash
yt-dlp -a urls.txt
```

---

## 🛠 Usage (For Developers)

### Requirements
- Python 3.10+
- Google Chrome installed

### Installation
1. Clone this repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Scripts
**1. Extract Cookies**
```bash
python get_cookies.py
```

**2. Scrape URLs**
```bash
python scraper.py <username>
```

### Building Executables
To create standalone `.exe` files, use PyInstaller:
```bash
# Build Cookie Extractor
python -m PyInstaller --onefile --name=get_cookies get_cookies.py

# Build Scraper
python -m PyInstaller --onefile --name=x_video_scraper scraper.py
```
The executables will appear in the `dist/` folder.

## Troubleshooting
- **"Login failed"**: Make sure you extracted cookies from a browser where you are *currently* logged into X.
- **Chrome Cookies Fails**: Ensure you completely close Chrome before running the cookie extractor (database locking issue).
- **0 Videos Found**: X's layout changes frequently. If the tool breaks, check the selectors in `scraper.py`.

## License
MIT
