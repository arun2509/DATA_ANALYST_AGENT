#!/usr/bin/env python3
import sys
import json
import subprocess

def main():
    try:

        # Call your FastAPI app with curl
        cmd = [
            "curl", "-s", "-X", "POST", "http://127.0.0.1:8000/",
            "-F", f"questions=@questions.txt",
            "-F", "files=@sample-sales.csv"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(json.dumps({"error": f"curl failed: {result.stderr}"}))
            return

        # Ensure response is always JSON
        try:
            output_json = json.loads(result.stdout)
        except json.JSONDecodeError:
            # Wrap non-JSON responses safely
            output_json = {"output": result.stdout.strip()}

        print(json.dumps(output_json))

    except Exception as e:
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    main()
