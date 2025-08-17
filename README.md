# Data Analyst Agent

This is a FastAPI-based data analyst agent that can process data files (CSV, XLSX, PDF, TXT) and answer questions dynamically. It can also generate charts and outputs in various formats.

---

## Features

- Accepts POST requests with a `questions.txt` file and optional data files.
- Supports common Python data libraries (pandas, matplotlib, seaborn, scipy, etc.).
- Generates structured JSON responses with tables, charts (as base64), or text answers.

---

## Deployment

The app is deployed on **Render**:

**Primary URL:** [https://data-analyst-agent-m7q3.onrender.com](https://data-analyst-agent-m7q3.onrender.com)

### Run locally

```bash
# Clone repo
git clone <repo_url>
cd DATA_ANALYST_AGENT

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server
uvicorn app:app --host 0.0.0.0 --port 8000
'''
---

## requirements
fastapi
uvicorn
pandas
numpy
matplotlib
seaborn
scipy
python-multipart
python-dotenv
requests
beautifulsoup4
