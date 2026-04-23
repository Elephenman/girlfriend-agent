# skills/scripts/evolve.py
#!/usr/bin/env python3
"""Skill bridge: evolve — run evolution cycle."""
import os
import sys

# Ensure the script's directory is on the path for server_utils imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx

from server_utils import SERVER_URL, ensure_server_running


def main():
    if not ensure_server_running():
        sys.exit(1)

    resp = httpx.post(f"{SERVER_URL}/evolve", timeout=30)

    if resp.status_code != 200:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)

    data = resp.json()
    print(f"进化触发: {data['trigger']}")
    print(f"观察: {data['observation']}")
    print(f"当前等级: Lv{data['level']}")
    print(f"亲密度: {data['intimacy']}")
    if data["adjustments"]:
        print()
        print("=== 人格微调 ===")
        for dim, delta in data["adjustments"].items():
            direction = "↑" if delta > 0 else "↓"
            print(f"  {dim:15s} {direction} {abs(delta):.4f}")


if __name__ == "__main__":
    main()