# tools/scrape_website.py
import requests

def scrape_website(url: str, out_file: str):
    """
    Download the HTML from a website and save to a file.
    """
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(resp.text)
