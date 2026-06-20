import os
import urllib.request

def download_file(url, filepath):
    print(f"Downloading {url} to {filepath}...")
    try:
        # User-Agent to avoid getting blocked by some CDN rules
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req) as response:
            with open(filepath, 'wb') as out_file:
                out_file.write(response.read())
        print("Success.")
    except Exception as e:
        print(f"Error downloading {url}: {e}")

def main():
    js_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "js")
    os.makedirs(js_dir, exist_ok=True)
    
    urls = {
        "tailwind.min.js": "https://cdn.tailwindcss.com",
        "react.production.min.js": "https://unpkg.com/react@18/umd/react.production.min.js",
        "react-dom.production.min.js": "https://unpkg.com/react-dom@18/umd/react-dom.production.min.js",
        "babel.min.js": "https://unpkg.com/@babel/standalone@7.23.5/babel.min.js"
    }
    
    for filename, url in urls.items():
        dest = os.path.join(js_dir, filename)
        download_file(url, dest)

if __name__ == "__main__":
    main()
