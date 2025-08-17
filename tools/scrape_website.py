import os
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any


def scrape_website(url: str, output_file: str) -> Dict[str, Any]:
    """Fetch a URL and save HTML to output_file."""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(resp.text)
    return {"ok": True, "file": output_file, "size": len(resp.text)}
