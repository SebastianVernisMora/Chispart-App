#!/usr/bin/env python3
import argparse
import json
import os
import sys

def read_file(path):
    if os.path.exists(path) and os.path.isfile(path):
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {"status": "success", "content": content}
    else:
        return {"status": "error", "message": "File not found or not a file"}

def main():
    parser = argparse.ArgumentParser(description="JSON file reader.")
    parser.add_argument('--json', type=str, help="JSON input string", required=True)
    args = parser.parse_args()
    try:
        request = json.loads(args.json)
    except Exception:
        print(json.dumps({"status": "error", "message": "Invalid JSON"}))
        sys.exit(1)

    if request.get("action") == "read_file":
        path = request.get("path")
        if not path:
            print(json.dumps({"status": "error", "message": "Missing file path"}))
            sys.exit(1)
        response = read_file(path)
        print(json.dumps(response))
    else:
        print(json.dumps({"status": "error", "message": "Unsupported action"}))

if __name__ == "__main__":
    main()
