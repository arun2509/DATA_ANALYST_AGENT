from bs4 import BeautifulSoup
from typing import Dict, Any

def get_relevant_data(file_name: str, js_selector: str = None) -> Dict[str, Any]:
    """
    Extracts relevant data from a local HTML file.

    Args:
        file_name (str): Path to the HTML file.
        js_selector (str): Optional CSS selector to target specific elements.

    Returns:
        dict: Extracted text data.
    """
    with open(file_name, encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")

    # ✅ First try: use provided selector
    if js_selector:
        elements = soup.select(js_selector)
        if elements:
            return {"data": [el.get_text(strip=True) for el in elements]}

    # ✅ Fallback 1: Return all tables if selector failed
    tables = soup.find_all("table")
    if tables:
        extracted_tables = []
        for idx, table in enumerate(tables, start=1):
            table_text = table.get_text(separator=" ", strip=True)
            extracted_tables.append(f"Table {idx}: {table_text}")
        return {"data": extracted_tables}

    # ✅ Fallback 2: Return all visible text if no tables found
    return {"data": soup.get_text(separator=" ", strip=True)}
