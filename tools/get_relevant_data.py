# tools/get_relevant_data.py
from bs4 import BeautifulSoup
import pandas as pd

def get_relevant_data(html_file: str):
    """
    Parse HTML and return first table (if any) or fallback text snippet.
    """
    with open(html_file, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    try:
        tables = pd.read_html(str(soup))
        return {"data": tables[0] if tables else str(soup.get_text()[:2000])}
    except Exception:
        return {"data": str(soup.get_text()[:2000])}
