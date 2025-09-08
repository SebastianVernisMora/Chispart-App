#!/usr/bin/env python3
import argparse
import json
import os
import sys

def read_file(path):
    if os.path.exists(path) and os.path.isfile(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {"status": "success", "content": content}
        except Exception as e:
            return {"status": "error", "message": f"Error reading file: {e}"}
    else:
        return {"status": "error", "message": "File not found or not a file"}

def read_directory(path):
    if not os.path.exists(path):
        return {"status": "error", "message": "Directory not found"}
    if not os.path.isdir(path):
        return {"status": "error", "message": "The given path is not a directory"}
    files_content = {}
    for root, _, files in os.walk(path):
        for file in files:
            filepath = os.path.join(root, file)
            rel_path = os.path.relpath(filepath, path)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                files_content[rel_path] = content
            except Exception as e:
                files_content[rel_path] = f"Error reading file: {e}"
    return {"status": "success", "files": files_content}

def main():
    parser = argparse.ArgumentParser(description="JSON file & directory reader tool.")
    parser.add_argument('--json', type=str, help="JSON input string", default=None)
    args = parser.parse_args()
    
    json_input = args.json
    if json_input is None:
        print("Ingresa el JSON:")
        json_input = sys.stdin.read()
    
    try:
        request = json.loads(json_input)
    except Exception:
        print(json.dumps({"status": "error", "message": "Invalid JSON"}))
        sys.exit(1)

    action = request.get("action")
    if action == "read_file":
        path = request.get("path")
        if not path:
            print(json.dumps({"status": "error", "message": "Missing file path"}))
            sys.exit(1)
        response = read_file(path)
        print(json.dumps(response))
    elif action == "read_directory":
        dir_path = request.get("path")
        if not dir_path:
            print(json.dumps({"status": "error", "message": "Missing directory path"}))
            sys.exit(1)
        response = read_directory(dir_path)
        print(json.dumps(response))
    else:
        print(json.dumps({"status": "error", "message": "Unsupported action"}))

if __name__ == "__main__":
    main()
