# skills/scripts/update.py
#!/usr/bin/env python3
"""Skill bridge: update — write a memory fragment."""
import argparse
import sys

import httpx

from server_utils import SERVER_URL, ensure_server_running


def main():
    parser = argparse.ArgumentParser(description="girlfriend-agent memory update")
    parser.add_argument("content", help="Memory content to store")
    parser.add_argument("--type", default="fact",
                        choices=["fact", "preference", "event", "emotion"])
    args = parser.parse_args()

    if not ensure_server_running():
        sys.exit(1)

    resp = httpx.post(f"{SERVER_URL}/memory/update", json={
        "content": args.content,
        "memory_type": args.type,
    }, timeout=10)

    if resp.status_code != 200:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)

    data = resp.json()
    print(f"记忆已写入: {args.content}")
    print(f"类型: {args.type}")
    print(f"ID: {data['chunk_id']}")


if __name__ == "__main__":
    main()