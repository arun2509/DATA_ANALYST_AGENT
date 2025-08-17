import os
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any
import pandas as pd

def get_relevant_data(file_name: str, js_selector: str | None = None) -> Dict[str, Any]:
    """Extract text/tables from a local HTML file.
    If a CSS selector is provided, return matching nodes' text.
    Else, try pandas.read_html to extract tables as CSV, else raw tables, else text.
    """
    with open(file_name, encoding="utf-8") as f:
        html = f.read()
    soup = BeautifulSoup(html, "html.parser")

    if js_selector:
        els = soup.select(js_selector)
        if els:
            return {"data": [el.get_text(strip=True) for el in els]}

    # Try parsing HTML tables into CSV strings
    try:
        dfs = pd.read_html(html)
        if dfs:
            return {"data": [df.to_csv(index=False) for df in dfs]}
    except Exception:
        pass

    # Fallback: BeautifulSoup table parsing
    tables = soup.find_all("table")
    if tables:
        out = []
        for i, table in enumerate(tables, 1):
            out.append(f"Table {i}: " + table.get_text(separator=" ", strip=True))
        return {"data": out}

    # Final fallback: all visible text
    return {"data": soup.get_text(separator=" ", strip=True)}