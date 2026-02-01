import re

with open("debug_page.html", "r", encoding="utf-8") as f:
    content = f.read()

# Find all occurrences of status links
matches = re.findall(r'<a[^>]*href="[^"]*/status/[^"]*"[^>]*>', content)

print(f"Found {len(matches)} status links.")
for i, m in enumerate(matches[:5]):
    print(f"[{i}] {m}")

# Also check for article tags
articles = re.findall(r'<article', content)
print(f"Found {len(articles)} article tags.")
