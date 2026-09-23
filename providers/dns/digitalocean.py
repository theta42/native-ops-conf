#!/usr/bin/env python3
"""
DigitalOcean DNS Provider Plugin for native-ops
Implements the native-ops DNS plugin contract: sync, list, delete.
"""
import sys
import os
import json
import urllib.request
import urllib.error

DO_API_BASE = "https://api.digitalocean.com/v2"

def get_token():
    token = os.environ.get("DO_API_TOKEN")
    if not token:
        sys.stderr.write("Error: DO_API_TOKEN environment variable is required\n")
        sys.exit(1)
    return token

def do_request(method, path, data=None):
    token = get_token()
    url = f"{DO_API_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            resp_body = resp.read().decode("utf-8")
            return json.loads(resp_body) if resp_body else {}
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        sys.stderr.write(f"DO API error ({e.code}): {err_msg}\n")
        sys.exit(1)

def list_records(domain):
    res = do_request("GET", f"/domains/{domain}/records?per_page=200")
    records = []
    for r in res.get("domain_records", []):
        records.append({
            "id": str(r.get("id")),
            "type": r.get("type"),
            "name": r.get("name"),
            "value": r.get("data"),
            "ttl": r.get("ttl", 1800)
        })
    return records

def sync_records(domain, desired_records):
    existing = list_records(domain)
    existing_map = {f"{r['type']}:{r['name']}": r for r in existing}

    for d in desired_records:
        key = f"{d['type']}:{d['name']}"
        curr = existing_map.get(key)
        if curr:
            if curr["value"] != d["value"]:
                do_request("PUT", f"/domains/{domain}/records/{curr['id']}", {"data": d["value"]})
        else:
            payload = {
                "type": d["type"],
                "name": d["name"],
                "data": d["value"],
                "ttl": d.get("ttl", 1800)
            }
            do_request("POST", f"/domains/{domain}/records", payload)

def main():
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: digitalocean.py [sync|list|delete] --domain <domain>\n")
        sys.exit(1)

    action = sys.argv[1]
    domain = None
    for i in range(2, len(sys.argv)):
        if sys.argv[i] == "--domain" and i + 1 < len(sys.argv):
            domain = sys.argv[i + 1]

    if not domain:
        sys.stderr.write("Error: --domain is required\n")
        sys.exit(1)

    if action == "list":
        records = list_records(domain)
        print(json.dumps(records, indent=2))
    elif action == "sync":
        stdin_data = sys.stdin.read()
        payload = json.loads(stdin_data) if stdin_data.strip() else {}
        records = payload.get("records", [])
        sync_records(domain, records)
        print(json.dumps({"status": "ok", "synced": len(records)}))

if __name__ == "__main__":
    main()
