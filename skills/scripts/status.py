# skills/scripts/status.py
#!/usr/bin/env python3
"""Skill bridge: status — view relationship status."""
import sys

import httpx

from server_utils import SERVER_URL, ensure_server_running


def main():
    if not ensure_server_running():
        sys.exit(1)

    resp = httpx.get(f"{SERVER_URL}/status", timeout=10)

    if resp.status_code != 200:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)

    data = resp.json()
    print(f"关系等级: Lv{data['current_level']}")
    print(f"亲密度: {data['intimacy_points']}")
    print(f"昵称: {data.get('nickname', '无')}")
    print(f"冲突模式: {'是' if data.get('conflict_mode') else '否'}")
    print()
    print("=== 属性 ===")
    for attr, val in data["attributes"].items():
        bar = "█" * (val // 10) + "░" * (10 - val // 10)
        print(f"  {attr:15s} {bar} {val}")
    print()
    print("=== 去AI味评分 ===")
    for dim, val in data["de_ai_score"].items():
        print(f"  {dim:25s} {val:.2f}")


if __name__ == "__main__":
    main()